// ortak/test/ozet.test.js — dilim 2D: özet piramidi + pencere sorgusu.
// Kararlar: tasarim/2026-10-02-alt-proje-2-ortak.md D1–D3, D5; üst tasarım §9, Ö1.
//
// Kaba kuvvet başvuruları bu dosyada, src'den BAĞIMSIZ yazıldı (kendi ikili
// aramaları, düz döngüler). Yalnız sütun sınırı formülü src ile ortak: o bir
// SÖZLEŞME (ozet.js başı) — "gerçek sütun" ise ayrıca ⌊(t − t0)/(t1 − t0)·W⌋
// ile hesaplanıp ±1 ölçütüyle sınanır.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  BLOK, altSinir, ustSinir, ozetKur, ozetPencere, ozetAralik, boslukBolumleri, blokZamani,
} from '../src/ozet.js';

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

/** İlk t[i] ≥ x (bağımsız ikili arama). */
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

const ayni = (p, q) => p === q || (Number.isNaN(p) && Number.isNaN(q));

/**
 * Sınanacak seri: ~500 örnek/s titreşimli zaman, eşit zaman damgaları,
 * boşluklar, sınırlı rastgele yürüyüş (|y| ≲ 5), dağınık NaN + bir NaN koşusu.
 */
function seriUret(n, tohum, { boslukSayisi = 12, nanOrani = 0.002, nanKosusu = 3000 } = {}) {
  const r = rastgele(tohum);
  const t = new Float64Array(n);
  const y = new Float64Array(n);
  const boslukYeri = new Set();
  while (boslukYeri.size < boslukSayisi) boslukYeri.add(1 + Math.floor(r() * (n - 2)));
  let zaman = 1_000_000 + r() * 1000;
  let deger = 0;
  for (let i = 0; i < n; i++) {
    if (i > 0) {
      let adim;
      if (boslukYeri.has(i)) adim = 2000 + r() * 60000; // boşluk
      else if (r() < 0.001) adim = 0; // eşit zaman damgası
      else adim = 2 + (r() - 0.5) * 0.6;
      zaman += adim;
    }
    t[i] = zaman;
    deger = 0.98 * deger + (r() - 0.5) * 0.5;
    y[i] = deger;
  }
  for (let i = 0; i < n; i++) if (r() < nanOrani) y[i] = NaN;
  if (nanKosusu > 0) {
    const bas = Math.floor(n * 0.6);
    for (let i = bas; i < bas + nanKosusu && i < n; i++) y[i] = NaN;
  }
  return { t, y, bosluklar: [...boslukYeri].sort((p, q) => p - q) };
}

/** K tek örneklik sıçrama: ilk/son indis, boşlukların iki yanı, rastgele yerler. */
function sicramaEkle(t, y, bosluklar, K, r) {
  const n = y.length;
  const yerler = new Set([0, n - 1]);
  for (const g of bosluklar.slice(0, 6)) {
    yerler.add(g - 1);
    yerler.add(g);
  }
  while (yerler.size < K) yerler.add(Math.floor(r() * n));
  const sicramalar = [];
  let j = 0;
  for (const i of [...yerler].sort((p, q) => p - q)) {
    const isaret = r() < 0.5 ? 1 : -1;
    const v = isaret * (50 + 1.37 * j++); // gürültünün (|y| ≲ 5) çok dışında, hepsi farklı
    y[i] = v;
    sicramalar.push({ i, v, t: t[i] });
  }
  return sicramalar;
}

/** Sözleşmeye göre sütunların kaba kuvvet min/maks'ı + her sütunun ilk indisi. */
function sutunlarKabaKuvvet(t, y, a, b, t0, t1, W) {
  const sinir = new Float64Array(W + 1);
  for (let c = 0; c <= W; c++) {
    let s = t0 + (t1 - t0) * c / W;
    if (s > t1) s = t1;
    sinir[c] = s;
  }
  const ref = new Float64Array(2 * W).fill(NaN);
  const ilk = new Int32Array(W).fill(-1);
  let c = 0;
  for (let i = a; i < b; i++) {
    while (c < W - 1 && t[i] >= sinir[c + 1]) c++;
    if (ilk[c] < 0) ilk[c] = i;
    const v = y[i];
    if (Number.isNaN(v)) continue;
    if (Number.isNaN(ref[2 * c]) || v < ref[2 * c]) ref[2 * c] = v;
    if (Number.isNaN(ref[2 * c + 1]) || v > ref[2 * c + 1]) ref[2 * c + 1] = v;
  }
  return { ref, ilk };
}

/** Bir pencereyi bütün iddialarla sınar; sayaçları günceller. */
function pencereSina(oz, t, y, t0, t1, W, sicramalar, sicramaKume, boslukMs, sayac) {
  const n = t.length;
  const a = ilkBuyukEsit(t, t0);
  const b = ilkBuyuk(t, t1);
  const etiket = `t0=${t0} t1=${t1} W=${W} (a=${a} b=${b})`;
  const r = ozetPencere(oz, t0, t1, W, { boslukMs });

  if (b - a <= 2 * W) {
    // HAM kip: aralıktaki bütün noktalar + iki yandaki birer komşu.
    assert.equal(r.tur, 'ham', etiket);
    assert.equal(r.i0, a > 0 ? a - 1 : 0, `i0 ${etiket}`);
    assert.equal(r.i1, b < n ? b + 1 : n, `i1 ${etiket}`);
    for (const s of sicramalar) {
      if (s.i >= a && s.i < b) {
        assert.ok(s.i >= r.i0 && s.i < r.i1, `sıçrama ${s.i} ham aralıkta yok ${etiket}`);
        assert.equal(y[s.i], s.v);
        sayac.hamSicrama++;
      }
    }
    // Boşluk parçaları (bağımsız): [i0, i1) dt > boslukMs olan yerde bölünür.
    const bek = [];
    let bas = r.i0;
    for (let i = r.i0 + 1; i < r.i1; i++) {
      if (t[i] - t[i - 1] > boslukMs) { bek.push([bas, i]); bas = i; }
    }
    if (r.i1 > r.i0) bek.push([bas, r.i1]);
    assert.deepEqual(r.bolumler, bek, `bolumler ${etiket}`);
    sayac.ham++;
    return;
  }

  assert.equal(r.tur, 'ozet', etiket);
  assert.equal(r.sutunlar.length, 2 * W);
  const sut = r.sutunlar;

  // (c) Uydurma uç yok — daha güçlüsü: her sütun, kendi zaman penceresindeki
  // NaN'sız ham örneklerin TAM min/maks'ı; örneksiz sütun NaN.
  const { ref, ilk } = sutunlarKabaKuvvet(t, y, a, b, t0, t1, W);
  for (let c = 0; c < W; c++) {
    if (!ayni(sut[2 * c], ref[2 * c]) || !ayni(sut[2 * c + 1], ref[2 * c + 1])) {
      assert.fail(`sütun ${c}: [${sut[2 * c]}, ${sut[2 * c + 1]}] ≠ ham [${ref[2 * c]}, ${ref[2 * c + 1]}] ${etiket}`);
    }
  }

  // Boşluk kesikleri (D1): sütunun ilk örneği ile bir önceki örnek arası > boslukMs.
  for (let c = 0; c < W; c++) {
    const i = ilk[c];
    const bek = i > 0 && t[i] - t[i - 1] > boslukMs ? 1 : 0;
    if (r.kesik[c] !== bek) assert.fail(`kesik[${c}] = ${r.kesik[c]}, beklenen ${bek} ${etiket}`);
    sayac.kesik += bek;
  }

  // (a) Ö1: NaN'sız HER ham örnek, gerçek sütununun ±1 komşuluğundaki bir
  // sütunun [min, maks] aralığında.
  const olcek = W / (t1 - t0);
  const gercekSutun = (ts) => {
    if (!(t1 > t0)) return W - 1;
    let c = Math.floor((ts - t0) * olcek);
    if (c > W - 1) c = W - 1;
    if (c < 0) c = 0;
    return c;
  };
  for (let i = a; i < b; i++) {
    const v = y[i];
    if (Number.isNaN(v)) continue;
    const gc = gercekSutun(t[i]);
    let kapsandi = false;
    for (let c = Math.max(0, gc - 1); c <= Math.min(W - 1, gc + 1); c++) {
      if (sut[2 * c] <= v && v <= sut[2 * c + 1]) { kapsandi = true; break; }
    }
    if (!kapsandi) assert.fail(`örnek ${i} (y=${v}) ±1 sütunda kapsanmıyor ${etiket}`);
  }

  // (b) Sıçramalar uç değer olarak görünür: ±1 sütunda min'e/maks'a EŞİT,
  // ya da o sütunda aynı işaretli daha büyük bir sıçrama onu örtüyor.
  for (const s of sicramalar) {
    if (s.i < a || s.i >= b) continue;
    const gc = gercekSutun(s.t);
    if (gc === 0 || gc === W - 1) sayac.kenarSicrama++;
    let esit = false;
    let ortulu = false;
    for (let c = Math.max(0, gc - 1); c <= Math.min(W - 1, gc + 1); c++) {
      const uc = s.v > 0 ? sut[2 * c + 1] : sut[2 * c];
      if (uc === s.v) esit = true;
      else if ((s.v > 0 ? uc > s.v : uc < s.v) && sicramaKume.has(uc)) ortulu = true;
    }
    if (esit) sayac.gorunur++;
    else if (ortulu) sayac.ortulu++;
    else assert.fail(`sıçrama ${s.i} (y=${s.v}) görünmüyor ${etiket}`);
  }
  sayac.ozet++;
}

// ── piramit yapısı ─────────────────────────────────────────────────────────

test('ozetKur: her düzeyin her bloğu ham bloğun NaN\'sız min/maks\'ı (kaba kuvvet)', () => {
  const r = rastgele(7);
  for (const n of [0, 1, 7, 8, 9, 63, 64, 65, 1000, 4097]) {
    for (const blok of [2, 3, BLOK, 16]) {
      const t = new Float64Array(n);
      const y = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        t[i] = i * 2;
        y[i] = r() < 0.1 ? NaN : (r() - 0.5) * 10;
      }
      if (n >= 40) for (let i = 16; i < 40; i++) y[i] = NaN; // tamamen NaN bloklar
      const oz = ozetKur(t, y, { blok });
      assert.equal(oz.n, n);
      assert.equal(oz.blok, blok);
      assert.equal(oz.min[0], null);
      let boy = 1;
      for (let k = 1; k < oz.min.length; k++) {
        boy *= blok;
        assert.equal(oz.min[k].length, Math.floor(n / boy), `n=${n} B=${blok} k=${k} uzunluk`);
        for (let j = 0; j < oz.min[k].length; j++) {
          let mn = NaN;
          let mx = NaN;
          for (let i = j * boy; i < (j + 1) * boy; i++) {
            if (Number.isNaN(y[i])) continue;
            if (Number.isNaN(mn) || y[i] < mn) mn = y[i];
            if (Number.isNaN(mx) || y[i] > mx) mx = y[i];
          }
          assert.ok(ayni(oz.min[k][j], mn) && ayni(oz.maks[k][j], mx), `n=${n} B=${blok} k=${k} j=${j}`);
          assert.deepEqual(blokZamani(oz, k, j), [t[j * boy], t[(j + 1) * boy - 1]]);
        }
      }
      // En üst düzeyin ötesinde tam blok kalmamalı.
      assert.ok(Math.floor(n / (boy * blok)) === 0, `n=${n} B=${blok} eksik düzey`);
    }
  }
});

test('ozetKur: bellek ek yükü ≈ %14 (D2) ve geçersiz girdi reddedilir', () => {
  const n = 800_000;
  const t = new Float64Array(n).map((_, i) => i);
  const y = new Float64Array(n);
  const oz = ozetKur(t, y);
  let ek = 0;
  for (let k = 1; k < oz.min.length; k++) ek += oz.min[k].length + oz.maks[k].length;
  const oran = ek / (2 * n);
  assert.ok(oran > 0.13 && oran < 0.15, `ek bellek oranı ${oran}`);

  assert.throws(() => ozetKur(new Float64Array(3), new Float64Array(2)), RangeError);
  assert.throws(() => ozetKur(Float64Array.of(0, 2, 1), new Float64Array(3)), RangeError);
  assert.throws(() => ozetKur(Float64Array.of(0, NaN, 1), new Float64Array(3)), RangeError);
  assert.throws(() => ozetKur(Float64Array.of(NaN), new Float64Array(1)), RangeError);
  assert.throws(() => ozetKur(Float64Array.of(0, Infinity), new Float64Array(2)), RangeError);
  assert.throws(() => ozetKur(t, y, { blok: 1 }), RangeError);
  assert.throws(() => ozetKur(t, y, { blok: 2.5 }), RangeError);
  const oz2 = ozetKur(Float64Array.of(0, 1), new Float64Array(2));
  assert.throws(() => ozetPencere(oz2, 1, 0, 10), RangeError);
  assert.throws(() => ozetPencere(oz2, 0, Infinity, 10), RangeError);
  assert.throws(() => ozetPencere(oz2, NaN, 1, 10), RangeError);
  assert.throws(() => ozetPencere(oz2, 0, 1, 0), RangeError);
  assert.throws(() => ozetPencere(oz2, 0, 1, 2.5), RangeError);
  assert.throws(() => ozetPencere(oz2, 0, 1, 4, { boslukMs: -1 }), RangeError);
  assert.throws(() => ozetPencere(oz2, 0, 1, 4, { boslukMs: NaN }), RangeError);
  assert.throws(() => blokZamani(oz, 0, 0), RangeError);
  assert.throws(() => blokZamani(oz, 1, oz.min[1].length), RangeError);
});

test('altSinir / ustSinir / ozetAralik kaba kuvvetle aynı', () => {
  const r = rastgele(11);
  const n = 5000;
  const t = new Float64Array(n);
  const y = new Float64Array(n);
  let z = 0;
  for (let i = 0; i < n; i++) {
    z += r() < 0.2 ? 0 : r() * 3;
    t[i] = Math.round(z * 4) / 4; // eşitler bol
    y[i] = r() < 0.05 ? NaN : r() * 100 - 50;
  }
  const oz = ozetKur(t, y);
  for (let k = 0; k < 500; k++) {
    const x = t[Math.floor(r() * n)] + (r() < 0.5 ? 0 : (r() - 0.5));
    assert.equal(altSinir(t, x), ilkBuyukEsit(t, x));
    assert.equal(ustSinir(t, x), ilkBuyuk(t, x));
    const a = Math.floor(r() * n);
    const b = Math.min(n, a + Math.floor(r() * r() * n));
    let mn = NaN;
    let mx = NaN;
    for (let i = a; i < b; i++) {
      if (Number.isNaN(y[i])) continue;
      if (Number.isNaN(mn) || y[i] < mn) mn = y[i];
      if (Number.isNaN(mx) || y[i] > mx) mx = y[i];
    }
    const s = ozetAralik(oz, a, b);
    assert.ok(ayni(s.min, mn) && ayni(s.maks, mx), `[${a}, ${b})`);
  }
  assert.ok(Number.isNaN(ozetAralik(oz, 10, 10).min));
  assert.ok(Number.isNaN(ozetAralik(oz, 10, 3).maks));
});

// ── Ö1 özellik testi ──────────────────────────────────────────────────────

test('Ö1: tek örneklik sıçramalar her yakınlaştırmada ve genişlikte görünür, uç uydurulmaz', () => {
  const n = 200_000;
  const { t, y, bosluklar } = seriUret(n, 20261002);
  const r = rastgele(424242);
  const sicramalar = sicramaEkle(t, y, bosluklar, 64, r);
  const sicramaKume = new Set(sicramalar.map((s) => s.v));
  const oz = ozetKur(t, y);
  const boslukMs = 1000; // seride boşluk ≥ 2000 ms, normal adım ≤ 2.3 ms

  const T0 = t[0];
  const T1 = t[n - 1];
  const toplam = T1 - T0;
  const sayac = { ham: 0, ozet: 0, gorunur: 0, ortulu: 0, hamSicrama: 0, kenarSicrama: 0, kesik: 0 };
  const rastgeleW = () => Math.max(1, Math.min(4000, Math.round(Math.exp(r() * Math.log(4000)))));

  // 1) Bütün seri, çeşitli genişlikler (W = 1 dahil: tek sütun bütün seriyi taşır).
  for (const W of [1, 2, 3, 5, 8, 13, 100, 333, 1000, 2500, 4000]) {
    pencereSina(oz, t, y, T0, T1, W, sicramalar, sicramaKume, boslukMs, sayac);
  }
  // 2) Rastgele yakınlaştırmalar: bütün seriden birkaç noktaya (10^-6.5), bazen serinin dışına taşan.
  for (let k = 0; k < 1000; k++) {
    const W = rastgeleW();
    const aralik = toplam * 10 ** (-r() * 6.5);
    const t0 = T0 - 0.02 * toplam + r() * (1.04 * toplam - aralik);
    pencereSina(oz, t, y, t0, t0 + aralik, W, sicramalar, sicramaKume, boslukMs, sayac);
  }
  // 3) Sıçrama merkezli: içinde, tam sol kenarda, tam sağ kenarda.
  for (const s of sicramalar) {
    const W = rastgeleW();
    const aralik = toplam * 10 ** (-r() * 6);
    const pay = r() * aralik;
    pencereSina(oz, t, y, s.t - pay, s.t - pay + aralik, W, sicramalar, sicramaKume, boslukMs, sayac);
    pencereSina(oz, t, y, s.t, s.t + aralik, rastgeleW(), sicramalar, sicramaKume, boslukMs, sayac);
    pencereSina(oz, t, y, s.t - aralik, s.t, rastgeleW(), sicramalar, sicramaKume, boslukMs, sayac);
  }

  // Testin gerçekten her yolu yürüdüğünün kanıtı (boş geçen özellik testi bir şey kanıtlamaz).
  assert.ok(sayac.ham >= 50, `ham kip az sınandı: ${sayac.ham}`);
  assert.ok(sayac.ozet >= 200, `özet kip az sınandı: ${sayac.ozet}`);
  assert.ok(sayac.gorunur >= 500, `görünür sıçrama az: ${sayac.gorunur}`);
  assert.ok(sayac.hamSicrama >= 20, `ham kipte sıçrama az: ${sayac.hamSicrama}`);
  assert.ok(sayac.kenarSicrama >= 50, `kenar sütunda sıçrama az: ${sayac.kenarSicrama}`);
  assert.ok(sayac.kesik >= 20, `boşluk kesiği az: ${sayac.kesik}`);
  console.log(`  Ö1 sayaçları: ${JSON.stringify(sayac)}`);
});

test('B bağımsızlığı: blok 2/3/8/16 ile sütunlar birebir aynı', () => {
  const { t, y } = seriUret(30_000, 99, { nanKosusu: 500 });
  const r = rastgele(5);
  const ozler = [2, 3, 8, 16].map((blok) => ozetKur(t, y, { blok }));
  for (let k = 0; k < 60; k++) {
    const W = 1 + Math.floor(r() * 700);
    const aralik = (t[t.length - 1] - t[0]) * 10 ** (-r() * 3);
    const t0 = t[0] + r() * (t[t.length - 1] - t[0] - aralik);
    const sonuclar = ozler.map((oz) => ozetPencere(oz, t0, t0 + aralik, W));
    for (const s of sonuclar.slice(1)) {
      assert.equal(s.tur, sonuclar[0].tur);
      if (s.tur === 'ozet') {
        for (let c = 0; c < 2 * W; c++) assert.ok(ayni(s.sutunlar[c], sonuclar[0].sutunlar[c]));
      }
    }
  }
});

// ── ham/özet eşiği ve uç durumlar ──────────────────────────────────────────

test('D3 eşiği: ≤ 2W ham, 2W + 1 özet; komşu noktalar; boş seri', () => {
  const n = 1000;
  const t = new Float64Array(n).map((_, i) => i);
  const y = new Float64Array(n).map((_, i) => Math.sin(i));
  const oz = ozetKur(t, y);
  assert.deepEqual(ozetPencere(oz, 0, 19, 10), { tur: 'ham', i0: 0, i1: 21 }); // 20 nokta
  const o = ozetPencere(oz, 0, 20, 10); // 21 nokta
  assert.equal(o.tur, 'ozet');
  assert.ok(!('kesik' in o), 'boslukMs verilmeden kesik dönmemeli');
  assert.deepEqual(ozetPencere(oz, 500, 519, 10), { tur: 'ham', i0: 499, i1: 521 });
  assert.deepEqual(ozetPencere(oz, 980.5, 2000, 10), { tur: 'ham', i0: 980, i1: 1000 });
  assert.deepEqual(ozetPencere(oz, -50, -10, 10), { tur: 'ham', i0: 0, i1: 1 });
  assert.deepEqual(ozetPencere(oz, 10.2, 10.7, 10), { tur: 'ham', i0: 10, i1: 12 }); // içi boş: iki komşu
  assert.deepEqual(ozetPencere(oz, 5000, 6000, 3), { tur: 'ham', i0: 999, i1: 1000 });

  const bos = ozetKur(new Float64Array(0), new Float64Array(0));
  assert.deepEqual(ozetPencere(bos, 0, 10, 100), { tur: 'ham', i0: 0, i1: 0 });

  // t0 = t1, aynı anda çok örnek: hepsi son sütunda.
  const te = new Float64Array(50).fill(7);
  const ye = new Float64Array(50).map((_, i) => i - 20);
  const s = ozetPencere(ozetKur(te, ye), 7, 7, 3);
  assert.equal(s.tur, 'ozet');
  assert.ok(Number.isNaN(s.sutunlar[0]) && Number.isNaN(s.sutunlar[3]));
  assert.deepEqual([s.sutunlar[4], s.sutunlar[5]], [-20, 29]);
});

// ── boşluk (D1) ────────────────────────────────────────────────────────────

test('boşluk: boşluğun üstündeki sütunlar NaN, kesik işareti, boslukBolumleri', () => {
  // 0…99 ms, sonra 1000…1099 ms: 901 ms'lik boşluk.
  const t = new Float64Array(200).map((_, i) => (i < 100 ? i : 900 + i));
  const y = new Float64Array(200).map((_, i) => (i % 7) - 3);
  const oz = ozetKur(t, y);
  const r = ozetPencere(oz, 0, 1099, 50, { boslukMs: 10 });
  assert.equal(r.tur, 'ozet');
  const w = 1099 / 50;
  for (let c = 0; c < 50; c++) {
    const bas = c * w;
    const son = (c + 1) * w;
    const verili = (bas <= 99) || (son > 1000);
    const mn = r.sutunlar[2 * c];
    const mx = r.sutunlar[2 * c + 1];
    if (verili) assert.ok(Number.isFinite(mn) && Number.isFinite(mx), `sütun ${c} veri bekleniyordu`);
    else assert.ok(Number.isNaN(mn) && Number.isNaN(mx), `sütun ${c} boşluğun üstünde, NaN olmalı`);
    assert.equal(r.kesik[c], c === 45 ? 1 : 0, `kesik[${c}]`);
  }
  assert.ok(Number.isNaN(r.sutunlar[2 * 20]), 'boşluğun ortası');
  // Sütun 45 = [989.1, 1011.1) ms → indis 100…111 (t 1000…1011): y = i mod 7 − 3'ün bütün değerleri.
  assert.deepEqual([r.sutunlar[90], r.sutunlar[91]], [-3, 3]);
  // Sütun 4 = [87.9, 109.9) ms → indis 88…99: boşluğun önündeki son sütun.
  assert.deepEqual([r.sutunlar[8], r.sutunlar[9]], [-3, 3]);

  assert.deepEqual(boslukBolumleri(t, 10), [[0, 100], [100, 200]]);
  assert.deepEqual(boslukBolumleri(t, 901), [[0, 200]], 'dt = boslukMs boşluk DEĞİL');
  assert.deepEqual(boslukBolumleri(t, 900.5), [[0, 100], [100, 200]]);
  assert.deepEqual(boslukBolumleri(t, 10, 50, 150), [[50, 100], [100, 150]]);
  assert.deepEqual(boslukBolumleri(t, 10, 0, 100), [[0, 100]]);
  assert.deepEqual(boslukBolumleri(t, 10, 100, 101), [[100, 101]]);
  assert.deepEqual(boslukBolumleri(t, 10, 60, 60), []);
  assert.deepEqual(boslukBolumleri(t, undefined), [[0, 200]]);
  assert.deepEqual(boslukBolumleri(t, Infinity), [[0, 200]]);
  assert.deepEqual(boslukBolumleri(new Float64Array(0), 10), []);
  assert.throws(() => boslukBolumleri(t, -1), RangeError);
  assert.throws(() => boslukBolumleri(t, '10'), RangeError);

  // Ham kipte boşluk parçaları; dt = boslukMs eşitliği bölmez.
  assert.deepEqual(ozetPencere(oz, 90, 1010, 100, { boslukMs: 10 }),
    { tur: 'ham', i0: 89, i1: 112, bolumler: [[89, 100], [100, 112]] });
  assert.deepEqual(ozetPencere(oz, 90, 1010, 100, { boslukMs: 901 }),
    { tur: 'ham', i0: 89, i1: 112, bolumler: [[89, 112]] });
});

test('boşluk bir sütunun içinde kalırsa: NaN sütun yok, kesik yok (piksel altı)', () => {
  // 0…450, sonra 455…1003: 5 ms'lik boşluk tek sütunun (100.3 ms) içinde.
  const t = new Float64Array(1000).map((_, i) => (i <= 450 ? i : i + 4));
  const y = new Float64Array(1000).map((_, i) => Math.cos(i / 10));
  const r = ozetPencere(ozetKur(t, y), 0, 1003, 10, { boslukMs: 2 });
  assert.equal(r.tur, 'ozet');
  for (let c = 0; c < 10; c++) {
    assert.ok(Number.isFinite(r.sutunlar[2 * c]), `sütun ${c}`);
    assert.equal(r.kesik[c], 0, `kesik[${c}]`);
  }
  assert.deepEqual(boslukBolumleri(t, 2), [[0, 451], [451, 1000]]);
});

// ── başarım (D5) ──────────────────────────────────────────────────────────

test('D5 başarım: 1 M noktada piramit < 500 ms, pencere sorgusu < 20 ms', (ctx) => {
  const n = 1_000_000;
  const { t, y } = seriUret(n, 31337, { boslukSayisi: 20, nanKosusu: 10_000 });
  const bas = performance.now();
  const oz = ozetKur(t, y);
  const kurSoguk = performance.now() - bas;
  const kurlar = [];
  for (let k = 0; k < 3; k++) {
    const b = performance.now();
    ozetKur(t, y);
    kurlar.push(performance.now() - b);
  }

  const r = rastgele(8);
  const T0 = t[0];
  const toplam = t[n - 1] - T0;
  const pencereler = [
    [T0, T0 + toplam, 4000], [T0, T0 + toplam, 1920], [T0, T0 + toplam, 1],
    [T0 + toplam * 0.3, T0 + toplam * 0.31, 4000], [T0 + toplam * 0.5, T0 + toplam * 0.5001, 1920],
  ];
  for (let k = 0; k < 45; k++) {
    const aralik = toplam * 10 ** (-r() * 3);
    const t0 = T0 + r() * (toplam - aralik);
    pencereler.push([t0, t0 + aralik, 500 + Math.floor(r() * 3500)]);
  }
  const b0 = performance.now();
  ozetPencere(oz, T0, T0 + toplam, 4000, { boslukMs: 1000 });
  const pencereSoguk = performance.now() - b0;
  const sureler = pencereler.map(([t0, t1, W]) => {
    const b = performance.now();
    ozetPencere(oz, t0, t1, W, { boslukMs: 1000 });
    return performance.now() - b;
  });
  const enKotu = Math.max(...sureler);
  const ozetBilgi = `ozetKur soğuk ${kurSoguk.toFixed(1)} ms, sıcak ${kurlar.map((x) => x.toFixed(1)).join('/')} ms; ` +
    `ozetPencere soğuk ${pencereSoguk.toFixed(2)} ms, ${sureler.length} sorguda en kötü ${enKotu.toFixed(2)} ms, ` +
    `ortanca ${sureler.sort((p, q) => p - q)[sureler.length >> 1].toFixed(2)} ms`;
  ctx.diagnostic(ozetBilgi);
  console.log(`  D5: ${ozetBilgi}`);
  assert.ok(kurSoguk < 500, `ozetKur ${kurSoguk} ms ≥ 500 ms`);
  assert.ok(pencereSoguk < 20, `ozetPencere (soğuk) ${pencereSoguk} ms ≥ 20 ms`);
  assert.ok(enKotu < 20, `ozetPencere ${enKotu} ms ≥ 20 ms`);
});
