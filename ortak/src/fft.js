/**
 * ortak/src/fft.js — FFT ve genlik spektrumu (alt proje 2, dilim 2E).
 *
 * Kartta FFT YOK; bu modül panel/PC/Android'in osiloskop yakalamasından (ya da herhangi
 * bir eşit aralıklı diziden) spektrum çizmesi içindir. Başvuru: kaba kuvvet DFT
 * (ortak/test/fft.test.js) — ayrı bir Python başvurusu gerekmiyor, DFT tanımın kendisi.
 *
 * TANIMLAR
 *   fft: X[k] = Σ x[i]·e^(−2πj·k·i/N)  (ileri yön, ölçeksiz), yerinde, iteratif radix-2
 *        (bit ters sıralama + kelebek). N 2'nin kuvveti olmalı (0 ve 1 de geçer).
 *   spektrum: TEK TARAFLI GENLİK, girdinin biriminde (V girersen V tepe):
 *        genlik[k] = c_k · |X[k]| / Σw,  c_0 = c_(N/2) = 1, diğerleri 2
 *        Σw ile bölmek pencerenin TUTARLI KAZANCINI (coherent gain) düzeltir: tam kutuya
 *        düşen A·cos tonu genlik A verir, pencere ne olursa olsun.
 *        f[k] = k·hz/N, k = 0 … N/2.
 *   Hann: PERİYODİK (DFT-çift) w[i] = 0.5 − 0.5·cos(2πi/n), n = VERİ uzunluğu (dolgu
 *        sıfırları pencerelenmez). Tutarlı kazanç tam 0.5. Kutular arası düşen tonda
 *        "scalloping" kaybı en çok −1.42 dB (genlik ×0.849); dikdörtgende −3.92 dB (×0.637).
 *        Tek örnekte (n = 1) Hann 0'a çökerdi → n = 1'de pencere 1 alınır.
 *   SIFIR DOLDURMA: n 2'nin kuvveti değilse veri sonuna sıfır eklenip N = 2^⌈log2 n⌉ ile
 *        dönüştürülür (varsayılan). Bu çözünürlüğü ARTIRMAZ (ana lob genişliği hz/n kalır),
 *        yalnız spektrumu sıklaştırır; genlik düzeltmesi Σw ile yapıldığından genlikler
 *        dolgudan etkilenmez. `sifirDoldur: false` iken n 2'nin kuvveti değilse RangeError.
 *   DC ÇIKARMA (varsayılan `dcCikar: true`): aritmetik ortalama pencerelemeden ÖNCE
 *        çıkarılır; dc = ortalama (işaretli), genlik[0] = |dc|. Sebep: DC pencerelenince
 *        kendi lobunu ve yan loblarını komşu kutulara sızdırır — periyodik Hann saf DC'yi
 *        1. kutuya DC KADAR genlikle, sıfır doldurulunca −31 dB yan loblarla daha uzağa.
 *        12 V rayda 50 mV dalgalanma gibi (büyük DC + küçük AC) her osiloskop sinyalinde
 *        bu sızıntı tondan büyük olur ve tepe diye bulunurdu (ölçüldü: 3000 örnek, DC 40,
 *        ton 0.5 → tepe 12 Hz'de çıkıyordu). Ortalamayı çıkarmak k ≥ 1 kutularını
 *        dikdörtgende hiç değiştirmez (n = N iken DC ortogonal).
 *        `dcCikar: false`: ders kitabı pencereli spektrum; dc = Re X[0]/Σw (pencere
 *        ağırlıklı ortalama), genlik[0] = |dc|, sızıntı olduğu gibi kalır.
 *
 * Bağımlılık yok, Node API'si yok.
 */

/** n'den büyük ya da eşit en küçük 2'nin kuvveti (n ≤ 1 → 1). */
export function ikiKuvveti(n) {
  let N = 1;
  while (N < n) N *= 2;
  return N;
}

/**
 * Yerinde ileri FFT. `re`, `im` aynı uzunlukta Float64Array (ya da sayı dizisi);
 * uzunluk 2'nin kuvveti olmalı (0 ve 1 dahil), değilse RangeError.
 */
export function fft(re, im) {
  const n = re.length;
  if (im.length !== n) throw new RangeError(`fft: re (${n}) ve im (${im.length}) uzunlukları farklı`);
  if (n <= 1) return;
  if ((n & (n - 1)) !== 0) throw new RangeError(`fft: uzunluk 2'nin kuvveti olmalı (${n})`);

  /* Bit ters sıralama. */
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      let t = re[i]; re[i] = re[j]; re[j] = t;
      t = im[i]; im[i] = im[j]; im[j] = t;
    }
  }

  /* Dönüş çarpanları tablodan (özyinelemeli çarpımla değil): hata ~1e-16, n'den bağımsız. */
  const yarim = n >> 1;
  const wRe = new Float64Array(yarim);
  const wIm = new Float64Array(yarim);
  for (let k = 0; k < yarim; k++) {
    const a = (-2 * Math.PI * k) / n;
    wRe[k] = Math.cos(a);
    wIm[k] = Math.sin(a);
  }

  for (let boy = 2; boy <= n; boy *= 2) {
    const yb = boy >> 1;
    const adim = n / boy;
    for (let bas = 0; bas < n; bas += boy) {
      for (let j = 0, k = 0; j < yb; j++, k += adim) {
        const a = bas + j;
        const b = a + yb;
        const cr = wRe[k];
        const ci = wIm[k];
        const tr = re[b] * cr - im[b] * ci;
        const ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr;
        im[b] = im[a] - ti;
        re[a] += tr;
        im[a] += ti;
      }
    }
  }
}

/** Pencere katsayıları (uzunluk n). 'hann' periyodik; 'dikdortgen' hepsi 1. */
export function pencere(ad, n) {
  if (ad !== 'hann' && ad !== 'dikdortgen') {
    throw new RangeError(`pencere: bilinmeyen pencere '${ad}' (hann | dikdortgen)`);
  }
  const w = new Float64Array(n);
  if (ad === 'dikdortgen' || n === 1) {
    w.fill(1);
  } else {
    for (let i = 0; i < n; i++) w[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / n);
  }
  return w;
}

/**
 * Tek taraflı genlik spektrumu.
 * @param {ArrayLike<number>} y  eşit aralıklı örnekler (NaN varsa sonuç NaN olur)
 * @param {number} hz  örnekleme hızı (> 0, sonlu), değilse RangeError
 * @param {{pencere?: 'hann'|'dikdortgen', sifirDoldur?: boolean, dcCikar?: boolean}} [secenek]
 *   varsayılanlar: pencere 'hann', sifirDoldur true, dcCikar true
 * @returns {{f: Float64Array, genlik: Float64Array, dc: number, n: number, nfft: number,
 *            df: number, pencere: string}}
 *   f, genlik uzunluğu nfft/2 + 1; n veri uzunluğu, nfft dönüşüm uzunluğu, df = hz/nfft.
 *   Boş girdide f/genlik boş, dc NaN.
 */
export function spektrum(y, hz, secenek = {}) {
  const pencereAdi = secenek.pencere ?? 'hann';
  const doldur = secenek.sifirDoldur ?? true;
  const dcCikar = secenek.dcCikar ?? true;
  if (!(hz > 0) || !Number.isFinite(hz)) throw new RangeError(`spektrum: hz pozitif ve sonlu olmalı (${hz})`);
  const n = y.length;
  if (n === 0) {
    pencere(pencereAdi, 0); // bilinmeyen pencere adı boş girdide de reddedilsin
    return { f: new Float64Array(0), genlik: new Float64Array(0), dc: NaN, n: 0, nfft: 0, df: NaN, pencere: pencereAdi };
  }
  const N = ikiKuvveti(n);
  if (N !== n && !doldur) throw new RangeError(`spektrum: uzunluk 2'nin kuvveti değil (${n}); sifirDoldur: true kullan`);

  const w = pencere(pencereAdi, n);
  let ort = 0;
  if (dcCikar) {
    for (let i = 0; i < n; i++) ort += y[i];
    ort /= n;
  }
  let wToplam = 0;
  const re = new Float64Array(N);
  const im = new Float64Array(N);
  for (let i = 0; i < n; i++) {
    re[i] = (y[i] - ort) * w[i];
    wToplam += w[i];
  }
  fft(re, im);

  const m = (N >> 1) + 1;
  const f = new Float64Array(m);
  const genlik = new Float64Array(m);
  const df = hz / N;
  for (let k = 0; k < m; k++) {
    f[k] = k * df;
    const kat = k === 0 || 2 * k === N ? 1 : 2;
    genlik[k] = (kat * Math.hypot(re[k], im[k])) / wToplam;
  }
  const dc = dcCikar ? ort : re[0] / wToplam;
  genlik[0] = Math.abs(dc);
  return { f, genlik, dc, n, nfft: N, df, pencere: pencereAdi };
}

/**
 * En büyük AC bileşen (k ≥ 1; 0. kutu = DC aranmaz), parabolik ara değerlemeyle.
 * Yavaş kayma da bir bileşendir: tondan büyükse tepe odur. `dcCikar: false` ile kurulan
 * Hann spektrumunda DC'nin 1. kutu sızıntısı tepe sanılır — varsayılanı kullan.
 * Bulunan tepe en büyük bileşenin (DC dahil) 1e-12'sinden küçükse sayısal gürültüdür →
 * null (saf DC, hepsi 0).
 *
 * Ara değerleme: tepe kutusu ve iki komşusunun LOGARİTMİK genliğine parabol,
 * δ = ½(a − c)/(a − 2b + c), f = (k + δ)·df, genlik = parabol tepesi. Komşulardan biri
 * tepenin 1e-6'sından küçükse (dikdörtgende tam kutuya düşen ton: komşular yuvarlama
 * gürültüsü, log'u anlamsız) doğrusal genliğe. Ölçülen (2026-10-02; tonu bir kutu boyunca
 * 1/400 adımla kaydırarak, n = 1024 ve dolgulu n = 1000): en büyük frekans hatası Hann
 * 0.016 kutu, dikdörtgen 0.17 kutu; ara değerli genlik hatası Hann ≤ %3.8, dikdörtgen
 * ≤ %27 (ham tepe kutusu: ≤ %15.1 / ≤ %36.3 scalloping). Doğrusal genliğe parabol Hann'da
 * 0.053 kutu — bu yüzden log. Ara değerleme YAPILMAYAN kutular: son (N/2, sağ komşu yok)
 * ve 1. (sol komşu DC kutusu, AC değil) — bunlarda f = k·df.
 *
 * @returns {{f: number, genlik: number, kutu: number} | null}
 *   f Hz, genlik = ara değerli tepe (scalloping kısmen düzeltilmiş), kutu = tepe kutusu.
 *   Tepe yoksa (boş, tek kutu, hepsi 0 ya da NaN) null.
 */
export function tepeFrekans(sp) {
  const g = sp.genlik;
  const m = g.length;
  if (m < 2) return null;
  let k = -1;
  let enb = 0;
  let tum = g[0] > 0 ? g[0] : 0;
  for (let i = 1; i < m; i++) {
    if (g[i] > enb) { enb = g[i]; k = i; }
  }
  if (k < 0) return null;
  if (enb > tum) tum = enb;
  if (enb <= 1e-12 * tum) return null;
  let d = 0;
  let tepe = enb;
  if (k > 1 && k + 1 < m) {
    const sol = g[k - 1];
    const sag = g[k + 1];
    const log = sol > 1e-6 * enb && sag > 1e-6 * enb;
    const [a, b, c] = log ? [Math.log(sol), Math.log(enb), Math.log(sag)] : [sol, enb, sag];
    const payda = a - 2 * b + c;
    if (payda < 0) {
      d = (0.5 * (a - c)) / payda;
      const t = b - 0.25 * (a - c) * d;
      tepe = log ? Math.exp(t) : t;
    }
  }
  return { f: (k + d) * sp.df, genlik: tepe, kutu: k };
}
