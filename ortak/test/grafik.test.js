// ortak/test/grafik.test.js — dilim 3B: grafik çekirdeği (ölçek, çizim planı, etkileşim,
// imleç okuması, ince çizici). Kararlar: ortak/src/grafik.js başı (G1–G9);
// tasarim/2026-10-02-alt-proje-3-panel.md P3/3B; alt proje 2 D1–D5; üst tasarım §9, Ö1.
//
// Kaba kuvvet başvuruları bu dosyada, src'den BAĞIMSIZ (düz döngüler, kendi ikili
// aramaları). Sütun sınırı formülü ozet.js'nin SÖZLEŞMESİ; burada ayrıca yazıldı.
// Ö1 iki yerde sınanır: düz komut PLANINDA ve sahte kanvas bağlamının ÇİZİM ÇAĞRILARINDA
// (panel tasarımı 3B kabulü: "sahte kanvas bağlamının çizim çağrılarında Ö1").

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ozetKur } from '../src/ozet.js';
import {
  EN_AZ_ORNEK, RENK_YEDEK, TUS_ORAN, TUS_KAYDIR, IMLEC_TUS_ADIM, PAY, KISKAC_EN_AZ_PX,
  guzelAdim, guzelAdimlar, zamanAdimi, zamanAdimlari, eksenAraligi, zamanYazi, sayiYazi,
  yerlesim, pencereHesapla, cizimPlani, lejantOgeleri, tipikAralik, durumKur, durumBirlestir,
  pencereKirp, yakinlastir, etkilesim, enYakinOrnek, imlecOkuma, seriHazirla, cssRenk,
  planUygula, Grafik, xSayiEkseni, sayiAdimlari, xYazici,
} from '../src/grafik.js';

// ── yardımcılar ─────────────────────────────────────────────────────────────

/** mulberry32: tohumlu, belirlenimci [0, 1) üreteci. */
function rastgele(tohum) {
  let a = tohum >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let z = a;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

/** İlk t[i] ≥ x. */
function ilkBuyukEsit(t, x) {
  let lo = 0;
  let hi = t.length;
  while (lo < hi) {
    const m = Math.floor((lo + hi) / 2);
    if (t[m] >= x) hi = m;
    else lo = m + 1;
  }
  return lo;
}

/** İlk t[i] > x. */
function ilkBuyuk(t, x) {
  let lo = 0;
  let hi = t.length;
  while (lo < hi) {
    const m = Math.floor((lo + hi) / 2);
    if (t[m] > x) hi = m;
    else lo = m + 1;
  }
  return lo;
}

const BOSLUK_MS = 10;

/**
 * Sınanacak kayıt: ~500 örnek/s (2 ms ± titreşim), unix ms zamanı (1.7e12: kayan nokta
 * duyarlığı da sınanır), 10 boşluk (0.4…60 s), V ≈ 12 ± gürültü (sol eksen),
 * A ≈ 0.5 ± gürültü (sağ eksen), dağınık NaN + bir NaN koşusu.
 */
function kayitUret(n, tohum) {
  const r = rastgele(tohum);
  const t = new Float64Array(n);
  const v = new Float64Array(n);
  const a = new Float64Array(n);
  const boslukYeri = new Set();
  while (boslukYeri.size < 10) boslukYeri.add(50 + Math.floor(r() * (n - 100)));
  let zaman = 1.7e12 + r() * 1000;
  let gv = 0;
  let ga = 0;
  for (let i = 0; i < n; i++) {
    if (i > 0) zaman += boslukYeri.has(i) ? 400 + r() * 60000 : 2 + (r() - 0.5) * 0.6;
    t[i] = zaman;
    gv = 0.98 * gv + (r() - 0.5) * 0.05;
    ga = 0.98 * ga + (r() - 0.5) * 0.01;
    v[i] = 12 + gv;
    a[i] = 0.5 + ga;
  }
  for (let i = 0; i < n; i++) {
    if (r() < 0.001) v[i] = NaN;
    if (r() < 0.001) a[i] = NaN;
  }
  const bas = Math.floor(n * 0.7);
  for (let i = bas; i < bas + 500; i++) v[i] = NaN;
  return { t, v, a, bosluklar: [...boslukYeri].sort((p, q) => p - q) };
}

/** K tek örneklik sıçrama (± dönüşümlü değil, rastgele işaret); ilk/son, boşluk kenarları dahil. */
function sicramaEkle(t, y, bosluklar, K, r, taban, genlik) {
  const n = y.length;
  const yerler = new Set([0, n - 1]);
  for (const g of bosluklar.slice(0, 5)) {
    yerler.add(g - 1);
    yerler.add(g);
  }
  while (yerler.size < K) yerler.add(Math.floor(r() * n));
  const sicramalar = [];
  let j = 0;
  for (const i of [...yerler].sort((p, q) => p - q)) {
    const isaret = j % 2 === 0 ? 1 : -1; // yarısı +, yarısı −
    const deger = taban + isaret * genlik * (1 + 0.013 * j++);
    y[i] = deger;
    sicramalar.push({ i, t: t[i], deger, isaret });
  }
  return sicramalar;
}

/** Ö1 düzeneği: 200 000 nokta, V'de 64 ve A'da 64 sıçrama. */
function o1Duzenek() {
  const n = 200_000;
  const { t, v, a, bosluklar } = kayitUret(n, 20261002);
  const r = rastgele(77);
  const sicV = sicramaEkle(t, v, bosluklar, 64, r, 12, 4);
  const sicA = sicramaEkle(t, a, bosluklar, 64, r, 0.5, 1.5);
  const seriler = [
    seriHazirla({ ad: 'V', t, y: v, birim: 'V', renk: 'volt', eksen: 'sol', boslukMs: BOSLUK_MS }),
    seriHazirla({ ad: 'A', t, y: a, birim: 'A', renk: 'amper', eksen: 'sag', boslukMs: BOSLUK_MS }),
  ];
  return { t, v, a, bosluklar, sicramalar: [sicV, sicA], seriler };
}

/** Plandaki k kanalının köşeleri ve parçaları (CSS px). */
function plandanKanal(plan, k) {
  const koseler = [];
  const parcalar = [];
  for (const c of plan.komutlar) {
    if (c.rol !== 'seri' || c.kanal !== k) continue;
    if (c.tur === 'nokta') koseler.push([c.x, c.y]);
    else if (c.tur === 'cizgi') {
      const p = c.noktalar;
      for (let i = 0; i < p.length; i += 2) koseler.push([p[i], p[i + 1]]);
      for (let i = 2; i < p.length; i += 2) parcalar.push([p[i - 2], p[i - 1], p[i], p[i + 1]]);
    }
  }
  return { koseler, parcalar };
}

/** Sahte bağlamın çizim çağrılarından bir rengin köşe ve parçaları. */
function baglamdanRenk(ctx, renk) {
  const koseler = [];
  const parcalar = [];
  for (const v of ctx.vuruslar) {
    if (v.renk !== renk) continue;
    let onceki = null;
    for (const [x, y, tur] of v.yol) {
      if (tur === 'arc') continue;
      koseler.push([x, y]);
      if (tur === 'lineTo' && onceki) parcalar.push([onceki[0], onceki[1], x, y]);
      onceki = [x, y];
    }
  }
  for (const d of ctx.dolgular) {
    if (d.renk !== renk) continue;
    for (const [x, y, tur] of d.yol) if (tur === 'arc') koseler.push([x, y]);
  }
  return { koseler, parcalar };
}

/** Köşe kovası: floor(x) → [y…]. */
function kovala(koseler) {
  const kova = new Map();
  for (const [x, y] of koseler) {
    const k = Math.floor(x);
    if (!kova.has(k)) kova.set(k, []);
    kova.get(k).push([x, y]);
  }
  return kova;
}

function koseVar(kova, xs, ys, dx = 1.5, dy = 1) {
  for (let k = Math.floor(xs - dx) - 1; k <= Math.floor(xs + dx) + 1; k++) {
    for (const [x, y] of kova.get(k) || []) if (Math.abs(x - xs) <= dx && Math.abs(y - ys) <= dy) return true;
  }
  return false;
}

/** ozet.js sütun SÖZLEŞMESİ: t'nin sütunu (sınırlar s_c = t0 + (t1 − t0)·c/W, t1'e kırpılı). */
function sozlesmeSutunu(t, t0, t1, W) {
  const s = (c) => Math.min(t0 + (t1 - t0) * c / W, t1);
  let c = Math.min(W - 1, Math.max(0, Math.floor((t - t0) / (t1 - t0) * W)));
  while (c > 0 && s(c) > t) c--;
  while (c < W - 1 && s(c + 1) <= t) c++;
  return c;
}

/** Görünür pencerenin kaba kuvvet min/maks'ı. */
function kabaUclar(t, y, x0, x1) {
  let enk = Infinity;
  let enb = -Infinity;
  const b = ilkBuyuk(t, x1);
  for (let i = ilkBuyukEsit(t, x0); i < b; i++) {
    const v = y[i];
    if (Number.isNaN(v)) continue;
    if (v < enk) enk = v;
    if (v > enb) enb = v;
  }
  return [enk, enb];
}

/**
 * Bir plan (ya da çizim çağrıları) için Ö1 + boşluk + oto ölçek iddiaları.
 * kanal = {k, t, y, sicramalar}; geo = {koseler, parcalar}.
 */
function o1Sina(plan, kanal, geo, sayac, etiket, { olcekSina = true } = {}) {
  const { alan } = plan;
  const { t0: x0, t1: x1 } = plan.x;
  const W = alan.w;
  const bilgi = plan.kanallar[kanal.k];
  assert.ok(bilgi, `kanal bilgisi ${etiket}`);
  const eks = plan.eksenler[bilgi.eksen];
  const ty = (v) => alan.y + alan.h - (v - eks.min) * alan.h / (eks.maks - eks.min);
  const tx = (tt) => alan.x + (tt - x0) * alan.w / (x1 - x0);
  sayac[bilgi.kip] = (sayac[bilgi.kip] || 0) + 1;

  // (1) Ö1: penceredeki her sıçrama, kendi sütununda (±1) kendi y'sine ulaşan bir köşe.
  // Özet kipte aynı sütunda AYNI YÖNDE daha uç bir sıçrama varsa o sütunun ucu odur
  // (ozet.js Ö1 b: "kendisinden daha uç bir değer yoksa"); gürültü (|δ| ≲ 0.2) hiçbir
  // sıçramaya (≥ 1.5) yaklaşmaz, yani başka bir uç ancak başka bir sıçrama olabilir.
  const kova = kovala(geo.koseler);
  const gorunur = kanal.sicramalar.filter((s) => s.t >= x0 && s.t <= x1 && !Number.isNaN(kanal.y[s.i]));
  const baskin = new Map(); // sütun → {arti, eksi}: o sütunun en uç sıçramaları
  if (bilgi.kip === 'ozet') {
    for (const s of gorunur) {
      const c = sozlesmeSutunu(s.t, x0, x1, W);
      const b = baskin.get(c) || { arti: -Infinity, eksi: Infinity };
      if (s.isaret > 0) b.arti = Math.max(b.arti, s.deger);
      else b.eksi = Math.min(b.eksi, s.deger);
      baskin.set(c, b);
    }
  }
  for (const s of gorunur) {
    if (bilgi.kip === 'ozet') {
      const b = baskin.get(sozlesmeSutunu(s.t, x0, x1, W));
      if (s.isaret > 0 ? b.arti > s.deger : b.eksi < s.deger) {
        sayac.ortulu++;
        continue;
      }
    }
    const xs = tx(s.t);
    const ys = ty(s.deger);
    assert.ok(ys >= alan.y - 1e-6 && ys <= alan.y + alan.h + 1e-6,
      `Ö1: sıçrama ${s.deger} ekseni dışında (y=${ys}, alan ${alan.y}…${alan.y + alan.h}) ${etiket}`);
    assert.ok(koseVar(kova, xs, ys), `Ö1: sıçrama i=${s.i} (${s.isaret > 0 ? '+' : '−'}${s.deger}) ` +
      `çizimde yok: x=${xs.toFixed(2)} y=${ys.toFixed(2)} kip=${bilgi.kip} ${etiket}`);
    sayac[s.isaret > 0 ? 'arti' : 'eksi']++;
  }

  // (2) Boşluk: iki yanı pencerede olan boşluğun üstünden çizgi YOK.
  for (const [ta, tb] of kanal.bosluklar) {
    if (ta < x0 || tb > x1) continue;
    let L;
    let R;
    if (bilgi.kip === 'ham') {
      L = tx(ta) + 1e-6;
      R = tx(tb) - 1e-6;
    } else {
      const ca = sozlesmeSutunu(ta, x0, x1, W);
      const cb = sozlesmeSutunu(tb, x0, x1, W);
      if (cb === ca) continue; // sütun içi boşluk piksel altıdır (ozet.js sözleşmesi)
      L = alan.x + ca + 0.5 + 1e-6;
      R = alan.x + cb + 0.5 - 1e-6;
      sayac[cb === ca + 1 ? 'bitisikBosluk' : 'genisBosluk']++;
    }
    for (const [xa, , xb] of geo.parcalar) {
      const sol = Math.min(xa, xb);
      const sag = Math.max(xa, xb);
      assert.ok(!(sol <= L && sag >= R), `boşluk (t ${ta}→${tb}) üstünden çizgi: ${sol}→${sag} kip=${bilgi.kip} ${etiket}`);
    }
    sayac.bosluk++;
  }

  // (3) Özet kipte çizgi yalnız BİTİŞİK sütunları bağlar (boş sütun = kesik).
  if (bilgi.kip === 'ozet') {
    for (const [xa, , xb] of geo.parcalar) {
      assert.ok(Math.abs(xb - xa) <= 1 + 1e-9, `özet kipte ${xa}→${xb} bitişik değil ${etiket}`);
    }
  }

  // (4) Oto ölçek: görünür verinin TAM uçları (+%5 pay) — sıçramalar dahil. (Her eksende
  // tek kanal var: V solda, A sağda.)
  if (olcekSina) {
    const [enk, enb] = kabaUclar(kanal.t, kanal.y, x0, x1);
    if (enb > enk) {
      const aralik = enb - enk;
      const tol = 1e-9 * Math.max(1, Math.abs(enb), Math.abs(enk));
      assert.ok(Math.abs(eks.min - (enk - PAY * aralik)) <= tol && Math.abs(eks.maks - (enb + PAY * aralik)) <= tol,
        `oto ölçek [${eks.min}, ${eks.maks}] ≠ kaba [${enk}, ${enb}] ± %5 ${etiket}`);
      sayac.olcek++;
    }
  }
}

/** Kayıttaki boşluklar: [önceki örneğin zamanı, sonrakinin zamanı]. */
function boslukCiftleri(t) {
  const c = [];
  for (let g = 1; g < t.length; g++) if (t[g] - t[g - 1] > BOSLUK_MS) c.push([t[g - 1], t[g]]);
  return c;
}

const yeniSayac = () => ({ arti: 0, eksi: 0, ortulu: 0, bosluk: 0, bitisikBosluk: 0, genisBosluk: 0, olcek: 0, ham: 0, ozet: 0 });

// ── sahte kanvas ────────────────────────────────────────────────────────────

class SahteBaglam {
  constructor() {
    this.cagrilar = [];
    this.vuruslar = [];
    this.dolgular = [];
    this.dikdortgenler = [];
    this.yazilar = [];
    this.yol = [];
    this.desen = [];
    this.strokeStyle = '#000';
    this.fillStyle = '#000';
    this.lineWidth = 1;
    this.globalAlpha = 1;
    this.font = '';
    this.textAlign = 'start';
    this.textBaseline = 'alphabetic';
    this.lineJoin = 'miter';
    this.lineCap = 'butt';
    this.derinlik = 0;
  }

  sifirla() {
    this.cagrilar = [];
    this.vuruslar = [];
    this.dolgular = [];
    this.dikdortgenler = [];
    this.yazilar = [];
  }

  setTransform(...a) { this.cagrilar.push(['setTransform', ...a]); }
  clearRect(...a) { this.cagrilar.push(['clearRect', ...a]); }
  beginPath() { this.yol = []; }
  moveTo(x, y) { this.yol.push([x, y, 'moveTo']); }
  lineTo(x, y) { this.yol.push([x, y, 'lineTo']); }
  arc(x, y, r) { this.yol.push([x, y, 'arc', r]); }
  rect(x, y, w, h) { this.yol.push([x, y, 'rect', w, h]); }
  stroke() {
    for (const [x, y] of this.yol) assert.ok(Number.isFinite(x) && Number.isFinite(y), `sonlu olmayan köşe ${x},${y}`);
    this.vuruslar.push({ renk: this.strokeStyle, kalinlik: this.lineWidth, yol: this.yol.slice(), desen: this.desen.slice() });
  }
  fill() { this.dolgular.push({ renk: this.fillStyle, yol: this.yol.slice() }); }
  clip() { this.cagrilar.push(['clip']); }
  save() { this.derinlik++; this.cagrilar.push(['save']); }
  restore() { this.derinlik--; this.cagrilar.push(['restore']); }
  setLineDash(d) { this.desen = d.slice(); }
  fillRect(x, y, w, h) { this.dikdortgenler.push({ tur: 'dolgu', renk: this.fillStyle, alfa: this.globalAlpha, x, y, w, h }); }
  strokeRect(x, y, w, h) { this.dikdortgenler.push({ tur: 'kenar', renk: this.strokeStyle, x, y, w, h }); }
  fillText(metin, x, y) { this.yazilar.push({ metin, x, y, renk: this.fillStyle, hiza: this.textAlign }); }
  measureText(m) { return { width: String(m).length * 6 }; }
}

function sahteKanvas(w = 800, h = 300) {
  const dinleyiciler = new Map();
  const ctx = new SahteBaglam();
  return {
    clientWidth: w,
    clientHeight: h,
    width: 300,
    height: 150,
    style: {},
    tabIndex: -1,
    odak: 0,
    yakalanan: [],
    ctx,
    secenekler: {},
    getContext(tur) { return tur === '2d' ? ctx : null; },
    addEventListener(tur, fn, ops) {
      if (!dinleyiciler.has(tur)) dinleyiciler.set(tur, new Set());
      dinleyiciler.get(tur).add(fn);
      this.secenekler[tur] = ops;
    },
    removeEventListener(tur, fn) { if (dinleyiciler.has(tur)) dinleyiciler.get(tur).delete(fn); },
    focus() { this.odak++; },
    setPointerCapture(id) { this.yakalanan.push(id); },
    gonder(tur, olay = {}) {
      const e = { engellendi: false, preventDefault() { this.engellendi = true; }, ...olay };
      for (const fn of dinleyiciler.get(tur) || []) fn(e);
      return e;
    },
    dinleyiciSayisi() {
      let n = 0;
      for (const s of dinleyiciler.values()) n += s.size;
      return n;
    },
    dinlenenler() { return [...dinleyiciler.entries()].filter(([, s]) => s.size).map(([t]) => t).sort(); },
  };
}

/** Düzgün seri (reducer testleri): 0…400 000 ms, 2 ms adım. */
function duzgunDurum() {
  const n = 200_001;
  const t = new Float64Array(n).map((_, i) => i * 2);
  return durumKur([{ t, y: new Float64Array(n) }]);
}

const ALAN = { x: 56, y: 16, w: 1000, h: 262 };
const xdenT = (d, x) => d.t0 + (x - ALAN.x) / ALAN.w * (d.t1 - d.t0);
const tdenX = (d, t) => ALAN.x + (t - d.t0) / (d.t1 - d.t0) * ALAN.w;

// ── 1. ÖLÇEK ────────────────────────────────────────────────────────────────

test('güzel adımlar: 1-2-5, aralığın içinde, eşit aralıklı, yuvarlak', () => {
  assert.deepEqual(guzelAdimlar(0, 1, 5), { adim: 0.2, degerler: [0, 0.2, 0.4, 0.6, 0.8, 1] });
  assert.deepEqual(guzelAdimlar(-7.3, -0.2, 5), { adim: 1, degerler: [-7, -6, -5, -4, -3, -2, -1] });
  const sifirli = guzelAdimlar(-3, 12, 5);
  assert.equal(sifirli.adim, 2);
  assert.ok(sifirli.degerler.includes(0) && sifirli.degerler.every((v) => !Object.is(v, -0)), 'sıfır var, −0 yok');
  assert.deepEqual(guzelAdimlar(0.1, 0.3, 2), { adim: 0.1, degerler: [0.1, 0.2, 0.3] }, 'kayan nokta kırıntısı yok');
  assert.deepEqual(guzelAdimlar(5, 5, 5), { adim: NaN, degerler: [] }, 'sabit aralık: çentik yok, çökme yok');
  assert.deepEqual(guzelAdimlar(NaN, 1, 5).degerler, []);

  const r = rastgele(5);
  for (let k = 0; k < 2000; k++) {
    const olcek = 10 ** (r() * 18 - 9);
    const min = (r() - 0.5) * 20 * olcek;
    const maks = min + olcek * (0.01 + r() * 10);
    const hedef = 2 + Math.floor(r() * 10);
    const { adim, degerler } = guzelAdimlar(min, maks, hedef);
    const e = Math.floor(Math.log10(adim) + 1e-12);
    const m = adim / 10 ** e;
    assert.ok([1, 2, 5, 10].some((c) => Math.abs(m - c) < 1e-9), `adım ${adim} 1-2-5 değil`);
    assert.ok(degerler.length >= Math.floor(hedef / 2) && degerler.length <= Math.ceil(hedef * 1.8) + 1,
      `${degerler.length} çentik, hedef ${hedef} (${min}…${maks}, adım ${adim})`);
    for (let i = 0; i < degerler.length; i++) {
      const v = degerler[i];
      assert.ok(v >= min - adim * 1e-6 && v <= maks + adim * 1e-6, `çentik ${v} dışarıda`);
      assert.ok(Math.abs(v / adim - Math.round(v / adim)) < 1e-6, `çentik ${v} adımın katı değil`);
      if (i) assert.ok(Math.abs(v - degerler[i - 1] - adim) <= adim * 1e-9, 'eşit aralık');
    }
  }
  assert.equal(guzelAdim(0), 1);
  assert.equal(guzelAdim(-5), 1);
  assert.equal(guzelAdim(Infinity), 1);
});

test('eksen aralığı: pay, sabit veri, sıfır, veri yok — sıfıra bölme yok', () => {
  assert.deepEqual(eksenAraligi(0, 10), [-0.5, 10.5]);
  assert.deepEqual(eksenAraligi(10, 0), [-0.5, 10.5], 'ters uçlar');
  assert.deepEqual(eksenAraligi(5, 5), [4.75, 5.25], 'sabit: ±%5·|v|');
  assert.deepEqual(eksenAraligi(-2, -2), [-2.1, -1.9]);
  assert.deepEqual(eksenAraligi(0, 0), [-1, 1], 'sabit sıfır: ±1');
  assert.deepEqual(eksenAraligi(NaN, NaN), [0, 1], 'veri yok');
  assert.deepEqual(eksenAraligi(-Infinity, 3), [0, 1]);
  const [a, b] = eksenAraligi(12.0000000000001, 12.0000000000002);
  assert.ok(b > a && b - a > 0.1, `neredeyse sabit veri yine ±%5: ${a}…${b}`);
});

test('zaman adımları ve yazılar', () => {
  const izinli = new Set([1000, 2000, 5000, 10000, 15000, 30000, 60000, 120000, 300000, 600000, 900000,
    1800000, 3600000, 7200000, 10800000, 21600000, 43200000, 86400000, 172800000, 604800000]);
  for (const aralik of [5, 37, 999, 4000, 59000, 61000, 3.6e6, 2.5e7, 8.64e7, 3e8, 2.6e9]) {
    const adim = zamanAdimi(aralik, 6);
    if (aralik / 6 >= 1000 && aralik / 6 <= 604800000) assert.ok(izinli.has(adim), `${aralik}: adım ${adim}`);
    const koken = 1.7e12 + 123.4;
    const { degerler } = zamanAdimlari(koken + aralik * 0.13, koken + aralik * 1.13, 6, koken);
    assert.ok(degerler.length >= 2 && degerler.length <= 13, `${aralik}: ${degerler.length} çentik`);
    for (const t of degerler) {
      assert.ok(t >= koken + aralik * 0.13 - 1e-3 && t <= koken + aralik * 1.13 + 1e-3);
      const k = (t - koken) / adim;
      assert.ok(Math.abs(k - Math.round(k)) < 1e-6, 'çentik kökene göre yuvarlak');
    }
  }
  assert.deepEqual(zamanAdimlari(5, 5).degerler, []);
  assert.equal(zamanYazi(0), '00:00:00');
  assert.equal(zamanYazi(3723000), '01:02:03');
  assert.equal(zamanYazi(90061000), '25:01:01', 'saat 24ü geçer, gün sözcüğü yok (G8)');
  assert.equal(zamanYazi(1500, 500), '00:00:01.5');
  assert.equal(zamanYazi(1234.5, 1), '00:00:01.235');
  assert.equal(zamanYazi(59999.6, 1000), '00:01:00', 'yuvarlama taşması');
  assert.equal(zamanYazi(-5000), '−00:00:05');
  assert.equal(zamanYazi(-0.1, 1000), '00:00:00', 'eksi sıfır yok');
  assert.equal(sayiYazi(-1.5, 0.5), '−1.5');
  assert.equal(sayiYazi(-0.00001, 0.1), '0.0', 'eksi sıfır yok');
  assert.equal(sayiYazi(2500, 500), '2500');
  assert.equal(sayiYazi(0.000123, 0.00002), '0.00012');
});

test('yerleşim: eksenlere göre kenar boşluğu, gezgin kenarsız, negatif boyut yok', () => {
  const sol = [{ eksen: 'sol' }];
  const iki = [{ eksen: 'sol' }, { eksen: 'sag' }];
  assert.deepEqual(yerlesim(sol, { w: 800, h: 300 }), { x: 56, y: 16, w: 734, h: 262 });
  assert.deepEqual(yerlesim(iki, { w: 800, h: 300 }), { x: 56, y: 16, w: 688, h: 262 });
  assert.deepEqual(yerlesim(iki, { w: 800, h: 44 }, { gezgin: true }), { x: 0, y: 1, w: 800, h: 42 });
  assert.deepEqual(yerlesim(sol, { w: 10, h: 10 }), { x: 56, y: 16, w: 0, h: 0 });
  assert.deepEqual(yerlesim(sol, { w: 500, h: 200 }, { kenar: { sol: 70 } }).x, 70);
});

test('oto ölçek: sabit / sıfır / eksi / NaN veri — sonlu koordinat, sıçramayı kapsar', () => {
  const n = 5000;
  const t = new Float64Array(n).map((_, i) => i * 10);
  const durum = durumKur([{ t }]);
  const kos = (y, ad) => {
    const s = seriHazirla({ ad, t, y, birim: 'V' });
    const plan = cizimPlani([s], durum, { w: 900, h: 300 });
    for (const c of plan.komutlar) {
      if (c.noktalar) for (const v of c.noktalar) assert.ok(Number.isFinite(v), `${ad}: sonlu olmayan koordinat`);
      if (c.tur === 'nokta' || c.tur === 'yazi') assert.ok(Number.isFinite(c.x) && Number.isFinite(c.y), `${ad}: ${c.tur}`);
    }
    return plan;
  };
  const sabit = kos(new Float64Array(n).fill(3.3), 'sabit');
  assert.ok(Math.abs(sabit.eksenler.sol.min - 3.135) < 1e-12 && Math.abs(sabit.eksenler.sol.maks - 3.465) < 1e-12);
  const yatay = sabit.komutlar.find((c) => c.rol === 'seri' && c.tur === 'cizgi');
  const ortaY = sabit.alan.y + sabit.alan.h / 2;
  for (let i = 1; i < yatay.noktalar.length; i += 2) assert.ok(Math.abs(yatay.noktalar[i] - ortaY) < 1e-9, 'sabit veri ortada yatay');
  assert.deepEqual([kos(new Float64Array(n), 'sifir').eksenler.sol.min, kos(new Float64Array(n), 'sifir').eksenler.sol.maks], [-1, 1]);
  const eksi = kos(new Float64Array(n).map((_, i) => -5 - Math.sin(i / 100)), 'eksi').eksenler.sol;
  assert.ok(eksi.maks < 0 && eksi.min < -5.9 && eksi.degerler.length >= 2);
  const bos = kos(new Float64Array(n).fill(NaN), 'nan');
  assert.deepEqual([bos.eksenler.sol.min, bos.eksenler.sol.maks], [0, 1]);
  assert.equal(bos.komutlar.filter((c) => c.rol === 'seri').length, 0, 'NaN veri: çizgi yok');

  // Tek örneklik sıçrama ölçeği belirler (özet kipte de).
  const y = new Float64Array(n).map((_, i) => Math.sin(i / 50));
  y[2345] = 40;
  y[4321] = -33;
  const plan = kos(y, 'sicrama');
  assert.equal(plan.kanallar[0].kip, 'ozet');
  assert.ok(Math.abs(plan.eksenler.sol.maks - (40 + 0.05 * 73)) < 1e-9 && Math.abs(plan.eksenler.sol.min - (-33 - 0.05 * 73)) < 1e-9,
    `ölçek [${plan.eksenler.sol.min}, ${plan.eksenler.sol.maks}] sıçramaları kapsamıyor`);
});

test('enAzAralik: düz sinyalin ekseni bundan dar olmaz, ortası korunur, sıçrama yine içeride; yoksa TAM ölçek', () => {
  const n = 4000;
  const t = new Float64Array(n).map((_, i) => i * 100);
  const y = new Float64Array(n).map((_, i) => 1 + 0.002 * Math.sin(i / 3));
  const d = durumKur([{ t }]);
  const tam = pencereHesapla([seriHazirla({ ad: 'I', t, y, birim: 'A' })], d, { w: 800, h: 300 }).eksenler.sol;
  assert.ok(tam.maks - tam.min < 0.005, 'verilmezse ölçek TAM veri (G3)');
  const genis = pencereHesapla([seriHazirla({ ad: 'I', t, y, birim: 'A', enAzAralik: 0.5 })], d, { w: 800, h: 300 }).eksenler.sol;
  assert.ok(Math.abs(genis.maks - genis.min - 0.5) < 1e-12 && Math.abs((genis.maks + genis.min) / 2 - 1) < 1e-6);
  y[1234] = 3; // sıçrama en az aralıktan geniş: ölçek yine TAM uçlardan
  const sic = pencereHesapla([seriHazirla({ ad: 'I', t, y, birim: 'A', enAzAralik: 0.5 })], d, { w: 800, h: 300 }).eksenler.sol;
  assert.ok(sic.maks >= 3 && sic.min <= 0.998);
});

test('pencereHesapla: ana grafikte pencere, gezginde bütün veri; gizli kanal sorgulanmaz', () => {
  const t = new Float64Array(10000).map((_, i) => i);
  const y = new Float64Array(10000).map((_, i) => i);
  const s = [seriHazirla({ ad: 'V', t, y, birim: 'V' }), seriHazirla({ ad: 'A', t, y, birim: 'A', eksen: 'sag', gizli: true })];
  const d = durumBirlestir(durumKur(s), { t0: 2000, t1: 3000 });
  const ana = pencereHesapla(s, d, { w: 600, h: 200 });
  assert.deepEqual([ana.x.t0, ana.x.t1], [2000, 3000]);
  assert.ok(Math.abs(ana.eksenler.sol.min - (2000 - 50)) < 1e-9 && Math.abs(ana.eksenler.sol.maks - (3000 + 50)) < 1e-9);
  assert.equal(ana.eksenler.sag, undefined, 'gizli kanalın ekseni yok');
  assert.equal(ana.sorgular[1], null);
  const gez = pencereHesapla(s, d, { w: 600, h: 44 }, { gezgin: true });
  assert.deepEqual([gez.x.t0, gez.x.t1], [0, 9999]);
  assert.ok(gez.eksenler.sol.maks > 9999);
  assert.deepEqual(lejantOgeleri(s), [{ ad: 'V', birim: 'V', renk: 'volt', eksen: 'sol' }]);
});

// ── 2. ÇİZİM PLANI: Ö1 ──────────────────────────────────────────────────────

test('Ö1 çizim PLANINDA: 200 000 nokta, 2×64 sıçrama, her yakınlaştırmada min ve maks görünür; boşlukta çizgi yok', () => {
  const dz = o1Duzenek();
  const { t, seriler } = dz;
  const bosluklar = boslukCiftleri(t);
  assert.equal(bosluklar.length, 10);
  const r = rastgele(4242);
  const boyutlar = [{ w: 120, h: 80 }, { w: 480, h: 200 }, { w: 1000, h: 300 }, { w: 1366, h: 260 }, { w: 1920, h: 400 }];
  const hepsi = [0, 1, 2, 3, 4];
  const temel = durumKur(seriler);
  const T0 = temel.veriT0;
  const T1 = temel.veriT1;
  const isler = [[T0, T1, hepsi]]; // [t0, t1, boyut indisleri]
  for (let k = 0; k < 60; k++) { // log-düzgün genişlik, rastgele yer
    const aralik = (T1 - T0) * 10 ** (-r() * 5.5);
    const bas = T0 + r() * (T1 - T0 - aralik);
    isler.push([bas, bas + aralik, hepsi]);
  }
  let d = 0;
  for (const s of dz.sicramalar[0].slice(0, 24)) { // sıçrama içeride, her düzeyde
    for (const aralik of [20, 300, 4000, 60000, 1e6]) {
      isler.push([s.t - aralik * r(), s.t + aralik * r() + 1, [d % 5, (d + 2) % 5]]);
      d++;
    }
  }
  for (const s of dz.sicramalar[1].slice(0, 6)) {
    isler.push([s.t, s.t + 5000, [1, 4]]); // sıçrama tam sol kenarda
    isler.push([s.t - 5000, s.t, [1, 4]]); // tam sağ kenarda
  }
  for (const [ta, tb] of bosluklar) { // boşluk: ham kipte iki yanı + özet kipte 0.7–2.5 sütunluk
    isler.push([ta - 30, tb + 30, hepsi]);
    for (let bi = 0; bi < boyutlar.length; bi++) {
      const W = yerlesim(seriler, boyutlar[bi]).w;
      for (const q of [0.7, 1.3, 1.9, 2.5]) {
        const aralik = (tb - ta) * W / q;
        const bas = ta - aralik * (0.2 + 0.6 * r());
        isler.push([bas, bas + aralik, [bi]]);
      }
    }
  }

  const sayac = yeniSayac();
  let planSayisi = 0;
  for (const [p0, p1, bler] of isler) {
    const durum = durumBirlestir(temel, { t0: p0, t1: p1 });
    for (const bi of bler) {
      const boyut = boyutlar[bi];
      const plan = cizimPlani(seriler, durum, boyut);
      planSayisi++;
      const etiket = `[${durum.t0 - T0}…${durum.t1 - T0}] ${boyut.w}×${boyut.h}`;
      for (let k = 0; k < 2; k++) {
        o1Sina(plan, { k, t, y: seriler[k].y, sicramalar: dz.sicramalar[k], bosluklar }, plandanKanal(plan, k), sayac, etiket);
      }
    }
  }
  console.log(`  Ö1 plan sayaçları: ${JSON.stringify(sayac)} (${planSayisi} plan)`);
  assert.ok(sayac.arti > 500 && sayac.eksi > 500, 'hem + hem − sıçramalar çok kez sınandı');
  assert.ok(sayac.ham > 50 && sayac.ozet > 300, 'iki kip de sınandı');
  assert.ok(sayac.bitisikBosluk > 20, `bitişik sütunlu boşluk (kesik[c]) sınandı: ${sayac.bitisikBosluk}`);
  assert.ok(sayac.genisBosluk > 20 && sayac.bosluk > 200 && sayac.olcek > 500);
});

test('Ö1 sahte kanvasın ÇİZİM ÇAĞRILARINDA (dpr 1 ve 2): sıçrama görünür, boşlukta çizgi yok', () => {
  const dz = o1Duzenek();
  const { t, seriler } = dz;
  const bosluklar = boslukCiftleri(t);
  const r = rastgele(99);
  const sayac = yeniSayac();
  // Dar kanvas (alan 18 px): uzun boşluklar da kayıt içinde 1–2 sütuna sığar.
  for (const [dpr, w, h] of [[1, 1000, 300], [2, 640, 220], [1.5, 1366, 260], [3, 130, 90]]) {
    const kanvas = sahteKanvas(w, h);
    const g = new Grafik(kanvas, { pencere: { devicePixelRatio: dpr } });
    g.veriAyarla(seriler);
    const T0 = g.durum.veriT0;
    const T1 = g.durum.veriT1;
    const pencereler = [[T0, T1]];
    for (let k = 0; k < 25; k++) {
      const aralik = (T1 - T0) * 10 ** (-r() * 5);
      const bas = T0 + r() * (T1 - T0 - aralik);
      pencereler.push([bas, bas + aralik]);
    }
    for (const s of dz.sicramalar[0].slice(0, 10)) pencereler.push([s.t - 50, s.t + 70], [s.t - 2e4, s.t + 3e4]);
    const W = yerlesim(seriler, { w, h }).w;
    for (const [ta, tb] of bosluklar.slice(0, 6)) {
      pencereler.push([ta - 30, tb + 30], [ta - 3e5, tb + 3e5]);
      for (const q of [0.7, 1.3, 1.9]) { // özet kipte boşluk ~1–2 sütun: kesik[c] yolu
        const aralik = (tb - ta) * W / q;
        const bas = ta - aralik * (0.2 + 0.6 * r());
        pencereler.push([bas, bas + aralik]);
      }
    }
    for (const [p0, p1] of pencereler) {
      g.durumAyarla({ t0: p0, t1: p1 });
      kanvas.ctx.sifirla();
      const plan = g.ciz();
      const sonDonusum = kanvas.ctx.cagrilar.filter((c) => c[0] === 'setTransform').at(-1);
      assert.deepEqual(sonDonusum, ['setTransform', dpr, 0, 0, dpr, 0, 0]);
      for (let k = 0; k < 2; k++) {
        const renk = RENK_YEDEK[seriler[k].renk];
        o1Sina(plan, { k, t, y: seriler[k].y, sicramalar: dz.sicramalar[k], bosluklar }, baglamdanRenk(kanvas.ctx, renk), sayac,
          `dpr ${dpr} ${w}×${h} [${p0 - T0}…${p1 - T0}]`, { olcekSina: false });
      }
    }
    g.yokEt();
  }
  console.log(`  Ö1 çizim çağrısı sayaçları: ${JSON.stringify(sayac)}`);
  assert.ok(sayac.arti > 100 && sayac.eksi > 100 && sayac.bosluk > 20);
  assert.ok(sayac.bitisikBosluk > 3, `bitişik sütunlu boşluk çizim çağrılarında da: ${sayac.bitisikBosluk}`);
});

test('özet kip sütunu: dikey min→maks, önceki noktaya yakın uçtan girilir; tek örnekli kanal nokta olur', () => {
  // 3 sütunluk el yapımı veri: her sütunda iki örnek.
  const t = Float64Array.of(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
  const y = Float64Array.of(0, 10, 9, 1, 2, 8, 5, 5, 3, 7);
  const s = [seriHazirla({ ad: 'V', t, y })];
  const durum = durumKur(s);
  const plan = cizimPlani(s, durum, { w: 10 + 56 + 4, h: 116 }, { kenar: { sol: 56, sag: 10, ust: 16, alt: 0 } });
  assert.equal(plan.alan.w, 4);
  assert.equal(plan.kanallar[0].kip, 'ozet');
  const cizgi = plan.komutlar.find((c) => c.rol === 'seri');
  const ty = (v) => 16 + 100 - (v - plan.eksenler.sol.min) * 100 / (plan.eksenler.sol.maks - plan.eksenler.sol.min);
  // Sütunlar (W = 4, sınırlar 0, 2.25, 4.5, 6.75, 9): {0,1,2}→[0,10] {3,4}→[1,2] {5,6}→[5,8] {7,8,9}→[3,7].
  // İlk sütun maks→min (önceki nokta yok); sonra her sütuna önceki noktaya YAKIN uçtan girilir.
  const bek = [56.5, ty(10), 56.5, ty(0), 57.5, ty(1), 57.5, ty(2), 58.5, ty(5), 58.5, ty(8), 59.5, ty(7), 59.5, ty(3)];
  assert.deepEqual([...cizgi.noktalar].map((v) => +v.toFixed(9)), bek.map((v) => +v.toFixed(9)));

  const tek = [seriHazirla({ ad: 'V', t: Float64Array.of(5), y: Float64Array.of(2) })];
  const tekPlan = cizimPlani(tek, durumKur(tek), { w: 400, h: 200 });
  const nokta = tekPlan.komutlar.find((c) => c.rol === 'seri');
  assert.equal(nokta.tur, 'nokta', 'tek örnek: nokta komutu');
  assert.ok(Math.abs(nokta.x - (tekPlan.alan.x + tekPlan.alan.w / 2)) < 1e-9);
});

test('ham kip: NaN çizgiyi keser; pencere dışındaki komşu kenara çekilir (eğim korunur, dev koordinat yok)', () => {
  // 0…400 ms (10 ms adım, y = indis, 100 ms'de NaN), sonra 1e9 ms'de tek örnek.
  const t = new Float64Array(42).map((_, i) => (i <= 40 ? i * 10 : 1e9));
  const y = new Float64Array(42).map((_, i) => (i === 10 ? NaN : i));
  const s = [seriHazirla({ ad: 'V', t, y })];
  const durum = durumBirlestir(durumKur(s), { t0: 50, t1: 450 });
  assert.deepEqual([durum.t0, durum.t1], [50, 450]);
  const plan = cizimPlani(s, durum, { w: 466, h: 200 });
  assert.equal(plan.alan.w, 400);
  assert.equal(plan.kanallar[0].kip, 'ham');
  const cizgiler = plan.komutlar.filter((c) => c.rol === 'seri' && c.tur === 'cizgi');
  assert.equal(cizgiler.length, 2, 'NaN iki parçaya böler');
  const tx = (tt) => plan.alan.x + (tt - 50) * plan.alan.w / 400;
  const L = plan.alan.x - 4;
  const R = plan.alan.x + plan.alan.w + 4;
  const ilk = cizgiler[0].noktalar;
  assert.equal(ilk[0], L, 'soldaki komşu (t = 40) kenara çekildi');
  assert.ok(Math.abs(ilk[ilk.length - 2] - tx(90)) < 1e-9, 'ilk parça NaN\'dan önce biter');
  const son = cizgiler[1].noktalar;
  assert.ok(Math.abs(son[0] - tx(110)) < 1e-9, 'ikinci parça NaN\'dan sonra başlar');
  assert.equal(son[son.length - 2], R, 'uzak komşu (1e9) sağ kenara çekildi, dev koordinat yok');
  // Kenara çekilen nokta 400 → 1e9 doğrusunun üstünde (eğim korunur).
  const eks = plan.eksenler.sol;
  const ty = (v) => plan.alan.y + plan.alan.h - (v - eks.min) * plan.alan.h / (eks.maks - eks.min);
  const tKenar = 50 + (R - plan.alan.x) * 400 / plan.alan.w;
  const vKenar = 40 + (41 - 40) * (tKenar - 400) / (1e9 - 400);
  assert.ok(Math.abs(son[son.length - 1] - ty(vKenar)) < 1e-6);
  // Sol kenar noktası 40 → 50 doğrusunda: t(L) = 50 + (L − alan.x)·400/400.
  const tL = 50 + (L - plan.alan.x);
  assert.ok(Math.abs(ilk[1] - ty(4 + (tL - 40) / 10)) < 1e-6);
});

test('plan: ızgara, seçim bandı, imleçler (B kesikli), eksen yazıları; gezginde pencere bandı', () => {
  const n = 20000;
  const t = new Float64Array(n).map((_, i) => i * 100);
  const v = new Float64Array(n).map((_, i) => 4 - i / n);
  const a = new Float64Array(n).fill(1);
  const s = [seriHazirla({ ad: 'V', t, y: v, birim: 'V', renk: 'volt' }), seriHazirla({ ad: 'I', t, y: a, birim: 'A', renk: 'amper', eksen: 'sag' })];
  let d = durumKur(s);
  d = durumBirlestir(d, { imlecA: 300000, imlecB: 1500000 });
  const plan = cizimPlani(s, d, { w: 1000, h: 300 });
  const rol = (r) => plan.komutlar.filter((c) => c.rol === r);
  assert.ok(rol('izgara').length >= 6, 'ızgara');
  const secim = rol('secim');
  assert.equal(secim.length, 1);
  const tx = (tt) => plan.alan.x + tt * plan.alan.w / t[n - 1];
  assert.ok(Math.abs(secim[0].x - tx(300000)) < 1e-9 && Math.abs(secim[0].w - (tx(1500000) - tx(300000))) < 1e-9);
  const imlecler = rol('imlec').filter((c) => c.tur === 'cizgi');
  assert.equal(imlecler.length, 2);
  assert.equal(imlecler[0].desen, undefined, 'A düz');
  assert.deepEqual(imlecler[1].desen, [6, 4], 'B kesikli (maket)');
  assert.deepEqual(rol('imlec').filter((c) => c.tur === 'yazi').map((c) => c.metin), ['A', 'B']);
  const yazilar = rol('eksen').map((c) => c.metin);
  assert.ok(yazilar.includes('V') && yazilar.includes('A'), 'birimler');
  assert.ok(yazilar.some((m) => /^\d\d:\d\d:\d\d$/.test(m)), 'zaman yazısı');
  // Sıra: ızgara → seçim → kırp → kanallar → kırpBitir → imleç → yazı.
  const ilk = (f) => plan.komutlar.findIndex(f);
  assert.ok(ilk((c) => c.rol === 'izgara') < ilk((c) => c.rol === 'secim'));
  assert.ok(ilk((c) => c.rol === 'secim') < ilk((c) => c.tur === 'kirp'));
  assert.ok(ilk((c) => c.tur === 'kirpBitir') < ilk((c) => c.rol === 'imlec'));
  for (const c of plan.komutlar) assert.ok(!c.metin || /^[0-9:.−AVB]*$/.test(c.metin), `dil metni yok (P7): ${c.metin}`);

  // Pencere dışındaki imleç çizilmez.
  const dar = cizimPlani(s, durumBirlestir(d, { t0: 400000, t1: 600000 }), { w: 1000, h: 300 });
  assert.equal(dar.komutlar.filter((c) => c.rol === 'imlec').length, 0);
  assert.equal(dar.komutlar.filter((c) => c.rol === 'secim').length, 1, 'bant pencereyi kaplar');

  const gd = durumBirlestir(d, { t0: 500000, t1: 700000 });
  const gez = cizimPlani(s, gd, { w: 1000, h: 44 }, { gezgin: true });
  const pencere = gez.komutlar.filter((c) => c.rol === 'pencere');
  assert.equal(pencere.length, 1);
  const gx = (tt) => tt * 1000 / t[n - 1];
  assert.ok(Math.abs(pencere[0].x - gx(500000)) < 1e-9 && Math.abs(pencere[0].w - (gx(700000) - gx(500000))) < 1e-9);
  assert.equal(gez.komutlar.filter((c) => c.rol === 'izgara' || c.rol === 'imlec' || c.tur === 'yazi').length, 0);
  assert.equal(gez.komutlar[0].rol, 'zemin');
  const cokDar = cizimPlani(s, durumBirlestir(d, { t0: 500000, t1: 500100 }), { w: 1000, h: 44 }, { gezgin: true });
  assert.ok(cokDar.komutlar.find((c) => c.rol === 'pencere').w >= 2, 'çok dar pencere de görünür');

  assert.deepEqual(cizimPlani(s, d, { w: 30, h: 20 }).komutlar, [], 'alan yoksa komut yok');
});

// ── 3. ETKİLEŞİM ────────────────────────────────────────────────────────────

test('durum: pencere = bütün veri, en dar pencere 10 örnek, tek örnek / boş veri', () => {
  const d = duzgunDurum();
  assert.deepEqual([d.veriT0, d.veriT1, d.t0, d.t1], [0, 400000, 0, 400000]);
  assert.equal(d.enAzPencere, EN_AZ_ORNEK * 2);
  assert.equal(tipikAralik(Float64Array.of(0, 2, 2, 4, 6, 1000)), 2);
  assert.ok(Number.isNaN(tipikAralik(Float64Array.of(5))));
  const tek = durumKur([{ t: Float64Array.of(7) }]);
  assert.ok(tek.veriT1 > tek.veriT0 && tek.t0 <= 7 && tek.t1 >= 7);
  const bos = durumKur([]);
  assert.deepEqual([bos.veriT0, bos.veriT1], [0, 1]);
  const az = durumKur([{ t: Float64Array.of(0, 1, 2) }]);
  assert.equal(az.enAzPencere, 2, 'en dar pencere veriden geniş olamaz');
});

test('tekerlek: işaretçi altındaki zaman SABİT (±1 ms), en dar pencere, uzaklaşınca bütün veri', () => {
  let d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 300000 });
  const x = ALAN.x + 250;
  const tSabit = xdenT(d, x);
  assert.equal(tSabit, 150000);
  for (let k = 0; k < 40; k++) {
    d = etkilesim(d, { tur: 'tekerlek', x, dy: -300, alan: ALAN });
    assert.ok(Math.abs(xdenT(d, x) - tSabit) <= 1, `adım ${k}: ${xdenT(d, x)} ≠ ${tSabit}`);
    assert.ok(d.t1 - d.t0 >= d.enAzPencere - 1e-9);
  }
  assert.ok(Math.abs(d.t1 - d.t0 - 20) < 1e-9, `en dar pencere 10 örnek: ${d.t1 - d.t0}`);
  const enDar = d;
  assert.equal(etkilesim(d, { tur: 'tekerlek', x, dy: -300, alan: ALAN }), enDar, 'en darda değişmez (aynı nesne)');

  // Rastgele: yakınlaş/uzaklaş; uca dayanmadıkça işaretçi zamanı sabit.
  const r = rastgele(3);
  let sinanan = 0;
  for (let k = 0; k < 500; k++) {
    const xp = ALAN.x + r() * ALAN.w;
    const once = xdenT(d, xp);
    const yeni = etkilesim(d, { tur: 'tekerlek', x: xp, dy: (r() - 0.45) * 600, alan: ALAN });
    if (yeni.t0 > yeni.veriT0 && yeni.t1 < yeni.veriT1) {
      assert.ok(Math.abs(xdenT(yeni, xp) - once) <= 1, `rastgele ${k}`);
      sinanan++;
    }
    assert.ok(yeni.t0 >= yeni.veriT0 && yeni.t1 <= yeni.veriT1, 'kırpılı');
    d = yeni;
  }
  assert.ok(sinanan > 300);
  for (let k = 0; k < 80; k++) d = etkilesim(d, { tur: 'tekerlek', x, dy: 500, alan: ALAN });
  assert.deepEqual([d.t0, d.t1], [0, 400000], 'en geniş = bütün veri');
  assert.equal(etkilesim(d, { tur: 'tekerlek', x, dy: 500, alan: ALAN }), d);
  // Yatay tekerlek kaydırır.
  const p = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 200000 });
  const h = etkilesim(p, { tur: 'tekerlek', x, dx: 100, dy: 3, alan: ALAN });
  assert.deepEqual([h.t0, h.t1], [110000, 210000]);
  assert.equal(etkilesim(p, { tur: 'tekerlek', x, dy: 100 }), p, 'alan yoksa değişmez');
});

test('sürükleyerek kaydırma: oran doğru, iki uçta KIRPILIR, genişlik korunur', () => {
  let d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 200000 });
  d = etkilesim(d, { tur: 'basla', id: 1, x: 500, alan: ALAN });
  assert.equal(d.suruklenen.tur, 'kaydir');
  const k1 = etkilesim(d, { tur: 'hareket', id: 1, x: 700, alan: ALAN });
  assert.deepEqual([k1.t0, k1.t1], [80000, 180000], 'sağa sürükle = önceki zaman');
  const k2 = etkilesim(k1, { tur: 'hareket', id: 1, x: 5000, alan: ALAN });
  assert.deepEqual([k2.t0, k2.t1], [0, 100000], 'sol uçta kırpılır');
  const k3 = etkilesim(k2, { tur: 'hareket', id: 1, x: -9000, alan: ALAN });
  assert.deepEqual([k3.t0, k3.t1], [300000, 400000], 'sağ uçta kırpılır');
  const k4 = etkilesim(k3, { tur: 'bitir', id: 1, alan: ALAN });
  assert.equal(k4.suruklenen, null);
  assert.deepEqual(k4.isaretciler, {});
  assert.equal(etkilesim(k4, { tur: 'bitir', id: 1 }), k4);
  // Klavye: oklar %10 kaydırır, uçta kırpılır; Home bütün veri.
  let kd = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 200000 });
  kd = etkilesim(kd, { tur: 'tus', tus: 'ArrowRight', alan: ALAN });
  assert.deepEqual([kd.t0, kd.t1], [100000 + TUS_KAYDIR * 100000, 200000 + TUS_KAYDIR * 100000]);
  for (let k = 0; k < 30; k++) kd = etkilesim(kd, { tur: 'tus', tus: 'ArrowLeft', alan: ALAN });
  assert.deepEqual([kd.t0, kd.t1], [0, 100000]);
  const ev = etkilesim(kd, { tur: 'tus', tus: 'Home', alan: ALAN });
  assert.deepEqual([ev.t0, ev.t1], [0, 400000]);
  // Programdan pencere de kırpılır.
  const pr = etkilesim(kd, { tur: 'pencere', t0: -5e5, t1: 9e9 });
  assert.deepEqual([pr.t0, pr.t1], [0, 400000]);
  assert.deepEqual(pencereKirp(kd, NaN, 5), { t0: kd.t0, t1: kd.t1 });
});

test('klavye +/−: orta sabit; bilinmeyen tuş aynı nesne', () => {
  let d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 200000 });
  const yak = etkilesim(d, { tur: 'tus', tus: '+', alan: ALAN });
  assert.ok(Math.abs((yak.t1 - yak.t0) - 100000 / TUS_ORAN) < 1e-6);
  assert.ok(Math.abs((yak.t0 + yak.t1) / 2 - 150000) < 1e-6);
  const uz = etkilesim(d, { tur: 'tus', tus: '-', alan: ALAN });
  assert.ok(Math.abs((uz.t1 - uz.t0) - 100000 * TUS_ORAN) < 1e-6);
  assert.equal(etkilesim(d, { tur: 'tus', tus: 'x', alan: ALAN }), d);
  assert.equal(etkilesim(d, { tur: 'bilinmeyen' }), d);
  assert.equal(etkilesim(d, null), d);
  d = yakinlastir(d, 150000, 0.5);
  assert.deepEqual(d, { t0: 125000, t1: 175000 });
});

test('iki parmak: iki zaman da parmakların altında kalır (±1 ms); bir parmak kalınca sıçramasız kaydırma', () => {
  let d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 300000 });
  d = etkilesim(d, { tur: 'basla', id: 7, x: ALAN.x + 200, alan: ALAN });
  d = etkilesim(d, { tur: 'basla', id: 9, x: ALAN.x + 600, alan: ALAN });
  assert.equal(d.suruklenen.tur, 'kiskac');
  const tA = 140000;
  const tB = 220000;
  d = etkilesim(d, { tur: 'hareket', id: 7, x: ALAN.x + 100, alan: ALAN });
  d = etkilesim(d, { tur: 'hareket', id: 9, x: ALAN.x + 700, alan: ALAN });
  assert.ok(Math.abs(xdenT(d, ALAN.x + 100) - tA) <= 1 && Math.abs(xdenT(d, ALAN.x + 700) - tB) <= 1,
    `parmak altı: ${xdenT(d, ALAN.x + 100)}, ${xdenT(d, ALAN.x + 700)}`);
  assert.ok(Math.abs((d.t1 - d.t0) - 80000 * 1000 / 600) < 1e-6);
  // Kesişen parmaklar yok sayılır.
  const kes = etkilesim(d, { tur: 'hareket', id: 7, x: ALAN.x + 800, alan: ALAN });
  assert.deepEqual([kes.t0, kes.t1], [d.t0, d.t1]);
  // Parmaklar çok açılır: en dar pencere; çok yaklaşır: bütün veri.
  let e = etkilesim(d, { tur: 'hareket', id: 7, x: ALAN.x - 1e7, alan: ALAN });
  e = etkilesim(e, { tur: 'hareket', id: 9, x: ALAN.x + 1e7, alan: ALAN });
  assert.ok(Math.abs(e.t1 - e.t0 - e.enAzPencere) < 1e-9, `en dar: ${e.t1 - e.t0}`);
  assert.ok(e.t0 >= e.veriT0 && e.t1 <= e.veriT1);
  let f = etkilesim(d, { tur: 'hareket', id: 9, x: ALAN.x + 100 + 10.5, alan: ALAN });
  f = etkilesim(f, { tur: 'hareket', id: 7, x: ALAN.x + 100, alan: ALAN });
  assert.deepEqual([f.t0, f.t1], [0, 400000], 'en geniş = bütün veri');
  const yakin = etkilesim(d, { tur: 'hareket', id: 9, x: ALAN.x + 100 + 9, alan: ALAN });
  assert.deepEqual([yakin.t0, yakin.t1], [d.t0, d.t1], `${KISKAC_EN_AZ_PX} px'ten yakın parmak: ölçek hesaplanmaz`);
  // Bir parmak kalkar: kalan parmak kaydırır, ilk harekette sıçrama yok.
  const b = etkilesim(d, { tur: 'bitir', id: 7, alan: ALAN });
  assert.equal(b.suruklenen.tur, 'kaydir');
  const ayni = etkilesim(b, { tur: 'hareket', id: 9, x: ALAN.x + 700, alan: ALAN });
  assert.deepEqual([ayni.t0, ayni.t1], [d.t0, d.t1], 'sıçrama yok');
  const kay = etkilesim(b, { tur: 'hareket', id: 9, x: ALAN.x + 750, alan: ALAN });
  assert.ok(Math.abs(kay.t0 - (d.t0 - 50 / 1000 * (d.t1 - d.t0))) < 1e-6);
  // Gezginde iki parmak yok.
  const g0 = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 300000 });
  const gz = etkilesim(etkilesim(g0, { tur: 'basla', id: 1, x: 10, alan: ALAN, gezgin: true }), { tur: 'basla', id: 2, x: 20, alan: ALAN, gezgin: true });
  assert.notEqual(gz.suruklenen && gz.suruklenen.tur, 'kiskac');
});

test('imleçler: klavye A/B yerleştirir, sürüklenir, A > B olunca takas (sürükleme aynı çizgide), veriye kırpılır', () => {
  let d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 300000 });
  d = etkilesim(d, { tur: 'tus', tus: 'a', alan: ALAN });
  assert.ok(Math.abs(d.imlecA - (100000 + 200000 / 3)) < 1e-6 && d.etkinImlec === 'A');
  d = etkilesim(d, { tur: 'tus', tus: 'B', shift: true, alan: ALAN });
  assert.ok(Math.abs(d.imlecB - (100000 + 400000 / 3)) < 1e-6 && d.etkinImlec === 'B');
  // Fare üstündeyken A fare konumuna.
  const fare = etkilesim(d, { tur: 'hareket', id: 1, x: ALAN.x + 900, alan: ALAN });
  assert.equal(fare.fareT, 280000);
  assert.deepEqual(fare.isaretciler, {}, 'basılı değil');
  const f2 = etkilesim(fare, { tur: 'tus', tus: 'a', alan: ALAN });
  assert.equal(f2.imlecB, 280000, 'A, B\'yi geçti: takas');
  assert.ok(Math.abs(f2.imlecA - (100000 + 400000 / 3)) < 1e-6);
  assert.equal(f2.etkinImlec, 'B', 'etkin imleç taşınan çizgiyi izler');
  assert.equal(etkilesim(f2, { tur: 'ayril' }).fareT, null);
  // Shift + ok etkin imleci %1 taşır.
  const s1 = etkilesim(f2, { tur: 'tus', tus: 'ArrowLeft', shift: true, alan: ALAN });
  assert.ok(Math.abs(s1.imlecB - (280000 - IMLEC_TUS_ADIM * 200000)) < 1e-6);
  assert.deepEqual([s1.t0, s1.t1], [f2.t0, f2.t1], 'pencere kaymadı');

  // Sürükleme: A çizgisinin yakınından tut.
  d = durumBirlestir(etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 300000 }), { imlecA: 150000, imlecB: 250000 });
  let s = etkilesim(d, { tur: 'basla', id: 3, x: tdenX(d, 150000) + 5, alan: ALAN });
  assert.equal(s.suruklenen.tur, 'imlecA');
  s = etkilesim(s, { tur: 'hareket', id: 3, x: tdenX(d, 180000), alan: ALAN });
  assert.ok(Math.abs(s.imlecA - 180000) < 1e-6);
  assert.deepEqual([s.t0, s.t1], [100000, 300000], 'imleç sürüklemek pencereyi kaydırmaz');
  s = etkilesim(s, { tur: 'hareket', id: 3, x: tdenX(d, 270000), alan: ALAN });
  assert.equal(s.imlecA, 250000, 'takas: A = eski B');
  assert.ok(Math.abs(s.imlecB - 270000) < 1e-6);
  assert.equal(s.suruklenen.tur, 'imlecB', 'sürükleme aynı (artık B) çizgide');
  s = etkilesim(s, { tur: 'hareket', id: 3, x: tdenX(d, 290000), alan: ALAN });
  assert.ok(Math.abs(s.imlecB - 290000) < 1e-6 && s.imlecA === 250000);
  assert.ok(s.imlecA <= s.imlecB);
  // Veriye kırpma: pencere sonda, imleç sağ kenarın ötesine.
  let u = durumBirlestir(duzgunDurum(), { t0: 300000, t1: 400000, imlecA: 350000, imlecB: 390000 });
  u = etkilesim(u, { tur: 'basla', id: 1, x: tdenX(u, 390000), alan: ALAN });
  u = etkilesim(u, { tur: 'hareket', id: 1, x: ALAN.x + ALAN.w + 500, alan: ALAN });
  assert.equal(u.imlecB, 400000, 'veri sonuna kırpılır');
  // B yakınında tutmak B'yi seçer; uzakta kaydırma.
  const bTut = etkilesim(d, { tur: 'basla', id: 4, x: tdenX(d, 250000) - 3, alan: ALAN });
  assert.equal(bTut.suruklenen.tur, 'imlecB');
  assert.equal(etkilesim(d, { tur: 'basla', id: 4, x: tdenX(d, 200000), alan: ALAN }).suruklenen.tur, 'kaydir');

  // imlecKoy: boşa A, sonra B, sonra en yakın; Escape siler.
  let k = duzgunDurum();
  k = etkilesim(k, { tur: 'imlecKoy', t: 300000 });
  assert.deepEqual([k.imlecA, k.imlecB], [300000, null]);
  k = etkilesim(k, { tur: 'imlecKoy', t: 100000 });
  assert.deepEqual([k.imlecA, k.imlecB], [100000, 300000], 'B konuldu, A > B → takas');
  k = etkilesim(k, { tur: 'imlecKoy', t: 280000 });
  assert.deepEqual([k.imlecA, k.imlecB], [100000, 280000], 'en yakın (B) taşındı');
  k = etkilesim(k, { tur: 'imlecKoy', x: ALAN.x + ALAN.w / 2, alan: ALAN, hangi: 'A' });
  assert.equal(k.imlecA, 200000);
  k = etkilesim(k, { tur: 'imlecKoy', t: -5e9, hangi: 'A' });
  assert.equal(k.imlecA, 0, 'veriye kırpılır');
  const sil = etkilesim(k, { tur: 'tus', tus: 'Escape', alan: ALAN });
  assert.deepEqual([sil.imlecA, sil.imlecB], [null, null]);
  assert.equal(etkilesim(sil, { tur: 'tus', tus: 'Escape', alan: ALAN }), sil);
  // durumBirlestir: eşleme — sıralar ve kırpar.
  const db = durumBirlestir(duzgunDurum(), { imlecA: 9e9, imlecB: 5 });
  assert.deepEqual([db.imlecA, db.imlecB], [5, 400000]);
});

test('gezgin: gövde taşır, kenarlar boyutlar (en dar pencere), dışarı tıklama ortalar, uçlarda kırpar', () => {
  const GA = { x: 0, y: 1, w: 1000, h: 42 };
  const gez = (d, o) => etkilesim(d, { ...o, alan: GA, gezgin: true });
  const d = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 100000, t1: 140000 }); // x 250…350
  let s = gez(d, { tur: 'basla', id: 1, x: 300 });
  assert.equal(s.suruklenen.tur, 'gezginTasi');
  s = gez(s, { tur: 'hareket', id: 1, x: 400 });
  assert.deepEqual([s.t0, s.t1], [140000, 180000], 'gövde: 100 px = 40 000 ms');
  s = gez(s, { tur: 'hareket', id: 1, x: 5000 });
  assert.deepEqual([s.t0, s.t1], [360000, 400000], 'sağ uçta kırpılır, genişlik korunur');
  s = gez(s, { tur: 'hareket', id: 1, x: -5000 });
  assert.deepEqual([s.t0, s.t1], [0, 40000]);

  let sol = gez(d, { tur: 'basla', id: 2, x: 252 });
  assert.equal(sol.suruklenen.tur, 'gezginSol');
  sol = gez(sol, { tur: 'hareket', id: 2, x: 200 });
  assert.deepEqual([sol.t0, sol.t1], [80000, 140000], 'sol kenar: t1 sabit');
  sol = gez(sol, { tur: 'hareket', id: 2, x: 900 });
  assert.ok(Math.abs(sol.t1 - sol.t0 - sol.enAzPencere) < 1e-9 && sol.t1 === 140000, 'kenar öbürünü geçemez: en dar pencere');
  let sag = gez(d, { tur: 'basla', id: 3, x: 349 });
  assert.equal(sag.suruklenen.tur, 'gezginSag');
  sag = gez(sag, { tur: 'hareket', id: 3, x: 2000 });
  assert.deepEqual([sag.t0, sag.t1], [100000, 400000]);

  const dis = gez(d, { tur: 'basla', id: 4, x: 800 });
  assert.deepEqual([dis.t0, dis.t1], [300000, 340000], 'dışarı tıklama: oraya ortalar');
  assert.equal(dis.suruklenen.tur, 'gezginTasi');
  const disUc = gez(d, { tur: 'basla', id: 4, x: 999 });
  assert.deepEqual([disUc.t0, disUc.t1], [360000, 400000]);
  const tek = gez(d, { tur: 'tekerlek', x: 900, dy: -200 });
  assert.ok(Math.abs((tek.t0 + tek.t1) / 2 - 120000) < 1e-6, 'gezgin tekerleği pencere ortasına göre');
  const kd = gez(d, { tur: 'tus', tus: 'a' });
  assert.equal(kd, d, 'gezginde imleç tuşu yok');
  const hv = gez(d, { tur: 'hareket', id: 8, x: 10 });
  assert.equal(hv, d, 'gezginde fare konumu tutulmaz');
  // Dar pencere: kenar yakalama yalnız dışta, içi taşır.
  const dar = etkilesim(duzgunDurum(), { tur: 'pencere', t0: 200000, t1: 204000 }); // x 500…510
  assert.equal(gez(dar, { tur: 'basla', id: 5, x: 505 }).suruklenen.tur, 'gezginTasi');
  assert.equal(gez(dar, { tur: 'basla', id: 5, x: 496 }).suruklenen.tur, 'gezginSol');
  assert.equal(gez(dar, { tur: 'basla', id: 5, x: 514 }).suruklenen.tur, 'gezginSag');
});

// ── 4. İMLEÇ OKUMASI ────────────────────────────────────────────────────────

/** Kaba kuvvet: en yakın NaN'sız örneğin uzaklığı ve o uzaklıktaki değerler. */
function kabaEnYakin(t, y, x) {
  let en = Infinity;
  for (let i = 0; i < t.length; i++) if (!Number.isNaN(y[i]) && Math.abs(t[i] - x) < en) en = Math.abs(t[i] - x);
  const degerler = [];
  for (let i = 0; i < t.length; i++) if (!Number.isNaN(y[i]) && Math.abs(t[i] - x) === en) degerler.push(y[i]);
  return { en, degerler };
}

function kabaIstat(t, y, a, b) {
  let adet = 0;
  let top = 0;
  let enk = Infinity;
  let enb = -Infinity;
  for (let i = 0; i < t.length; i++) {
    if (t[i] < a || t[i] > b || Number.isNaN(y[i])) continue;
    adet++;
    top += y[i];
    if (y[i] < enk) enk = y[i];
    if (y[i] > enb) enb = y[i];
  }
  return { adet, ort: top / adet, min: enk, maks: enb };
}

function kabaEnerji(t, v, i, a, b, bosluk) {
  let wms = 0;
  let ams = 0;
  let onceki = -1;
  for (let k = 0; k < t.length; k++) {
    if (t[k] < a || t[k] > b || Number.isNaN(v[k]) || Number.isNaN(i[k])) continue;
    if (onceki >= 0 && t[k] - t[onceki] <= bosluk) {
      const dt = t[k] - t[onceki];
      wms += (v[onceki] * i[onceki] + v[k] * i[k]) / 2 * dt;
      ams += (i[onceki] + i[k]) / 2 * dt;
    }
    onceki = k;
  }
  return { wh: wms / 3.6e6, mah: ams / 3600 };
}

test('imleç okuması kaba kuvvete karşı: değer, ΔV, ortalama, min/maks, mAh/Wh (HAM, boşluk hariç)', () => {
  const n = 30000;
  const { t, v, a } = kayitUret(n, 555);
  // Eşit zaman damgaları da olsun.
  for (let i = 100; i < n; i += 997) t[i] = t[i - 1];
  const s = [
    seriHazirla({ ad: 'V', t, y: v, birim: 'V', boslukMs: BOSLUK_MS }),
    seriHazirla({ ad: 'I', t, y: a, birim: 'A', eksen: 'sag', boslukMs: BOSLUK_MS }),
  ];
  const r = rastgele(17);
  const T0 = t[0];
  const T1 = t[n - 1];
  for (let k = 0; k < 300; k++) {
    let tA = T0 - 1000 + r() * (T1 - T0 + 2000);
    let tB = k % 5 === 0 ? tA + r() * 50 : T0 + r() * (T1 - T0);
    const o = imlecOkuma(s, tA, tB);
    if (tA > tB) [tA, tB] = [tB, tA];
    assert.ok(o.tA === tA && o.tB === tB && o.dt === tB - tA, 'sıralı');
    for (let c = 0; c < 2; c++) {
      const y = s[c].y;
      const kc = o.kanallar[c];
      for (const [imlec, x] of [[kc.a, tA], [kc.b, tB]]) {
        const kaba = kabaEnYakin(t, y, x);
        assert.equal(Math.abs(imlec.t - x), kaba.en, `kanal ${c}: en yakın uzaklık`);
        assert.ok(kaba.degerler.includes(imlec.deger) && y[imlec.i] === imlec.deger && t[imlec.i] === imlec.t);
      }
      assert.equal(kc.fark, kc.b.deger - kc.a.deger);
      const ki = kabaIstat(t, y, tA, tB);
      assert.equal(kc.istat.adet, ki.adet, 'adet');
      if (ki.adet) {
        assert.equal(kc.istat.min, ki.min);
        assert.equal(kc.istat.maks, ki.maks);
        assert.ok(Math.abs(kc.istat.ort - ki.ort) <= 1e-10 * Math.abs(ki.ort), `ort ${kc.istat.ort} ≠ ${ki.ort}`);
      }
    }
    assert.equal(o.dV, o.kanallar[0].fark);
    assert.equal(o.ortI, o.kanallar[1].istat.ort);
    const ke = kabaEnerji(t, v, a, tA, tB, BOSLUK_MS);
    assert.ok(Math.abs(o.enerji.mah - ke.mah) <= 1e-9 * Math.max(1, Math.abs(ke.mah)), `mAh ${o.enerji.mah} ≠ ${ke.mah}`);
    assert.ok(Math.abs(o.enerji.wh - ke.wh) <= 1e-9 * Math.max(1, Math.abs(ke.wh)), `Wh ${o.enerji.wh} ≠ ${ke.wh}`);
  }
  assert.deepEqual(enYakinOrnek(Float64Array.of(), Float64Array.of(), 3), null);
  assert.deepEqual(enYakinOrnek(Float64Array.of(1, 2), Float64Array.of(NaN, NaN), 3), null);
  assert.deepEqual(enYakinOrnek(Float64Array.of(1, 2, 3), Float64Array.of(4, NaN, 6), 2.2), { i: 2, t: 3, deger: 6 }, 'NaN atlanır');
  assert.deepEqual(enYakinOrnek(Float64Array.of(1, 2, 3), Float64Array.of(4, NaN, 6), 1.9), { i: 0, t: 1, deger: 4 });
  assert.deepEqual(enYakinOrnek(Float64Array.of(1, 2, 3), Float64Array.of(4, 5, 6), 99), { i: 2, t: 3, deger: 6 });
  assert.deepEqual(enYakinOrnek(Float64Array.of(1, 2, 3), Float64Array.of(4, 5, 6), -9), { i: 0, t: 1, deger: 4 });
});

test('mAh/Wh: 1 A × 3600 s = 1000 mAh; 2 V → 2 Wh; boşluk dışlanır; V/A yoksa enerji yok', () => {
  const t = new Float64Array(3601).map((_, i) => i * 1000);
  const v = new Float64Array(3601).fill(2);
  const i = new Float64Array(3601).fill(1);
  const s = [seriHazirla({ ad: 'V', t, y: v, birim: 'V', boslukMs: 2500 }), seriHazirla({ ad: 'I', t, y: i, birim: 'A' })];
  const o = imlecOkuma(s, 0, 3600000);
  assert.equal(o.enerji.mah, 1000);
  assert.equal(o.enerji.wh, 2);
  assert.equal(o.ortI, 1);
  assert.equal(o.dV, 0);

  // 1200…1800 s arası örnek yok (600 s boşluk): 3000 s integre edilir.
  const tb = [];
  for (let k = 0; k <= 3600; k++) if (k <= 1200 || k >= 1800) tb.push(k * 1000);
  const t2 = Float64Array.from(tb);
  const v2 = new Float64Array(t2.length).fill(2);
  const i2 = new Float64Array(t2.length).fill(1);
  const s2 = [seriHazirla({ ad: 'V', t: t2, y: v2, birim: 'V', boslukMs: 2500 }), seriHazirla({ ad: 'I', t: t2, y: i2, birim: 'A' })];
  const o2 = imlecOkuma(s2, 0, 3600000);
  assert.ok(Math.abs(o2.enerji.mah - 3000 / 3600 * 1000) < 1e-9, `boşluk dışlanmadı: ${o2.enerji.mah}`);
  assert.ok(Math.abs(o2.enerji.wh - 2 * 3000 / 3600) < 1e-12);
  const s3 = [{ ...s2[0], boslukMs: undefined }, s2[1]];
  assert.equal(imlecOkuma(s3, 0, 3600000).enerji.mah, 1000, 'boslukMs verilmezse köprülenir (çağıranın kararı, G2)');

  assert.equal(imlecOkuma([s[0]], 0, 1000).enerji, null, 'akım kanalı yok');
  const baskaT = seriHazirla({ ad: 'I', t: new Float64Array(3601).map((_, k) => k * 1000 + 1), y: i, birim: 'A' });
  assert.equal(imlecOkuma([s[0], baskaT], 0, 3600000).enerji, null, 'farklı zaman dizisi');
  assert.equal(imlecOkuma(s, 0, 3600000, { gerilim: 'yok' }).enerji, null);
  const kopyaT = seriHazirla({ ad: 'I', t: Float64Array.from(t), y: i, birim: 'A' });
  assert.equal(imlecOkuma([s[0], kopyaT], 0, 3600000).enerji.mah, 1000, 'eşit içerikli ayrı dizi kabul');
  const tekImlec = imlecOkuma(s, 5000, null);
  assert.equal(tekImlec.kanallar[0].a.deger, 2);
  assert.equal(tekImlec.kanallar[0].b, null);
  assert.equal(tekImlec.kanallar[0].istat, null);
  assert.equal(tekImlec.enerji, null);
  assert.ok(Number.isNaN(tekImlec.dt));
});

// ── İNCE ÇİZİCİ ─────────────────────────────────────────────────────────────

function ornekSeriler() {
  const n = 5000;
  const t = new Float64Array(n).map((_, i) => 1e6 + i * 20);
  return [
    { ad: 'V', t, y: new Float64Array(n).map((_, i) => 3.7 - i / n), birim: 'V', renk: 'volt' },
    { ad: 'I', t, y: new Float64Array(n).map((_, i) => 1 + 0.01 * Math.sin(i)), birim: 'A', renk: 'amper', eksen: 'sag' },
  ];
}

test('çizici: hatasız çizer, devicePixelRatio, focuslanabilir, touch-action, dinleyiciler YALNIZ canvas\'ta', () => {
  const eskiEkle = globalThis.addEventListener;
  let globalEklenen = 0;
  globalThis.addEventListener = () => { globalEklenen++; };
  try {
    const k = sahteKanvas(800, 300);
    const g = new Grafik(k, { pencere: { devicePixelRatio: 2 } });
    assert.equal(k.tabIndex, 0);
    assert.equal(k.style.touchAction, 'none');
    assert.deepEqual(k.dinlenenler(), ['dblclick', 'keydown', 'pointercancel', 'pointerdown', 'pointerleave', 'pointermove', 'pointerup', 'wheel']);
    assert.deepEqual(k.secenekler.wheel, { passive: false });
    assert.equal(globalEklenen, 0, 'global dinleyici YOK (klavye yalnız odakta)');
    g.veriAyarla(ornekSeriler());
    assert.equal(k.width, 1600);
    assert.equal(k.height, 600);
    assert.deepEqual(k.ctx.cagrilar.filter((c) => c[0] === 'setTransform').at(-1), ['setTransform', 2, 0, 0, 2, 0, 0]);
    assert.equal(k.ctx.derinlik, 0, 'save/restore dengeli');
    const renkler = new Set(k.ctx.vuruslar.map((v) => v.renk));
    assert.ok(renkler.has(RENK_YEDEK.volt) && renkler.has(RENK_YEDEK.amper) && renkler.has(RENK_YEDEK.izgara));
    assert.ok(k.ctx.yazilar.length > 5);
    // Kesirli dpr ve boyut değişimi.
    k.clientWidth = 333;
    g.pencere.devicePixelRatio = 1.5;
    g.ciz();
    assert.equal(k.width, 500);
    // Sıfır boyut ve boş veri: çökmez.
    k.clientWidth = 0;
    assert.equal(g.ciz(), null);
    k.clientWidth = 800;
    g.veriAyarla([]);
    assert.ok(g.ciz());
    g.yokEt();
  } finally {
    if (eskiEkle === undefined) delete globalThis.addEventListener;
    else globalThis.addEventListener = eskiEkle;
  }
});

test('çizici: renkler her ciz()\'de YENİDEN okunur; varsayılan okuyucu CSS değişkenleri + eşdeğerleri', () => {
  const k = sahteKanvas(600, 240);
  const harita = { volt: '#111111', amper: '#222222', izgara: '#333333', soluk: '#444444' };
  const g = new Grafik(k, { renk: (ad) => harita[ad] || '' });
  g.veriAyarla(ornekSeriler());
  k.ctx.sifirla();
  g.ciz();
  assert.ok(k.ctx.vuruslar.some((v) => v.renk === '#111111'));
  harita.volt = '#abcdef'; // görünüm değişti
  k.ctx.sifirla();
  g.ciz();
  const yeni = new Set(k.ctx.vuruslar.map((v) => v.renk));
  assert.ok(yeni.has('#abcdef') && !yeni.has('#111111'), 'eski renk önbellekte kalmadı');
  g.yokEt();

  // Varsayılan okuyucu: pencere.getComputedStyle(canvas).getPropertyValue('--ad').
  const degiskenler = { '--volt': ' #0f0f0f ', '--kenar-c': '#c0c0c0' };
  let istenen = null;
  const pencere = {
    devicePixelRatio: 1,
    getComputedStyle(el) {
      istenen = el;
      return { getPropertyValue: (ad) => degiskenler[ad] || '' };
    },
  };
  const k2 = sahteKanvas(600, 240);
  const g2 = new Grafik(k2, { pencere });
  g2.veriAyarla(ornekSeriler());
  assert.equal(istenen, k2, 'stil canvas\'tan okunur');
  const r2 = new Set(k2.ctx.vuruslar.map((v) => v.renk));
  assert.ok(r2.has('#0f0f0f'), 'kırpılmış CSS değeri');
  assert.ok(r2.has('#c0c0c0'), '--izgara yok → --kenar-c (arayuz3 adı)');
  assert.ok(r2.has(RENK_YEDEK.amper), '--amper yok → yedek');
  degiskenler['--volt'] = '#123456';
  k2.ctx.sifirla();
  g2.ciz();
  assert.ok(k2.ctx.vuruslar.some((v) => v.renk === '#123456'));
  g2.yokEt();
  assert.equal(cssRenk({}, {})('volt'), '', 'getComputedStyle yoksa boş');
});

test('çizici: olaylar indirgeyiciye gider, onDegisim çağrılır, preventDefault yalnız değişince; yokEt temizler', () => {
  const k = sahteKanvas(1112, 300);
  const degisimler = [];
  const g = new Grafik(k, { onDegisim: (d) => degisimler.push({ t0: d.t0, t1: d.t1, A: d.imlecA, B: d.imlecB }) });
  g.veriAyarla(ornekSeriler());
  const alan = g.sonPlan.alan;
  assert.equal(degisimler.length, 0, 'veriAyarla onDegisim çağırmaz');
  // Bütün veride uzaklaştırma: değişiklik yok → sayfa kayabilir.
  const e0 = k.gonder('wheel', { offsetX: alan.x + 10, deltaY: 100, deltaX: 0, deltaMode: 0 });
  assert.equal(e0.engellendi, false);
  assert.equal(degisimler.length, 0);
  const e1 = k.gonder('wheel', { offsetX: alan.x + alan.w / 2, deltaY: -30, deltaX: 0, deltaMode: 1 });
  assert.equal(e1.engellendi, true);
  assert.equal(degisimler.length, 1);
  assert.ok(degisimler[0].t1 - degisimler[0].t0 < g.durum.veriT1 - g.durum.veriT0);
  // Klavye: Ctrl'li tuş tarayıcıya kalır.
  const ctrl = k.gonder('keydown', { key: '+', ctrlKey: true });
  assert.equal(ctrl.engellendi, false);
  assert.equal(degisimler.length, 1);
  const ok = k.gonder('keydown', { key: 'ArrowRight' });
  assert.equal(ok.engellendi, true);
  assert.equal(degisimler.length, 2);
  assert.equal(k.gonder('keydown', { key: 'q' }).engellendi, false);
  // İşaretçi: odak + yakalama, sürükleme kaydırır.
  const once = g.durum.t0;
  k.gonder('pointerdown', { pointerId: 5, offsetX: alan.x + 500 });
  assert.equal(k.odak, 1);
  assert.deepEqual(k.yakalanan, [5]);
  k.gonder('pointermove', { pointerId: 5, offsetX: alan.x + 400 });
  k.gonder('pointerup', { pointerId: 5, offsetX: alan.x + 400 });
  assert.ok(g.durum.t0 > once, 'sola sürükle = sonraki zaman');
  assert.equal(g.durum.suruklenen, null);
  // Çift tık imleç koyar; okuma ham veriden.
  k.gonder('dblclick', { offsetX: alan.x + 100 });
  k.gonder('dblclick', { offsetX: alan.x + 700 });
  assert.ok(Number.isFinite(g.durum.imlecA) && Number.isFinite(g.durum.imlecB));
  const okuma = g.okuma();
  assert.ok(okuma.enerji && okuma.enerji.mah > 0 && Number.isFinite(okuma.dV));
  assert.ok(degisimler.at(-1).A === g.durum.imlecA);
  // durumAyarla (eşleme) onDegisim ÇAĞIRMAZ ama çizer.
  const sayi = degisimler.length;
  k.ctx.sifirla();
  g.durumAyarla({ t0: g.durum.veriT0, t1: g.durum.veriT0 + 5000, imlecA: g.durum.veriT0 + 1000, imlecB: null });
  assert.equal(degisimler.length, sayi);
  assert.ok(k.ctx.vuruslar.length > 0, 'eşlemede yeniden çizildi');
  assert.equal(g.durum.imlecB, null);
  // veriAyarla koru: pencere ve imleç kalır.
  const p = [g.durum.t0, g.durum.t1];
  g.veriAyarla(ornekSeriler(), { koru: true });
  assert.deepEqual([g.durum.t0, g.durum.t1], p);
  assert.ok(Number.isFinite(g.durum.imlecA));
  // yokEt: dinleyici kalmaz, çizim durur, olay etkisiz.
  g.yokEt();
  assert.equal(k.dinleyiciSayisi(), 0);
  k.ctx.sifirla();
  assert.equal(g.ciz(), null);
  assert.equal(k.ctx.vuruslar.length, 0);
  g.yokEt();
});

test('çizici: requestAnimationFrame ile tek kare; yokEt bekleyen kareyi iptal eder; gezgin kipi', () => {
  const kuyruk = [];
  const iptal = [];
  let kareNo = 0;
  const pencere = {
    devicePixelRatio: 1,
    requestAnimationFrame(fn) { kuyruk.push(fn); return ++kareNo; },
    cancelAnimationFrame(no) { iptal.push(no); },
  };
  const k = sahteKanvas(800, 44);
  const degisim = [];
  const g = new Grafik(k, { pencere, gezgin: true, onDegisim: (d) => degisim.push([d.t0, d.t1]) });
  g.veriAyarla(ornekSeriler());
  g.durumAyarla({ t0: 1e6 + 20000, t1: 1e6 + 40000 });
  g.durumAyarla({ t0: 1e6 + 30000, t1: 1e6 + 50000 });
  assert.equal(kuyruk.length, 1, 'birden çok değişiklik tek kare');
  assert.equal(k.ctx.vuruslar.length, 0, 'kare gelmeden çizim yok');
  kuyruk.shift()();
  const pencereBandi = k.ctx.dikdortgenler.filter((r) => r.renk === RENK_YEDEK.vurgu);
  assert.equal(pencereBandi.length, 2, 'gezgin penceresi: dolgu + kenar');
  assert.equal(k.ctx.yazilar.length, 0, 'gezginde yazı yok');
  // Gezginde sürükleme pencereyi taşır ve bildirir.
  k.gonder('pointerdown', { pointerId: 1, offsetX: g.sonPlan.alan.x + (1e6 + 40000 - 1e6) / (99980) * 800 });
  k.gonder('pointermove', { pointerId: 1, offsetX: 600 });
  assert.equal(degisim.length, 1);
  assert.ok(degisim[0][0] > 1e6 + 30000);
  assert.equal(kuyruk.length, 1);
  g.yokEt();
  assert.deepEqual(iptal, [2]);
});

// ── BAŞARIM ─────────────────────────────────────────────────────────────────

test('başarım: 1 M nokta × 2 kanal, 1200 px plan < 20 ms / kare (piramitten sonra)', (ctx) => {
  const n = 1_000_000;
  const { t, v, a } = kayitUret(n, 31337);
  const b0 = performance.now();
  const s = [
    seriHazirla({ ad: 'V', t, y: v, birim: 'V', boslukMs: BOSLUK_MS }),
    seriHazirla({ ad: 'I', t, y: a, birim: 'A', eksen: 'sag', boslukMs: BOSLUK_MS }),
  ];
  const kurulum = performance.now() - b0;
  const temel = durumKur(s);
  const boyut = { w: 1200 + 112, h: 300 };
  assert.equal(yerlesim(s, boyut).w, 1200);
  const r = rastgele(8);
  const T0 = temel.veriT0;
  const T1 = temel.veriT1;
  const pencereler = [[T0, T1], [T0, T0 + (T1 - T0) / 2]];
  for (let k = 0; k < 40; k++) {
    const aralik = (T1 - T0) * 10 ** (-r() * 4);
    const bas = T0 + r() * (T1 - T0 - aralik);
    pencereler.push([bas, bas + aralik]);
  }
  const sureler = pencereler.map(([p0, p1]) => {
    const d = durumBirlestir(temel, { t0: p0, t1: p1, imlecA: p0 + (p1 - p0) / 3, imlecB: p0 + (p1 - p0) * 2 / 3 });
    let en = Infinity;
    for (let k = 0; k < 3; k++) { // gürültü: üç ölçümün en küçüğü
      const b = performance.now();
      cizimPlani(s, d, boyut);
      en = Math.min(en, performance.now() - b);
    }
    return en;
  });
  // Tam kare (plan + sahte bağlama uygulama) ve imleç okuması.
  const kanvas = sahteKanvas(boyut.w, boyut.h);
  const g = new Grafik(kanvas, { pencere: { devicePixelRatio: 2 } });
  g.veriAyarla(s);
  const kareler = pencereler.slice(0, 15).map(([p0, p1]) => {
    g.durumAyarla({ t0: p0, t1: p1 });
    kanvas.ctx.sifirla();
    const b = performance.now();
    g.ciz();
    return performance.now() - b;
  });
  const bo = performance.now();
  imlecOkuma(s, T0 + (T1 - T0) * 0.1, T0 + (T1 - T0) * 0.9);
  const okuma = performance.now() - bo;
  g.yokEt();
  const sirali = sureler.slice().sort((p, q) => p - q);
  const bilgi = `piramit (2 kanal) ${kurulum.toFixed(1)} ms; plan ${sureler.length} kare: ortanca ` +
    `${sirali[sirali.length >> 1].toFixed(2)} ms, en kötü ${sirali.at(-1).toFixed(2)} ms; tam kare (sahte ctx) en kötü ` +
    `${Math.max(...kareler).toFixed(2)} ms; imleç okuması (%80 aralık, 800 bin örnek) ${okuma.toFixed(1)} ms`;
  ctx.diagnostic(bilgi);
  console.log(`  başarım: ${bilgi}`);
  assert.ok(sirali.at(-1) < 20, `plan ${sirali.at(-1)} ms ≥ 20 ms`);
  assert.ok(kurulum < 1000, `piramit ${kurulum} ms`);
});

test('planUygula: komut türleri bağlama doğru çevrilir (saydamlık geri alınır, desen sıfırlanır)', () => {
  const c = new SahteBaglam();
  const plan = {
    komutlar: [
      { tur: 'dikdortgen', x: 1, y: 2, w: 3, h: 4, dolgu: 'imlec', saydamlik: 0.07, kenar: 'vurgu', kalinlik: 1.5 },
      { tur: 'kirp', x: 0, y: 0, w: 10, h: 10 },
      { tur: 'cizgi', noktalar: Float64Array.of(0, 0, 5, 5, 9, 1), renk: 'volt', kalinlik: 1.5, desen: [6, 4] },
      { tur: 'nokta', x: 3, y: 3, r: 1.5, renk: 'amper' },
      { tur: 'kirpBitir' },
      { tur: 'yazi', x: 7, y: 8, metin: 'A', renk: 'imlec', hiza: 'left', taban: 'top' },
      { tur: 'bilinmeyen' },
    ],
  };
  planUygula(c, plan, (ad) => `#${ad}`);
  assert.deepEqual(c.dikdortgenler, [
    { tur: 'dolgu', renk: '#imlec', alfa: 0.07, x: 1, y: 2, w: 3, h: 4 },
    { tur: 'kenar', renk: '#vurgu', x: 1, y: 2, w: 3, h: 4 },
  ]);
  assert.equal(c.globalAlpha, 1);
  assert.deepEqual(c.vuruslar[0].yol.map((p) => p.slice(0, 3)), [[0, 0, 'moveTo'], [5, 5, 'lineTo'], [9, 1, 'lineTo']]);
  assert.deepEqual(c.vuruslar[0].desen, [6, 4]);
  assert.deepEqual(c.desen, [], 'desen sonda sıfırlanır');
  assert.equal(c.dolgular[0].renk, '#amper');
  assert.deepEqual(c.yazilar, [{ metin: 'A', x: 7, y: 8, renk: '#imlec', hiza: 'left' }]);
  assert.equal(c.derinlik, 0);
  assert.equal(c.lineCap, 'round');
});

test('seriHazirla: piramit bir kez; uyumsuz uzunluk reddedilir; Grafik canvas ister', () => {
  const t = Float64Array.of(0, 1, 2);
  const y = Float64Array.of(1, 2, 3);
  const oz = ozetKur(t, y);
  const s = seriHazirla({ ad: 'V', t, y, oz, eksen: 'yanlis' });
  assert.equal(s.oz, oz, 'verilen piramit kullanılır');
  assert.equal(s.eksen, 'sol');
  assert.notEqual(seriHazirla({ ad: 'V', t, y: Float64Array.of(1, 2, 3), oz }).oz, oz, 'başka y: yeniden kurulur');
  assert.throws(() => seriHazirla({ ad: 'V', t, y: Float64Array.of(1) }), RangeError);
  assert.throws(() => new Grafik(null), TypeError);
  assert.throws(() => new Grafik({}), TypeError);
});

// ── 3E (OS2): x ekseni seçeneği — spektrumda x = Hz, çentik düz 1-2-5, yazı çağırandan ──
/** Spektrum benzeri seri: x 0 … 41 666 Hz (artan sayı), 2049 nokta. */
function spektrumSerisi() {
  const n = 2049;
  const t = new Float64Array(n).map((_, i) => i * (83333 / 4096));
  const y = new Float64Array(n).map((_, i) => (i === 50 ? 1 : 0.001));
  return [seriHazirla({ ad: 'S', t, y, birim: 'V', renk: 'volt' })];
}
const hzYazi = (v) => (v >= 1000 ? (v / 1000).toFixed(1) + ' kHz' : v.toFixed(0) + ' Hz');

test('3E xEksen: verilmezse G8 (zaman çentikleri, ss:dd:sn); verilirse düz 1-2-5 ve yazı çağırandan', () => {
  const s = spektrumSerisi();
  const d = durumKur(s);
  const zaman = cizimPlani(s, d, { w: 800, h: 240 }, { zamanKokeni: 0 });
  const zamanYazilari = zaman.komutlar.filter((k) => k.tur === 'yazi' && k.rol === 'eksen' && k.y > zaman.alan.y + zaman.alan.h);
  assert.ok(zamanYazilari.length >= 2 && zamanYazilari.every((k) => /^\d\d:\d\d:\d\d/.test(k.metin)), zamanYazilari.map((k) => k.metin).join(' '));
  const sayi = cizimPlani(s, d, { w: 800, h: 240 }, { zamanKokeni: 0, xEksen: { tur: 'sayi', yazi: hzYazi } });
  const adim = sayi.x.adim;
  assert.ok([1, 2, 5].includes(adim / 10 ** Math.floor(Math.log10(adim))), `1-2-5 değil: ${adim}`);
  assert.equal(adim, guzelAdimlar(0, 83333 / 2, Math.max(2, Math.floor(sayi.alan.w / 110))).adim);
  assert.ok(sayi.x.degerler.every((v) => Math.abs(v / adim - Math.round(v / adim)) < 1e-9), 'çentik adımın katı');
  const yazilar = sayi.komutlar.filter((k) => k.tur === 'yazi' && k.rol === 'eksen' && k.y > sayi.alan.y + sayi.alan.h);
  assert.deepEqual(yazilar.map((k) => k.metin), sayi.x.degerler.map((v) => hzYazi(v)));
  assert.ok(yazilar.some((k) => k.metin.endsWith('kHz')));
  /* x ölçeği değişmez: aynı t aynı piksele düşer (yalnız çentik ve yazı farklı) */
  const nokta = (p) => p.komutlar.find((k) => k.rol === 'seri');
  assert.deepEqual(Array.from(nokta(sayi).noktalar), Array.from(nokta(zaman).noktalar));
});

test('3E xEksen: sayiAdimlari kökene göre; atan / boş yazıcı boş metin; xSayiEkseni yalnız tur === sayi', () => {
  assert.deepEqual(sayiAdimlari(0, 10, 5, 0), guzelAdimlar(0, 10, 5));
  assert.deepEqual(sayiAdimlari(100, 110, 5, 100).degerler, guzelAdimlar(0, 10, 5).degerler.map((v) => v + 100));
  assert.equal(xSayiEkseni({ xEksen: { tur: 'sayi' } }), true);
  assert.equal(xSayiEkseni({ xEksen: { tur: 'zaman' } }), false);
  assert.equal(xSayiEkseni({}), false);
  assert.equal(xSayiEkseni(undefined), false);
  assert.equal(xYazici({})(61000, 1000), zamanYazi(61000, 1000));
  assert.equal(xYazici({ xEksen: { tur: 'sayi', yazi: () => { throw new Error('x'); } } })(5, 1), '');
  assert.equal(xYazici({ xEksen: { tur: 'sayi', yazi: () => null } })(5, 1), '');
  assert.equal(xYazici({ xEksen: { tur: 'sayi', yazi: (v) => v * 2 } })(5, 1), '10');
});

test('3E xEksen: Grafik sınıfı seçeneği plana geçiriyor (çizilen yazı Hz)', () => {
  const k = sahteKanvas(800, 240);
  const g = new Grafik(k, { pencere: { devicePixelRatio: 1 }, zamanKokeni: 0, xEksen: { tur: 'sayi', yazi: hzYazi } });
  g.veriAyarla(spektrumSerisi());
  const plan = g.ciz();
  assert.ok(plan.x.degerler.length >= 2);
  const yazilan = k.ctx.yazilar.map((y) => y.metin);
  assert.ok(plan.x.degerler.every((v) => yazilan.includes(hzYazi(v))), yazilan.join(' | '));
  assert.ok(!yazilan.some((m) => /^\d\d:\d\d:\d\d/.test(m)), 'zaman yazısı kalmadı');
  g.yokEt();
});
