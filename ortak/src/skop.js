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
 * NEDEN float32 öykünmesi (çift duyarlık + tolerans DEĞİL): eşikler ve kesirli kenar
 * konumları float32'de kurulur; `0.1f` sabitiyle ama çift duyarlıkla kurulan %10 eşiği
 * tamsayının biraz üstünde kalır, eşiğe EŞİT örnek float32'de kenar sayılır, öbüründe
 * sayılmaz → tr başka örnekten ölçülür (vektör `esik_float32`: rampa eşikte bekler, kart
 * beklemenin başından ölçer).
 * Panel/PC kartın gösterdiği sayının AYNISINI göstersin diye kart taklit edilir.
 *
 * 1F (2026-10-02) — C'deki dört kusur düzeltildi, bu dosya yeni C'yi izler:
 *   S1 Vac/Vrms/Vort artık TAM tamsayı toplamlardan (S1 = Σh, S2 = Σh², n·S2 − S1²;
 *      sonuncusu 2^53'ü aşar → BigInt) ve tek karekökle; eskiden float32 kare farkıydı
 *      (sabit 2048 kodda 0.196 V, ±3 kod gürültüde 0). `u64f` = C `skop_u64_float`.
 *   S2 kart artık kaynaştırmasız derleniyor (madd.s yok) → kart = AVR = bu dosya.
 *   S3 duty örnekleri (taban(ilk), taban(son)] — eskiden bir örnek fazlaydı.
 *   S4 tr/tf: %10 → %90 arasında karşı eşik geçilirse başlangıç bırakılır.
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

const IKI24 = 16777216n;

/**
 * C `skop_u64_float`: negatif olmayan tamsayı (BigInt) → float32, DOĞRU yuvarlanmış (en
 * yakına, eşitlikte çifte). C ile adım adım aynı: 2^24'ün altına inene dek sağa kaydır
 * (son atılan bit + yapışkan), yuvarla, tam dönüştür, 2'nin kuvvetiyle çarp.
 * (`Math.fround(Number(b))` 2^53 üstünde İKİ KEZ yuvarlar — kullanılmaz.)
 */
export function u64f(x) {
  let k = 0;
  let son = 0n;
  let artik = 0n;
  while (x >= IKI24) {
    artik |= son;
    son = x & 1n;
    x >>= 1n;
    k++;
  }
  if (son && (artik || (x & 1n))) x += 1n;
  let f = Number(x); // ≤ 2^24: tam
  for (; k > 0; k--) f = f32(f * 2);
  return f;
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

  /* --- 1. geçiş: uçlar + TAM tamsayı toplamlar (1F S1) ----------------- */
  let hmin = h[0];
  let hmax = h[0];
  let s1 = 0; // Σh  < 2^32: Number'da tam
  let s2 = 0; // Σh² < 2^48: Number'da tam
  for (let i = 0; i < n; i++) {
    const k = h[i];
    if (k < hmin) hmin = k;
    if (k > hmax) hmax = k;
    s1 += k;
    s2 += k * k;
  }
  o.Vmax = f32(hmax * va);
  o.Vmin = f32(hmin * va);
  o.Vpp = f32(o.Vmax - o.Vmin);
  /* n·S2 − S1² = n²·varyans (kod²) ≤ 65535⁴ < 2^64, ≥ 0 — TAM (BigInt), sonra tek karekök. */
  const pay = BigInt(n) * BigInt(s2) - BigInt(s1) * BigInt(s1);
  const vaMutlak = va < 0 ? -va : va; // RMS'ler işaretsiz (C ile aynı)
  const ort = f32(u64f(BigInt(s1)) / n); // kod
  const ac = f32(f32(Math.sqrt(u64f(pay))) / n); // kod, ≥ 0
  o.Vort = f32(ort * va);
  o.Vac = f32(ac * vaMutlak);
  /* Vrms özdeşlikten √(ort² + ac²): sadeleşmesiz; düz çizgide TAM Vort. */
  o.Vrms = f32(f32(Math.sqrt(f32(f32(ort * ort) + f32(ac * ac)))) * vaMutlak);

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

      /* Duty: yalnız TAM çevrimler — örnekler (taban(ilk), taban(son)], tam (son − bas)
       * tane (1F S3; eskiden [bas, son]: bir örnek fazla, temiz %50 kare %49.79). */
      const bas = Math.trunc(ilkKesim);
      const son = Math.trunc(sonKesim);
      let ustSayi = 0;
      let top = 0;
      for (let i = bas + 1; i <= son && i < n; i++) {
        if (h[i] >= orta) ustSayi++;
        top++;
      }
      if (top > 0) o.duty = f32(f32(100 * ustSayi) / top);
    }
  }

  /* --- 3. geçiş: yükselme / düşme süresi (%10 → %90) -------------------
   * KURAL (1F S4): yükselme = %10'u yukarı geçiş → %90'ı yukarı geçiş, ARADA %10'un altına
   * (s < alt) inmeden; inerse başlangıç bırakılır, sonraki yukarı geçişte yeniden kurulur.
   * Düşme simetrik (arada s > ust olursa bırakılır). Kayıttaki İLK tam geçiş ölçülür. */
  const aralik = f32(hmax - hmin);
  const alt = f32(hmin + f32(aralik * ON));
  const ust = f32(hmin + f32(aralik * DOKSAN));
  {
    let t10 = -1;
    let t90 = -1;
    onceki = h[0];
    for (let i = 1; i < n && t90 < 0; i++) {
      const s = h[i];
      if (t10 >= 0 && s < alt) t10 = -1; // %90'a varmadan geri indi
      if (t10 < 0 && onceki < alt && s >= alt) t10 = f32((i - 1) + kesisim(onceki, s, alt));
      if (t10 >= 0 && onceki < ust && s >= ust) t90 = f32((i - 1) + kesisim(onceki, s, ust));
      onceki = s;
    }
    if (t10 >= 0 && t90 > t10) o.tr = f32(f32(t90 - t10) / hz);
  }
  {
    let t90 = -1;
    let t10 = -1;
    onceki = h[0];
    for (let i = 1; i < n && t10 < 0; i++) {
      const s = h[i];
      if (t90 >= 0 && s > ust) t90 = -1; // %10'a varmadan geri çıktı
      if (t90 < 0 && onceki > ust && s <= ust) t90 = f32((i - 1) + kesisim(onceki, s, ust));
      if (t90 >= 0 && onceki > alt && s <= alt) t10 = f32((i - 1) + kesisim(onceki, s, alt));
      onceki = s;
    }
    if (t90 >= 0 && t10 > t90) o.tf = f32(f32(t10 - t90) / hz);
  }
  return o;
}

/* ═══ 3E — KARTIN `M` SATIRI (alt proje 3, karar OS4) ════════════════════════
 * Kart `M` satirini `skop_olc`'un CIPLAK sonucundan basmaz: kod/olcum-karti-a3/
 * olcum-karti-a3.ino `skop_olc_kalibre` (B43) + `skop_ofsetle` (B19). Kayitli yakalama
 * (SKOP 10) olcum TASIMIYOR, ham kod tasiyor; panel kartin gosterecegi sayiyi bu iki
 * islevin birebir kopyasiyla bulur:
 *   * egri GECERLIYSE (OLAY KO_SKOP_KAL, 17 nokta; karttaki `kal_tab_var`):
 *       gerilimler egriden — kal_mv (float32) x SKOP_ORAN/1000, toplamlar DOUBLE;
 *       zaman buyuklukleri skop_olc'tan, egriyle DOGRUSALLASTIRILMIS kodlarla.
 *   * egri yoksa: skop_olc(ham, adim) (ofsetsiz).
 *   * sonra skop_ofsetle: Vmax/Vmin/Vort -= ofset (float32), Vrms = sqrtf(Vac² + Vort²).
 * Kanit: gercek karttan alinmis yakalama (uretim/olcum-skop-fikstur.json, 2026-09-13) —
 * bu kod kartin `M` satirindaki gerilimleri, f, T ve n'yi BASILAN HANEYE KADAR ayni
 * veriyor (test/skop.test.js). duty/tr/tf o tarihten sonra 1F (S3/S4) ile degisti.
 * ⚠ Kart egriyi kayda HER ZAMAN yazar (kal_tab_var olmasa da `kal_mv_tab` sifir ya da
 *   yarim dolu) — gecerlilik `egriGecerli` ile: tam 17 nokta, ilk >= 0, KESIN ARTAN
 *   (eFuse egrisi monoton; sifir / yarim dizi degil). */

/** olcum3.h sabitleri — derleyicinin float32 katlamasiyla (her islem SFmode'da). */
export const KART_SABIT = Object.freeze({
  ORAN: f32(38.03703704),                       // SKOP_ORAN
  ADC_TAVAN: f32(3.10),                         // SKOP_ADC_TAVAN
  ADC_SAYIM: 4096,                              // SKOP_ADC_SAYIM
  VREF: f32(1.7153125),                         // VREF_NOMINAL
});
/** SKOP_VOLT_ADIM = ADC_TAVAN / ADC_SAYIM * ORAN; SKOP_VOLT_OFSET = VREF * (ORAN - 1). */
export const KART_VOLT_ADIM = f32(f32(KART_SABIT.ADC_TAVAN / KART_SABIT.ADC_SAYIM) * KART_SABIT.ORAN);
export const KART_VOLT_OFSET = f32(KART_SABIT.VREF * f32(KART_SABIT.ORAN - 1));
/** Egri nokta sayisi (KAL_N) ve dugum kodu (kal_dugum_kod: 0, 256, ..., 3840, 4095). */
export const KAL_N = 17;
export function kalDugumKod(k) {
  return k === KAL_N - 1 ? 4095 : k * 256;
}

/** Kartin `kal_tab_var` karsiligi: 17 sayi, ilk >= 0, kesin artan. */
export function egriGecerli(egri) {
  if (!egri || typeof egri.length !== 'number' || egri.length !== KAL_N) return false;
  for (let k = 0; k < KAL_N; k++) {
    const v = egri[k];
    if (!Number.isFinite(v) || (k === 0 ? v < 0 : v <= egri[k - 1])) return false;
  }
  return true;
}

/** C `kal_mv(kod)`: ham kod -> pin mV, tablo ara degerlemesi (float32; tablo disi UZATILIR). */
export function kalMvKart(egri, kod) {
  const x = f32(kod);
  let i;
  if (x <= 256) i = 0;
  else if (x >= 3840) i = KAL_N - 2;
  else i = Math.trunc(f32(x / 256));
  const k0 = kalDugumKod(i);
  const k1 = kalDugumKod(i + 1);
  const v0 = f32(egri[i]);
  const v1 = f32(egri[i + 1]);
  return f32(v0 + f32(f32(f32(v1 - v0) * f32(x - k0)) / f32(k1 - k0)));
}

/** C `skop_ofsetle(m)` — `o` YERINDE degisir ve doner. ofset float32'ye yuvarlanir. */
export function skopOfsetle(o, ofset) {
  const of = f32(ofset);
  o.Vmax = f32(o.Vmax - of);
  o.Vmin = f32(o.Vmin - of);
  o.Vort = f32(o.Vort - of);
  o.Vrms = f32(Math.sqrt(f32(f32(o.Vac * o.Vac) + f32(o.Vort * o.Vort))));
  return o;
}

/**
 * C `skop_olc_kalibre` (egri GECERLI dali; ofsetsiz — ofseti `skopOfsetle` uygular).
 * Egri gecersizse kart gibi `skopOlc`a duser.
 */
export function skopOlcKalibre(ham, adet, voltAdim, orneklemeHz, egri) {
  const uzunluk = ham && typeof ham.length === 'number' ? ham.length : 0;
  let n = adet === undefined ? uzunluk : Math.floor(Number(adet));
  if (!(n > 0)) n = 0;
  n = Math.min(n, uzunluk, AZAMI_ADET);
  if (!egriGecerli(egri) || n === 0) return skopOlc(ham, n, voltAdim, orneklemeHz);
  const mvKod = f32(KART_SABIT.ADC_SAYIM / f32(KART_SABIT.ADC_TAVAN * 1000));   // pin mV -> dogrusal kod
  const mvV = f32(KART_SABIT.ORAN / 1000);                                      // pin mV -> V (ofsetsiz)
  const h = new Uint16Array(n);
  for (let i = 0; i < n; i++) h[i] = ham[i];
  const gecici = new Uint16Array(n);
  let hmin = h[0];
  let hmax = h[0];
  let top = 0;
  let kare = 0;
  for (let i = 0; i < n; i++) {
    const mv = kalMvKart(egri, h[i]);
    const d = f32(f32(mv * mvKod) + 0.5);
    gecici[i] = d <= 0 ? 0 : d >= 65535 ? 65535 : Math.trunc(d);
    const v = mv * mvV;              // float x float: double'da TAM (24 + 24 bit)
    top += v;
    kare += v * v;
    if (h[i] < hmin) hmin = h[i];
    if (h[i] > hmax) hmax = h[i];
  }
  const o = skopOlc(gecici, n, voltAdim, orneklemeHz);   // zaman buyuklukleri
  const ort = top / n;
  const ac = kare / n - ort * ort;
  o.Vmax = f32(kalMvKart(egri, hmax) * mvV);
  o.Vmin = f32(kalMvKart(egri, hmin) * mvV);
  o.Vpp = f32(o.Vmax - o.Vmin);
  o.Vort = f32(ort);
  o.Vac = ac > 0 ? f32(Math.sqrt(ac)) : 0;
  o.Vrms = f32(Math.sqrt(kare / n));
  return o;
}

/**
 * Kartin `M` satirinin sayilari: `skop_olc_kalibre` (ya da egrisizse `skop_olc`) +
 * `skop_ofsetle`. `adim`/`ofset`/`hz` kaydin META'sindan (kartin float32 degerleri),
 * `egri` OLAY KO_SKOP_KAL'in 17 mV'si (yoksa / gecersizse egrisiz yol).
 * @returns {{f,T,Vpp,Vmax,Vmin,Vort,Vrms,Vac,duty,tr,tf,n, egri: boolean}}
 */
export function skopOlcKart(ham, { adim, ofset, hz, egri = null, adet } = {}) {
  const egriVar = egriGecerli(egri);
  const o = egriVar ? skopOlcKalibre(ham, adet, adim, hz, egri) : skopOlc(ham, adet, adim, hz);
  /* adet 0 ya da hz <= 0: kart da skop_ofsetle'yi cagirir — ama gercekte M basilmaz
     (yakalama yok); burada da sozlesme ayni kalsin. */
  skopOfsetle(o, ofset);
  return { ...o, egri: egriVar };
}
