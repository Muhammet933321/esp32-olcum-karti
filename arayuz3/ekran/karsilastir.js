/* ═══════════════════════════════════════════════════════════════════════
   3G — KARSILASTIRMA                                 (ekran/karsilastir.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3G kararlari" (KR1-KR8)
   ve "3G uygulama kararlari" (KU1-KU10). Ozet:
     KR1 Secim Kayitlar listesinden (ekran/kayitlar.js secilebilir,
         karsilastirRotaYaz); adres `#/karsilastir/<no>[@kimlik],…` + kip ve
         kanal sorguda (`?x=saat&k=I`; KU2). Geri tusu calisir.
     KR2 TEK grafik, TEK birim (V · I · W'den biri); her kayit ayri cizgi.
         Renkler tema belirteclerinden TURETILIR (KR_RENKLER; KU3): ilk uc
         kayit --volt / --amper / --watt duz, 4.-6. kayit karisim + KESIK
         cizgi — renk korlugunde de ayrilsin (B7 renk korlugu benzetimiyle
         sinar). Renk SECIM SIRASINA bagli: bir kayit bir kipte disarida
         kalinca digerlerinin rengi KAYMAZ.
     KR3 x ekseni uc kip: 'baslangic' (K1: kayit_gorunum.grafikSerileri'nin
         ekseni, saatsiz yeniden baslama "tahmini"), 'saat' (unix ms; saati
         olmayan / kismen olan / geri giden kayit DISARIDA, sebep lejantta),
         'mah' (yalniz pil; pil.js mahEkseni = PU9: bosluk ya da eksi akim
         -> DISARIDA, zaman eksenine DUSMEZ).
     KR4 Iki imlec; okuma KAYIT BASINA (kayit_gorunum.okumaHesapla = imlecOkuma
         + K3 enerji). Imlec kaydin araliginin disindaysa o deger "—" (KU4).
     KR5 Veri YALNIZ bu tarayicidaki kopyadan (EsitlemeDenetcisi.akisVerisi).
     KR7 Birlesik CSV: her kayit kendi x + deger sutunu, yan yana; satir j =
         her kaydin j. ornegi — ortak zaman YOK, ara deger YOK.
   Hesap kodu burada YOK: seriler/K1 kayit_gorunum.js, mAh ekseni pil.js,
   okuma imlecOkuma + aralikEnerji, sayi/hucre yazimi ortak/disari.js.
   NEDEN TEMBEL: app.js `defineAsyncComponent` ile ekran ilk acilinca iner
   (Kayitlar deseni, U1); Kayitlar'dan gelince zinciri zaten inmistir.
   ⚠ Saf fonksiyonlar Vue'suz ve DOM'suz (B7 node'da sinar).
   ═══════════════════════════════════════════════════════════════════════ */

import { Grafik, cssRenk, yerlesim, seriHazirla } from '/ortak/grafik.js';
import { sayiYaz, metinHucre, csvBayt, BASAMAK, BICIM_EXCEL_TR, BICIM_EN } from '/ortak/disari.js';
import { ceviri } from '/ortak/sozluk.js';
import {
  grafikSerileri, okumaHesapla, oturumTuru, metinler, sureYaz, okumaJson, TUR_METIN,
  sayiYaz as sayiGoster,
} from './kayit_gorunum.js';
import { EsitlemeDenetcisi, dilOku } from './esitleme.js';
import { KR_AZAMI, KR_TURLER, karsilastirRotaYaz } from './kayitlar.js';
import { mahEkseni, mahYazi } from './pil.js';

/* ── sabitler ───────────────────────────────────────────────────────── */

export const KIPLER = Object.freeze(['baslangic', 'saat', 'mah']);

/** Kanal: grafikSerileri dizileri (nokta: ort; ayrintili: ornek), okuma anahtari, CSV basligi. */
export const KANALLAR = Object.freeze({
  V: Object.freeze({ birim: 'V', nokta: 'vOrt', ayrinti: 'v', okuma: 'v', csvNokta: 'csv.v_ort',
    csvAyrinti: 'csv.v', basamak: BASAMAK.V, hane: 4, enAz: 0.01, ad: 'kr.kanal_v' }),
  I: Object.freeze({ birim: 'A', nokta: 'iOrt', ayrinti: 'i', okuma: 'i', csvNokta: 'csv.i_ort',
    csvAyrinti: 'csv.i', basamak: BASAMAK.A, hane: 5, enAz: 0.001, ad: 'kr.kanal_i' }),
  W: Object.freeze({ birim: 'W', nokta: 'wOrt', ayrinti: 'w', okuma: 'w', csvNokta: 'csv.w_ort',
    csvAyrinti: 'csv.w', basamak: BASAMAK.W, hane: 4, enAz: 0.01, ad: 'kr.kanal_w' }),
});

/** KR2/KU3: kesik cizgi deseni (CSS px) — grafik.js imlec B'ninkinden ([6, 4]) ayri. */
export const KR_DESEN = Object.freeze([7, 4]);

/**
 * KR2/KU3: kayit sirasina gore cizgi: belirtec (+ istege bagli kutba dogru karisim) + desen.
 * Yeni renk TANIMLANMIYOR (Koyu takim 3A oncesine kilitli, B7): hepsi tema belirteclerinden.
 * 4.-6. kayit kesik: renk korlugu benzetiminde AYNI desenli her cift ayrisiyor (B7 olcer).
 */
export const KR_RENKLER = Object.freeze([
  Object.freeze({ belirtec: 'volt', kutup: null, oran: 0, desen: null }),
  Object.freeze({ belirtec: 'amper', kutup: null, oran: 0, desen: null }),
  Object.freeze({ belirtec: 'watt', kutup: null, oran: 0, desen: null }),
  Object.freeze({ belirtec: 'volt', kutup: 'yazi', oran: 0.5, desen: KR_DESEN }),
  Object.freeze({ belirtec: 'amper', kutup: 'yazi', oran: 0.35, desen: KR_DESEN }),
  Object.freeze({ belirtec: 'vurgu', kutup: 'kart', oran: 0.35, desen: KR_DESEN }),
]);

/* ── SAF: rota ──────────────────────────────────────────────────────── */

/**
 * KR1: `#/karsilastir[/<no>[@kimlik],…][?x=<kip>&k=<kanal>]` -> {secim, kip, kanal, fazla,
 * gecersiz}. Anlasilmayan parca sayilir ve atilir; ayni (no, kimlik) bir kez; KR_AZAMI'dan
 * fazlasi atilir (`fazla`). Bilinmeyen kip/kanal varsayilana duser. Yazicisi kayitlar.js
 * karsilastirRotaYaz (B7 birbirinin tersi oldugunu sinar).
 */
export function karsilastirRotaCoz(hash) {
  const h = String(hash || '').replace(/^#\/?/, '');
  const r = { secim: [], kip: 'baslangic', kanal: 'V', fazla: 0, gecersiz: 0 };
  const m = /^karsilastir(?:\/([^?]*))?(?:\?(.*))?$/.exec(h);
  if (!m) return r;
  for (const p of String(m[1] || '').split(',')) {
    if (!p.trim()) continue;
    const x = /^(\d+)(?:@(\d+))?$/.exec(p.trim());
    if (!x || Number(x[1]) <= 0) {
      r.gecersiz++;
      continue;
    }
    const o = { oturum: Number(x[1]), kimlik: x[2] === undefined ? null : Number(x[2]) };
    if (r.secim.some((s) => s.oturum === o.oturum && s.kimlik === o.kimlik)) continue;
    if (r.secim.length >= KR_AZAMI) {
      r.fazla++;
      continue;
    }
    r.secim.push(o);
  }
  const q = new URLSearchParams(m[2] || '');
  if (KIPLER.includes(q.get('x'))) r.kip = q.get('x');
  if (Object.prototype.hasOwnProperty.call(KANALLAR, q.get('k'))) r.kanal = q.get('k');
  return r;
}

/* ── SAF: renk ──────────────────────────────────────────────────────── */

/** '#rrggbb' (ya da '#rgb') -> [r, g, b]; degilse null. */
export function hexCoz(s) {
  const t = String(s || '').trim();
  let m = /^#([0-9a-f]{6})$/i.exec(t);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  m = /^#([0-9a-f]{3})$/i.exec(t);
  if (m) return [0, 1, 2].map((i) => parseInt(m[1][i] + m[1][i], 16));
  return null;
}

/** a'yi b'ye dogru `oran` kadar karistir (sRGB, kanal basina Math.round). Cozulemezse a. */
export function renkKar(a, b, oran) {
  const x = hexCoz(a);
  if (!x) return String(a || '').trim();
  const y = hexCoz(b);
  const f = y && oran > 0 ? oran : 0;
  const k = x.map((v, i) => Math.round(f ? v * (1 - f) + y[i] * f : v));
  return '#' + k.map((v) => v.toString(16).padStart(2, '0')).join('');
}

/** k. kaydin cizgi rengi; `belirtec(ad)` CSS degiskeninin degeri (cssRenk). */
export function krRenk(k, belirtec) {
  const r = KR_RENKLER[((k % KR_RENKLER.length) + KR_RENKLER.length) % KR_RENKLER.length];
  return r.kutup ? renkKar(belirtec(r.belirtec), belirtec(r.kutup), r.oran) : renkKar(belirtec(r.belirtec), null, 0);
}

/* ── SAF: seriler ───────────────────────────────────────────────────── */

/** h (grafikSerileri) -> secili kanalin dizisi (nokta: ort; ayrintili: ornek). */
export function kanalDizisi(h, kanal = 'V') {
  const k = KANALLAR[kanal] || KANALLAR.V;
  return h.tur === 'ayrinti' ? h.s[k.ayrinti] : h.s[k.nokta];
}

/** h'nin BUTUN serilerini baska bir x dizisine baglar (okumaHesapla ayni t'yi paylasan seriler ister). */
export function xDegistir(h, x) {
  return { ...h, t: x, seriler: h.seriler.map((s) => ({ ...s, t: x })) };
}

/**
 * KR3: kaydin bu kipteki x/y dizisi. Donus {x, y, boslukMs, hx (okuma icin x'e bagli h),
 * tahmini, mahSon} ya da {sebep (sozluk anahtari), d (degiskenler)} — DISARIDA.
 *   baslangic: x = h.t (K1). saat: unix ms; HER noktanin saati bilinmeli ve azalmamali.
 *   mah: yalniz pil (nokta) oturumu; pil.js mahEkseni (PU9) — hata -> disarida.
 */
export function kipSerisi(h, { kip = 'baslangic', kanal = 'V', tur = null } = {}) {
  if (!h || h.tur === 'yok' || !h.adet) return { sebep: 'kr.bos_kayit', d: {} };
  const y = kanalDizisi(h, kanal);
  const n = h.adet;
  if (kip === 'saat') {
    let u = h.s.unixMs;
    if (h.tur === 'ayrinti') {
      u = new Float64Array(n);
      for (let k = 0; k < n; k++) u[k] = h.s.unixUs[k] / 1000;
    }
    let bilinen = 0;
    for (let k = 0; k < n; k++) if (Number.isFinite(u[k])) bilinen++;
    if (!bilinen) return { sebep: 'kr.disari_saatsiz', d: {} };
    if (bilinen < n) return { sebep: 'kr.disari_saat_kismi', d: { eksik: n - bilinen, toplam: n } };
    for (let k = 1; k < n; k++) if (u[k] < u[k - 1]) return { sebep: 'kr.disari_saat_geri', d: {} };
    return { x: u, y, boslukMs: h.boslukMs, hx: xDegistir(h, u), tahmini: false, mahSon: NaN };
  }
  if (kip === 'mah') {
    if (tur !== 'pil' || h.tur !== 'nokta') return { sebep: 'kr.disari_pil_degil', d: {} };
    const m = mahEkseni(h.t, h.s.iOrt, h.boslukMs);
    if (m.hata) return { sebep: m.hata === 'pl.mah_eksi' ? 'kr.disari_mah_eksi' : 'kr.disari_mah_bosluk', d: {} };
    return { x: m.x, y, boslukMs: undefined, hx: { ...xDegistir(h, m.x), boslukMs: Infinity }, tahmini: false,
      mahSon: m.x[n - 1] };
  }
  return { x: h.t, y, boslukMs: h.boslukMs, hx: h, tahmini: h.tahmini.length > 0, mahSon: NaN };
}

/**
 * KR4/KU4: TEK kaydin imlec okumasi (secili kanal). Imlec kaydin [ilk x, son x] araliginin
 * DISINDAYSA o imlecin degeri NaN; fark, ort, mAh, Wh yalniz IKI imlec de icerdeyse. mAh /
 * Wh yalniz zaman kiplerinde (mah kipinde x zaten yuk). Degerler okumaHesapla'dan (en yakin
 * NaN'siz HAM ornek, aralik ortalamasi istatistik.js, enerji K3 — kayit gorunumuyle ayni).
 */
export function kayitOkuma(ks, tA, tB, { kip = 'baslangic', kanal = 'V' } = {}) {
  const x = ks.x;
  const n = x ? x.length : 0;
  const ic = (t) => n > 0 && Number.isFinite(t) && t >= x[0] && t <= x[n - 1];
  const aIc = ic(tA);
  const bIc = ic(tB);
  const r = { a: NaN, b: NaN, fark: NaN, ort: NaN, mah: NaN, wh: NaN, aIcinde: aIc, bIcinde: bIc };
  if (!aIc && !bIc) return r;
  const ok = okumaHesapla(ks.hx, aIc ? tA : NaN, bIc ? tB : NaN);
  const c = ok ? ok[(KANALLAR[kanal] || KANALLAR.V).okuma] : null;
  if (!c) return r;
  if (aIc) r.a = c.a;
  if (bIc) r.b = c.b;
  if (aIc && bIc) {
    r.fark = c.fark;
    r.ort = c.ort;
    if (kip !== 'mah' && ok.enerji) {
      r.mah = ok.enerji.mah;
      r.wh = ok.enerji.wh;
    }
  }
  return r;
}

/* ── SAF: birlesik CSV (KR7) ────────────────────────────────────────── */

const X_SUTUN = Object.freeze({ baslangic: 'csv.gecen_ms', saat: 'csv.unix_s', mah: 'csv.mah' });

/**
 * KR7: girdiler = [{no, kimlik, ayrinti (bool), x, y}] (cizilen kayitlar, secim sirasiyla).
 * Baslik: `<onek><no>[@kimlik]_<x sutunu>` ve `…_<kanal sutunu>` (onek sozlukte: kayit / rec;
 * @kimlik yalniz ayni numara iki akistan seciliyse). Satir j: her kaydin j. ornegi; kisa kayit
 * BOS hucre — ortak zaman ve ara deger YOK. x: baslangic gecen_ms (3 ondalik), saat unix_s
 * (3), mah yuk_mAh (6); deger 6 ondalik (disari.js BASAMAK). Bicim BICIM_EXCEL_TR / BICIM_EN.
 */
export function birlesikCsv(girdiler, { kip = 'baslangic', kanal = 'V', bicim = BICIM_EXCEL_TR } = {}) {
  const b = { ...BICIM_EXCEL_TR, ...(bicim || {}) };
  const k = KANALLAR[kanal] || KANALLAR.V;
  const dil = b.dil === 'en' ? 'en' : 'tr';
  const say = new Map();
  for (const g of girdiler) say.set(g.no, (say.get(g.no) || 0) + 1);
  const onek = (g) => ceviri('kr.csv_onek', dil) + g.no + (say.get(g.no) > 1 ? '@' + g.kimlik : '');
  const xAd = ceviri(X_SUTUN[kip] || X_SUTUN.baslangic, dil);
  const baslik = [];
  for (const g of girdiler) {
    baslik.push(metinHucre(onek(g) + '_' + xAd, b.ayrac));
    baslik.push(metinHucre(onek(g) + '_' + ceviri(g.ayrinti ? k.csvAyrinti : k.csvNokta, dil), b.ayrac));
  }
  const xYaz = (x) => (kip === 'saat' ? sayiYaz(x / 1000, BASAMAK.unix_s, b.ondalik)
    : kip === 'mah' ? sayiYaz(x, BASAMAK.mAh, b.ondalik) : sayiYaz(x, BASAMAK.ayrinti_ms, b.ondalik));
  const satirlar = [baslik.join(b.ayrac) + b.satirSonu];
  const n = girdiler.reduce((e, g) => Math.max(e, g.x.length), 0);
  for (let j = 0; j < n; j++) {
    const h = [];
    for (const g of girdiler) {
      if (j < g.x.length) h.push(xYaz(g.x[j]), sayiYaz(g.y[j], k.basamak, b.ondalik));
      else h.push('', '');
    }
    satirlar.push(h.join(b.ayrac) + b.satirSonu);
  }
  return (b.bom ? '﻿' : '') + satirlar.join('');
}

/** Dosya adi: karsilastirma-<kip>-<kanal>[-en].csv */
export function karsilastirDosyaAdi(kip, kanal, dil = 'tr') {
  return `karsilastirma-${kip}-${String(kanal).toLowerCase()}${dil === 'en' ? '-en' : ''}.csv`;
}

/* ── SAF: zaman yazilari ───────────────────────────────────────────── */

const iki = (x) => String(x).padStart(2, '0');

/** Saat ekseni cizgisi: yerel SS:DD[:SN][.mmm] (adima gore); gun ve ustu adimda YYYY-AA-GG. */
export function saatYazi(ms, adim = 1000) {
  if (!Number.isFinite(ms)) return '';
  const d = new Date(ms);
  if (adim >= 86400000) return `${d.getFullYear()}-${iki(d.getMonth() + 1)}-${iki(d.getDate())}`;
  let s = `${iki(d.getHours())}:${iki(d.getMinutes())}`;
  if (adim < 60000) s += ':' + iki(d.getSeconds());
  if (adim < 1000) s += '.' + String(d.getMilliseconds()).padStart(3, '0');
  return s;
}

/** Tam yerel an: YYYY-AA-GG SS:DD:SN.mmm */
export function saatTamYazi(ms) {
  if (!Number.isFinite(ms)) return '—';
  const d = new Date(ms);
  return `${d.getFullYear()}-${iki(d.getMonth() + 1)}-${iki(d.getDate())} ${iki(d.getHours())}:`
    + `${iki(d.getMinutes())}:${iki(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, '0')}`;
}

/** Saat kipinde eksen koku: en erken anin YEREL gece yarisi (cizgiler yuvarlak saatlere otursun). */
export function geceYarisi(ms) {
  const d = new Date(ms);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** Imlec konumu kipe gore. */
export function anYazi(x, kip) {
  if (!Number.isFinite(x)) return '—';
  if (kip === 'saat') return saatTamYazi(x);
  if (kip === 'mah') return x.toFixed(3) + ' mAh';
  return sureYaz(x);
}

/* ── metinler (sozluk anahtarlari; KR8) ─────────────────────────────── */
export const KR_METIN = Object.freeze({
  baslik: 'kr.baslik', bos: 'kr.bos', kayitlaraGit: 'kr.kayitlara_git', kayitlaraDon: 'kr.kayitlara_don',
  kanal: 'kr.kanal', xEksen: 'kr.x_eksen', kipBaslangic: 'kr.kip_baslangic', kipSaat: 'kr.kip_saat',
  kipMah: 'kr.kip_mah', kanalV: 'kr.kanal_v', kanalI: 'kr.kanal_i', kanalW: 'kr.kanal_w', tumu: 'kr.tumu',
  imlecSil: 'kr.imlec_sil', lejant: 'kr.lejant', yukleniyor: 'kr.yukleniyor', cizilecekYok: 'kr.cizilecek_yok',
  gezginEtiket: 'kr.gezgin_etiket', grafikIpucu: 'kr.grafik_ipucu', okuma: 'kr.okuma', imlecYok: 'kr.imlec_yok',
  tabloBaslik: 'kr.tablo_baslik', kayit: 'kr.kayit', fark: 'kr.fark', ort: 'kr.ort', mah: 'kr.mah', wh: 'kr.wh',
  imlecDisarida: 'kr.imlec_disarida', disariBaslik: 'kr.disari_baslik', csvTr: 'kr.csv_tr', csvEn: 'kr.csv_en',
  disariIpucu: 'kr.disari_ipucu', disariHata: 'kr.disari_hata', yok: 'kr.yok', bosKayit: 'kr.bos_kayit',
  tahmini: 'kr.tahmini',
});

/* ── Vue bileseni ───────────────────────────────────────────────────── */

const SABLON = `
<div class="kr">
  <section class="kart" v-if="!rota.secim.length">
    <h1 class="kg-baslik" ref="baslik" tabindex="-1"><span class="kg-ad">{{ m.baslik }}</span></h1>
    <p class="ipucu kr-bos" data-kr="bos">{{ m.bos }}</p>
    <p><a class="kr-git" href="#/kayitlar" data-kr="kayitlara-git">{{ m.kayitlaraGit }}</a></p>
  </section>

  <template v-else>
    <section class="kart">
      <div class="kg-ust"><a class="kg-geri" href="#/kayitlar" data-kr="kayitlara-don">{{ m.kayitlaraDon }}</a></div>
      <h1 class="kg-baslik" ref="baslik" tabindex="-1"><span class="kg-ust-ad">{{ m.baslik }}</span><span class="gorunmez">: </span><span
        class="kg-ad">{{ baslikAlt }}</span></h1>
      <p v-for="u in uyarilar" :key="u" class="uyari">{{ u }}</p>
      <div class="kr-denetim">
        <label>{{ m.kanal }}
          <select v-model="kanalSecim" class="kg-secim" data-kr="kanal">
            <option value="V">{{ m.kanalV }}</option>
            <option value="I">{{ m.kanalI }}</option>
            <option value="W">{{ m.kanalW }}</option>
          </select>
        </label>
        <label>{{ m.xEksen }}
          <select v-model="kipSecim" class="kg-secim" data-kr="kip">
            <option value="baslangic">{{ m.kipBaslangic }}</option>
            <option value="saat">{{ m.kipSaat }}</option>
            <option value="mah">{{ m.kipMah }}</option>
          </select>
        </label>
        <span class="bosluk"></span>
        <button type="button" @click="tumunuGoster" :disabled="!grafikVar">{{ m.tumu }}</button>
        <button type="button" @click="imlecTemizle" :disabled="!okuma">{{ m.imlecSil }}</button>
      </div>
      <ul class="kr-lejant" :aria-label="m.lejant">
        <li v-for="l in lejant" :key="l.anahtar" class="kr-lejant-oge" :data-kr-lejant="l.anahtar"
            :data-durum="l.durum">
          <svg class="kr-ornek" viewBox="0 0 30 8" aria-hidden="true"><line x1="1" y1="4" x2="29" y2="4"
            :stroke="l.renk" stroke-width="2.5" :stroke-dasharray="l.desen"></line></svg>
          <span class="kr-lejant-ad">{{ l.ad }}</span>
          <span class="kr-lejant-tur">{{ l.tur }}</span>
          <span v-if="l.not" class="kr-lejant-not" :class="{ 'kr-disari': l.durum !== 'ici' }">{{ l.not }}</span>
        </li>
      </ul>
      <p v-if="yukleniyor" class="ipucu">{{ m.yukleniyor }}</p>
      <p v-else-if="!grafikVar" class="ipucu kr-cizilecek-yok" data-kr="cizilecek-yok">{{ m.cizilecekYok }}</p>
      <div class="kg-tuval" v-show="grafikVar" :data-pencere="pencereJson">
        <canvas ref="tuval" class="kr-grafik" role="img" :aria-label="grafikEtiket"></canvas>
      </div>
      <canvas ref="gezgin" v-show="grafikVar" class="kg-gezgin" role="img" :aria-label="m.gezginEtiket"></canvas>
      <p class="ipucu">{{ m.grafikIpucu }}</p>
    </section>

    <section class="kart">
      <h2>{{ m.okuma }}</h2>
      <!-- WIG: tablo canli bolge DEGIL (her imlec adiminda onlarca hucre); ~300 ms durulunca ozet -->
      <p class="gorunmez" aria-live="polite">{{ duyuru }}</p>
      <div class="kr-okuma" :data-okuma="okumaMetni">
        <template v-if="okuma">
          <p class="kr-imlecler">A {{ an(okuma.tA) }} · B {{ an(okuma.tB) }}<template v-if="Number.isFinite(okuma.dt)"> · Δ {{ dtYazi }}</template></p>
          <div class="kg-tablo-sarmal">
            <table class="kg-tablo kr-tablo">
              <caption class="gorunmez">{{ m.tabloBaslik }}</caption>
              <thead><tr>
                <th scope="col">{{ m.kayit }}</th><th scope="col">A</th><th scope="col">B</th>
                <th scope="col">{{ m.fark }}</th><th scope="col">{{ m.ort }}</th>
                <th scope="col" v-if="rota.kip !== 'mah'">{{ m.mah }}</th><th scope="col" v-if="rota.kip !== 'mah'">{{ m.wh }}</th>
              </tr></thead>
              <tbody>
                <tr v-for="r in okumaSatirlari" :key="r.anahtar" :data-kr-okuma="r.anahtar">
                  <th scope="row"><svg class="kr-ornek" viewBox="0 0 30 8" aria-hidden="true"><line x1="1" y1="4" x2="29" y2="4"
                    :stroke="r.renk" stroke-width="2.5" :stroke-dasharray="r.desen"></line></svg> {{ r.ad }}</th>
                  <td>{{ r.a }}</td><td>{{ r.b }}</td><td>{{ r.fark }}</td><td>{{ r.ort }}</td>
                  <td v-if="rota.kip !== 'mah'">{{ r.mah }}</td><td v-if="rota.kip !== 'mah'">{{ r.wh }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="okumaDisarida" class="ipucu" data-kr="imlec-disarida">{{ m.imlecDisarida }}</p>
        </template>
        <p v-else class="ipucu">{{ m.imlecYok }}</p>
      </div>
    </section>

    <section class="kart">
      <h2>{{ m.disariBaslik }}</h2>
      <div class="dugme-grup">
        <button type="button" data-kr-disari="tr" @click="indir('tr')" :disabled="!grafikVar">{{ m.csvTr }}</button>
        <button type="button" data-kr-disari="en" @click="indir('en')" :disabled="!grafikVar">{{ m.csvEn }}</button>
      </div>
      <p class="ipucu">{{ m.disariIpucu }}</p>
      <p v-if="hata" class="hata" role="alert">{{ hata }}</p>
    </section>
  </template>
</div>`;

const vueAl = () => globalThis.Vue;

export const KarsilastirEkrani = {
  name: 'KarsilastirEkrani',
  props: {
    kartAdres: { type: Function, required: true },
    etkin: { type: Boolean, default: true },
    dilSecim: { type: String, default: null },     // 3H (AY3): kabugun secili dili
  },
  template: SABLON,
  data() {
    return {
      rota: karsilastirRotaCoz(globalThis.location ? globalThis.location.hash : ''),
      dil: this.dilSecim === 'en' || this.dilSecim === 'tr' ? this.dilSecim : dilOku(), yukleniyor: false, depoHata: '', lejantVeri: [], renkler: [],
      okuma: null, pencereJson: '', duyuru: '', hata: '', grafikVar: false,
    };
  },
  created() {
    this._den = new EsitlemeDenetcisi({ kartAdres: this.kartAdres });
    this._girdiler = [];
    this._hOnbellek = new Map();        // `${kimlik}:${no}:${bayt}` -> grafikSerileri
    this._kipOnbellek = new Map();      // + kip + kanal -> {ks, hazir}
    this._cizilen = [];                 // [{g, ks}] bu kipte cizilenler
    this._g = null;
    this._gz = null;
    this._nesil = 0;
    this._sonImlec = '';
  },
  computed: {
    m() { return metinler(KR_METIN, this.dil); },
    kipSecim: {
      get() { return this.rota.kip; },
      set(v) { this.rotaGuncelle({ kip: v }); },
    },
    kanalSecim: {
      get() { return this.rota.kanal; },
      set(v) { this.rotaGuncelle({ kanal: v }); },
    },
    kipAdi() {
      return this.m[{ baslangic: 'kipBaslangic', saat: 'kipSaat', mah: 'kipMah' }[this.rota.kip]];
    },
    kanalAdi() { return ceviri((KANALLAR[this.rota.kanal] || KANALLAR.V).ad, this.dil); },
    baslikAlt() {
      return ceviri('kr.alt_baslik', this.dil, { n: this.rota.secim.length, kanal: this.kanalAdi, kip: this.kipAdi });
    },
    grafikEtiket() { return ceviri('kr.grafik_etiket', this.dil, { kanal: this.kanalAdi, kip: this.kipAdi }); },
    uyarilar() {
      const u = [];
      if (this.rota.fazla) u.push(ceviri('kr.fazla', this.dil, { n: this.rota.fazla }));
      if (this.rota.gecersiz) u.push(ceviri('kr.gecersiz', this.dil, { n: this.rota.gecersiz }));
      if (this.depoHata) u.push(ceviri('kr.depo_hata', this.dil, { mesaj: this.depoHata }));
      return u;
    },
    lejant() {
      return this.lejantVeri.map((l) => ({ ...l, renk: this.renkler[l.pos] || '',
        desen: KR_RENKLER[l.pos].desen ? KR_RENKLER[l.pos].desen.join(' ') : null }));
    },
    okumaMetni() { return this.okuma ? okumaJson(this.okuma) : ''; },
    dtYazi() {
      const o = this.okuma;
      if (!o || !Number.isFinite(o.dt)) return '';
      return this.rota.kip === 'mah' ? o.dt.toFixed(3) + ' mAh' : sureYaz(o.dt);
    },
    okumaSatirlari() {
      const o = this.okuma;
      if (!o) return [];
      const k = KANALLAR[this.rota.kanal] || KANALLAR.V;
      const f = (v, hane, birim) => (Number.isFinite(v) ? sayiGoster(v, hane) + ' ' + birim : '—');
      return o.kayitlar.map((r) => {
        const l = this.lejant.find((x) => x.anahtar === r.anahtar) || {};
        return { anahtar: r.anahtar, ad: l.ad, renk: l.renk, desen: l.desen,
          a: f(r.a, k.hane, k.birim), b: f(r.b, k.hane, k.birim), fark: f(r.fark, k.hane, k.birim),
          ort: f(r.ort, k.hane, k.birim), mah: f(r.mah, 4, 'mAh'), wh: f(r.wh, 6, 'Wh') };
      });
    },
    okumaDisarida() {
      return !!this.okuma && this.okuma.kayitlar.some((r) => (Number.isFinite(this.okuma.tA) && !r.aIcinde)
        || (Number.isFinite(this.okuma.tB) && !r.bIcinde));
    },
  },
  watch: {
    etkin(v) {
      if (!v) return;
      this.renklerOku();
      this.yukle();
    },
    /* 3H (AY3): dil degisti — lejant / sebepler kurulurken yaziliyor: yeniden kur. */
    dilSecim(v) {
      if (v !== 'tr' && v !== 'en') return;
      this.dil = v;
      this.kur();
    },
  },
  mounted() {
    this._hash = () => {
      if (!/^#\/?karsilastir(?:[/?]|$)/.test(location.hash)) return;   // baska ekrana gidildi
      this.rota = karsilastirRotaCoz(location.hash);
      this.yukle();
    };
    window.addEventListener('hashchange', this._hash);
    /* Gorunum degisince tuval bit eslem: renkler yeniden okunup cizilir (kayit_gorunum deseni). */
    this._gozcu = new MutationObserver(() => { this.renklerOku(); this.ciz(); });
    this._gozcu.observe(document.documentElement, { attributes: true, attributeFilter: ['data-tema'] });
    this._boyut = () => this.ciz();
    window.addEventListener('resize', this._boyut);
    this.renklerOku();
    if (this.etkin) this.yukle();
  },
  beforeUnmount() {
    window.removeEventListener('hashchange', this._hash);
    window.removeEventListener('resize', this._boyut);
    if (this._gozcu) this._gozcu.disconnect();
    if (this._duyuruZaman) clearTimeout(this._duyuruZaman);
    this.grafikYokEt();
  },
  methods: {
    an(x) { return anYazi(x, this.rota.kip); },
    renklerOku() {
      if (typeof document === 'undefined') return;
      const cs = cssRenk(document.documentElement, window);
      this.renkler = KR_RENKLER.map((_, k) => krRenk(k, cs));
    },
    /** KU2: kip / kanal adreste — replaceState (gecmise girdi eklemez; geri tusu ekrandan cikar). */
    rotaGuncelle(parca) {
      const yeni = { ...this.rota, ...parca };
      this.rota = yeni;
      try { history.replaceState(null, '', karsilastirRotaYaz(yeni)); } catch (e) { /* file:// */ }
      this.kur();
    },
    /** KR5: secimi bu tarayicinin kopyasindan oku. @kimlik yoksa oturumu TASIYAN en yeni akis (3E S4). */
    async yukle() {
      const nesil = ++this._nesil;
      const r = this.rota;
      if (!r.secim.length) {
        this._girdiler = [];
        this.lejantVeri = [];
        this.okuma = null;
        this.grafikVar = false;
        this.grafikYokEt();
        this.odakla();
        return;
      }
      this.yukleniyor = true;
      this.depoHata = '';
      let akislar = [];
      const veri = new Map();
      try {
        akislar = [...await this._den.akislar()].sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
      } catch (h) {
        this.depoHata = (h && h.message) || String(h);
      }
      const al = async (k) => {
        if (!veri.has(k)) {
          try {
            veri.set(k, await this._den.akisVerisi(k));
          } catch (h) {
            veri.set(k, null);
            this.depoHata = (h && h.message) || String(h);
          }
        }
        return veri.get(k);
      };
      const girdiler = [];
      for (const [pos, s] of r.secim.entries()) {
        const adaylar = akislar.map((a) => a.kimlik).filter((k) => s.kimlik === null || k === s.kimlik);
        let bulunan = null;
        for (const k of adaylar) {
          const v = await al(k);
          const o = v && v.oturumlar ? v.oturumlar.get(s.oturum) : null;
          if (o) { bulunan = { v, o }; break; }
        }
        if (nesil !== this._nesil) return;
        const kimlik = bulunan ? bulunan.v.kimlik : s.kimlik;
        const g = { pos, no: s.oturum, kimlik, anahtar: `${kimlik === null ? '?' : kimlik}:${s.oturum}`,
          durum: 'yok', o: null, tur: 'bilinmeyen', h: null, bayt: 0,
          kimlikGoster: kimlik !== null && akislar.length > 1 && kimlik !== akislar[0].kimlik };
        if (bulunan) {
          g.o = bulunan.o;
          g.tur = oturumTuru(bulunan.o);
          g.bayt = bulunan.v.bayt;
          if (KR_TURLER.includes(g.tur)) {
            const ha = `${kimlik}:${s.oturum}:${g.bayt}`;
            if (!this._hOnbellek.has(ha)) this._hOnbellek.set(ha, grafikSerileri(bulunan.o, { kayitlar: bulunan.v.kayitlar }));
            g.h = this._hOnbellek.get(ha);
          }
          g.durum = g.h && g.h.tur !== 'yok' && g.h.adet > 0 ? 'tamam' : 'bos';
        }
        girdiler.push(g);
      }
      if (nesil !== this._nesil) return;
      this._girdiler = vueAl().markRaw(girdiler);
      this.yukleniyor = false;
      this.kur();
      this.odakla();
    },
    /** Kaydin bu kip + kanaldaki serisi (onbellekli; piramit bir kez kurulur). */
    kipSerisiAl(g) {
      const { kip, kanal } = this.rota;
      const a = `${g.anahtar}:${g.bayt}:${kip}:${kanal}`;
      let c = this._kipOnbellek.get(a);
      if (!c) {
        const ks = kipSerisi(g.h, { kip, kanal, tur: g.tur });
        const k = KANALLAR[kanal] || KANALLAR.V;
        c = { ks, hazir: ks.sebep ? null : seriHazirla({ ad: 'K' + g.pos, t: ks.x, y: ks.y, birim: k.birim,
          renk: 'kr' + g.pos, eksen: 'sol', boslukMs: ks.boslukMs, enAzAralik: k.enAz,
          ...(KR_RENKLER[g.pos].desen ? { desen: KR_RENKLER[g.pos].desen } : {}) }) };
        this._kipOnbellek.set(a, vueAl().markRaw(c));
      }
      return c;
    },
    /** Lejant + cizilecek seriler (KR2/KR3); grafik bir sonraki karede. */
    kur() {
      const lejant = [];
      const cizilen = [];
      const turAd = (t) => ceviri(TUR_METIN[t] || TUR_METIN.bilinmeyen, this.dil);
      for (const g of this._girdiler) {
        const ad = (g.o && g.o.ad ? `${g.o.ad} #${g.no}` : `${turAd(g.tur)} #${g.no}`) + (g.kimlikGoster ? ' @' + g.kimlik : '');
        const l = { anahtar: g.anahtar, pos: g.pos, ad, tur: turAd(g.tur), durum: 'ici', not: '' };
        if (g.durum === 'yok') { l.durum = 'yok'; l.not = this.m.yok; l.tur = ''; }
        else if (g.durum === 'bos') { l.durum = 'bos'; l.not = this.m.bosKayit; }
        else {
          const c = this.kipSerisiAl(g);
          if (c.ks.sebep) {
            l.durum = 'disari';
            l.not = ceviri('kr.disari', this.dil, { sebep: ceviri(c.ks.sebep, this.dil, c.ks.d) });
          } else {
            cizilen.push({ g, ks: c.ks, hazir: c.hazir });
            if (this.rota.kip === 'mah') l.not = ceviri('kr.mah_son', this.dil, { mah: sayiGoster(c.ks.mahSon, 3) });
            else if (c.ks.tahmini) l.not = this.m.tahmini;
          }
        }
        lejant.push(l);
      }
      this._cizilen = vueAl().markRaw(cizilen);
      this.lejantVeri = lejant;
      this.grafikVar = cizilen.length > 0;
      this.okuma = null;
      this._sonImlec = '';
      this.$nextTick(() => this.grafikGuncelle());
    },
    renkCozucu(tuval) {
      const cs = cssRenk(tuval, window);
      return (ad) => {
        if (ad === 'imlec') return cs('yazi');                         // K5
        const m = /^kr(\d)$/.exec(ad);
        return m ? krRenk(Number(m[1]), cs) : cs(ad);
      };
    },
    grafikYokEt() {
      if (this._g) this._g.yokEt();
      if (this._gz) this._gz.yokEt();
      this._g = null;
      this._gz = null;
    },
    /** Grafigi (gerekirse yeniden: v-if tuvali degistirdiyse) kur ve seriyi yukle. */
    grafikGuncelle() {
      const t = this.$refs.tuval;
      const gz = this.$refs.gezgin;
      if (!t || !gz) return;
      const { markRaw } = vueAl();
      if (!this._g || this._g.canvas !== t) {
        this.grafikYokEt();
        this._g = markRaw(new Grafik(t, { renk: this.renkCozucu(t), zamanKokeni: 0,
          onDegisim: (d) => this.degisti(d) }));
        this._gz = markRaw(new Grafik(gz, { gezgin: true, renk: this.renkCozucu(gz),
          onDegisim: (d) => { if (this._g) this._g.durumAyarla({ t0: d.t0, t1: d.t1 }); this.pencereYaz(); } }));
      }
      const seriler = this._cizilen.map((c) => c.hazir);
      const kip = this.rota.kip;
      const sec = this._g.secenek;
      if (kip === 'saat' && seriler.length) {
        const koken = geceYarisi(Math.min(...seriler.map((s) => s.t[0])));
        sec.zamanKokeni = koken;
        sec.xEksen = { tur: 'zaman', yazi: (v, adim) => saatYazi(v + koken, adim) };
      } else if (kip === 'mah') {
        sec.zamanKokeni = 0;
        sec.xEksen = { tur: 'sayi', yazi: mahYazi };
      } else {
        sec.zamanKokeni = 0;
        sec.xEksen = undefined;
      }
      this._g.veriAyarla(seriler);
      this._gz.veriAyarla(seriler);
      this._gz.durumAyarla({ t0: this._g.durum.t0, t1: this._g.durum.t1 });
      this.ciz();
    },
    degisti(d) {
      if (this._gz) this._gz.durumAyarla({ t0: d.t0, t1: d.t1 });
      const A = d.imlecA;
      const B = d.imlecB;
      const anahtar = `${A}|${B}`;
      if (anahtar !== this._sonImlec) {            // kaydirma/yakinlastirmada yeniden hesap yok
        this._sonImlec = anahtar;
        this.okuma = Number.isFinite(A) || Number.isFinite(B) ? this.okumaKur(A, B) : null;
        this.duyuruZamanla();
      }
      this.pencereYaz();
    },
    /** KR4: her cizilen kayit icin AYRI okuma (kayitOkuma). */
    okumaKur(A, B) {
      const { kip, kanal } = this.rota;
      const tA = Number.isFinite(A) ? A : NaN;
      const tB = Number.isFinite(B) ? B : NaN;
      return {
        kip, kanal, tA, tB, dt: Number.isFinite(tA) && Number.isFinite(tB) ? tB - tA : NaN,
        kayitlar: this._cizilen.map(({ g, ks }) => ({ anahtar: g.anahtar, no: g.no, ...kayitOkuma(ks, tA, tB, { kip, kanal }) })),
      };
    },
    /** WIG: okuma ~300 ms durulunca TEK satir (ilk iki kaydin A/B'si). */
    duyuruZamanla() {
      if (this._duyuruZaman) clearTimeout(this._duyuruZaman);
      this._duyuruZaman = setTimeout(() => {
        this.duyuru = this.okumaSatirlari.slice(0, 2).map((r) => ceviri('kr.duyuru', this.dil,
          { kayit: r.ad, a: r.a, b: r.b })).join(' · ');
      }, 300);
    },
    pencereYaz() {
      if (!this._g) return;
      const d = this._g.durum;
      const c = this.$refs.tuval;
      if (!c) return;
      const alan = yerlesim(this._g.seriler, { w: c.clientWidth, h: c.clientHeight });
      this.pencereJson = JSON.stringify({ kip: this.rota.kip, t0: d.t0, t1: d.t1, veriT0: d.veriT0, veriT1: d.veriT1,
        imlecA: d.imlecA, imlecB: d.imlecB, alanX: alan.x, alanW: alan.w });
    },
    ciz() {
      if (this._g) this._g.ciz();
      if (this._gz) this._gz.ciz();
      this.pencereYaz();
    },
    tumunuGoster() {
      if (!this._g) return;
      const d = this._g.durum;
      this._g.durumAyarla({ t0: d.veriT0, t1: d.veriT1 });
      this.degisti(this._g.durum);
    },
    imlecTemizle() {
      if (!this._g) return;
      this._g.durumAyarla({ imlecA: null, imlecB: null });
      this.degisti(this._g.durum);
    },
    /** WIG: ekran acilinca / secim degisince odak basliga (klavye kullanicisi sayfa basina atilmaz). */
    odakla() {
      if (!this.etkin) return;
      this.$nextTick(() => {
        const b = this.$refs.baslik;
        if (b && typeof b.focus === 'function') b.focus({ preventScroll: true });
      });
    },
    /** KR7: birlesik CSV (yalniz bu kipte cizilen kayitlar). */
    indir(dil) {
      this.hata = '';
      const { kip, kanal } = this.rota;
      let bayt;
      try {
        const girdiler = this._cizilen.map(({ g, ks }) => ({ no: g.no, kimlik: g.kimlik, ayrinti: g.h.tur === 'ayrinti',
          x: ks.x, y: ks.y }));
        bayt = csvBayt(birlesikCsv(girdiler, { kip, kanal, bicim: dil === 'en' ? BICIM_EN : BICIM_EXCEL_TR }));
      } catch (h) {
        this.hata = this.m.disariHata + ' ' + ((h && h.message) || h);
        return;
      }
      const url = URL.createObjectURL(new Blob([bayt], { type: 'text/csv;charset=utf-8' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = karsilastirDosyaAdi(kip, kanal, dil);
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    },
  },
};
