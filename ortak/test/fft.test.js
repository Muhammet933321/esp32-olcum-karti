// B73 / 2E — ortak/src/fft.js: FFT == kaba kuvvet DFT (tanim), Parseval, genlik/frekans olcegi.
// Python vektoru yok: basvuru DFT'nin tanimi (burada O(N^2) ile hesaplanir).
import { test } from "node:test";
import assert from "node:assert/strict";
import { fft, spektrum, tepeFrekans, pencere, ikiKuvveti } from "../src/fft.js";

/** Belirlenimci [-1, 1) (LCG). */
function rastgele(tohum) {
  let x = tohum >>> 0;
  return () => {
    x = (Math.imul(1664525, x) + 1013904223) >>> 0;
    return x / 2147483648 - 1;
  };
}

/** Kaba kuvvet DFT, X[k] = sum x[i] e^(-2 pi j k i / N). Aci tamsayi indeksle (k*i mod N). */
function dft(re, im) {
  const n = re.length;
  const Xr = new Float64Array(n);
  const Xi = new Float64Array(n);
  for (let k = 0; k < n; k++) {
    let sr = 0;
    let si = 0;
    for (let i = 0; i < n; i++) {
      const a = (-2 * Math.PI * ((k * i) % n)) / n;
      const c = Math.cos(a);
      const s = Math.sin(a);
      sr += re[i] * c - im[i] * s;
      si += re[i] * s + im[i] * c;
    }
    Xr[k] = sr;
    Xi[k] = si;
  }
  return [Xr, Xi];
}

const ton = (n, hz, f0, A, dc = 0, faz = 0.3) =>
  Float64Array.from({ length: n }, (_, i) => dc + A * Math.cos((2 * Math.PI * f0 * i) / hz + faz));

// ── FFT cekirdegi ───────────────────────────────────────────────────────
test("FFT == kaba kuvvet DFT, karmasik rastgele girdi, N = 1 ... 1024 (bagil hata < 1e-9)", () => {
  const r = rastgele(12345);
  let enKotu = 0;
  for (let N = 1; N <= 1024; N *= 2) {
    const re = Float64Array.from({ length: N }, r);
    const im = Float64Array.from({ length: N }, r);
    const [Xr, Xi] = dft(re, im);
    fft(re, im);
    let olcek = 0;
    for (let k = 0; k < N; k++) olcek = Math.max(olcek, Math.hypot(Xr[k], Xi[k]));
    for (let k = 0; k < N; k++) {
      const h = Math.hypot(re[k] - Xr[k], im[k] - Xi[k]) / olcek;
      enKotu = Math.max(enKotu, h);
      assert.ok(h < 1e-9, `N=${N} k=${k}: ${re[k]},${im[k]} != ${Xr[k]},${Xi[k]}`);
    }
  }
  assert.ok(enKotu < 1e-12, `en kotu bagil hata ${enKotu}`); // gercekte ~1e-15
});

test("FFT gercek girdi: X[N-k] = X[k]* (yon ve isaret)", () => {
  const r = rastgele(7);
  const N = 64;
  const re = Float64Array.from({ length: N }, r);
  const im = new Float64Array(N);
  const x1 = re[1];
  fft(re, im);
  for (let k = 1; k < N; k++) {
    assert.ok(Math.abs(re[N - k] - re[k]) < 1e-12 && Math.abs(im[N - k] + im[k]) < 1e-12, `k=${k}`);
  }
  // ileri yon: tek x[1] = 1 darbesi X[1] = e^(-2 pi j / N) verir (im EKSI)
  const d = new Float64Array(N);
  d[1] = 1;
  const z = new Float64Array(N);
  fft(d, z);
  assert.ok(Math.abs(d[1] - Math.cos((2 * Math.PI) / N)) < 1e-15);
  assert.ok(Math.abs(z[1] + Math.sin((2 * Math.PI) / N)) < 1e-15, "ileri FFT'de im[1] = -sin(2pi/N)");
  assert.ok(Number.isFinite(x1));
});

test("Parseval: sum |x|^2 = sum |X|^2 / N (N = 2 ... 4096)", () => {
  const r = rastgele(99);
  for (let N = 2; N <= 4096; N *= 2) {
    const re = Float64Array.from({ length: N }, r);
    const im = Float64Array.from({ length: N }, r);
    let ex = 0;
    for (let i = 0; i < N; i++) ex += re[i] * re[i] + im[i] * im[i];
    fft(re, im);
    let eX = 0;
    for (let k = 0; k < N; k++) eX += re[k] * re[k] + im[k] * im[k];
    assert.ok(Math.abs(eX / N - ex) / ex < 1e-12, `N=${N}: ${eX / N} != ${ex}`);
  }
});

test("FFT uc durumlar: N 0 ve 1 degismez; 2'nin kuvveti degilse / uzunluk farkliysa RangeError", () => {
  const a = new Float64Array(0);
  fft(a, new Float64Array(0));
  const b = Float64Array.of(3.5);
  const bi = Float64Array.of(-1);
  fft(b, bi);
  assert.deepEqual([b[0], bi[0]], [3.5, -1]);
  const c = Float64Array.of(1, 2);
  const ci = new Float64Array(2);
  fft(c, ci);
  assert.deepEqual([...c, ...ci], [3, -1, 0, 0]);
  for (const n of [3, 6, 12, 1000]) {
    assert.throws(() => fft(new Float64Array(n), new Float64Array(n)), RangeError);
  }
  assert.throws(() => fft(new Float64Array(4), new Float64Array(8)), RangeError);
  assert.deepEqual([0, 1, 2, 3, 5, 1000, 1024, 1025].map(ikiKuvveti), [1, 1, 2, 4, 8, 1024, 1024, 2048]);
});

// ── spektrum: genlik olcegi ───────────────────────────────────────────────
test("kutuya dusen ton: genlik = A (her iki pencere, tutarli kazanc duzeltmesi), dc = ofset", () => {
  const n = 1024;
  const hz = 2048;
  for (const pen of ["hann", "dikdortgen"]) {
    const sp = spektrum(ton(n, hz, 100, 1.7, -0.4), hz, { pencere: pen });
    assert.equal(sp.nfft, 1024);
    assert.equal(sp.f.length, 513);
    assert.equal(sp.df, 2);
    assert.equal(sp.f[50], 100);
    assert.ok(Math.abs(sp.genlik[50] - 1.7) < 1e-12, `${pen}: ${sp.genlik[50]}`);
    assert.ok(Math.abs(sp.dc + 0.4) < 1e-12, `${pen}: dc ${sp.dc}`);
    assert.ok(Math.abs(sp.genlik[0] - 0.4) < 1e-12);
    const t = tepeFrekans(sp);
    assert.equal(t.kutu, 50);
    assert.ok(Math.abs(t.f - 100) < 1e-9 && Math.abs(t.genlik - 1.7) < 1e-9, JSON.stringify(t));
  }
});

test("pencere: periyodik Hann, tutarli kazanc tam 0.5; bilinmeyen ad RangeError", () => {
  const w = pencere("hann", 8);
  assert.equal(w[0], 0);
  assert.ok(Math.abs(w[4] - 1) < 1e-15);
  assert.ok(Math.abs(w[1] - w[7]) < 1e-15, "periyodik: w[i] = w[n-i]");
  assert.ok(Math.abs(w.reduce((a, b) => a + b, 0) - 4) < 1e-12);
  assert.deepEqual([...pencere("dikdortgen", 3)], [1, 1, 1]);
  assert.deepEqual([...pencere("hann", 1)], [1], "tek ornekte Hann 0'a cokmesin");
  assert.throws(() => pencere("hamming", 8), RangeError);
  assert.throws(() => pencere("hamming", 1), RangeError);
  assert.throws(() => spektrum([1, 2], 10, { pencere: "flat" }), RangeError);
  assert.throws(() => spektrum([], 10, { pencere: "flat" }), RangeError);
});

test("kutular arasi ton (Hann): tepe kutusu genligi scalloping sinirinda, ara degerli f <= 0.02 kutu", () => {
  const n = 1024;
  const hz = 1000;
  const df = hz / n;
  let enKotuF = 0;
  let enKotuA = 0;
  let enKucukKutu = Infinity;
  for (let s = 0; s <= 40; s++) {
    const f0 = (123 + s / 40) * df;
    const sp = spektrum(ton(n, hz, f0, 2, 0.8), hz);
    const t = tepeFrekans(sp);
    enKotuF = Math.max(enKotuF, Math.abs(t.f - f0) / df);
    enKotuA = Math.max(enKotuA, Math.abs(t.genlik - 2) / 2);
    enKucukKutu = Math.min(enKucukKutu, sp.genlik[t.kutu] / 2);
    assert.ok(sp.genlik[t.kutu] <= 2 * (1 + 1e-9), "tepe kutusu genligi A'yi asmaz");
  }
  // Hann scalloping: yarim kutuda 8/(3 pi) = 0.8488 (-1.42 dB)
  assert.ok(enKucukKutu >= 0.8488 - 1e-3 && enKucukKutu < 0.86, `scalloping ${enKucukKutu}`);
  assert.ok(enKotuF <= 0.02, `frekans hatasi ${enKotuF} kutu`);
  assert.ok(enKotuA <= 0.04, `ara degerli genlik hatasi ${enKotuA}`);
});

test("kutular arasi ton (dikdortgen): scalloping 2/pi, ara degerli f <= 0.2 kutu", () => {
  const n = 1024;
  const hz = 1000;
  const df = hz / n;
  let enKotuF = 0;
  let enKucukKutu = Infinity;
  for (let s = 0; s <= 40; s++) {
    const f0 = (77 + s / 40) * df;
    const sp = spektrum(ton(n, hz, f0, 1), hz, { pencere: "dikdortgen" });
    const t = tepeFrekans(sp);
    enKotuF = Math.max(enKotuF, Math.abs(t.f - f0) / df);
    enKucukKutu = Math.min(enKucukKutu, sp.genlik[t.kutu]);
  }
  assert.ok(enKucukKutu >= 2 / Math.PI - 3e-3 && enKucukKutu < 0.66, `scalloping ${enKucukKutu}`);
  assert.ok(enKotuF <= 0.2, `frekans hatasi ${enKotuF} kutu`);
});

test("sifir doldurma: n = 1000 -> nfft 1024, genlik ve frekans yine dogru; kapaliyken RangeError", () => {
  const n = 1000;
  const hz = 1000;
  const sp = spektrum(ton(n, hz, 50, 3, 1), hz);
  assert.equal(sp.n, 1000);
  assert.equal(sp.nfft, 1024);
  assert.equal(sp.genlik.length, 513);
  const t = tepeFrekans(sp);
  assert.ok(Math.abs(t.f - 50) < 0.02 * sp.df, `${t.f}`);
  assert.ok(Math.abs(t.genlik - 3) / 3 < 0.04, `${t.genlik}`);
  assert.ok(Math.abs(sp.dc - 1) < 1e-3, `dc ${sp.dc}`); // 50 tam cevrim: agirlikli ortalama = 1
  assert.throws(() => spektrum(new Float64Array(1000), hz, { sifirDoldur: false }), RangeError);
  assert.equal(spektrum(new Float64Array(1024), hz, { sifirDoldur: false }).nfft, 1024);
});

test("DC: sabit sinyal -> genlik[0] = |c|, dc isaretli, baska kutu 0; tepe yok", () => {
  for (const pen of ["hann", "dikdortgen"]) {
    for (const n of [256, 300]) {
      const sp = spektrum(new Float64Array(n).fill(-2.5), 100, { pencere: pen });
      assert.equal(sp.dc, -2.5, `${pen} ${n}: dc ${sp.dc}`);
      assert.equal(sp.genlik[0], 2.5);
      for (let k = 1; k < sp.genlik.length; k++) assert.ok(sp.genlik[k] < 1e-12, `${pen} ${n} k=${k}`);
      assert.equal(tepeFrekans(sp), null, `${pen} ${n}: saf DC'de tepe yok`);
    }
  }
});

test("dcCikar: false = ders kitabi pencereli spektrum (periyodik Hann saf DC'yi 1. kutuya DC KADAR sizdirir)", () => {
  const sp = spektrum(new Float64Array(256).fill(-2.5), 100, { dcCikar: false });
  assert.ok(Math.abs(sp.dc + 2.5) < 1e-12 && Math.abs(sp.genlik[0] - 2.5) < 1e-12);
  assert.ok(Math.abs(sp.genlik[1] - 2.5) < 1e-12, `genlik[1] ${sp.genlik[1]}`);
  for (let k = 2; k < sp.genlik.length; k++) assert.ok(sp.genlik[k] < 1e-12);
  assert.equal(tepeFrekans(sp).kutu, 1, "belgelenen tuzak: sizinti tepe sanilir");
  // dikdortgen, n = N: DC ortogonal -> dcCikar k >= 1 kutularini DEGISTIRMEZ
  const y = ton(512, 512, 37, 1.2, 5);
  const a = spektrum(y, 512, { pencere: "dikdortgen" });
  const b = spektrum(y, 512, { pencere: "dikdortgen", dcCikar: false });
  for (let k = 1; k < a.genlik.length; k++) assert.ok(Math.abs(a.genlik[k] - b.genlik[k]) < 1e-12, `k=${k}`);
  assert.ok(Math.abs(a.dc - b.dc) < 1e-12);
});

test("buyuk DC + kucuk ton (12 V rayda dalgalanma gibi; Hann, dolgulu): tepe ton, DC sizintisi degil", () => {
  const hz = 10_000;
  const y = ton(3000, hz, 1234.5, 0.5, 40);
  const t = tepeFrekans(spektrum(y, hz));
  assert.ok(Math.abs(t.f - 1234.5) < 0.02 * (hz / 4096), `${t.f}`);
  assert.ok(Math.abs(t.genlik - 0.5) / 0.5 < 0.04, `${t.genlik}`);
  // DC cikarmadan: DC'nin -31 dB yan lobu (40 x 0.027 x 2 > 0.5) tepe olur — varsayilanin sebebi
  const ham = tepeFrekans(spektrum(y, hz, { dcCikar: false }));
  assert.ok(ham.f < 50, `dcCikar:false tepesi ${ham.f} Hz`);
});

test("Nyquist: (-1)^i genlik A, katsayi 1 (iki kat DEGIL); son kutuda ara degerleme yok", () => {
  const n = 64;
  const y = Float64Array.from({ length: n }, (_, i) => 0.75 * (i % 2 ? -1 : 1));
  const sp = spektrum(y, 1000, { pencere: "dikdortgen" });
  const m = sp.genlik.length;
  assert.equal(m, 33);
  assert.equal(sp.f[m - 1], 500);
  assert.ok(Math.abs(sp.genlik[m - 1] - 0.75) < 1e-12, `${sp.genlik[m - 1]}`);
  const t = tepeFrekans(sp);
  assert.equal(t.kutu, m - 1);
  assert.equal(t.f, 500);
  const sh = spektrum(y, 1000); // Hann: Nyquist tonu yine A (tutarli kazanc)
  assert.ok(Math.abs(sh.genlik[m - 1] - 0.75) < 1e-12, `${sh.genlik[m - 1]}`);
});

test("uzunluk 0 / 1 / 2 ve gecersiz hz", () => {
  const s0 = spektrum([], 100);
  assert.equal(s0.f.length, 0);
  assert.equal(s0.genlik.length, 0);
  assert.ok(Number.isNaN(s0.dc));
  assert.equal(tepeFrekans(s0), null);
  for (const pen of ["hann", "dikdortgen"]) {
    const s1 = spektrum([4.25], 100, { pencere: pen });
    assert.deepEqual([s1.nfft, s1.f.length, s1.f[0], s1.genlik[0], s1.dc], [1, 1, 0, 4.25, 4.25]);
    assert.equal(tepeFrekans(s1), null);
  }
  const s2 = spektrum([3, 1], 10, { pencere: "dikdortgen" });
  assert.deepEqual([...s2.f], [0, 5]);
  assert.deepEqual([...s2.genlik], [2, 1]);
  assert.equal(s2.dc, 2);
  assert.equal(tepeFrekans(s2).f, 5);
  const s2h = spektrum([3, 1], 10); // periyodik Hann n=2: w = [0, 1]; ortalama 2 cikar -> [0, -1]
  assert.deepEqual([...s2h.genlik], [2, 1]);
  assert.deepEqual([...spektrum([3, 1], 10, { dcCikar: false }).genlik], [1, 1]);
  for (const hz of [0, -5, NaN, Infinity, undefined]) assert.throws(() => spektrum([1, 2, 3, 4], hz), RangeError);
});

test("NaN iceren girdi atmaz; tepe yok", () => {
  const y = ton(128, 100, 10, 1);
  y[5] = NaN;
  const sp = spektrum(y, 100);
  assert.ok(Number.isNaN(sp.dc));
  assert.equal(tepeFrekans(sp), null);
});

test("Float64Array, Float32Array ve duz dizi ayni spektrumu verir", () => {
  const y = Array.from({ length: 200 }, (_, i) => Math.fround(Math.sin(i / 3)));
  const a = spektrum(y, 50);
  const b = spektrum(Float32Array.from(y), 50);
  const c = spektrum(Float64Array.from(y), 50);
  assert.deepEqual(a.genlik, b.genlik);
  assert.deepEqual(a.genlik, c.genlik);
});
