/* ═══════════════════════════════════════════════════════════════════════
   3D — CANLI GRAFIK                                    (ekran/canli.js)

   Canli ekranin zaman grafigi `ortak/src/grafik.js` ile (karar D3, P3:
   tek grafik cekirdegi; kayit gorunumuyle ayni cizim ve etkilesim).
   Olcum durumu (gecmis, KPI, kayit durumu) app.js'te — tek ayristirici
   `satirIsle` orada (B22.2). Bu modul yalniz gecmisten seri kurar ve
   cizer.

   NEDEN AYRI ve TEMBEL: grafik.js + ozet.js + istatistik.js ~24 KB gzip ve
   uc dosya. Canli ekran ilk gorunur olunca `import()` ile iner (Kayitlar'in
   U1 deseni); okuma kartlari ve kayit denetimi onu BEKLEMEDEN app.js'ten
   cizilir. Acilista istenen statik dosya sayisi (B7 bolum 15: <= 8) boyle
   korunuyor; Canli ile acilisin toplami (statik + bu modulun agaci) B7'de
   AYRICA olculuyor — gizlenmiyor.

   KARARLAR (D1-D8 disinda):
   K1 SAG EKSEN TEK BIRIM: Akim YA DA Guc (3C K4 ile ayni). Eski tuval uc
      kanali birbirinden bagimsiz olcekliyordu (eksen yazisi yoktu); grafik.js
      eksenleri YAZIYOR ve iki birim tek eksende eksen yazisini yalanci yapar.
   K2 GURULTU TABANI (B45) korunuyor: kanal basina en dar eksen araligi
      2 x taban (app.js `olcekTabani`, 20 LSB) — bostaki +-3 uA gurultusu
      ekrani doldurmaz. grafik.js'te bunun adi `enAzAralik` (G3).
   K3 CANLIDA etkilesim KAPALI (pointer-events: none): her D satiri pencereyi
      yeniden kurar, kullanicinin yakinlastirmasi 200 ms sonra silinirdi; ayrica
      telefonda grafigin ustunden sayfa kaydirilabilsin (grafik.js
      touch-action: none koyuyor). DONDUR: anlik kopya alinir, pencere ayni
      kalir, imlec + yakinlastirma + kaydirma acilir (D3).
   K4 X EKSENI "simdi"ye gore: zaman koken = penceredeki son nokta, yazilar
      eksi (-00:00:30 ... 00:00:00) — eski tuvalin "-60 sn ... simdi" yazisi.
   K5 Imlec rengi temanin `--yazi`si (3C K5 ile ayni).
   ═══════════════════════════════════════════════════════════════════════ */

import { Grafik, cssRenk } from '/ortak/grafik.js';

/** Kanallar: gecmis alani, grafik adi/birimi, renk belirteci, eksen. */
export const CANLI_KANALLAR = Object.freeze([
  Object.freeze({ ad: 'V', alan: 'v', birim: 'V', renk: 'volt', eksen: 'sol' }),
  Object.freeze({ ad: 'I', alan: 'i', birim: 'A', renk: 'amper', eksen: 'sag' }),
  Object.freeze({ ad: 'W', alan: 'w', birim: 'W', renk: 'watt', eksen: 'sag' }),
]);

/** Sag eksen secenekleri (K1). */
export const SAG_EKSENLER = Object.freeze(['akim', 'guc', 'yok']);

/** Kanal gorunur mu: V `gosterV` ile; sag eksende yalniz SECILEN birim (K1). */
export function kanalGorunur(alan, { gosterV = true, sagEksen = 'akim' } = {}) {
  if (alan === 'v') return !!gosterV;
  if (alan === 'i') return sagEksen === 'akim';
  if (alan === 'w') return sagEksen === 'guc';
  return false;
}

/** `gecmis` (t artan, saniye) icinde t >= basT olan ilk indis (ikili arama). */
export function pencereBasi(gecmis, basT) {
  let a = 0;
  let b = gecmis.length;
  while (a < b) {
    const o = (a + b) >> 1;
    if (gecmis[o].t < basT) a = o + 1;
    else b = o;
  }
  return a;
}

/** Bosluk esigi (ms): ardisik iki nokta arasi bundan buyukse cizgi KESILIR (G2).
 *  Rapor araliginin 2.5 kati — kayit gorunumunun `hiz x 2.5` kuraliyla ayni. */
export function canliBoslukMs(aralikMs) {
  const a = Number(aralikMs);
  return Math.max(250, 2.5 * (a > 0 ? a : 200));
}

/**
 * Pencere verisinden grafik serileri. Uc kanal AYNI `t` dizisini paylasir
 * (imlecOkuma'nin enerji kosulu, G5). NaN = o satirda kanal yanit vermedi:
 * cizgi kopar (B27 A2 / G2). En dar eksen araligi 2 x taban (K2).
 */
export function canliSeriler(veri, { taban = { v: 0, i: 0, w: 0 }, boslukMs = 500,
  gosterV = true, sagEksen = 'akim' } = {}) {
  const n = veri.length;
  const t = new Float64Array(n);
  const y = { v: new Float64Array(n), i: new Float64Array(n), w: new Float64Array(n) };
  for (let k = 0; k < n; k++) {
    const d = veri[k];
    t[k] = d.t * 1000;
    y.v[k] = d.v;
    y.i[k] = d.i;
    y.w[k] = d.w;
  }
  return CANLI_KANALLAR.map((kn) => ({
    ad: kn.ad, t, y: y[kn.alan], birim: kn.birim, renk: kn.renk, eksen: kn.eksen, boslukMs,
    enAzAralik: 2 * (Number(taban[kn.alan]) || 0),
    gizli: !kanalGorunur(kn.alan, { gosterV, sagEksen }),
  }));
}

/**
 * Lejant (HTML'de; tuvalde dil metni yok, grafik.js G8): GORUNUR her kanal icin
 * penceredeki gecerli ornek sayisi, tepe |deger| ve olcek gurultu tabanindan mi geliyor.
 * `gecerli === 0` -> "veri yok" (B27 A2: sahte 1.72 V duz cizgi olarak cizilmesin).
 */
export function canliLejant(veri, taban, secim = {}) {
  const sonuc = [];
  for (const kn of CANLI_KANALLAR) {
    if (!kanalGorunur(kn.alan, secim)) continue;
    let gecerli = 0;
    let tepe = 0;
    let enk = Infinity;
    let enb = -Infinity;
    for (const d of veri) {
      const x = d[kn.alan];
      if (Number.isNaN(x)) continue;
      gecerli++;
      if (Math.abs(x) > tepe) tepe = Math.abs(x);
      if (x < enk) enk = x;
      if (x > enb) enb = x;
    }
    const tb = Number(taban && taban[kn.alan]) || 0;
    sonuc.push({
      ad: kn.ad, alan: kn.alan, renk: kn.renk, birim: kn.birim, gecerli, tepe,
      /* olcek gurultu tabanindan: penceredeki salinim en dar araligin altinda (K2) */
      tabanda: gecerli > 0 && tb > 0 && (enb - enk) < 2 * tb, olcek: tb,
    });
  }
  return sonuc;
}

/** Renk cozucu: `imlec` -> `--yazi` (K5), gerisi grafik.js'in CSS okuyucusu. */
export function renkCozucu(eleman, pencere = globalThis) {
  const cs = cssRenk(eleman, pencere);
  return (ad) => cs(ad === 'imlec' ? 'yazi' : ad);
}

/**
 * Canli grafik. `ciz(d)` her D satirindan sonra (app.js istekleri bir kareye
 * birlestiriyor) ve gorunum/tema degisince cagrilir.
 *   d = { gecmis, pencereS, gosterV, sagEksen, taban (islev(veri) | {v,i,w}),
 *         aralikMs (rapor araligi; bosluk esigi bundan) | boslukMs, donmus }
 * `degisti(bilgi)`: cizimden ve (donmusken) kullanici etkilesiminden sonra
 *   bilgi = { lejant, pencere: {t0, t1, alanX, alanW, imlecA, imlecB, koken}, okuma, donmus }
 */
export class CanliGrafik {
  constructor(canvas, { pencere = globalThis, degisti = null } = {}) {
    this.canvas = canvas;
    this.degisti = typeof degisti === 'function' ? degisti : null;
    this.g = new Grafik(canvas, {
      renk: renkCozucu(canvas, pencere), zamanKokeni: 0, gerilim: 'V', akim: 'I', pencere,
      onDegisim: () => this._bildir(),
    });
    this.donmus = false;
    this.kopya = null;          // dondurulmus gecmis (dizi kopyasi; ogeler donuk nesne)
    this.son = null;            // son `ciz` argumani (secimler)
    this._etkilesim(false);
  }

  _etkilesim(acik) {
    const c = this.canvas;
    if (c.style) c.style.pointerEvents = acik ? '' : 'none';      // K3
    if (typeof c.tabIndex === 'number') c.tabIndex = acik ? 0 : -1;
  }

  _secim(d) {
    return { gosterV: d.gosterV !== false, sagEksen: SAG_EKSENLER.includes(d.sagEksen) ? d.sagEksen : 'akim' };
  }

  ciz(d) {
    this.son = d;
    const gecmis = d.gecmis || [];
    const secim = this._secim(d);
    const pencereMs = Math.max(1, Number(d.pencereS) || 60) * 1000;
    if (d.donmus && !this.donmus) {                  // DONDUR: anlik kopya, pencere ayni
      this.donmus = true;
      this.kopya = gecmis.slice();
      this._donukAnahtar = secim.gosterV + '/' + secim.sagEksen;
      this._kur(this.kopya, d, secim);
      const n = this.kopya.length;
      if (n) {
        const sonT = this.kopya[n - 1].t * 1000;
        this.g.durumAyarla({ t0: sonT - pencereMs, t1: sonT });
      }
      this._etkilesim(true);
    } else if (!d.donmus && this.donmus) {           // CANLIYA DON
      this.donmus = false;
      this.kopya = null;
      this._etkilesim(false);
    }
    if (this.donmus) {
      /* Donmusken yeni D satirlari kopyaya GIRMEZ; yalniz secim (V / sag eksen) degisince
         ayni kopyadan, pencere + imlecler korunarak yeniden kurulur. Taban dondurma anindaki. */
      const anahtar = secim.gosterV + '/' + secim.sagEksen;
      if (anahtar !== this._donukAnahtar) {
        this._donukAnahtar = anahtar;
        this._kur(this.kopya, { ...d, taban: this._taban, boslukMs: this._bosluk }, secim, true);
      }
    } else {
      const n = gecmis.length;
      const basT = n ? gecmis[n - 1].t - pencereMs / 1000 : 0;
      this._kur(gecmis.slice(pencereBasi(gecmis, basT)), d, secim);
    }
    this.g.ciz();
    return this._bildir();
  }

  _kur(veri, d, secim, koru = false) {
    /* taban: app.js `olcekTabani(pencereVerisi)` (islev) ya da donmusken saklanan nesne */
    const taban = typeof d.taban === 'function' ? d.taban(veri) : (d.taban || { v: 0, i: 0, w: 0 });
    const boslukMs = Number.isFinite(d.boslukMs) ? d.boslukMs : canliBoslukMs(d.aralikMs);
    const seriler = canliSeriler(veri, { taban, boslukMs, ...secim });
    this._veri = veri;
    this._taban = taban;
    this._bosluk = boslukMs;
    this._secimSon = secim;
    /* K4: koken = son nokta (canli) ya da dondurma ani */
    this.g.secenek.zamanKokeni = veri.length ? veri[veri.length - 1].t * 1000 : 0;
    this.g.veriAyarla(seriler, { koru });
  }

  _bildir() {
    const g = this.g;
    const dur = g.durum;
    const plan = g.sonPlan;
    const veri = this._veri || [];
    /* lejant GORUNEN pencereden (donmusken yakinlastirmayla daralir) */
    const a = pencereBasi(veri, dur.t0 / 1000 - 1e-9);
    const b = pencereBasi(veri, dur.t1 / 1000 + 1e-9);
    const bilgi = {
      donmus: this.donmus,
      lejant: canliLejant(veri.slice(a, b), this._taban || {}, this._secimSon || {}),
      pencere: {
        t0: dur.t0, t1: dur.t1, imlecA: dur.imlecA, imlecB: dur.imlecB,
        koken: g.secenek.zamanKokeni,
        alanX: plan && plan.alan ? plan.alan.x : null, alanW: plan && plan.alan ? plan.alan.w : null,
      },
      okuma: this.donmus && (Number.isFinite(dur.imlecA) || Number.isFinite(dur.imlecB)) ? g.okuma() : null,
    };
    if (this.degisti) this.degisti(bilgi);
    return bilgi;
  }

  imlecTemizle() {
    this.g.durumAyarla({ imlecA: null, imlecB: null });
    this.g.ciz();
    this._bildir();
  }

  yokEt() {
    this.g.yokEt();
    this.kopya = null;
    this._veri = null;
  }
}
