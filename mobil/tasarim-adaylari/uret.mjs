// A44 — üç görsel tasarım adayının ÜRETECİ (durağan maketler).
//   node uret.mjs          → aday-a.html, aday-b.html, aday-c.html, OKU.md
// Bağımlılık yok, ağ yok. Renkler `arayuz3/style.css`'in üç görünümünden
// (koyu · acik · onpanel) BİREBİR; yalnız `onpanel-acik` ve `durdur` burada türetildi.
// Kontrast (WCAG 2.x) burada hesaplanır; 4.5'in altında çift varsa betik HATA ile çıkar.
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const BURASI = dirname(fileURLToPath(import.meta.url));

// ───────────────────────────────────────────────────────────── temalar
const TEMA = {
  koyu: {
    zemin: '#0b0f14', 'zemin-2': '#101821', kart: '#131c25', 'kenar-c': '#1f2b37',
    'kenar-koyu': '#31414f', yazi: '#dee7ef', soluk: '#94a3b3',
    vurgu: '#4cc4e0', 'vurgu-zemin': '#0d2a34', dolgu: '#4cc4e0', 'dolgu-yazi': '#05131a',
    iyi: '#74d99b', 'iyi-zemin': '#0c2a1c',
    volt: '#6ea8fe', amper: '#f2a33c', watt: '#35d39a',
    durdur: '#c62828', 'durdur-yazi': '#ffffff', sema: 'dark',
  },
  acik: {
    zemin: '#f4f5f7', 'zemin-2': '#ffffff', kart: '#ffffff', 'kenar-c': '#dde1e6',
    'kenar-koyu': '#c9cfd6', yazi: '#18202a', soluk: '#5b6775',
    vurgu: '#0b5d67', 'vurgu-zemin': '#e3f1f2', dolgu: '#0b5d67', 'dolgu-yazi': '#ffffff',
    iyi: '#15784f', 'iyi-zemin': '#e4f4ec',
    volt: '#2f63c6', amper: '#a85a06', watt: '#15784f',
    durdur: '#c62828', 'durdur-yazi': '#ffffff', sema: 'light',
  },
  onpanel: {
    zemin: '#16181b', 'zemin-2': '#101214', kart: '#1d2024', 'kenar-c': '#2a2e33',
    'kenar-koyu': '#3a3f45', yazi: '#e4e6e8', soluk: '#9aa1a8',
    vurgu: '#f5a524', 'vurgu-zemin': '#33260f', dolgu: '#f5a524', 'dolgu-yazi': '#1b1203',
    iyi: '#7fd99a', 'iyi-zemin': '#13261b',
    volt: '#8fb6ff', amper: '#ffc46b', watt: '#6fe3a8',
    durdur: '#c2361f', 'durdur-yazi': '#ffffff', sema: 'dark',
  },
  // Panelde "ön panel"in açık hali YOK — burada türetildi: açık gri alüminyum yüz,
  // turuncu DOLGU aynı (#f5a524 + koyu yazı), turuncu METİN koyulaştırıldı.
  'onpanel-acik': {
    zemin: '#eceae6', 'zemin-2': '#dedbd5', kart: '#f7f6f3', 'kenar-c': '#cfcbc3',
    'kenar-koyu': '#b3aea4', yazi: '#1c1e21', soluk: '#4d535a',
    vurgu: '#7d4700', 'vurgu-zemin': '#f6e3c2', dolgu: '#f5a524', 'dolgu-yazi': '#1b1203',
    iyi: '#0f5f3d', 'iyi-zemin': '#d6ecdf',
    volt: '#234fa8', amper: '#7d4700', watt: '#0f5f3d',
    durdur: '#c2361f', 'durdur-yazi': '#ffffff', sema: 'light',
  },
};
const TEMA_ADI = { koyu: 'Koyu', acik: 'Açık', onpanel: 'Ön panel (koyu)', 'onpanel-acik': 'Ön panel (açık)' };

// ───────────────────────────────────────────────────────────── kontrast
const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const parlak = (h) => {
  const n = parseInt(h.slice(1), 16);
  return 0.2126 * lin(((n >> 16) & 255) / 255) + 0.7152 * lin(((n >> 8) & 255) / 255) + 0.0722 * lin((n & 255) / 255);
};
const oran = (a, b) => {
  const [x, y] = [parlak(a), parlak(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
// [nerede, metin belirteci, zemin belirteci, hangi adaylar]
const CIFT = [
  ['asıl metin · sayfa', 'yazi', 'zemin', 'ABC'],
  ['asıl metin · kart', 'yazi', 'kart', 'ABC'],
  ['asıl metin · çubuk / gömük ekran', 'yazi', 'zemin-2', 'ABC'],
  ['ikincil metin · sayfa', 'soluk', 'zemin', 'ABC'],
  ['ikincil metin · kart', 'soluk', 'kart', 'ABC'],
  ['ikincil metin · çubuk / gömük ekran', 'soluk', 'zemin-2', 'ABC'],
  ['etkin sekme', 'vurgu', 'zemin-2', 'AC'],
  ['etkin sekme etiketi (hap zemini)', 'yazi', 'vurgu-zemin', 'B'],
  ['vurgu metni · sayfa', 'vurgu', 'zemin', 'ABC'],
  ['vurgu metni · kart', 'vurgu', 'kart', 'AC'],
  ['seçili seçenek', 'vurgu', 'vurgu-zemin', 'ABC'],
  ['ana düğme yazısı', 'dolgu-yazi', 'dolgu', 'ABC'],
  ['DURDUR yazısı', 'durdur-yazi', 'durdur', 'ABC'],
  ['bağlantı metni (iyi)', 'iyi', 'iyi-zemin', 'A'],
  ['bağlantı metni (iyi) · sayfa', 'iyi', 'zemin', 'B'],
  ['bağlantı metni (iyi) · çubuk', 'iyi', 'zemin-2', 'C'],
  ['V rakamı · kart', 'volt', 'kart', 'A'],
  ['A rakamı · kart', 'amper', 'kart', 'A'],
  ['W rakamı · kart', 'watt', 'kart', 'A'],
  ['V rakamı · sayfa', 'volt', 'zemin', 'B'],
  ['A rakamı · sayfa', 'amper', 'zemin', 'B'],
  ['W rakamı · sayfa', 'watt', 'zemin', 'B'],
  ['V rakamı · gömük ekran', 'volt', 'zemin-2', 'C'],
  ['A rakamı · gömük ekran', 'amper', 'zemin-2', 'C'],
  ['W rakamı · gömük ekran', 'watt', 'zemin-2', 'C'],
];
const SAYFA = { zemin: '#c5c7ca', yazi: '#1b1d20' };

// ───────────────────────────────────────────────────────────── örnek veri
function rasgele(tohum) {
  return () => {
    tohum = (tohum + 0x6d2b79f5) | 0;
    let t = Math.imul(tohum ^ (tohum >>> 15), 1 | tohum);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function canliVeri() {
  const r = rasgele(7), V = [], A = [];
  for (let i = 0; i < 120; i++) {
    const t = i / 119, adim = t > 0.42 && t < 0.71 ? 0.13 : 0;
    A.push(1.9 + adim + 0.02 * Math.sin(t * 21) + (r() - 0.5) * 0.03);
    V.push(12.52 - adim * 0.35 + 0.012 * Math.sin(t * 9) + (r() - 0.5) * 0.012);
  }
  return { V, A, W: V.map((v, i) => v * A[i]) };
}
function kayitVeri() {
  const r = rasgele(31), V = [], A = [];
  for (let i = 0; i < 220; i++) {
    const t = i / 219;
    const yuk = t > 0.2 && t < 0.34 ? 0.16 : t > 0.6 && t < 0.78 ? -0.1 : 0;
    A.push(1.93 + yuk + (r() - 0.5) * 0.04);
    V.push(12.62 - 0.34 * t - 0.07 * t * t - yuk * 0.3 + (r() - 0.5) * 0.015);
  }
  return { V, A, W: V.map((v, i) => v * A[i]) };
}
const CANLI = canliVeri(), KAYIT = kayitVeri();
const SEC = [0.35, 0.62]; // seçili aralık (kaydın kesri)

function yol(d, W, H, ust, alt) {
  const lo = Math.min(...d), hi = Math.max(...d), n = d.length;
  return d.map((v, i) => {
    const x = (i / (n - 1)) * W, y = (alt - (alt - ust) * ((v - lo) / (hi - lo || 1))) * H;
    return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
  }).join('');
}
const CZ = 'fill="none" stroke-linejoin="round" vector-effect="non-scaling-stroke"';
function grafik(veri, { sinif = '', sec = null, ad = 'Grafik' } = {}) {
  const W = 320, H = 140;
  let s = `<svg class="grafik ${sinif}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${ad}">`;
  for (let i = 1; i < 4; i++) s += `<line x1="0" x2="${W}" y1="${(H * i) / 4}" y2="${(H * i) / 4}" stroke="var(--kenar-c)" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
  for (let i = 1; i < 6; i++) s += `<line y1="0" y2="${H}" x1="${(W * i) / 6}" x2="${(W * i) / 6}" stroke="var(--kenar-c)" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
  if (sec) {
    const x0 = sec[0] * W, x1 = sec[1] * W;
    s += `<rect x="${x0}" y="0" width="${x1 - x0}" height="${H}" fill="var(--vurgu)" opacity=".16"/>`;
    for (const x of [x0, x1]) s += `<line x1="${x}" x2="${x}" y1="0" y2="${H}" stroke="var(--vurgu)" stroke-width="2" vector-effect="non-scaling-stroke"/>`;
  }
  s += `<path d="${yol(veri.V, W, H, 0.08, 0.4)}" stroke="var(--volt)" stroke-width="1.6" ${CZ}/>`;
  s += `<path d="${yol(veri.A, W, H, 0.38, 0.68)}" stroke="var(--amper)" stroke-width="1.6" ${CZ}/>`;
  s += `<path d="${yol(veri.W, W, H, 0.62, 0.94)}" stroke="var(--watt)" stroke-width="1.6" ${CZ}/>`;
  return s + '</svg>';
}
function kucukGrafik(veri) {
  return `<svg class="kucuk" viewBox="0 0 320 60" preserveAspectRatio="none" role="img" aria-label="Son 10 dakikanın gücü">` +
    `<path d="${yol(veri.W, 320, 60, 0.12, 0.88)}L320 60L0 60Z" fill="var(--watt)" opacity=".14"/>` +
    `<path d="${yol(veri.W, 320, 60, 0.12, 0.88)}" stroke="var(--watt)" stroke-width="1.6" ${CZ}/></svg>`;
}
function gezgin(veri, sec) {
  const W = 320, H = 48, x0 = sec[0] * W, x1 = sec[1] * W;
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">` +
    `<path d="${yol(veri.W, W, H, 0.15, 0.85)}" stroke="var(--soluk)" stroke-width="1.3" ${CZ}/>` +
    `<rect x="${x0}" y="1" width="${x1 - x0}" height="${H - 2}" fill="var(--vurgu)" opacity=".2"/>` +
    `<rect x="${x0}" y="1" width="${x1 - x0}" height="${H - 2}" fill="none" stroke="var(--vurgu)" stroke-width="2" vector-effect="non-scaling-stroke"/>` +
    `<rect x="${x0 - 3}" y="14" width="6" height="20" rx="2" fill="var(--vurgu)"/><rect x="${x1 - 3}" y="14" width="6" height="20" rx="2" fill="var(--vurgu)"/></svg>`;
}

// ───────────────────────────────────────────────────────────── ortak parçalar
const IKON = {
  durum: '<path d="M4 16a8 8 0 1 1 16 0"/><path d="M12 16l4-5"/><circle cx="12" cy="16" r="1.2" fill="currentColor"/>',
  canli: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
  kayitlar: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
  ayarlar: '<path d="M4 7h9M19 7h1M4 17h1M11 17h9"/><circle cx="16" cy="7" r="2.4"/><circle cx="8" cy="17" r="2.4"/>',
  geri: '<path d="M15 5l-7 7 7 7"/>',
  paylas: '<circle cx="6" cy="12" r="2.2"/><circle cx="17" cy="6" r="2.2"/><circle cx="17" cy="18" r="2.2"/><path d="M8 11l7-4M8 13l7 4"/>',
  dur: '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5" fill="currentColor" stroke="none"/>',
  basla: '<circle cx="12" cy="12" r="5.5" fill="currentColor" stroke="none"/>',
  esit: '<path d="M5 10a7 7 0 0 1 12-4l2 2M19 14a7 7 0 0 1-12 4l-2-2"/><path d="M19 4v4h-4M5 20v-4h4"/>',
};
const ik = (ad) => `<svg class="ik" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IKON[ad]}</svg>`;
const SEKMELER = [['durum', 'Durum'], ['canli', 'Canlı'], ['kayitlar', 'Kayıtlar'], ['ayarlar', 'Ayarlar']];
const sekme = (etkin, buyuk = false) => `<nav class="sekme" aria-label="Gezinme">` + SEKMELER.map(([k, e]) =>
  `<button type="button"${k === etkin ? ' aria-current="page"' : ''}><span class="si">${ik(k)}</span><span>${buyuk ? e.toLocaleUpperCase('tr') : e}</span></button>`).join('') + `</nav>`;
const sb = `<div class="sb" aria-hidden="true"><span>09:41</span><span>%82</span></div>`;
const hiz = (sinif = 'secim') => `<div class="${sinif}" role="radiogroup" aria-label="Kayıt hızı">` + ['1/s', '5/s', '10/s', '50/s'].map((h) =>
  `<button type="button" role="radio" aria-checked="${h === '5/s'}">${h}</button>`).join('') + `</div>`;
const durdur = (ek = '') => `<button type="button" class="durdur ${ek}" aria-label="Acil durdur: yükü kes">${ik('dur')}<span>DURDUR</span></button>`;

const K = { ad: 'Akü deşarj denemesi 3', tarih: '03.10.2026 09:12', sure: '01:24:10', aralik: '00:29:24 – 00:52:05', arasure: '22 dk 41 sn' };
const IST = [['V', 'volt', '12.214', '12.471', '12.602'], ['A', 'amper', '1.802', '1.931', '2.104'], ['W', 'watt', '22.41', '24.08', '26.12']];
const istTablo = () => `<table class="ist"><thead><tr><th></th><th>En düşük</th><th>Ortalama</th><th>En yüksek</th></tr></thead><tbody>` +
  IST.map(([b, r, a, o, y]) => `<tr style="color:var(--${r})"><th>${b}</th><td>${a}</td><td>${o}</td><td>${y}</td></tr>`).join('') + `</tbody></table>`;

// ───────────────────────────────────────────────────────────── ortak CSS
const temaCss = (ad) => `.telefon[data-tema="${ad}"]{${Object.entries(TEMA[ad]).map(([k, v]) => (k === 'sema' ? `color-scheme:${v}` : `--${k}:${v}`)).join(';')}}`;
const ORTAK_CSS = `
:root{--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
--govde:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
*,*::before,*::after{box-sizing:border-box}
html{font-size:100%}
body{margin:0;background:${SAYFA.zemin};color:${SAYFA.yazi};font:1rem/1.4 var(--govde);-webkit-font-smoothing:antialiased}
.sayfa{padding:28px 32px 56px;width:max-content;margin:0 auto}
.sayfa>h1{font-size:1.25rem;margin:0 0 4px}
.sayfa>p{margin:0;font-size:.875rem;max-width:1144px}
.satir-et{font-size:.8125rem;font-weight:700;letter-spacing:.05em;margin:24px 0 10px}
.satir{display:grid;grid-template-columns:repeat(3,360px);gap:32px}
@media (max-width:800px){.sayfa{padding:16px 0 32px}.sayfa>h1,.sayfa>p,.satir-et{padding:0 16px;max-width:360px}.satir{grid-template-columns:360px;gap:20px}}
.telefon{width:360px;height:760px;border-radius:28px;overflow:hidden;position:relative;display:flex;flex-direction:column;
background:var(--zemin);color:var(--yazi);font:400 .9375rem/1.35 var(--govde);box-shadow:0 0 0 2px #2b2d30,0 10px 28px rgba(0,0,0,.28)}
.telefon button{appearance:none;font-family:inherit;margin:0;cursor:pointer}
.telefon h2,.telefon h3,.telefon p{margin:0}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.ik{width:1.5rem;height:1.5rem;flex:none}
.sb{flex:none;height:1.5rem;display:flex;justify-content:space-between;align-items:center;padding:0 1.5rem;font-size:.75rem;color:var(--soluk)}
.icerik{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;display:flex;flex-direction:column}
.icerik>*{flex:none}
.grafik,.kucuk{display:block;width:100%}
.gezgin{display:block;width:100%;height:3rem;padding:0;border:0;background:var(--zemin-2)}
.gezgin svg{display:block;width:100%;height:100%}
.sekme{flex:none;display:grid;grid-template-columns:repeat(4,1fr)}
.sekme button{border:0;background:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.125rem;font-size:.75rem;padding:0}
.ist{width:100%;border-collapse:collapse;font-family:var(--mono);font-variant-numeric:tabular-nums}
.ist td,.ist th{text-align:right;font-weight:600;padding:0}
.ist thead th{font:400 .75rem var(--govde);color:var(--soluk)}
.ist tbody th{text-align:left}
`;

function belge({ harf, baslik, fikir, css, asil, karsit, ekran }) {
  const satir = (tema) => `<div class="satir-et">${TEMA_ADI[tema].toLocaleUpperCase('tr')}${tema === asil ? ' — ASIL HAL' : ' — KARŞIT TEMA'}</div>
<div class="satir">${['durum', 'canli', 'kayit'].map((e) => ekran(e, tema)).join('\n')}</div>`;
  return `<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aday ${harf} — ${baslik}</title>
<style>${ORTAK_CSS}${temaCss(asil)}
${temaCss(karsit)}
${css}</style>
</head>
<body>
<div class="sayfa">
<h1>Aday ${harf} — ${baslik}</h1>
<p>${fikir} Durağan maket: örnek veri, hiçbir düğme bir şey yapmaz. Her çerçeve 360 × 760.</p>
${satir(asil)}
${satir(karsit)}
</div>
</body>
</html>
`;
}
const cerceve = (tema, ad, ic) => `<section class="telefon" data-tema="${tema}" aria-label="${ad} — ${TEMA_ADI[tema]}">${sb}${ic}</section>`;

// ═════════════════════════════════════════════════════════════ ADAY A — Tezgah
const CSS_A = `
.telefon{--r:10px}
.ust{flex:none;display:flex;align-items:center;gap:.5rem;min-height:3.25rem;padding:0 1rem;background:var(--zemin-2);border-bottom:1px solid var(--kenar-c)}
.ust h2{flex:1;min-width:0;font-size:1.0625rem;font-weight:650}
.geri{width:3rem;height:3rem;margin-left:-.75rem;border:0;background:none;color:var(--yazi);display:grid;place-items:center}
.ustdugme{min-height:3rem;padding:0 .75rem;border:1px solid var(--kenar-koyu);border-radius:var(--r);background:var(--kart);color:var(--yazi);font-size:.875rem;font-weight:600;display:flex;align-items:center;gap:.375rem}
.ustdugme .ik{width:1.25rem;height:1.25rem}
.cip{display:inline-flex;align-items:center;gap:.375rem;font-size:.75rem;font-weight:600;color:var(--iyi);background:var(--iyi-zemin);border-radius:999px;padding:.25rem .625rem}
.cip::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:currentColor}
.icerik{padding:.625rem 1rem;gap:.625rem}
.bag{display:flex;gap:.375rem;align-items:baseline;font-size:.8125rem;color:var(--soluk)}
.bag b{color:var(--yazi);font-weight:600}
.bag .sag{margin-left:auto}
.kart{background:var(--kart);border:1px solid var(--kenar-c);border-radius:var(--r);padding:.625rem .75rem;display:flex;flex-direction:column;gap:.5rem}
.kb{display:flex;align-items:center;gap:.5rem}
.rozet{font-size:.75rem;font-weight:700;color:var(--vurgu);background:var(--vurgu-zemin);border-radius:5px;padding:.125rem .5rem}
.kb .sure{margin-left:auto;font-size:1.375rem;font-weight:600}
.ikili{display:grid;grid-template-columns:1fr 1fr;gap:.5rem .75rem}
.et{font-size:.75rem;color:var(--soluk)}
.ikili b{display:block;font-weight:600}
.cubuk{height:.375rem;border-radius:3px;background:var(--kenar-c);margin-top:.25rem;overflow:hidden}
.cubuk i{display:block;height:100%;background:var(--vurgu)}
.uclu{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;border-top:1px solid var(--kenar-c);padding-top:.5rem}
.uclu b{display:block;white-space:nowrap;font:600 1.1875rem var(--mono);font-variant-numeric:tabular-nums}
.kucuk{height:4.75rem}
.dugme{width:100%;min-height:3rem;padding:0 1rem;border:1px solid var(--kenar-koyu);border-radius:var(--r);background:var(--kart);color:var(--yazi);font-size:.9375rem;font-weight:600;display:flex;align-items:center;justify-content:center;gap:.5rem}
.dugme.ana{background:var(--dolgu);border-color:var(--dolgu);color:var(--dolgu-yazi)}
.esit{display:flex;align-items:center;gap:.5rem;font-size:.8125rem;color:var(--soluk)}
.esit b{color:var(--yazi);font-weight:600}
.esit .ik{width:1.25rem;height:1.25rem}
.deger{display:flex;align-items:baseline;gap:.5rem;padding:.25rem 0;border-top:1px solid var(--kenar-c)}
.deger:first-child{border-top:0}
.deger .et{flex:1}
.deger b{font:600 2.375rem/1.15 var(--mono);font-variant-numeric:tabular-nums}
.deger i{font:normal 600 1rem var(--mono);width:1.25rem}
.gb{display:flex;justify-content:space-between;font-size:.75rem;color:var(--soluk)}
.gb .l b{font-weight:600;margin-left:.5rem}
.canli .grafik{height:8.5rem}
.secim{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--kenar-koyu);border-radius:var(--r);overflow:hidden}
.secim button{min-height:3rem;border:0;border-left:1px solid var(--kenar-c);background:var(--kart);color:var(--soluk);font:600 .875rem var(--mono)}
.secim button:first-child{border-left:0}
.secim button[aria-checked=true]{background:var(--vurgu-zemin);color:var(--vurgu)}
.kayit h3{font-size:1.0625rem;font-weight:650}
.kayit .grafik{height:9.5rem}
.aralik{font-size:.8125rem;color:var(--soluk)}
.aralik b{color:var(--vurgu);font-weight:600}
.ist td,.ist th{font-size:.875rem;line-height:1.7}
.enerji{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;border-top:1px solid var(--kenar-c);padding-top:.375rem}
.enerji b{display:block;font:600 1rem var(--mono)}
.serit{flex:none;padding:.5rem 1rem;background:var(--zemin-2);border-top:1px solid var(--kenar-c)}
.durdur{width:100%;min-height:3.5rem;border:0;border-radius:var(--r);background:var(--durdur);color:var(--durdur-yazi);font-size:1.0625rem;font-weight:700;letter-spacing:.1em;display:flex;align-items:center;justify-content:center;gap:.5rem}
.sekme{background:var(--zemin-2);border-top:1px solid var(--kenar-c)}
.sekme button{min-height:3.5rem;color:var(--soluk)}
.sekme button[aria-current]{color:var(--vurgu);font-weight:600}
`;
function ekranA(e, tema) {
  const alt = (s) => `<div class="serit">${durdur()}</div>${sekme(s)}`;
  if (e === 'durum') return cerceve(tema, 'Durum', `
<header class="ust"><h2>Durum</h2></header>
<main class="icerik">
  <div class="bag"><b>Bu ağda</b><span>· 2 sn önce</span><span class="sag">ev ağı</span></div>
  <article class="kart">
    <div class="kb"><span class="rozet">Kayıt sürüyor</span><span class="sure mono">01:24:10</span></div>
    <div class="ikili">
      <div><span class="et">Tür</span><b>Ölçüm</b></div>
      <div><span class="et">Hız</span><b class="mono">5/s</b></div>
      <div><span class="et">Kart belleği</span><b class="mono">%38 dolu</b><div class="cubuk"><i style="width:38%"></i></div></div>
      <div><span class="et">Eşitlenmemiş</span><b class="mono">%4</b><div class="cubuk"><i style="width:4%"></i></div></div>
    </div>
    <div class="uclu">
      <div><span class="et">Gerilim · V</span><b style="color:var(--volt)">12.482</b></div>
      <div><span class="et">Akım · A</span><b style="color:var(--amper)">1.936</b></div>
      <div><span class="et">Güç · W</span><b style="color:var(--watt)">24.17</b></div>
    </div>
    ${kucukGrafik(CANLI)}
  </article>
  <button type="button" class="dugme">${ik('dur')}Kaydı durdur</button>
  <div class="esit">${ik('esit')}<span><b>Eşitleme güncel</b> · son 12 sn önce · telefonda 44 kayıt</span></div>
</main>${alt('durum')}`);
  if (e === 'canli') return cerceve(tema, 'Canlı', `
<header class="ust"><h2>Canlı</h2><span class="cip">Bu ağda</span></header>
<main class="icerik canli">
  <div class="kart" style="gap:0">
    <div class="deger"><span class="et">Gerilim</span><b style="color:var(--volt)">12.482</b><i style="color:var(--volt)">V</i></div>
    <div class="deger"><span class="et">Akım</span><b style="color:var(--amper)">1.936</b><i style="color:var(--amper)">A</i></div>
    <div class="deger"><span class="et">Güç</span><b style="color:var(--watt)">24.17</b><i style="color:var(--watt)">W</i></div>
  </div>
  <div class="kart">
    <div class="gb"><span>Son 60 s</span><span class="l"><b style="color:var(--volt)">V</b><b style="color:var(--amper)">A</b><b style="color:var(--watt)">W</b></span></div>
    ${grafik(CANLI, { ad: 'Son 60 saniye: gerilim, akım, güç' })}
    <div class="gb mono"><span>−60 s</span><span>−30 s</span><span>şimdi</span></div>
  </div>
  <div><span class="et">Kayıt hızı</span>${hiz()}</div>
  <button type="button" class="dugme ana">${ik('basla')}Kaydı başlat</button>
</main>${alt('canli')}`);
  return cerceve(tema, 'Kayıt görünümü', `
<header class="ust"><button type="button" class="geri" aria-label="Geri">${ik('geri')}</button><h2>Kayıt</h2><button type="button" class="ustdugme">${ik('paylas')}Paylaş</button></header>
<main class="icerik kayit">
  <div><h3>${K.ad}</h3><p class="et">${K.tarih} · ${K.sure} · Ölçüm · 5/s</p></div>
  <div class="kart">
    ${grafik(KAYIT, { sec: SEC, ad: 'Kaydın tamamı, seçili aralık işaretli' })}
    <div class="gb mono"><span>00:00</span><span>00:42</span><span>01:24</span></div>
    <button type="button" class="gezgin" aria-label="Gezgin şeridi: aralığı kaydır">${gezgin(KAYIT, SEC)}</button>
  </div>
  <div class="kart">
    <p class="aralik">Seçili aralık <b class="mono">${K.aralik}</b> · ${K.arasure}</p>
    ${istTablo()}
    <div class="enerji"><div><span class="et">Enerji</span><b>9.104 Wh</b></div><div><span class="et">Yük</span><b>730.0 mAh</b></div></div>
  </div>
</main>${alt('kayitlar')}`);
}

// ═════════════════════════════════════════════════════════════ ADAY B — Sade
const CSS_B = `
.telefon{--r:16px;font-size:1rem}
.ust{flex:none;display:flex;align-items:center;gap:.5rem;min-height:4.5rem;padding:.5rem 1rem}
.ust .bas{flex:1;min-width:0}
.ust h2{font-size:1.5rem;font-weight:700;line-height:1.2}
.ust p{font-size:.8125rem;color:var(--soluk)}
.ust p b{color:var(--iyi);font-weight:600}
.geri{width:3rem;height:3rem;margin-left:-.75rem;border:0;background:none;color:var(--yazi);display:grid;place-items:center}
.durdur{flex:none;min-height:3.5rem;min-width:6rem;padding:0 .75rem;border:0;border-radius:999px;background:var(--durdur);color:var(--durdur-yazi);font-size:.9375rem;font-weight:700;letter-spacing:.06em;display:flex;align-items:center;justify-content:center;gap:.375rem}
.durdur .ik{width:1.25rem;height:1.25rem}
.icerik{padding:.25rem 1.25rem 1rem;gap:1rem}
.et{font-size:.8125rem;color:var(--soluk)}
.kahraman b{display:block;white-space:nowrap;font:300 3rem/1.1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.dolu{display:grid;gap:.625rem}
.dolu div{display:flex;justify-content:space-between;font-size:.875rem}
.dolu b{font:600 .875rem var(--mono)}
.cubuk{height:.375rem;border-radius:999px;background:var(--kenar-c);overflow:hidden;margin-top:.25rem}
.cubuk i{display:block;height:100%;border-radius:999px;background:var(--vurgu)}
.uclu{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;padding:.75rem 0;border-top:1px solid var(--kenar-c);border-bottom:1px solid var(--kenar-c)}
.uclu b{display:block;white-space:nowrap;font:500 1.125rem var(--mono);font-variant-numeric:tabular-nums}
.kucuk{height:5.5rem}
.dugme{width:100%;min-height:3.25rem;padding:0 1.25rem;border:1.5px solid var(--kenar-koyu);border-radius:999px;background:none;color:var(--yazi);font-size:1rem;font-weight:600;display:flex;align-items:center;justify-content:center;gap:.5rem}
.dugme.ana{background:var(--dolgu);border-color:var(--dolgu);color:var(--dolgu-yazi)}
.esit{display:flex;align-items:center;gap:.5rem;font-size:.8125rem;color:var(--soluk)}
.esit b{color:var(--yazi);font-weight:600}
.buyukv b{font:300 3.5rem/1.05 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.buyukv b,.yari b{display:inline-block}
.buyukv i,.yari i{font:normal 500 1.125rem var(--mono);margin-left:.25rem}
.yari{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.yari b{font:400 1.625rem/1.1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.gb{display:flex;justify-content:space-between;font-size:.75rem;color:var(--soluk)}
.gb .l{display:flex;gap:.75rem;color:var(--yazi)}
.gb .l i{display:inline-block;width:.75rem;height:.1875rem;border-radius:2px;margin-right:.25rem;vertical-align:middle}
.canli .grafik{height:10.5rem;margin:.25rem 0}
.secim{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:.25rem;padding:.25rem;border-radius:999px;background:var(--zemin-2);border:1px solid var(--kenar-c);margin-top:.25rem}
.secim button{min-height:3rem;border:0;border-radius:999px;background:none;color:var(--soluk);font-size:.875rem;font-weight:600}
.secim button[aria-checked=true]{background:var(--vurgu-zemin);color:var(--vurgu)}
.kayit{gap:.75rem}
.kayit h3{font-size:1.1875rem;font-weight:700;line-height:1.25}
.kayit .grafik{height:11.5rem}
.gezgin{border-radius:var(--r);overflow:hidden;margin-top:.375rem}
.aralik{font-size:.8125rem;color:var(--soluk);margin-top:.25rem}
.aralik b{color:var(--vurgu);font-weight:600}
.ucist{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem}
.ucist b{display:block;white-space:nowrap;font:500 1.1875rem var(--mono);font-variant-numeric:tabular-nums;color:var(--volt)}
.enerji{display:flex;flex-wrap:wrap;gap:.125rem 1.25rem;font-size:.875rem;color:var(--soluk)}
.enerji b{font:600 .9375rem var(--mono);color:var(--yazi)}
.sekme{padding:.25rem 0 .375rem}
.sekme button{min-height:3.75rem;color:var(--soluk)}
.sekme .si{display:grid;place-items:center;width:3.5rem;height:1.875rem;border-radius:999px}
.sekme button[aria-current]{color:var(--yazi);font-weight:700}
.sekme button[aria-current] .si{background:var(--vurgu-zemin)}
`;
function ekranB(e, tema) {
  if (e === 'durum') return cerceve(tema, 'Durum', `
<header class="ust"><div class="bas"><h2>Durum</h2><p><b>● Bu ağda</b> · 2 sn önce</p></div>${durdur()}</header>
<main class="icerik">
  <div class="kahraman"><span class="et">Ölçüm kaydı sürüyor</span><b>01:24:10</b><span class="et">Hız 5/s · 09:12'de başladı</span></div>
  <div class="dolu">
    <div><span>Kart belleği</span><b>%38 dolu</b></div><div class="cubuk"><i style="width:38%"></i></div>
    <div><span>Eşitlenmemiş</span><b>%4</b></div><div class="cubuk"><i style="width:4%"></i></div>
  </div>
  <div class="uclu">
    <div><span class="et">Gerilim · V</span><b style="color:var(--volt)">12.482</b></div>
    <div><span class="et">Akım · A</span><b style="color:var(--amper)">1.936</b></div>
    <div><span class="et">Güç · W</span><b style="color:var(--watt)">24.17</b></div>
  </div>
  ${kucukGrafik(CANLI)}
  <button type="button" class="dugme">${ik('dur')}Kaydı durdur</button>
  <div class="esit">${ik('esit')}<span><b>Eşitleme güncel</b> · son 12 sn önce</span></div>
</main>${sekme('durum')}`);
  if (e === 'canli') return cerceve(tema, 'Canlı', `
<header class="ust"><div class="bas"><h2>Canlı</h2><p><b>● Bu ağda</b> · 2 sn önce</p></div>${durdur()}</header>
<main class="icerik canli">
  <div class="buyukv"><span class="et">Gerilim</span><div style="color:var(--volt)"><b>12.482</b><i>V</i></div></div>
  <div class="yari">
    <div><span class="et">Akım</span><div style="color:var(--amper)"><b>1.936</b><i>A</i></div></div>
    <div><span class="et">Güç</span><div style="color:var(--watt)"><b>24.17</b><i>W</i></div></div>
  </div>
  <div>
    <div class="gb"><span>Son 60 s</span><span class="l"><span><i style="background:var(--volt)"></i>V</span><span><i style="background:var(--amper)"></i>A</span><span><i style="background:var(--watt)"></i>W</span></span></div>
    ${grafik(CANLI, { ad: 'Son 60 saniye: gerilim, akım, güç' })}
    <div class="gb mono"><span>−60 s</span><span>−30 s</span><span>şimdi</span></div>
  </div>
  <div><span class="et">Kayıt hızı</span>${hiz()}</div>
  <button type="button" class="dugme ana">${ik('basla')}Kaydı başlat</button>
</main>${sekme('canli')}`);
  return cerceve(tema, 'Kayıt görünümü', `
<header class="ust"><button type="button" class="geri" aria-label="Geri">${ik('geri')}</button><div class="bas"><h2>Kayıt</h2></div>${durdur()}</header>
<main class="icerik kayit">
  <div><h3>${K.ad}</h3><p class="et">${K.tarih} · süre ${K.sure}</p></div>
  <div>
    ${grafik(KAYIT, { sec: SEC, ad: 'Kaydın tamamı, seçili aralık işaretli' })}
    <button type="button" class="gezgin" aria-label="Gezgin şeridi: aralığı kaydır">${gezgin(KAYIT, SEC)}</button>
    <p class="aralik">Seçili aralık <b class="mono">${K.aralik}</b> · ${K.arasure}</p>
  </div>
  <div class="secim" role="radiogroup" aria-label="Büyüklük" style="margin-top:0">
    <button type="button" role="radio" aria-checked="true">Gerilim</button><button type="button" role="radio" aria-checked="false">Akım</button><button type="button" role="radio" aria-checked="false">Güç</button>
  </div>
  <div class="ucist">
    <div><span class="et">En düşük · V</span><b>12.214</b></div>
    <div><span class="et">Ortalama · V</span><b>12.471</b></div>
    <div><span class="et">En yüksek · V</span><b>12.602</b></div>
  </div>
  <div class="enerji"><span>Enerji <b>9.104 Wh</b></span><span>Yük <b>730.0 mAh</b></span></div>
  <button type="button" class="dugme ana">${ik('paylas')}Paylaş</button>
</main>${sekme('kayitlar')}`);
}

// ═════════════════════════════════════════════════════════════ ADAY C — Ön panel
const CSS_C = `
.telefon{--r:4px}
.ust{flex:none;display:flex;align-items:center;gap:.5rem;min-height:3.25rem;padding:0 1rem;background:var(--zemin-2);border-bottom:2px solid var(--dolgu)}
.ust h2{flex:1;min-width:0;font-size:1rem;font-weight:700;letter-spacing:.14em}
.geri{width:3rem;height:3rem;margin-left:-.75rem;border:0;background:none;color:var(--yazi);display:grid;place-items:center}
.lamba{display:inline-flex;align-items:center;gap:.375rem;font-size:.75rem;font-weight:700;letter-spacing:.08em;color:var(--iyi)}
.lamba::before{content:"";width:.625rem;height:.625rem;border-radius:50%;background:currentColor;box-shadow:0 0 6px currentColor}
.lamba small{font-size:.75rem;font-weight:400;letter-spacing:0;color:var(--soluk)}
.icerik{padding:.625rem .75rem;gap:.625rem}
.et{font-size:.75rem;font-weight:600;letter-spacing:.1em;color:var(--soluk)}
.pano{background:var(--kart);border:1px solid var(--kenar-koyu);border-radius:var(--r);padding:.625rem;display:flex;flex-direction:column;gap:.5rem}
.pb{display:flex;justify-content:space-between;align-items:center}
.pb .kyt{color:var(--vurgu)}
.ekran{background:var(--zemin-2);border:1px solid var(--kenar-c);border-radius:var(--r);box-shadow:inset 0 2px 4px rgba(0,0,0,.25);padding:.375rem .625rem}
.sure{font:700 2.5rem/1.15 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:.02em;text-align:center}
.olcek{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:.25rem .625rem}
.olcek b{font:700 .875rem var(--mono);text-align:right}
.led{height:.75rem;position:relative;background:repeating-linear-gradient(90deg,var(--kenar-koyu) 0 8px,transparent 8px 11px)}
.led i{position:absolute;inset:0 auto 0 0;background:repeating-linear-gradient(90deg,var(--dolgu) 0 8px,transparent 8px 11px)}
.uclu{display:grid;grid-template-columns:repeat(3,1fr);gap:.375rem}
.uclu .ekran{padding:.25rem .375rem}
.uclu b{display:block;white-space:nowrap;font:700 1rem var(--mono);font-variant-numeric:tabular-nums}
.kucuk{height:6rem}
.dugme{width:100%;min-height:3rem;padding:0 1rem;border:1px solid var(--kenar-koyu);border-radius:var(--r);background:var(--zemin);color:var(--yazi);font-size:.875rem;font-weight:700;letter-spacing:.06em;display:flex;align-items:center;justify-content:center;gap:.5rem}
.dugme.ana{background:var(--dolgu);border-color:var(--dolgu);color:var(--dolgu-yazi)}
.sira{display:flex;align-items:baseline;gap:.5rem;border-top:1px solid var(--kenar-c);padding:.125rem 0}
.sira:first-child{border-top:0}
.sira .et{flex:1}
.sira b{font:700 2.5rem/1.15 var(--mono);font-variant-numeric:tabular-nums}
.sira.bas{flex-wrap:wrap;gap:0 .5rem}
.sira.bas .et{flex:0 0 100%}
.sira.bas b{font-size:3rem;flex:1;text-align:right}
.sira i{font:normal 700 1.125rem var(--mono);width:1.25rem}
.gb{display:flex;justify-content:space-between;font-size:.75rem;color:var(--soluk)}
.canli .grafik{height:7.75rem}
.tuslar{display:grid;grid-template-columns:repeat(4,1fr);gap:.375rem;margin-top:.25rem}
.tuslar button{min-height:3rem;border:1px solid var(--kenar-koyu);border-radius:var(--r);background:var(--kart);color:var(--soluk);font:700 .875rem var(--mono);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.25rem}
.tuslar button::before{content:"";width:1.25rem;height:.25rem;border-radius:2px;background:var(--kenar-koyu)}
.tuslar button[aria-checked=true]{color:var(--vurgu);background:var(--vurgu-zemin);border-color:var(--dolgu)}
.tuslar button[aria-checked=true]::before{background:var(--dolgu)}
.kayit h3{font-size:1rem;font-weight:700}
.kayit .alt{font-size:.8125rem;color:var(--soluk)}
.kayit .grafik{height:8.25rem}
.gezgin{border:1px solid var(--kenar-c)}
.aralik{font-size:.8125rem;color:var(--soluk)}
.aralik b{color:var(--vurgu);font-weight:700}
.ist td,.ist th{font-size:.9375rem;line-height:1.65;font-weight:700}
.ist thead th{font:600 .75rem var(--govde)}
.enerji{display:grid;grid-template-columns:1fr 1fr;gap:.375rem}
.enerji b{display:block;font:700 1rem var(--mono)}
.bant{flex:none;display:flex;align-items:center;gap:.75rem;min-height:5.25rem;padding:.375rem .75rem;background:var(--zemin-2);border-top:1px solid var(--kenar-koyu)}
.bant .sol{flex:1;min-width:0;font-size:.8125rem;color:var(--soluk)}
.bant .sol b{display:block;color:var(--yazi);font-weight:700}
.durdur{flex:none;width:4.5rem;height:4.5rem;border-radius:50%;border:3px solid var(--kenar-koyu);background:var(--durdur);color:var(--durdur-yazi);font-size:.75rem;font-weight:800;letter-spacing:.04em;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.4)}
.sekme{background:var(--zemin-2);border-top:1px solid var(--kenar-c)}
.sekme button{min-height:3.5rem;color:var(--soluk);font-weight:600;border-top:3px solid transparent}
.sekme button[aria-current]{color:var(--vurgu);border-top-color:var(--dolgu)}
`;
function ekranC(e, tema) {
  const alt = (sol, s) => `<div class="bant"><div class="sol">${sol}</div>${durdur()}</div>${sekme(s, true)}`;
  if (e === 'durum') return cerceve(tema, 'Durum', `
<header class="ust"><h2>DURUM</h2><span class="lamba">BU AĞDA <small>· 2 sn önce</small></span></header>
<main class="icerik">
  <section class="pano">
    <div class="pb"><span class="et kyt">● KAYIT · ÖLÇÜM</span><span class="et">HIZ 5/s</span></div>
    <div class="ekran sure">01:24:10</div>
    <div class="olcek">
      <span class="et">BELLEK</span><div class="led"><i style="width:38%"></i></div><b>%38</b>
      <span class="et">EŞİTLENMEMİŞ</span><div class="led"><i style="width:4%"></i></div><b>%4</b>
    </div>
  </section>
  <section class="pano">
    <div class="pb"><span class="et">SON ÖLÇÜM</span><span class="et">SON 10 dk</span></div>
    <div class="uclu">
      <div class="ekran"><span class="et">V</span><b style="color:var(--volt)">12.482</b></div>
      <div class="ekran"><span class="et">A</span><b style="color:var(--amper)">1.936</b></div>
      <div class="ekran"><span class="et">W</span><b style="color:var(--watt)">24.17</b></div>
    </div>
    <div class="ekran" style="padding:.25rem">${kucukGrafik(CANLI)}</div>
  </section>
  <button type="button" class="dugme">${ik('dur')}KAYDI DURDUR</button>
</main>${alt('<b>Eşitleme güncel</b>son 12 sn önce · telefonda 44 kayıt', 'durum')}`);
  if (e === 'canli') return cerceve(tema, 'Canlı', `
<header class="ust"><h2>CANLI</h2><span class="lamba">BU AĞDA <small>· 2 sn önce</small></span></header>
<main class="icerik canli">
  <section class="pano"><div class="ekran">
    <div class="sira bas"><span class="et">GERİLİM</span><b style="color:var(--volt)">12.482</b><i style="color:var(--volt)">V</i></div>
    <div class="sira"><span class="et">AKIM</span><b style="color:var(--amper)">1.936</b><i style="color:var(--amper)">A</i></div>
    <div class="sira"><span class="et">GÜÇ</span><b style="color:var(--watt)">24.17</b><i style="color:var(--watt)">W</i></div>
  </div></section>
  <section class="pano">
    <div class="pb"><span class="et">SON 60 s</span><span class="et"><span style="color:var(--volt)">V</span> · <span style="color:var(--amper)">A</span> · <span style="color:var(--watt)">W</span></span></div>
    <div class="ekran" style="padding:0">${grafik(CANLI, { ad: 'Son 60 saniye: gerilim, akım, güç' })}</div>
    <div class="gb mono"><span>−60 s</span><span>−30 s</span><span>şimdi</span></div>
  </section>
  <div><span class="et">KAYIT HIZI</span>${hiz('tuslar')}</div>
</main>${alt(`<button type="button" class="dugme ana">${ik('basla')}KAYDI BAŞLAT</button>`, 'canli')}`);
  return cerceve(tema, 'Kayıt görünümü', `
<header class="ust"><button type="button" class="geri" aria-label="Geri">${ik('geri')}</button><h2>KAYIT</h2></header>
<main class="icerik kayit">
  <div><h3>${K.ad}</h3><p class="alt">${K.tarih} · süre ${K.sure}</p></div>
  <section class="pano">
    <div class="ekran" style="padding:0">${grafik(KAYIT, { sec: SEC, ad: 'Kaydın tamamı, seçili aralık işaretli' })}</div>
    <div class="gb mono"><span>00:00</span><span>00:42</span><span>01:24</span></div>
    <button type="button" class="gezgin" aria-label="Gezgin şeridi: aralığı kaydır">${gezgin(KAYIT, SEC)}</button>
  </section>
  <section class="pano">
    <p class="aralik">ARALIK <b class="mono">${K.aralik}</b> · ${K.arasure}</p>
    <div class="ekran">${istTablo()}</div>
    <div class="enerji"><div class="ekran"><span class="et">Wh</span><b>9.104</b></div><div class="ekran"><span class="et">mAh</span><b>730.0</b></div></div>
  </section>
</main>${alt(`<button type="button" class="dugme ana">${ik('paylas')}PAYLAŞ</button>`, 'kayitlar')}`);
}

// Ölçüm sonuçları — başsız Edge'de `olc.mjs` ile ölçüldü (2026-10-04); maket değişirse yeniden ölç.
const OLCUM_METNI = "Başsız Edge (Chromium), pencere 1400 × 2000, 3 dosya × 6 çerçeve = 18 çerçeve; her biri dört koşulda:\nkök yazı boyutu %100 ve %130, eş aralıklı yazı Consolas (0.55 em) ve \"Courier New\" (0.60 em — Android'in\neş aralıklı yazısının genişliği). Araç: olc.mjs (node olc.mjs aday-a.html \"msedge.exe yolu\").\n\n| Ölçülen | Sonuç |\n|---|---|\n| Çerçeve boyutu | 18/18 tam 360 × 760 |\n| En küçük dokunma alanı (bütün button'lar: sekmeler, seçiciler, geri, gezgin şeridi, düğmeler) | **48.0 px** (%100); %130'da 62.4 px — 48'in altında hiçbiri yok |\n| DURDUR boyutu (%100) | A 328 × 56 · B 118.8 × 56 · C 72 × 72 (daire) |\n| DURDUR en üstte mi (elementFromPoint), çerçeve içinde mi | 72/72 koşulda evet |\n| Düğmelerin görünür alanda birbirine binmesi | 0 |\n| Yatay taşma / kırpılan metin / ebeveyninden taşan öğe / ikinci satıra saran rakam | 0 (dört koşulda da) |\n| %100'de dikey kaydırma gereği | 0 px (her ekran tek sayfaya sığıyor) |\n| %130'da dikey kaydırma | A 95–224 px · B 137–215 px · C 103–231 px — yalnız içerik alanı kayar; üst çubuk, DURDUR ve sekmeler yerinde kalır |\n\n%130 notları: C'de \"KAYDI BAŞLAT\" iki satıra iner (düğme büyür, taşma yok); C'nin LED çubuğu daralır.\nİlk ölçümde bulunan ve düzeltilenler: B'de \"Kayıt\" başlığı %130'da kırpılıyordu (DURDUR dolgusu azaltıldı);\nC'de 3.5 rem gerilim rakamı %130'da göstergeden taşıyordu (3 rem + etiket üst satıra); üçlü V/A/W\nhücrelerinde \"12.482 V\" ikinci satıra sarıyordu (birim etikete alındı).\n";

// ───────────────────────────────────────────────────────────── yaz
const ADAY = [
  { harf: 'A', dosya: 'aday-a.html', baslik: 'Tezgah', asil: 'koyu', karsit: 'acik', css: CSS_A, ekran: ekranA,
    fikir: 'Panelin "Koyu" görünümünden: yoğun, kartlı tezgah aleti; her bilgi tek ekranda, rakamlar eş aralıklı. DURDUR sekmelerin hemen üstünde tam genişlik kırmızı şerit.' },
  { harf: 'B', dosya: 'aday-b.html', baslik: 'Sade', asil: 'acik', karsit: 'koyu', css: CSS_B, ekran: ekranB,
    fikir: 'Panelin "Açık" görünümünden: ferah, kartsız, büyük ince rakamlar ve yuvarlak hatlar; tek bakışta tek ana bilgi. DURDUR üst çubukta sağda, hap biçiminde.' },
  { harf: 'C', dosya: 'aday-c.html', baslik: 'Ön panel', asil: 'onpanel', karsit: 'onpanel-acik', css: CSS_C, ekran: ekranC,
    fikir: 'Panelin "Ön panel" görünümünden: grafit + turuncu ölçü aleti yüzü; gömük göstergeler, kalın büyük rakamlar, LED çubuklar, köşeli tuşlar. DURDUR sağ altta yuvarlak kırmızı düğme (sekmelerin üstündeki eylem bandında).' },
];
let kotu = 0;
let tablo = '';
for (const a of ADAY) {
  writeFileSync(join(BURASI, a.dosya), belge(a), 'utf8');
  for (const t of [a.asil, a.karsit]) {
    tablo += `\n### Aday ${a.harf} — ${TEMA_ADI[t]}\n\n| Nerede | Metin | Zemin | Oran |\n|---|---|---|---|\n`;
    let enaz = 99;
    for (const [nerede, m, z, kim] of CIFT) {
      if (!kim.includes(a.harf)) continue;
      const o = oran(TEMA[t][m], TEMA[t][z]);
      enaz = Math.min(enaz, o);
      if (o < 4.5) { kotu++; console.error(`KIRMIZI ${a.harf}/${t}: ${nerede} ${o.toFixed(2)}`); }
      tablo += `| ${nerede} | \`${TEMA[t][m]}\` | \`${TEMA[t][z]}\` | ${o.toFixed(2)} |\n`;
    }
    tablo += `\nEn düşük: **${enaz.toFixed(2)}**\n`;
    console.log(`${a.harf} ${t.padEnd(13)} en düşük ${enaz.toFixed(2)}`);
  }
}
const sayfaOran = oran(SAYFA.yazi, SAYFA.zemin);
const OLCUM = OLCUM_METNI;
writeFileSync(join(BURASI, 'OKU.md'), `# Görsel tasarım adayları (A44)

Üç durağan maket; uygulama koduna dokunmaz. Tarayıcıda (ya da telefonda) doğrudan açılır, ağ gerekmez.

| Dosya | Aday | Asıl / karşıt tema | DURDUR düğmesi |
|---|---|---|---|
${ADAY.map((a) => `| \`${a.dosya}\` | ${a.harf} — ${a.baslik} | ${TEMA_ADI[a.asil]} / ${TEMA_ADI[a.karsit]} | ${a.fikir.split('DURDUR ')[1]} |`).join('\n')}

Her dosyada 6 çerçeve (360 × 760): üst satır asıl tema, alt satır karşıt tema; sütunlar Durum · Canlı · Kayıt görünümü.

Dosyalar \`uret.mjs\` ile ÜRETİLİR (\`node uret.mjs\`); elle düzenleme. Renkler \`arayuz3/style.css\`'in
\`koyu\` · \`acik\` · \`onpanel\` bloklarından birebir. Burada türetilenler: \`onpanel-acik\` takımı (panelde yok)
ve DURDUR dolgusu (\`#c62828\` / \`#c2361f\` + beyaz). \`--cok-soluk\` hiçbir adayda metin rengi olarak kullanılmadı
(koyu temada kart üstünde 4.5'in altında).

## Ölçüm sonuçları (dokunma alanı, %130 yazı boyutu)

${OLCUM}
## Kontrast (WCAG 2.x, hesap \`uret.mjs\` içinde; 4.5 altı çift betiği kırmızı bitirir)

Sayfa etiketi (çerçevelerin dışı): \`${SAYFA.yazi}\` / \`${SAYFA.zemin}\` = ${sayfaOran.toFixed(2)}
${tablo}`, 'utf8');
if (kotu) { console.error(`${kotu} çift 4.5'in altında`); process.exit(1); }
