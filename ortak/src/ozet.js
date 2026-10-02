/**
 * ortak/src/ozet.js — min/maks özet piramidi ve pencere sorgusu (alt proje 2, dilim 2D).
 *
 * Bağlayıcı kararlar: tasarim/2026-10-02-alt-proje-2-ortak.md D1–D3, D5;
 * üst tasarım 2026-09-29-yazilim-sistemi.md §9 "Çizim kuralı" ve Ö1.
 * Özetlenen YALNIZ ekran resmidir; istatistik / enerji / imleç her zaman ham
 * veriden hesaplanır (istatistik.js).
 *
 * Bağımlılık yok, Node API'si yok: tarayıcı, Node ve Capacitor aynı dosyayı yükler.
 *
 * ── SERİ (D1) ─────────────────────────────────────────────────────────────
 * `t` Float64Array (ms, azalmayan; eşit zaman damgası olabilir), `y` Float64Array,
 * aynı uzunlukta. `y`'deki NaN "eksik örnek"tir: özetlerde atlanır.
 * BOŞLUK: ardışık iki örnek arası `> boslukMs` (çağıran verir — kayıtta DEVAM
 * sınırı ya da hız × 2.5). Tam eşitlik boşluk DEĞİLDİR.
 *
 * ── PİRAMİT (D2) ──────────────────────────────────────────────────────────
 * Düzey 0 = ham `y`. Düzey k ≥ 1: B^k ardışık ham örneklik TAM blokların NaN'sız
 * min'i ve maks'ı (Float64Array; blok tamamen NaN ise ikisi de NaN). Sondaki
 * eksik blok saklanmaz — sorgu o örnekleri alt düzeyden tek tek okur. Blokların
 * ilk/son zamanı `t`'den türer (`blokZamani`), saklanmaz. Ek bellek
 * 2·n/(B−1) sayı ≈ ham (t + y) belleğinin %14'ü (B = 8). Kurulum O(n).
 *
 * ── PENCERE (D3) ──────────────────────────────────────────────────────────
 * `[t0, t1]` aralığındaki ham örnek sayısı ≤ 2·W ise HAM kip: çizici ham
 * noktaları çizer (aralığın iki yanındaki birer komşu dahil, çizgi kenara
 * ulaşsın diye). Değilse ÖZET kip: W piksel sütunu, sütun başına [min, maks].
 *
 * SÜTUN SÖZLEŞMESİ: sınırlar s_c = t0 + (t1 − t0)·c / W (c = 0…W; t1'i aşan
 * sınır t1'e kırpılır, s_W = t1). Örnek i, s_c ≤ t[i] < s_{c+1} ise c
 * sütunundadır; son sütun t1'i de içerir. Sütunun [min, maks]'ı o sütundaki
 * NaN'sız ham örneklerin TAM min'i ve maks'ıdır: sütunun indis aralığı piramitte
 * hizalı tam bloklara, kenarlarda alt düzey öğelerine bölünür — sütun sınırını
 * aşan hiçbir blok kullanılmaz. Örneği olmayan (ya da hepsi NaN) sütun: NaN, NaN
 * (D3'ün "null"u; Float64Array null tutamaz, çizici NaN'ı kesik sayar).
 *
 * Ö1 GÜVENCESİ (kesin, uygulanan):
 *   (a) [t0, t1] içindeki NaN'sız HER ham örnek tam bir sütuna düşer ve o
 *       sütunda min ≤ y ≤ maks sağlanır — zaman hatası 0 sütun.
 *   (b) Tek örneklik bir sıçrama, sütununda kendisinden daha uç bir değer yoksa
 *       o sütunun maks'ı (ya da min'i) OLUR; yani her yakınlaştırmada görünür.
 *   (c) Uydurma uç yok: her sütun ucu, o sütunun zaman penceresindeki gerçek bir
 *       örneğin değeridir.
 *   "Gerçek sütun" ⌊(t − t0)/(t1 − t0)·W⌋ ile ayrıca hesaplanırsa kayan nokta
 *   yuvarlaması sınırda en çok 1 sütun fark yaratabilir; D3'ün "zaman hatası
 *   ≤ 1 sütun" ölçütü bunu kapsar (test bu ±1 ölçütüyle de sınar).
 *
 * BOŞLUK ÇİZİMİ (D1): ham kipte `bolumler` (boslukBolumleri), özet kipte boş
 * sütunlar NaN ve `kesik[c] = 1` — c sütununun ilk örneği ile bir önceki örnek
 * arasında boşluk var, çizgi önceki sütundan c'ye BAĞLANMAZ. Bir sütunun İÇİNDE
 * kalan boşluk piksel altıdır; sütunun dikey çubuğu iki yanı da gerçekten içerir.
 *
 * Karmaşıklık: özet kipte sütun başına bir ikili arama + O(B · düzey) öğe.
 */

/** Varsayılan blok çarpanı (D2: B = 8). */
export const BLOK = 8;

/** t[lo, hi) içinde t[i] ≥ x olan ilk indis; yoksa hi. `t` azalmayan olmalı. */
export function altSinir(t, x, lo = 0, hi = t.length) {
  while (lo < hi) {
    const m = (lo + hi) >>> 1;
    if (t[m] < x) lo = m + 1;
    else hi = m;
  }
  return lo;
}

/** t[lo, hi) içinde t[i] > x olan ilk indis; yoksa hi. `t` azalmayan olmalı. */
export function ustSinir(t, x, lo = 0, hi = t.length) {
  while (lo < hi) {
    const m = (lo + hi) >>> 1;
    if (t[m] <= x) lo = m + 1;
    else hi = m;
  }
  return lo;
}

/** boslukMs doğrulaması: verilmezse Infinity (boşluk yok). */
function boslukDenetle(boslukMs) {
  if (boslukMs === undefined || boslukMs === null) return Infinity;
  if (typeof boslukMs !== 'number' || !(boslukMs >= 0)) {
    throw new RangeError(`boslukMs ≥ 0 sayı olmalı (${boslukMs})`);
  }
  return boslukMs;
}

/**
 * Özet piramidini kurar (D2).
 * @param {Float64Array} t  zaman, ms, azalmayan, sonlu
 * @param {Float64Array} y  değer; NaN = eksik örnek
 * @param {{blok?: number}} [secenek]  B (≥ 2 tamsayı), varsayılan 8
 * @returns {{t, y, n: number, blok: number, min: Array<Float64Array|null>, maks: Array<Float64Array|null>}}
 *   `min[k]`, `maks[k]` düzey k ≥ 1 (indis 0 = ham, null).
 */
export function ozetKur(t, y, { blok = BLOK } = {}) {
  const n = t.length;
  if (y.length !== n) {
    throw new RangeError(`ozetKur: t (${n}) ve y (${y.length}) aynı uzunlukta olmalı`);
  }
  if (!Number.isInteger(blok) || blok < 2) {
    throw new RangeError(`ozetKur: blok ≥ 2 tamsayı olmalı (${blok})`);
  }
  if (n > 0 && !(Number.isFinite(t[0]) && Number.isFinite(t[n - 1]))) {
    throw new RangeError('ozetKur: t sonlu sayılardan oluşmalı');
  }
  for (let i = 1; i < n; i++) {
    if (!(t[i] >= t[i - 1])) throw new RangeError(`ozetKur: t azalmayan olmalı (indis ${i})`);
  }

  const min = [null];
  const maks = [null];

  // Düzey 1: ham örneklerin B'li tam blokları.
  let uzunluk = Math.floor(n / blok);
  if (uzunluk > 0) {
    const mn = new Float64Array(uzunluk);
    const mx = new Float64Array(uzunluk);
    for (let j = 0, i = 0; j < uzunluk; j++) {
      let enKucuk = Infinity;
      let enBuyuk = -Infinity;
      let dolu = false;
      for (const son = i + blok; i < son; i++) {
        const v = y[i];
        if (v !== v) continue; // NaN: eksik örnek
        dolu = true;
        if (v < enKucuk) enKucuk = v;
        if (v > enBuyuk) enBuyuk = v;
      }
      mn[j] = dolu ? enKucuk : NaN;
      mx[j] = dolu ? enBuyuk : NaN;
    }
    min.push(mn);
    maks.push(mx);
  }

  // Düzey k + 1: düzey k'nin B'li tam grupları.
  while ((uzunluk = Math.floor(uzunluk / blok)) > 0) {
    const altMin = min[min.length - 1];
    const altMaks = maks[maks.length - 1];
    const mn = new Float64Array(uzunluk);
    const mx = new Float64Array(uzunluk);
    for (let j = 0, i = 0; j < uzunluk; j++) {
      let ustKucuk = Infinity;
      let ustBuyuk = -Infinity;
      let ustDolu = false;
      for (const son = i + blok; i < son; i++) {
        const altK = altMin[i];
        if (altK !== altK) continue; // boş (tamamen NaN) alt blok
        ustDolu = true;
        if (altK < ustKucuk) ustKucuk = altK;
        const altB = altMaks[i];
        if (altB > ustBuyuk) ustBuyuk = altB;
      }
      mn[j] = ustDolu ? ustKucuk : NaN;
      mx[j] = ustDolu ? ustBuyuk : NaN;
    }
    min.push(mn);
    maks.push(mx);
  }

  return { t, y, n, blok, min, maks };
}

/**
 * Ham indis aralığı [a, b) içindeki NaN'sız örneklerin min/maks'ını
 * hedef[o], hedef[o + 1]'e yazar (örnek yoksa NaN, NaN).
 * Dönüş: kullanılan en kaba düzey (0 = yalnız ham).
 *
 * Her düzeyde hizasız baş [lo, bas) ve hizasız son [son, hi) tek tek alınır;
 * arada kalan [bas, son) B'ye hizalıdır ve bir üst düzeyin TAM blokları olarak
 * devredilir. Böylece hiçbir blok [a, b) dışına taşmaz. En üst düzeyde
 * devredecek yer yoktur: kalan her öğe tek tek alınır.
 */
function aralikYaz(oz, a, b, hedef, o) {
  const B = oz.blok;
  const y = oz.y;
  const ust = oz.min.length - 1;
  let enk = Infinity;
  let enb = -Infinity;
  let dolu = false;
  let enKaba = 0;
  let lo = a;
  let hi = b;
  for (let k = 0; lo < hi; k++) {
    let bas = hi;
    let son = hi;
    if (k < ust) {
      bas = lo + ((B - (lo % B)) % B); // ilk hizalı indis
      if (bas > hi) bas = hi;
      son = hi - (hi % B); // son hizalı indis
      if (son < bas) son = bas;
    }
    if (k === 0) {
      for (let i = lo; i < bas; i++) {
        const v = y[i];
        if (v === v) { dolu = true; if (v < enk) enk = v; if (v > enb) enb = v; }
      }
      for (let i = son; i < hi; i++) {
        const v = y[i];
        if (v === v) { dolu = true; if (v < enk) enk = v; if (v > enb) enb = v; }
      }
    } else {
      const mn = oz.min[k];
      const mx = oz.maks[k];
      for (let j = lo; j < bas; j++) {
        const p = mn[j];
        if (p === p) { dolu = true; if (p < enk) enk = p; const q = mx[j]; if (q > enb) enb = q; }
      }
      for (let j = son; j < hi; j++) {
        const p = mn[j];
        if (p === p) { dolu = true; if (p < enk) enk = p; const q = mx[j]; if (q > enb) enb = q; }
      }
    }
    if (bas > lo || hi > son) enKaba = k;
    lo = bas / B;
    hi = son / B;
  }
  hedef[o] = dolu ? enk : NaN;
  hedef[o + 1] = dolu ? enb : NaN;
  return enKaba;
}

/**
 * Ham indis aralığı [a, b)'nin NaN'sız min/maks'ı (piramitten, tam).
 * Gezgin şeridi gibi indis tabanlı kullanımlar için.
 * @returns {{min: number, maks: number, duzey: number}}
 */
export function ozetAralik(oz, a, b) {
  const lo = Math.max(0, a);
  const hi = Math.min(oz.n, b);
  const h = new Float64Array(2);
  const duzey = aralikYaz(oz, lo, Math.max(lo, hi), h, 0);
  return { min: h[0], maks: h[1], duzey };
}

/**
 * Pencere sorgusu (D3). Ö1 güvencesi dosya başında.
 * @param oz        ozetKur sonucu
 * @param {number} t0, t1   ms, sonlu, t0 ≤ t1 (iki uç dahil)
 * @param {number} genislik W: piksel sütunu sayısı, ≥ 1 tamsayı
 * @param {{boslukMs?: number}} [secenek]
 * @returns
 *   {tur: 'ham', i0, i1[, bolumler]}  — ham noktalar t/y[i0, i1) (yarı açık);
 *     aralığın iki yanındaki birer komşu dahil. boslukMs verilmişse
 *     `bolumler` = boslukBolumleri(t, boslukMs, i0, i1).
 *   {tur: 'ozet', duzey, sutunlar[, kesik]} — sutunlar Float64Array(2W):
 *     [min_0, maks_0, min_1, maks_1, …], boş sütun NaN. `duzey` = kullanılan en
 *     kaba piramit düzeyi (bilgi). boslukMs verilmişse `kesik` Uint8Array(W).
 */
export function ozetPencere(oz, t0, t1, genislik, { boslukMs } = {}) {
  if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 < t0) {
    throw new RangeError(`ozetPencere: sonlu t0 ≤ t1 olmalı (${t0}, ${t1})`);
  }
  if (!Number.isInteger(genislik) || genislik < 1) {
    throw new RangeError(`ozetPencere: genislik ≥ 1 tamsayı olmalı (${genislik})`);
  }
  const bosluk = boslukDenetle(boslukMs);
  const t = oz.t;
  const n = oz.n;
  const a = altSinir(t, t0);
  const b = ustSinir(t, t1, a);

  if (b - a <= 2 * genislik) {
    const i0 = a > 0 ? a - 1 : 0;
    const i1 = b < n ? b + 1 : n;
    const hamSonuc = { tur: 'ham', i0, i1 };
    if (bosluk < Infinity) hamSonuc.bolumler = boslukBolumleri(t, bosluk, i0, i1);
    return hamSonuc;
  }

  const W = genislik;
  const sutunlar = new Float64Array(2 * W);
  const kesik = bosluk < Infinity ? new Uint8Array(W) : null;
  const aralik = t1 - t0;
  let bas = a;
  let duzey = 0;
  for (let c = 0; c < W; c++) {
    let son = b;
    if (c < W - 1) {
      let sinir = t0 + aralik * (c + 1) / W;
      if (sinir > t1) sinir = t1;
      son = altSinir(t, sinir, bas, b);
    }
    const k = aralikYaz(oz, bas, son, sutunlar, 2 * c);
    if (k > duzey) duzey = k;
    if (kesik !== null && son > bas && bas > 0 && t[bas] - t[bas - 1] > bosluk) kesik[c] = 1;
    bas = son;
  }
  const ozetSonuc = { tur: 'ozet', duzey, sutunlar };
  if (kesik !== null) ozetSonuc.kesik = kesik;
  return ozetSonuc;
}

/**
 * Boşlukla bölünmüş çizim parçaları (D1): t[i0, i1) aralığı, t[i] − t[i−1] >
 * boslukMs olan her i'de yeni parçaya başlar. Tam eşitlik boşluk değildir.
 * @returns {Array<[number, number]>} yarı açık [bas, son) çiftleri; boş aralıkta [].
 *   boslukMs verilmezse (ya da Infinity) tek parça.
 */
export function boslukBolumleri(t, boslukMs, i0 = 0, i1 = t.length) {
  const bosluk = boslukDenetle(boslukMs);
  const lo = Math.max(0, i0);
  const hi = Math.min(t.length, i1);
  const bolumler = [];
  if (!(hi > lo)) return bolumler;
  let bas = lo;
  if (bosluk < Infinity) {
    for (let i = lo + 1; i < hi; i++) {
      if (t[i] - t[i - 1] > bosluk) {
        bolumler.push([bas, i]);
        bas = i;
      }
    }
  }
  bolumler.push([bas, hi]);
  return bolumler;
}

/**
 * Düzey k ≥ 1, blok j'nin ilk ve son örneğinin zamanı (D2; t'den türetilir).
 * @returns {[number, number]}
 */
export function blokZamani(oz, duzey, j) {
  if (!(Number.isInteger(duzey) && duzey >= 1 && duzey < oz.min.length)) {
    throw new RangeError(`blokZamani: düzey 1…${oz.min.length - 1} olmalı (${duzey})`);
  }
  if (!(Number.isInteger(j) && j >= 0 && j < oz.min[duzey].length)) {
    throw new RangeError(`blokZamani: blok 0…${oz.min[duzey].length - 1} olmalı (${j})`);
  }
  const boy = oz.blok ** duzey;
  return [oz.t[j * boy], oz.t[(j + 1) * boy - 1]];
}
