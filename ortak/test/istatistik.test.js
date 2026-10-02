// ortak/test/istatistik.test.js — dilim 2D: aralık istatistiği + enerji (D4, D1).
//
// Başvurular bu dosyada, src'den BAĞIMSIZ düz döngülerle yazıldı: aralık
// doğrusal tarama ile süzülür (ikili arama yok), toplam düz, enerji birim
// çevrimi parça başına saat cinsinden (src ise ms toplayıp sonda böler).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { istatistik, enerji, MS_SAAT, AMS_MAH } from '../src/istatistik.js';

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

function istatistikRef(t, y, t0, t1) {
  let adet = 0;
  let min = NaN;
  let maks = NaN;
  let tMin = NaN;
  let tMaks = NaN;
  let top = 0;
  let kare = 0;
  for (let i = 0; i < t.length; i++) {
    if (!(t[i] >= t0 && t[i] <= t1)) continue;
    const v = y[i];
    if (Number.isNaN(v)) continue;
    adet++;
    if (adet === 1 || v < min) { min = v; tMin = t[i]; }
    if (adet === 1 || v > maks) { maks = v; tMaks = t[i]; }
    top += v;
    kare += v * v;
  }
  if (adet === 0) return { adet, min, maks, ort: NaN, rms: NaN, tepeTepe: NaN, tMin, tMaks };
  return { adet, min, maks, ort: top / adet, rms: Math.sqrt(kare / adet), tepeTepe: maks - min, tMin, tMaks };
}

/** Parça başına saat cinsinden yamuk; ölçek = Σ|parça| (karşılaştırma toleransı için). */
function enerjiRef(t, v, i, t0, t1, bosluk = Infinity) {
  const gecerli = [];
  for (let j = 0; j < t.length; j++) {
    if (t[j] >= t0 && t[j] <= t1 && !Number.isNaN(v[j]) && !Number.isNaN(i[j])) gecerli.push(j);
  }
  let wh = 0;
  let mah = 0;
  let sureS = 0;
  let olcekWh = 0;
  let olcekMah = 0;
  for (let k = 1; k < gecerli.length; k++) {
    const p = gecerli[k - 1];
    const q = gecerli[k];
    const dtMs = t[q] - t[p];
    if (dtMs > bosluk) continue;
    const saat = dtMs / 3600 / 1000;
    const pWh = 0.5 * (v[p] * i[p] + v[q] * i[q]) * saat;
    const pMah = 0.5 * (i[p] + i[q]) * 1000 * saat;
    wh += pWh;
    mah += pMah;
    olcekWh += Math.abs(pWh);
    olcekMah += Math.abs(pMah);
    sureS += dtMs / 1000;
  }
  return { wh, mah, sureS, olcekWh, olcekMah };
}

const ayni = (p, q) => p === q || (Number.isNaN(p) && Number.isNaN(q));

function yakin(gercek, beklenen, olcek, etiket, bagil = 1e-12) {
  if (Number.isNaN(beklenen)) {
    assert.ok(Number.isNaN(gercek), `${etiket}: NaN beklenen, ${gercek}`);
    return;
  }
  const tol = bagil * Math.max(Math.abs(olcek), Math.abs(beklenen), 1e-300);
  assert.ok(Math.abs(gercek - beklenen) <= tol, `${etiket}: ${gercek} ≠ ${beklenen} (tol ${tol})`);
}

/** Boşluklu, NaN'lı, eşit zamanlı seri. */
function seri(n, tohum) {
  const r = rastgele(tohum);
  const t = new Float64Array(n);
  const v = new Float64Array(n);
  const i = new Float64Array(n);
  let z = 5000;
  let ak = 0.8;
  for (let j = 0; j < n; j++) {
    if (j > 0) z += r() < 0.002 ? 3000 + r() * 20000 : (r() < 0.01 ? 0 : 1 + r() * 2);
    t[j] = z;
    v[j] = r() < 0.01 ? NaN : 3.0 + r() * 1.2;
    ak = 0.95 * ak + (r() - 0.45) * 0.3; // çoğunlukla artı, bazen eksi (şarj)
    i[j] = r() < 0.01 ? NaN : ak;
  }
  return { t, v, i, r };
}

// ── istatistik ─────────────────────────────────────────────────────────────

test('istatistik: rastgele aralıklarda kaba kuvvetle aynı (NaN, eşit zaman, kenar örnekler)', () => {
  const { t, v: y, r } = seri(20_000, 77);
  // Tek örneklik sıçramalar: maks/min ham veriden gelmeli.
  y[123] = 1e3;
  y[19_000] = -1e3;
  const n = t.length;
  let sayi = 0;
  for (let k = 0; k < 400; k++) {
    let t0;
    let t1;
    const tur = k % 4;
    if (tur === 0) { // iki uç tam örnek zamanında
      const p = Math.floor(r() * n);
      const q = Math.min(n - 1, p + Math.floor(r() * 3000));
      t0 = t[p]; t1 = t[q];
    } else if (tur === 1) { // örneklerin arasında
      t0 = t[0] + r() * (t[n - 1] - t[0]);
      t1 = t0 + r() * 5000;
    } else if (tur === 2) { // serinin dışına taşan
      t0 = t[0] - 1000 + r() * 2000;
      t1 = t[n - 1] - 1000 + r() * 2000;
    } else { // çok dar
      const p = Math.floor(r() * n);
      t0 = t[p] - 0.5; t1 = t[p] + 0.5;
    }
    const s = istatistik(t, y, t0, t1);
    const e = istatistikRef(t, y, t0, t1);
    const etiket = `[${t0}, ${t1}]`;
    assert.equal(s.adet, e.adet, `adet ${etiket}`);
    for (const alan of ['min', 'maks', 'tMin', 'tMaks', 'tepeTepe']) {
      assert.ok(ayni(s[alan], e[alan]), `${alan} ${etiket}: ${s[alan]} ≠ ${e[alan]}`);
    }
    yakin(s.ort, e.ort, e.rms, `ort ${etiket}`);
    yakin(s.rms, e.rms, e.rms, `rms ${etiket}`);
    if (e.adet > 0) sayi++;
  }
  assert.ok(sayi > 300, `dolu aralık az: ${sayi}`);
  const hepsi = istatistik(t, y);
  assert.equal(hepsi.maks, 1e3);
  assert.equal(hepsi.min, -1e3);
  assert.equal(hepsi.tMaks, t[123]);
  assert.equal(hepsi.tMin, t[19_000]);
  assert.deepEqual(hepsi, istatistik(t, y, -Infinity, Infinity));
});

test('istatistik: boş aralık, tek nokta, hepsi NaN, eşitlikte ilk görülen, örnek ortalaması', () => {
  const t = Float64Array.of(0, 10, 20, 30, 40, 1000);
  const y = Float64Array.of(3, 1, 5, 1, 5, NaN);
  const bos = { adet: 0, min: NaN, maks: NaN, ort: NaN, rms: NaN, tepeTepe: NaN, tMin: NaN, tMaks: NaN };
  assert.deepEqual(istatistik(t, y, 41, 999), bos); // örneklerin arası
  assert.deepEqual(istatistik(t, y, 30, 20), bos); // t1 < t0
  assert.deepEqual(istatistik(t, y, -5, -1), bos);
  assert.deepEqual(istatistik(t, y, 1000, 1000), bos); // yalnız NaN
  assert.deepEqual(istatistik(new Float64Array(0), new Float64Array(0)), bos);

  assert.deepEqual(istatistik(t, y, 20, 20),
    { adet: 1, min: 5, maks: 5, ort: 5, rms: 5, tepeTepe: 0, tMin: 20, tMaks: 20 });
  assert.deepEqual(istatistik(Float64Array.of(7), Float64Array.of(-2)),
    { adet: 1, min: -2, maks: -2, ort: -2, rms: 2, tepeTepe: 0, tMin: 7, tMaks: 7 });

  const s = istatistik(t, y); // iki uç dahil, NaN atlanır
  assert.equal(s.adet, 5);
  assert.equal(s.tMin, 10, 'min (1) ilk kez t=10\'da');
  assert.equal(s.tMaks, 20, 'maks (5) ilk kez t=20\'de');
  assert.equal(s.tepeTepe, 4);
  assert.equal(s.ort, 3);
  assert.equal(s.rms, Math.sqrt((9 + 1 + 25 + 1 + 25) / 5));
  assert.equal(istatistik(t, y, 10, 30).adet, 3, 't0 ve t1 dahil');

  // ort ÖRNEK ortalamasıdır, zaman ağırlıklı değil (belgelenen karar).
  assert.equal(istatistik(Float64Array.of(0, 1, 1000), Float64Array.of(0, 0, 9)).ort, 3);

  assert.throws(() => istatistik(t, new Float64Array(2)), RangeError);
  assert.throws(() => istatistik(t, y, NaN, 10), RangeError);
});

test('istatistik: 1 M örnekte büyük ofset — telafili toplam sapmaz (düz toplam ~1e-5 sapardı)', () => {
  const n = 1_000_000;
  const t = new Float64Array(n).map((_, j) => j);
  const y = new Float64Array(n).map((_, j) => 1e6 + 0.1 * (j % 3)); // 1e6, 1e6+0.1, 1e6+0.2 …
  const s = istatistik(t, y);
  // Analitik: sapma d ∈ {0, 0.1, 0.2}, adetler 333 334 / 333 333 / 333 333.
  const ortD = (0.1 * 333_333 + 0.2 * 333_333) / n;
  const varD = (0.01 * 333_333 + 0.04 * 333_333) / n - ortD * ortD;
  const ort = 1e6 + ortD;
  const rms = Math.sqrt(ort * ort + varD);
  assert.ok(Math.abs(s.ort - ort) <= 1e-9, `ort ${s.ort} ≠ ${ort}`);
  assert.ok(Math.abs(s.rms - rms) <= 1e-8, `rms ${s.rms} ≠ ${rms}`);
  assert.equal(s.tepeTepe, y[2] - y[0]);
});

// ── enerji ─────────────────────────────────────────────────────────────────

test('enerji: sabit 2 V × 0.5 A × 3600 s = 1 Wh, 500 mAh (tam)', () => {
  // Tamsayı ms ızgaraları: sonuç TAM.
  for (const adim of [1000, 10]) {
    const n = 3_600_000 / adim + 1;
    const t = new Float64Array(n).map((_, j) => j * adim);
    const v = new Float64Array(n).fill(2);
    const i = new Float64Array(n).fill(0.5);
    const e = enerji(t, v, i);
    assert.equal(e.wh, 1, `adım ${adim} ms`);
    assert.equal(e.mah, 500, `adım ${adim} ms`);
    assert.equal(e.sureS, 3600, `adım ${adim} ms`);
    assert.deepEqual(enerji(t, v, i, 0, 3_600_000, { boslukMs: adim }), e, 'dt = boslukMs boşluk değil');
  }
  // Rastgele (tamsayı olmayan) zamanlar, uçlar tam: 1e-12 bağıl.
  const r = rastgele(3);
  const n = 50_001;
  const t = new Float64Array(n);
  for (let j = 1; j < n - 1; j++) t[j] = r() * 3_600_000;
  t[0] = 0;
  t[n - 1] = 3_600_000;
  t.sort();
  const e = enerji(t, new Float64Array(n).fill(2), new Float64Array(n).fill(0.5));
  yakin(e.wh, 1, 1, 'Wh');
  yakin(e.mah, 500, 500, 'mAh');
  yakin(e.sureS, 3600, 3600, 'sureS');
  assert.equal(MS_SAAT, 3_600_000);
  assert.equal(AMS_MAH, 3_600);
});

test('enerji: boşluğun üstünden integral YOK (D4)', () => {
  // 0…3600 s ve 7200…10800 s, 1 s adım; arada 3600 s boşluk.
  const t = [];
  for (let s = 0; s <= 3600; s++) t.push(s * 1000);
  for (let s = 7200; s <= 10800; s++) t.push(s * 1000);
  const tt = Float64Array.from(t);
  const v = new Float64Array(tt.length).fill(2);
  const i = new Float64Array(tt.length).fill(0.5);
  assert.deepEqual(enerji(tt, v, i, -Infinity, Infinity, { boslukMs: 5000 }), { wh: 2, mah: 1000, sureS: 7200 });
  assert.deepEqual(enerji(tt, v, i, -Infinity, Infinity, { boslukMs: 3_599_999.5 }),
    { wh: 2, mah: 1000, sureS: 7200 });
  // Testin duyarlılığı: boşluk sayılmazsa (ya da tam sınırda) 3 Wh çıkar.
  assert.deepEqual(enerji(tt, v, i), { wh: 3, mah: 1500, sureS: 10800 });
  assert.deepEqual(enerji(tt, v, i, -Infinity, Infinity, { boslukMs: 3_600_000 }),
    { wh: 3, mah: 1500, sureS: 10800 }, 'dt = boslukMs boşluk değil');
  // Yalnız boşluğun iki yanındaki örnekler: integral 0.
  assert.deepEqual(enerji(tt, v, i, 3_600_000, 7_200_000, { boslukMs: 5000 }), { wh: 0, mah: 0, sureS: 0 });
});

test('enerji: rastgele seri, aralık ve boşluk eşiğinde kaba kuvvetle aynı', () => {
  const { t, v, i, r } = seri(20_000, 1234);
  const n = t.length;
  let sayi = 0;
  for (let k = 0; k < 300; k++) {
    const p = Math.floor(r() * n);
    const q = Math.min(n - 1, p + Math.floor(r() * 8000));
    const t0 = k % 3 === 0 ? t[p] : t[p] - 0.5;
    const t1 = k % 3 === 1 ? t[q] : t[q] + 0.25;
    const bosluk = [undefined, 2.5, 50, 5000][k % 4];
    const e = enerji(t, v, i, t0, t1, { boslukMs: bosluk });
    const b = enerjiRef(t, v, i, t0, t1, bosluk ?? Infinity);
    const etiket = `[${t0}, ${t1}] bosluk=${bosluk}`;
    yakin(e.wh, b.wh, b.olcekWh, `Wh ${etiket}`);
    yakin(e.mah, b.mah, b.olcekMah, `mAh ${etiket}`);
    yakin(e.sureS, b.sureS, b.sureS, `sureS ${etiket}`);
    if (b.sureS > 0) sayi++;
  }
  assert.ok(sayi > 250, `dolu aralık az: ${sayi}`);
});

test('enerji: NaN örnek atlanır, komşular birleşir; boş/tek nokta; geçersiz girdi', () => {
  const t = Float64Array.of(0, 1000, 2000, 3000);
  const v = Float64Array.of(1, NaN, 1, 1);
  const i = Float64Array.of(1, 1, 1, NaN);
  // Geçerli örnekler 0 ve 2000 ms: 1 W × 2000 ms.
  assert.deepEqual(enerji(t, v, i), { wh: 2000 / MS_SAAT, mah: 2000 / AMS_MAH, sureS: 2 });
  // Atlanan örnek yüzünden oluşan 2000 ms aralık da boşluk denetiminden geçer.
  assert.deepEqual(enerji(t, v, i, -Infinity, Infinity, { boslukMs: 1500 }), { wh: 0, mah: 0, sureS: 0 });
  const sifir = { wh: 0, mah: 0, sureS: 0 };
  assert.deepEqual(enerji(t, v, i, 10, 20), sifir);
  assert.deepEqual(enerji(t, v, i, 0, 0), sifir);
  assert.deepEqual(enerji(new Float64Array(0), new Float64Array(0), new Float64Array(0)), sifir);
  // Şarj (eksi akım) eksi Wh/mAh verir.
  const ts = Float64Array.of(0, 3_600_000);
  assert.deepEqual(enerji(ts, Float64Array.of(4, 4), Float64Array.of(-1, -1)), { wh: -4, mah: -1000, sureS: 3600 });

  assert.throws(() => enerji(t, v, new Float64Array(2)), RangeError);
  assert.throws(() => enerji(t, new Float64Array(2), i), RangeError);
  assert.throws(() => enerji(t, v, i, 0, 1, { boslukMs: -1 }), RangeError);
  assert.throws(() => enerji(t, v, i, NaN, 1), RangeError);
});

// ── S9: zamanı sonlu olmayan örnek EKSİK örnektir (aralığı kesmez) ────────────

/** Başvuru: zamanı sonlu olmayan örnekleri diziden ÇIKAR, sonra düz başvuruyu çağır. */
function sonluSuz(t, ...diziler) {
  const k = [];
  for (let j = 0; j < t.length; j++) if (Number.isFinite(t[j])) k.push(j);
  return [Float64Array.from(k, (j) => t[j]), ...diziler.map((d) => Float64Array.from(k, (j) => d[j]))];
}

test('S9: [0, NaN, 2] — NaN zamanlı örnek atlanır, aralık KESİLMEZ (istatistik + enerji)', () => {
  const t = Float64Array.of(0, NaN, 2);
  const y = Float64Array.of(1, 100, 3);
  const iki = { adet: 2, min: 1, maks: 3, ort: 2, rms: Math.sqrt(5), tepeTepe: 2, tMin: 0, tMaks: 2 };
  assert.deepEqual(istatistik(t, y), iki);
  assert.deepEqual(istatistik(t, y, 0, 2), iki);
  assert.deepEqual(istatistik(t, y, -Infinity, Infinity), iki);
  assert.equal(istatistik(t, y, 1, 2).adet, 1);
  assert.equal(istatistik(t, y, 0, 1).adet, 1);
  // delik başta / sonda / ±∞ / art arda: hepsi eksik örnek
  for (const [tt, yy] of [
    [[NaN, 0, 2], [100, 1, 3]], [[0, 2, NaN], [1, 3, 100]], [[-Infinity, 0, NaN, NaN, 2, Infinity], [100, 1, 100, 100, 3, 100]],
    [[0, Infinity, 2], [1, 100, 3]], [[0, -Infinity, 2], [1, 100, 3]], [[NaN, NaN, 0, NaN, 2, NaN, NaN], [9, 9, 1, 9, 3, 9, 9]],
  ]) {
    assert.deepEqual(istatistik(Float64Array.from(tt), Float64Array.from(yy)), iki, String(tt));
  }
  assert.equal(istatistik(Float64Array.of(NaN, Infinity), Float64Array.of(1, 2)).adet, 0);
  // enerji: 0 ve 2000 ms birleşir (1 W × 2000 ms); birleşen parça boşluk denetiminden geçer
  const te = Float64Array.of(0, NaN, 2000);
  const bir = new Float64Array(3).fill(1);
  assert.deepEqual(enerji(te, bir, bir), { wh: 2000 / MS_SAAT, mah: 2000 / AMS_MAH, sureS: 2 });
  assert.deepEqual(enerji(Float64Array.of(0, Infinity, 2000), bir, bir), { wh: 2000 / MS_SAAT, mah: 2000 / AMS_MAH, sureS: 2 });
  assert.deepEqual(enerji(te, bir, bir, -Infinity, Infinity, { boslukMs: 1500 }), { wh: 0, mah: 0, sureS: 0 });
  assert.deepEqual(enerji(te, bir, bir, 0, 2000), { wh: 2000 / MS_SAAT, mah: 2000 / AMS_MAH, sureS: 2 });
});

test('S9: rastgele delikli zaman (NaN / ±∞ dizileri) — sonlu olmayanlar ÇIKARILMIŞ seriyle aynı', () => {
  const { t, v, i, r } = seri(20_000, 99);
  for (let j = 0; j < t.length;) {        // ~%3 delik, 1…40'lık diziler
    if (r() < 0.003) {
      const n = 1 + Math.floor(r() * 40);
      for (let k = 0; k < n && j < t.length; k++, j++) t[j] = [NaN, Infinity, -Infinity][Math.floor(r() * 3)];
    } else j++;
  }
  const [tf, vf, iff] = sonluSuz(t, v, i);
  assert.ok(tf.length < t.length - 300, `delik az: ${t.length - tf.length}`);
  const n = tf.length;
  let dolu = 0;
  for (let k = 0; k < 300; k++) {
    const p = Math.floor(r() * n);
    const q = Math.min(n - 1, p + Math.floor(r() * 4000));
    const t0 = k % 3 === 0 ? tf[p] : tf[p] - 0.5;
    const t1 = k % 3 === 1 ? tf[q] : tf[q] + 0.25;
    const etiket = `[${t0}, ${t1}]`;
    const s = istatistik(t, v, t0, t1);
    const e = istatistikRef(tf, vf, t0, t1);
    assert.equal(s.adet, e.adet, `adet ${etiket}`);
    for (const alan of ['min', 'maks', 'tMin', 'tMaks', 'tepeTepe']) {
      assert.ok(ayni(s[alan], e[alan]), `${alan} ${etiket}: ${s[alan]} ≠ ${e[alan]}`);
    }
    yakin(s.ort, e.ort, e.rms, `ort ${etiket}`);
    const bosluk = [undefined, 2.5, 50][k % 3];
    const en = enerji(t, v, i, t0, t1, { boslukMs: bosluk });
    const b = enerjiRef(tf, vf, iff, t0, t1, bosluk ?? Infinity);
    yakin(en.wh, b.wh, b.olcekWh, `Wh ${etiket}`);
    yakin(en.mah, b.mah, b.olcekMah, `mAh ${etiket}`);
    yakin(en.sureS, b.sureS, b.sureS, `sureS ${etiket}`);
    if (e.adet > 0) dolu++;
  }
  assert.ok(dolu > 250, `dolu aralık az: ${dolu}`);
  assert.equal(istatistik(t, v).adet, istatistikRef(tf, vf, -Infinity, Infinity).adet);
});
