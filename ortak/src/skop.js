/**
 * ortak/src/skop.js — osiloskop otomatik ölçümleri (alt proje 2, dilim 2E).
 *
 * Kartın `skop_olc()` işlevinin (kod/olcum-karti-a3/skop_olc.h, olcum2.h'den üretilen
 * birebir kopya) JS karşılığı. Aynı girdi, aynı çıktı, aynı "ölçülemedi" kuralları —
 * BİT BİT: C float32 hesaplar; burada her C işlemi aynı noktada `Math.fround` ile
 * float32'ye yuvarlanır. (Çift duyarlıkta hesaplanıp float32'ye çevrilen +, −, ×, ÷ ve √
 * doğru yuvarlanmış float32 sonucunu verir: 53 ≥ 2·24 + 2.) Vektörler: kartın C kodu AVR
 * emülatöründe koşturulur (uretim/ortak_vektor_skop.py → test/vektor/skop.json).
 *
 * NEDEN float32 öykünmesi (çift duyarlık + tolerans DEĞİL): float32 sonuç çift duyarlıklı
 * "doğru" sonuçtan yalnız son hanelerde ayrılmıyor (ölçüldü, 2026-10-02) —
 *   - Vac = √(kare_ort − ort²) float32 toplamlarla: sabit 2048 kodda kart 0.196 V basar,
 *     double 0 verir; ±3 kod gürültüde kart 0 basar, double 0.057 V; sabit 65535'te
 *     0.559 V'a 6e-5 V (vektörler `duz`, `dc_ustu_kucuk_ac`, `sabit_65535`). Hiçbir makul
 *     tolerans bunları "aynı" yapmaz.
 *   - Yarım öykünme de yetmez: `0.1f` sabitiyle ama çift duyarlıkla kurulan %10 eşiği
 *     tamsayının biraz üstünde kalır; eşiğe EŞİT örnek float32'de kenar sayılır, öbüründe
 *     sayılmaz → tr başka kenardan ölçülür (vektör `esik_float32`: kart 3.2 ms, 0.8 değil).
 * Panel/PC kartın gösterdiği sayının AYNISINI göstersin diye kart taklit edilir. Doğru
 * (double) gerilim istatistiği gerekiyorsa: istatistik.js (2D) volt dizisi üzerinde.
 *
 * Bağımlılık yok, Node API'si yok (tarayıcı + Capacitor aynı dosyayı yükler).
 */

const f32 = Math.fround;

/** C'deki `1e-9f`. */
const EPS = f32(1e-9);
/** C'deki `0.1f` ve `0.9f` — çift duyarlıklı 0.1/0.9 DEĞİL. */
const ON = f32(0.1);
const DOKSAN = f32(0.9);

/** C `uint16_t adet` üst sınırı. */
export const AZAMI_ADET = 65535;

/** Çıktı alan adları — kartın `M` satırıyla (arayüz `skopMCoz`) aynı. */
export const ALANLAR = Object.freeze(['f', 'T', 'Vpp', 'Vmax', 'Vmin', 'Vort', 'Vrms', 'Vac',
  'duty', 'tr', 'tf', 'n']);

/**
 * C `skop_kesisim`: iki örnek arasında `esik`in geçildiği kesirli konum (doğrusal ara
 * değerleme). Bütün girdiler float32 değerli.
 */
function kesisim(onceki, simdi, esik) {
  const fark = f32(simdi - onceki);
  if (fark > -EPS && fark < EPS) return 0;
  return f32(f32(esik - onceki) / fark);
}

function sifir() {
  return { f: 0, T: 0, Vpp: 0, Vmax: 0, Vmin: 0, Vort: 0, Vrms: 0, Vac: 0, duty: 0, tr: 0, tf: 0, n: 0 };
}

/**
 * Osiloskop otomatik ölçümleri — C `skop_olc(ham, adet, volt_adim, ornekleme_hz, &o)`.
 *
 * @param {ArrayLike<number>} ham  ham ADC kodları (C `uint16_t`); her öğe Uint16Array
 *        dönüşümüyle alınır (kesirli kısım atılır, NaN → 0, mod 65536 — C'nin uint16_t
 *        ataması gibi)
 * @param {number} [adet=ham.length]  kullanılacak örnek sayısı; ham.length'e ve
 *        AZAMI_ADET'e (65535, C uint16_t) kırpılır; NaN/eksi → 0. (C dizi sonunun
 *        ötesini okurdu; burada okunmaz.)
 * @param {number} voltAdim  V/kod (float32'ye yuvarlanır). OFSET YOK: V = kod × voltAdim
 *        (kartta ofseti çağıran `skop_ofsetle` uygular).
 * @param {number} orneklemeHz  örnekleme hızı (float32'ye yuvarlanır)
 * @returns {{f:number,T:number,Vpp:number,Vmax:number,Vmin:number,Vort:number,Vrms:number,
 *            Vac:number,duty:number,tr:number,tf:number,n:number}}
 *   f Hz, T s, gerilimler V, duty %, tr/tf s (%10→%90 / %90→%10), n = tam çevrim sayısı.
 *   Hepsi float32 değerli (n tamsayı). C sözleşmesi aynen:
 *   - adet 0 ya da orneklemeHz ≤ 0 → HER alan 0 (gerilimler DAHİL)
 *   - hmax − hmin < 8 kod (histerezis < 1) → yalnız gerilimler; f, T, duty, tr, tf, n = 0
 *   - en az iki yükselen kenar yoksa f = T = duty = n = 0 ("periyodik değil")
 *   - tr/tf bulunamazsa 0
 *   Atmaz: geçersiz girdide yukarıdaki sıfırları ya da NaN'ı (C de NaN üretir) döndürür.
 */
export function skopOlc(ham, adet, voltAdim, orneklemeHz) {
  const o = sifir();
  const uzunluk = ham && typeof ham.length === 'number' ? ham.length : 0;
  let n = adet === undefined ? uzunluk : Math.floor(Number(adet));
  if (!(n > 0)) n = 0;
  n = Math.min(n, uzunluk, AZAMI_ADET);
  const hz = f32(orneklemeHz);
  const va = f32(voltAdim);
  if (n === 0 || hz <= 0) return o;

  const h = new Uint16Array(n);
  for (let i = 0; i < n; i++) h[i] = ham[i];

  /* --- 1. geçiş: uçlar, ortalama, RMS --------------------------------- */
  let hmin = h[0];
  let hmax = h[0];
  let toplam = 0;
  let kareToplam = 0;
  for (let i = 0; i < n; i++) {
    const k = h[i];
    if (k < hmin) hmin = k;
    if (k > hmax) hmax = k;
    const v = f32(k * va);
    toplam = f32(toplam + v);
    kareToplam = f32(kareToplam + f32(v * v));
  }
  o.Vmax = f32(hmax * va);
  o.Vmin = f32(hmin * va);
  o.Vpp = f32(o.Vmax - o.Vmin);
  o.Vort = f32(toplam / n);
  const kareOrt = f32(kareToplam / n);
  o.Vrms = f32(Math.sqrt(kareOrt));
  /* AC RMS = √(kare_ort − ort²); float32 yuvarlaması eksiye düşürebilir → kırp. */
  const fark = f32(kareOrt - f32(o.Vort * o.Vort));
  o.Vac = fark > 0 ? f32(Math.sqrt(fark)) : 0;

  /* --- 2. geçiş: periyot, histerezisli yükselen kenarlar --------------- */
  const orta = f32(f32(hmin + hmax) * 0.5);
  const hist = f32(f32(hmax - hmin) * 0.125); // %12.5
  if (hist < 1) return o; // düz çizgi: zaman ölçümü yok

  const kurmaEsigi = f32(orta - hist);
  let ilkKesim = 0;
  let sonKesim = 0;
  let kesimSayisi = 0;
  let hazir = false;
  let onceki = h[0];
  for (let i = 1; i < n; i++) {
    const s = h[i];
    if (!hazir) {
      if (s < kurmaEsigi) hazir = true;
    } else if (s >= orta) {
      const k = f32((i - 1) + kesisim(onceki, s, orta));
      if (kesimSayisi === 0) ilkKesim = k;
      sonKesim = k;
      kesimSayisi++;
      hazir = false;
    }
    onceki = s;
  }

  if (kesimSayisi >= 2) {
    const ornekPeriyot = f32(f32(sonKesim - ilkKesim) / (kesimSayisi - 1));
    if (ornekPeriyot > 0) {
      o.n = kesimSayisi - 1;
      o.T = f32(ornekPeriyot / hz);
      o.f = f32(hz / ornekPeriyot);

      /* Duty: yalnız TAM çevrimler — ilk ve son kenarın örnekleri dahil (C: i <= son). */
      const bas = Math.trunc(ilkKesim);
      const son = Math.trunc(sonKesim);
      let ustSayi = 0;
      let top = 0;
      for (let i = bas; i <= son && i < n; i++) {
        if (h[i] >= orta) ustSayi++;
        top++;
      }
      if (top > 0) o.duty = f32(f32(100 * ustSayi) / top);
    }
  }

  /* --- 3. geçiş: yükselme / düşme süresi (%10 → %90) ------------------- */
  const aralik = f32(hmax - hmin);
  const alt = f32(hmin + f32(aralik * ON));
  const ust = f32(hmin + f32(aralik * DOKSAN));
  {
    let t10 = -1;
    let t90 = -1;
    onceki = h[0];
    for (let i = 1; i < n; i++) {
      const s = h[i];
      if (t10 < 0 && onceki < alt && s >= alt) t10 = f32((i - 1) + kesisim(onceki, s, alt));
      if (t10 >= 0 && t90 < 0 && onceki < ust && s >= ust) t90 = f32((i - 1) + kesisim(onceki, s, ust));
      onceki = s;
    }
    if (t10 >= 0 && t90 > t10) o.tr = f32(f32(t90 - t10) / hz);
  }
  {
    let t90 = -1;
    let t10 = -1;
    onceki = h[0];
    for (let i = 1; i < n; i++) {
      const s = h[i];
      if (t90 < 0 && onceki > ust && s <= ust) t90 = f32((i - 1) + kesisim(onceki, s, ust));
      if (t90 >= 0 && t10 < 0 && onceki > alt && s <= alt) t10 = f32((i - 1) + kesisim(onceki, s, alt));
      onceki = s;
    }
    if (t90 >= 0 && t10 > t90) o.tf = f32(f32(t10 - t90) / hz);
  }
  return o;
}
