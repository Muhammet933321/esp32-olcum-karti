/**
 * ortak/src/istatistik.js — aralık istatistiği ve enerji (alt proje 2, dilim 2D).
 *
 * Bağlayıcı karar D4 (tasarim/2026-10-02-alt-proje-2-ortak.md): istatistik ve
 * enerji HER ZAMAN HAM veriden; özet piramidi (ozet.js) yalnız ekran resmidir.
 * Bağımlılık yok, Node API'si yok.
 *
 * ARALIK: [t0, t1] iki ucu da dahil; verilmezse bütün seri. Aralık dışındaki
 * kısım tahmin edilmez (ilk örnekten önce / son örnekten sonra integral yok).
 * NaN = eksik örnek: atlanır.
 *
 * ZAMAN (S9): zamanı SONLU OLMAYAN (NaN, ±∞) örnek de EKSİK örnektir: değeri ne
 * olursa olsun atlanır, aralığı KESMEZ (eskiden ikili arama NaN'da dönüp
 * [0, NaN, 2]'yi 1 örneğe indiriyordu). Sonlu zamanlar azalmayan olmalı; delikler
 * (sonlu olmayan zamanlar) aralarında her yerde olabilir. Enerjide atlanan
 * örneğin iki komşusu birleşir (NaN değerli örnekle aynı kural).
 *
 * TOPLAMA: Neumaier (telafili) toplam — 30 günlük kayıtta (~1e9 örnek) bile
 * toplam hatası sabit kalır; düz toplamdaki n·ε birikimi olmaz.
 */

/** k ≥ m olan ilk SONLU zamanlı indis (yoksa hi). */
function sonluIlk(t, m, hi) {
  while (m < hi && !Number.isFinite(t[m])) m++;
  return m;
}

/** t[lo, hi) içinde SONLU t[i] ≥ x olan ilk sınır: önündeki her sonlu zaman < x,
 *  kendisinden sonraki her sonlu zaman ≥ x (ozet.js altSinir'in delik bilen eşi). */
function altSinir(t, x, lo = 0, hi = t.length) {
  while (lo < hi) {
    const m = (lo + hi) >>> 1;
    const k = sonluIlk(t, m, hi);
    if (k < hi && t[k] < x) lo = k + 1;
    else hi = m;
  }
  return lo;
}

/** t[lo, hi) içinde SONLU t[i] > x olan ilk sınır (delik bilen ustSinir). */
function ustSinir(t, x, lo = 0, hi = t.length) {
  while (lo < hi) {
    const m = (lo + hi) >>> 1;
    const k = sonluIlk(t, m, hi);
    if (k < hi && t[k] <= x) lo = k + 1;
    else hi = m;
  }
  return lo;
}

/** 1 saat = 3 600 000 ms. */
export const MS_SAAT = 3_600_000;

/** 1 mAh = 1e-3 A × 3 600 000 ms = 3 600 A·ms. */
export const AMS_MAH = 3_600;

/** Neumaier telafili toplam. */
class Toplam {
  constructor() {
    this.s = 0;
    this.d = 0;
  }

  ekle(x) {
    const s = this.s + x;
    if (Math.abs(this.s) >= Math.abs(x)) this.d += (this.s - s) + x;
    else this.d += (x - s) + this.s;
    this.s = s;
  }

  get deger() {
    return this.s + this.d;
  }
}

function aralikIndis(t, t0, t1, ad) {
  if (Number.isNaN(t0) || Number.isNaN(t1)) {
    throw new RangeError(`${ad}: t0 ve t1 sayı olmalı (${t0}, ${t1})`);
  }
  const a = altSinir(t, t0);
  return [a, ustSinir(t, t1, a)]; // t1 < t0 ise boş aralık
}

/**
 * [t0, t1] aralığındaki HAM örneklerin istatistiği (NaN değer ve sonlu olmayan zaman atlanır).
 *  - adet: zamanı sonlu, değeri NaN olmayan örnek sayısı
 *  - min, maks, tepeTepe = maks − min
 *  - tMin, tMaks: min'in / maks'ın İLK görüldüğü örneğin zamanı (ms)
 *  - ort: örnek ortalaması Σy/adet (zaman ağırlıklı DEĞİL — multimetre gibi)
 *  - rms: √(Σy²/adet)
 * Örnek yoksa adet 0, geri kalan her alan NaN.
 * @param {Float64Array} t  ms; sonlu olanlar azalmayan (NaN/±∞ = eksik örnek, S9)
 * @param {Float64Array} y
 */
export function istatistik(t, y, t0 = -Infinity, t1 = Infinity) {
  if (y.length !== t.length) {
    throw new RangeError(`istatistik: t (${t.length}) ve y (${y.length}) aynı uzunlukta olmalı`);
  }
  const [a, b] = aralikIndis(t, t0, t1, 'istatistik');
  let adet = 0;
  let enk = NaN;
  let enb = NaN;
  let tMin = NaN;
  let tMaks = NaN;
  const top = new Toplam();
  const kare = new Toplam();
  for (let i = a; i < b; i++) {
    if (!Number.isFinite(t[i])) continue; // S9: zamanı sonlu değil: eksik örnek
    const v = y[i];
    if (v !== v) continue; // NaN: eksik örnek
    adet++;
    if (adet === 1 || v < enk) { enk = v; tMin = t[i]; }
    if (adet === 1 || v > enb) { enb = v; tMaks = t[i]; }
    top.ekle(v);
    kare.ekle(v * v);
  }
  if (adet === 0) {
    return { adet: 0, min: NaN, maks: NaN, ort: NaN, rms: NaN, tepeTepe: NaN, tMin: NaN, tMaks: NaN };
  }
  return {
    adet,
    min: enk,
    maks: enb,
    ort: top.deger / adet,
    rms: Math.sqrt(kare.deger / adet),
    tepeTepe: enb - enk,
    tMin,
    tMaks,
  };
}

/**
 * [t0, t1] aralığında enerji ve yük (D4), yamuk kuralıyla HAM örneklerden:
 *   Wh  = ∫ V·I dt,   mAh = ∫ I dt,   sureS = integre edilen süre (s).
 * Örnek GEÇERLİ ⇔ v ve i ikisi de NaN değil VE zamanı sonlu (S9); geçersiz örnek atlanır ve
 * komşu iki geçerli örnek birleşir (aralarındaki süre yine boşluk denetiminden
 * geçer). Böylece Wh, mAh ve sureS hep AYNI zaman parçalarını kapsar.
 *
 * BOŞLUK (D1/D4): ardışık iki geçerli örnek arası dt > boslukMs ise o parça
 * İNTEGRE EDİLMEZ (boşluğun üstünden integral yok). dt = boslukMs boşluk
 * değildir. boslukMs verilmezse boşluk yok sayılır (Infinity).
 *
 * BİRİM ÇEVRİMİ (kesin): parçalar V·A·ms ve A·ms olarak toplanır, çevrim en
 * sonda TEK bölmeyle yapılır — Wh = Σ(W·ms) / 3 600 000, mAh = Σ(A·ms) / 3 600,
 * sureS = Σms / 1000. Tamsayı ms ızgarasında sabit güç için sonuç tam çıkar
 * (2 V × 0.5 A × 3600 s → tam 1 Wh, tam 500 mAh).
 *
 * @param {Float64Array} t  ms; sonlu olanlar azalmayan (NaN/±∞ = eksik örnek, S9)
 * @param {Float64Array} v  gerilim (V)
 * @param {Float64Array} i  akım (A); işaretli (şarjda eksi)
 * @returns {{wh: number, mah: number, sureS: number}}
 */
export function enerji(t, v, i, t0 = -Infinity, t1 = Infinity, { boslukMs } = {}) {
  if (v.length !== t.length || i.length !== t.length) {
    throw new RangeError(`enerji: t (${t.length}), v (${v.length}), i (${i.length}) aynı uzunlukta olmalı`);
  }
  let bosluk = Infinity;
  if (boslukMs !== undefined && boslukMs !== null) {
    if (typeof boslukMs !== 'number' || !(boslukMs >= 0)) {
      throw new RangeError(`enerji: boslukMs ≥ 0 sayı olmalı (${boslukMs})`);
    }
    bosluk = boslukMs;
  }
  const [a, b] = aralikIndis(t, t0, t1, 'enerji');
  const wms = new Toplam(); // W·ms
  const ams = new Toplam(); // A·ms
  const ms = new Toplam();
  let oncekiVar = false;
  let tOnce = 0;
  let pOnce = 0;
  let iOnce = 0;
  for (let j = a; j < b; j++) {
    const vj = v[j];
    const ij = i[j];
    if (vj !== vj || ij !== ij) continue; // eksik örnek
    const tj = t[j];
    if (!Number.isFinite(tj)) continue; // S9: zamanı sonlu değil: eksik örnek, komşular birleşir
    const pj = vj * ij;
    if (oncekiVar) {
      const dt = tj - tOnce;
      if (dt <= bosluk) {
        wms.ekle((pOnce + pj) * dt / 2);
        ams.ekle((iOnce + ij) * dt / 2);
        ms.ekle(dt);
      }
    }
    oncekiVar = true;
    tOnce = tj;
    pOnce = pj;
    iOnce = ij;
  }
  return {
    wh: wms.deger / MS_SAAT,
    mah: ams.deger / AMS_MAH,
    sureS: ms.deger / 1000,
  };
}
