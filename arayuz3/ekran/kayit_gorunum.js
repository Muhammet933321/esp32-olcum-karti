/* ═══════════════════════════════════════════════════════════════════════
   3C — KAYIT GORUNUMU                            (ekran/kayit_gorunum.js)

   Tek oturumun ekrani (karar C5): grafik (ortak/src/grafik.js) V · I · W,
   iki imlec + okuma, notlar, pil olaylari, osiloskop yakalama TABLOSU,
   disa aktarma (C6) ve yazdirilabilir rapor. Hesap HEP ortak/'ta (tek
   kopya, §9): zaman ekseni `disari.zamanEkseni`, seriler `noktaSerileri`
   / `ayrintiSerileri`, imlec `imlecOkuma`, rapor `oturumRaporu`.
   Veri YALNIZ bu tarayicidaki kopyadan (C5); kartta olup esitlenmemis
   oturumu `kayitlar.js` "once esitle" diye karsilar.

   KARARLAR (C1–C8 disinda, gerekce yaninda):
   K1 X EKSENI = oturum baslangicindan gecen ms (`gecen_ms`, saat yoksa da
      bilinir: BASLA'ya gore). Yeniden baslamadan sonraki parcanin
      baslangica uzakligi bilinmiyorsa (iki capadan biri saatsiz) parca
      oncekinin ARDINA, arada 3 x bosluk esigiyle konur ve ekranda
      "konumu tahmini" diye yazar — zaman uydurulmaz, gorunur kilinir.
   K2 Nokta oturumunda her kanalin ort cizgisi + ince min/maks cizgileri
      (zarf): Ö1 — tek orneklik sicrama ortalamada erir, min/maks'ta kalir.
      Okumanin min/maks'i da min/maks KODLARINDAN (rapor.js ile ayni kural).
   K3 Okumanin mAh / Wh'si ACILIS BASINA (DEVAM sinirinin ustunden integral
      yok) ve nokta oturumunda Wh KARTIN W'sinden (ort V x ort A degil) —
      rapor.js / pilCsv ile ayni kural; tam aralikta rapor enerjisiyle
      ayni sayi (B7 sinar). Degerler ve aralik istatistigi `imlecOkuma`.
   K3b (W1) Ayrintili oturumda W ve Wh HIZALI gucten (kayit.js ayrintiGuc:
      V akim ornegi anina tasinir) — ayni ornegin V x I'si degil; rapor ile ayni.
   K3c (W1/Y7) Osiloskop yakalamalari grafikte kesik dikey isaret "S<no>"
      (grafik.js `isaretler`): x = META t_ms, yakalamanin KENDI acilisinda
      (kayit sirasi zaman sirasi degil; `yakalamaIsaretleri`).
   K4 Sag eksen tek birim: Akim YA DA Guc (secilir). Iki farkli birimi tek
      eksene koymak eksen yazisini yalanci yapardi.
   K5 Imlec rengi temanin YAZI rengi (`--yazi`): uc gorunumde de zemine
      karsi en yuksek karsitlik ve uc kanal renginden ayri. grafik.js'in
      `imlec` yedegi sabit bir renk; burada belirtece baglaniyor.
   K6 Rapor yazdirilirken (beforeprint) gecici olarak ACIK gorunum: koyu
      zemin kagida basilmaz, koyu temanin acik yazisi beyaz kagitta okunmaz.
      Yeni renk TANIMLANMIYOR — mevcut Acik takim kullaniliyor; afterprint
      eski gorunumu geri koyar (localStorage'a dokunulmaz).
   ═══════════════════════════════════════════════════════════════════════ */

import { Grafik, imlecOkuma, zamanYazi, cssRenk, yerlesim, seriHazirla, yOlcekNormal, yOlcekEksen }
  from '/ortak/grafik.js';
import { enerji } from '/ortak/istatistik.js';
import {
  zamanEkseni, noktaSerileri, ayrintiSerileri, anZamani, noktaBoslukMs, AYRINTI_BOSLUK_MS,
  oturumCsv, ayrintiCsv, pilCsv, skopCsv, hamDisari, csvBayt, BICIM_EXCEL_TR, BICIM_EN,
} from '/ortak/disari.js';
import { oturumRaporu, RAPOR_ETIKET } from '/ortak/rapor.js';
import { ceviriKod } from '/ortak/sozluk.js';
/* W3 (EU32): kl./kg./kr. metinleri acilis sozlugunde DEGIL — bu zincirle iner (sozluk_kayit.js; yoksa sozluk.js) */
import { ceviriKayit as ceviri } from '/ortak/sozluk_kayit.js';
import { ceviriPc } from '/ortak/sozluk_pc.js';
import { OTURUM_OLCUM, OTURUM_PIL, OTURUM_SKOP, skopYerleri } from '/ortak/kayit.js';

/* ── SAF yardimcilar (B7 node'da sinar) ─────────────────────────────── */

/** Oturumun ekran turu: olcum · ayrinti · pil · skop · bilinmeyen. */
export function oturumTuru(o) {
  const t = o.basla ? o.basla.oturum_turu : 0;
  const ayr = o.ayrinti.length > 0 && o.noktalar.length === 0;
  if (t === OTURUM_PIL) return 'pil';
  if (t === OTURUM_SKOP) return 'skop';
  if (t === OTURUM_OLCUM) return ayr ? 'ayrinti' : 'olcum';
  if (ayr) return 'ayrinti';
  if (o.noktalar.length) return 'olcum';
  if (o.skoplar.size) return 'skop';
  return 'bilinmeyen';
}

/** Acilis basina [bas, son) indis araliklari (satirlar acilis sirasinda bitisik). */
export function acilisParcalari(acilis) {
  const p = [];
  let bas = 0;
  for (let k = 1; k <= acilis.length; k++) {
    if (k === acilis.length || acilis[k] !== acilis[bas]) {
      p.push([bas, k]);
      bas = k;
    }
  }
  return p;
}

/**
 * K1: grafigin x ekseni (ms, oturum baslangicindan). segOfset[acilis] = o acilisin
 * capasinin x'i; bilinmeyen ya da geriye dusen parca oncekinin ardina (tahmini).
 * Donus {t: Float64Array, segOfset, tahmini: [acilis], duzeltilen}.
 */
export function xEkseni(acilis, relMs, araliklar, eksen, boslukMs) {
  const ara = Number.isFinite(boslukMs) ? 3 * boslukMs : 60000;
  const segOfset = [];
  const tahmini = [];
  let onceSon = -Infinity;
  eksen.segmentler.forEach((sg, s) => {
    const a = araliklar[s];
    let o = sg.ofsetMs;
    if (!a) {
      segOfset[s] = o;
      return;
    }
    if (o === null || o + a[0] < onceSon) {
      o = (onceSon === -Infinity ? 0 : onceSon + ara) - a[0];
      tahmini.push(s);
    }
    segOfset[s] = o;
    onceSon = o + a[1];
  });
  const n = relMs.length;
  const t = new Float64Array(n);
  let duzeltilen = 0;
  for (let k = 0; k < n; k++) {
    let x = segOfset[acilis[k]] + relMs[k];
    if (k && x < t[k - 1]) { x = t[k - 1]; duzeltilen++; }      // grafik/istatistik azalmayan t ister
    t[k] = x;
  }
  return { t, segOfset, tahmini, duzeltilen };
}

/**
 * Grafik serileri (K1, K2). Donus {tur: 'nokta'|'ayrinti'|'yok', seriler, t, eksen,
 * araliklar, acilis, segOfset, tahmini, boslukMs, adet, s (ortak seriler), birler}.
 * Her seri ayni `t` dizisini paylasir (imlecOkuma'nin enerji kosulu).
 */
export function grafikSerileri(oturum, { kayitlar = null } = {}) {
  const eksen = zamanEkseni(oturum, kayitlar);
  const ayr = oturum.ayrinti.length > 0 && oturum.noktalar.length === 0;
  if (!ayr && !oturum.noktalar.length) {
    return { tur: 'yok', seriler: [], eksen, araliklar: [], acilis: [], segOfset: [0], tahmini: [], adet: 0 };
  }
  const s = ayr ? ayrintiSerileri(oturum, { eksen }) : noktaSerileri(oturum, { eksen });
  const boslukMs = ayr ? AYRINTI_BOSLUK_MS : noktaBoslukMs(oturum);
  const x = xEkseni(s.acilis, s.relMs, s.araliklar, eksen, boslukMs);
  const t = x.t;
  const kanal = (ad, y, birim, renk, eksenAd, enAz, zarf = false) => ({
    ad, t, y, birim, renk, eksen: eksenAd, boslukMs, enAzAralik: enAz,
    ...(zarf ? { zarf: true, kalinlik: 0.75 } : {}),
  });
  let seriler;
  if (ayr) {
    seriler = [kanal('V', s.v, 'V', 'volt', 'sol', 0.01), kanal('I', s.i, 'A', 'amper', 'sag', 0.001),
      kanal('W', s.w, 'W', 'watt', 'sag', 0.01)];
  } else {
    seriler = [
      kanal('V', s.vOrt, 'V', 'volt', 'sol', 0.01), kanal('V min', s.vMin, 'V', 'volt', 'sol', 0.01, true),
      kanal('V maks', s.vMaks, 'V', 'volt', 'sol', 0.01, true),
      kanal('I', s.iOrt, 'A', 'amper', 'sag', 0.001), kanal('I min', s.iMin, 'A', 'amper', 'sag', 0.001, true),
      kanal('I maks', s.iMaks, 'A', 'amper', 'sag', 0.001, true),
      kanal('W', s.wOrt, 'W', 'watt', 'sag', 0.01), kanal('W min', s.wMin, 'W', 'watt', 'sag', 0.01, true),
      kanal('W maks', s.wMaks, 'W', 'watt', 'sag', 0.01, true),
    ];
  }
  return { tur: ayr ? 'ayrinti' : 'nokta', seriler, t, eksen, araliklar: s.araliklar, acilis: s.acilis,
    segOfset: x.segOfset, tahmini: x.tahmini, duzeltilen: x.duzeltilen, boslukMs, adet: s.adet, s,
    birler: new Float64Array(s.adet).fill(1) };
}

/** K4 gorunurluk: V (sol), sag eksen 'akim' | 'guc' | 'yok', zarf (min/maks). */
export function gorunurluk(seriler, { v = true, sag = 'akim', zarf = true } = {}) {
  return seriler.map((s) => {
    const kok = s.ad.split(' ')[0];
    let gizli = kok === 'V' ? !v : kok === 'I' ? sag !== 'akim' : kok === 'W' ? sag !== 'guc' : false;
    if (s.zarf && !zarf) gizli = true;
    return { ...s, gizli };
  });
}

/** K3: [tA, tB] araliginda mAh / Wh, ACILIS BASINA (rapor.js ile ayni kural). */
export function aralikEnerji(h, tA, tB) {
  if (!h || h.tur === 'yok' || !Number.isFinite(tA) || !Number.isFinite(tB)) return null;
  if (tA > tB) [tA, tB] = [tB, tA];
  let wh = 0;
  let mah = 0;
  let sureS = 0;
  const kip = { boslukMs: h.boslukMs };
  for (const [p, q] of acilisParcalari(h.acilis)) {
    const t = h.t.subarray(p, q);
    if (h.tur === 'nokta') {
      const ew = enerji(t, h.s.wOrt.subarray(p, q), h.birler.subarray(p, q), tA, tB, kip);
      const ei = enerji(t, h.s.vOrt.subarray(p, q), h.s.iOrt.subarray(p, q), tA, tB, kip);
      wh += ew.wh;
      mah += ei.mah;
      sureS += ew.sureS;
    } else {
      const ew = enerji(t, h.s.w.subarray(p, q), h.birler.subarray(p, q), tA, tB, kip);   // K3b: hizali W
      const ei = enerji(t, h.s.v.subarray(p, q), h.s.i.subarray(p, q), tA, tB, kip);
      wh += ew.wh;
      mah += ei.mah;
      sureS += ei.sureS;
    }
  }
  return { wh, mah, sureS };
}

/** Imlec okumasi: degerler + aralik istatistigi imlecOkuma'dan, enerji K3. */
export function okumaHesapla(h, tA, tB) {
  if (!h || h.tur === 'yok') return null;
  const ok = imlecOkuma(h.seriler, tA, tB, { gerilim: 'V', akim: 'I' });
  const bul = (ad) => ok.kanallar.find((k) => k.ad === ad) || null;
  const kanal = (ad) => {
    const o = bul(ad);
    if (!o) return null;
    const mn = bul(ad + ' min');
    const mx = bul(ad + ' maks');
    const ist = o.istat;
    return {
      ad, birim: o.birim, a: o.a ? o.a.deger : NaN, b: o.b ? o.b.deger : NaN, fark: o.fark,
      tA: o.a ? o.a.t : NaN, tB: o.b ? o.b.t : NaN,
      adet: ist ? ist.adet : 0, ort: ist ? ist.ort : NaN, rms: ist ? ist.rms : NaN,
      min: mn && mn.istat ? mn.istat.min : ist ? ist.min : NaN,
      maks: mx && mx.istat ? mx.istat.maks : ist ? ist.maks : NaN,
    };
  };
  return { tA: ok.tA, tB: ok.tB, dt: ok.dt, v: kanal('V'), i: kanal('I'), w: kanal('W'),
    dV: ok.dV, ortI: ok.ortI, enerji: aralikEnerji(h, ok.tA, ok.tB) };
}

/** K3c (W1/Y7): yakalama isaretleri [{t, metin: 'S<no>'}], ZAMAN sirasiyla (kayit.js
 *  skopYerleri); x = yakalamanin acilisinin grafik ofseti + t_ms'nin capaya farki. Acilisi
 *  grafikte olmayan (o acilista olcum verisi yok) yakalama atlanir. */
export function yakalamaIsaretleri(oturum, h) {
  if (!h || h.tur === 'yok') return [];
  const l = [];
  for (const y of h.s && h.s.yerler ? h.s.yerler : skopYerleri(oturum)) {   // W1: seriler hesapladi
    const z = anZamani(h.eksen, h.araliklar, y.t_ms, y.sira, y.acilis);
    const o = z.acilis === null ? undefined : h.segOfset[z.acilis];
    if (o === null || o === undefined || z.relMs === null) continue;
    l.push({ t: o + z.relMs, metin: 'S' + y.no });
  }
  return l;
}

/** Notlar, kayit sirasiyla: {sira, metin, genel, x (grafikte) | null, gecenMs | null}. */
export function notListesi(oturum, h) {
  return [...oturum.notlar.entries()].sort((a, b) => a[0] - b[0]).map(([sira, n]) => {
    if (!n.nokta_ms) return { sira, metin: n.metin, genel: true, x: null, gecenMs: null };
    const z = anZamani(h.eksen, h.araliklar, n.nokta_ms, null);
    const o = z.acilis === null ? null : h.segOfset[z.acilis];
    return { sira, metin: n.metin, genel: false, x: o === null || o === undefined ? null : o + z.relMs,
      gecenMs: z.gecenMs };
  });
}

/** Notun anina git: pencere ona ortalanir; butun veri gorunuyorsa onda bire daralir. */
export function notPenceresi(durum, x) {
  const tam = durum.veriT1 - durum.veriT0;
  let g = durum.t1 - durum.t0;
  if (g >= tam * 0.999) g = tam / 10;
  return { t0: x - g / 2, t1: x + g / 2 };
}

/** ASCII dosya adi parcasi (Turkce harfler sadelesir). */
export function sadeAd(s) {
  return String(s || '').toLocaleLowerCase('tr-TR')
    .replace(/ı/g, 'i')                    // noktasiz i NFD ile AYRISMAZ; c g o s u isaretleri asagida duser
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
}

/** Disa aktarma dosyasinin adi: kayit-<no>[-<ad>][-<ek>].<uzanti> */
export function dosyaAdi(oturum, ek, uzanti) {
  const ad = sadeAd(oturum.ad);
  return `kayit-${oturum.id}${ad ? '-' + ad : ''}${ek ? '-' + ek : ''}.${uzanti}`;
}

/** 3E (OS6): yakalamayi osiloskopta acan adres `#/skop/kayit/<oturum>/<sira>[@kimlik]`
 *  (sira = yakalamanin 0. parcasinin kayit sirasi, oturum.skoplar anahtari). Cozucusu
 *  ekran/osiloskop.js skopRotaCoz — B7 ikisinin birbirinin tersi oldugunu sinar. */
export function skopRotaYaz({ oturum, sira, kimlik = null } = {}) {
  return `#/skop/kayit/${oturum}/${sira}${kimlik === null || kimlik === undefined ? '' : '@' + kimlik}`;
}

/** Oturuma uygun disa aktarma turleri (C6). */
export function disariTurleri(oturum) {
  const tur = oturumTuru(oturum);
  const d = [];
  if (tur === 'olcum') d.push('csv_tr', 'csv_en');
  if (tur === 'ayrinti') d.push('ayrinti_tr', 'ayrinti_en');
  if (tur === 'pil') d.push('pil_tr', 'pil_en');
  d.push('ham');
  return d;
}

const CSV = 'text/csv;charset=utf-8';

/** Disa aktarma: {ad, mime, bayt}. skop icin `yakalama` (oturum.skoplar degeri) verilir. */
export function disariUret(tur, oturum, kayitlar, yakalama = null) {
  const s = (bicim) => ({ ...bicim, kayitlar });
  switch (tur) {
    case 'csv_tr': return { ad: dosyaAdi(oturum, '', 'csv'), mime: CSV, bayt: csvBayt(oturumCsv(oturum, s(BICIM_EXCEL_TR))) };
    case 'csv_en': return { ad: dosyaAdi(oturum, 'en', 'csv'), mime: CSV, bayt: csvBayt(oturumCsv(oturum, s(BICIM_EN))) };
    case 'ayrinti_tr': return { ad: dosyaAdi(oturum, 'ayrintili', 'csv'), mime: CSV, bayt: csvBayt(ayrintiCsv(oturum, s(BICIM_EXCEL_TR))) };
    case 'ayrinti_en': return { ad: dosyaAdi(oturum, 'ayrintili-en', 'csv'), mime: CSV, bayt: csvBayt(ayrintiCsv(oturum, s(BICIM_EN))) };
    case 'pil_tr': return { ad: dosyaAdi(oturum, 'pil', 'csv'), mime: CSV, bayt: csvBayt(pilCsv(oturum, s(BICIM_EXCEL_TR))) };
    case 'pil_en': return { ad: dosyaAdi(oturum, 'pil-en', 'csv'), mime: CSV, bayt: csvBayt(pilCsv(oturum, s(BICIM_EN))) };
    case 'skop': {
      const m = yakalama ? skopCsv(yakalama, BICIM_EXCEL_TR) : null;
      return m === null ? null : { ad: dosyaAdi(oturum, 'yakalama-' + yakalama.no + '-' + yakalama.t_sira, 'csv'), mime: CSV, bayt: csvBayt(m) };
    }
    case 'ham': return { ad: dosyaAdi(oturum, '', 'kyt'), mime: 'application/octet-stream', bayt: hamDisari(kayitlar, oturum.id) };
    default: return null;
  }
}

/** Gecen sure yazisi (ms -> ss:dd:sn.mmm); bilinmiyorsa '—'. */
export function sureYaz(ms) {
  return Number.isFinite(ms) ? zamanYazi(ms, 1) : '—';
}

/** Unix saniye -> yerel 'YYYY-AA-GG SS:DD:SN'; 0 / bilinmiyor -> null. */
export function tarihYaz(unixS) {
  if (!unixS) return null;
  const d = new Date(unixS * 1000);
  if (Number.isNaN(d.getTime())) return null;
  const i = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}:${i(d.getSeconds())}`;
}

export function sayiYaz(x, hane) {
  return Number.isFinite(x) ? x.toFixed(hane) : '—';
}

/** JSON'a sayilari TAM hassasiyetle (NaN -> null) — `data-okuma` test kancasi. */
export function okumaJson(ok) {
  return JSON.stringify(ok, (k, v) => (typeof v === 'number' && !Number.isFinite(v) ? null : v));
}

/* Ölçek tercihi Canlı ile ORTAK (`olcum.yOlcek`, app.js ayarOku ile aynı JSON). */
function olcekOku() {
  try { return yOlcekNormal(JSON.parse(localStorage.getItem('olcum.yOlcek'))); } catch (e) { return yOlcekNormal(null); }
}
function olcekYaz(v) {
  try { localStorage.setItem('olcum.yOlcek', JSON.stringify(v)); } catch (e) { /* ozel kip: yalniz bu oturum */ }
  try { window.dispatchEvent(new Event('olcum-yolcek')); } catch (e) { /* olay yoksa Canli acilista okur */ }
}

/* ── metinler (sozluk anahtarlari; C8) ──────────────────────────────── */
export const KG_METIN = Object.freeze({
  geri: 'kg.geri', rapor: 'kg.rapor', raporKapat: 'kg.rapor_kapat', yazdir: 'kg.yazdir',
  baslik: 'kg.baslik', raporBaslik: 'kg.rapor_baslik', grafik: 'kg.grafik', gerilim: 'kg.gerilim',
  sagEksen: 'kg.sag_eksen', akim: 'kg.akim', guc: 'kg.guc', yok: 'kg.yok', zarf: 'kg.zarf',
  olcekSol: 'kg.olcek_sol', olcekSag: 'kg.olcek_sag', olcekOto: 'kg.olcek_oto', olcekSifir: 'kg.olcek_sifir',
  olcekElle: 'kg.olcek_elle', olcekEnAz: 'kg.olcek_en_az', olcekEnCok: 'kg.olcek_en_cok',
  tumu: 'kg.tumu', imlecSil: 'kg.imlec_sil', grafikEtiket: 'kg.grafik_etiket',
  gezginEtiket: 'kg.gezgin_etiket', grafikIpucu: 'kg.grafik_ipucu', imlecYok: 'kg.imlec_yok',
  notlar: 'kg.notlar', genelNot: 'kg.genel_not', notIpucu: 'kg.not_ipucu', pil: 'kg.pil',
  yakalamalar: 'kg.yakalamalar', skopIpucu: 'kg.skop_ipucu', disari: 'kg.disari',
  disariIpucu: 'kg.disari_ipucu', okumaDt: 'kg.okuma_dt', okumaOrt: 'kg.okuma_ort',
  okumaMin: 'kg.okuma_min', okumaMaks: 'kg.okuma_maks', okumaFark: 'kg.okuma_fark',
  okumaMah: 'kg.okuma_mah', okumaWh: 'kg.okuma_wh', okumaSure: 'kg.okuma_sure',
  tur: 'kg.tur', no: 'kg.no', baslangic: 'kg.baslangic', saatYok: 'kg.saat_yok', sure: 'kg.sure',
  nokta: 'kg.nokta', ornek: 'kg.ornek', yakalama: 'kg.yakalama', hiz: 'kg.hiz', firmware: 'kg.firmware',
  kalNo: 'kg.kal_no', durum: 'kg.durum', nerede: 'kg.nerede', acik: 'kg.acik',
  uyariTahmini: 'kg.uyari_tahmini', uyariEksik: 'kg.uyari_eksik', uyariEski: 'kg.uyari_eski',
  sutunNo: 'kg.sutun_no', sutunZaman: 'kg.sutun_zaman', sutunOrnek: 'kg.sutun_ornek',
  sutunHz: 'kg.sutun_hz', sutunTdiv: 'kg.sutun_tdiv', sutunTetik: 'kg.sutun_tetik',
  sutunTam: 'kg.sutun_tam', evet: 'kg.evet', hayir: 'kg.hayir', eksikYakalama: 'kg.eksik_yakalama',
  csvTr: 'kg.csv_tr', csvEn: 'kg.csv_en', ayrintiTr: 'kg.ayrinti_tr', ayrintiEn: 'kg.ayrinti_en',
  pilTr: 'kg.pil_tr', pilEn: 'kg.pil_en', ham: 'kg.ham', skopCsv: 'kg.skop_csv',
  osiloskoptaAc: 'kg.osiloskopta_ac',
  disariHata: 'kg.disari_hata', herOrnek: 'kg.her_ornek',
  veriYok: 'kg.veri_yok', dahaFazla: 'kg.daha_fazla',
});

/** WIG: rapor disinda yakalama tablosu bu kadar satirla baslar ("daha fazla" 100'er ekler):
 *  Gt0 / Gt1000 gunlugu binlerce satir — telefonda kayit acilirken donma. */
export const YAKALAMA_SINIR = 100;

export const TUR_METIN = Object.freeze({
  olcum: 'kl.tur_olcum', ayrinti: 'kl.tur_ayrinti', pil: 'kl.tur_pil', skop: 'kl.tur_skop',
  bilinmeyen: 'kl.tur_bilinmeyen',
});

/* 4D: 'pc' — kayit koprunun PC arsivinden (salt okuma); metni sozluk_pc.js'te (ceviriPc). */
export const NEREDE_METIN = Object.freeze({
  kart: 'kl.nerede_kart', tarayici: 'kl.nerede_tarayici', ikisi: 'kl.nerede_ikisi', pc: 'pc.nerede',
});

/** W3: `pc.` anahtari sozluk_pc.js'ten, digerleri (kl./kg./kr. + acilis) sozluk_kayit.js zincirinden. ATMAZ. */
export function ceviriKlPc(anahtar, dil = 'tr', d = null) {
  return typeof anahtar === 'string' && anahtar.startsWith('pc.') ? ceviriPc(anahtar, dil, d) : ceviri(anahtar, dil, d);
}

/** Anahtar haritasini dile cevir. */
export function metinler(harita, dil) {
  const m = {};
  for (const [a, k] of Object.entries(harita)) m[a] = ceviri(k, dil);
  return m;
}

/* ── Vue bileseni ───────────────────────────────────────────────────── */

const SABLON = `
<div class="kg" :class="{ 'kg-rapor-kipi': rapor }">
  <div class="kg-ust yazdirma-yok">
    <a class="kg-geri" :href="listeAdresi">{{ m.geri }}</a>
    <span class="bosluk"></span>
    <a v-if="!rapor" class="kg-bag" :href="raporAdresi">{{ m.rapor }}</a>
    <template v-else>
      <a class="kg-bag" :href="kayitAdresi">{{ m.raporKapat }}</a>
      <button type="button" class="birincil" @click="yazdir">{{ m.yazdir }}</button>
    </template>
  </div>

  <section class="kart">
    <!-- WIG: sayfa basligi h1 = "Kayit" + kaydin ADI (eskiden ad duz bir div'di). Kayit
         acilinca odak buraya (mounted) — liste v-else ile kalkinca odak body'ye dusuyordu. -->
    <h1 class="kg-baslik" ref="baslik" tabindex="-1"><span class="kg-ust-ad">{{ rapor ? m.raporBaslik : m.baslik }}</span><span class="gorunmez">: </span><span
      class="kg-ad">{{ adMetni }}</span></h1>
    <div class="kg-kpiler">
      <div class="kpi" v-for="k in kimlikSatirlari" :key="k.a">
        <span class="kpi-ad">{{ k.etiket }}</span><span class="kpi-deger">{{ k.deger }}</span>
      </div>
    </div>
    <div class="kg-etiketler" v-if="etiketler.length">
      <span class="kg-etiket" v-for="e in etiketler" :key="e">{{ e }}</span>
    </div>
    <p v-for="u in uyarilar" :key="u" class="uyari">{{ u }}</p>
  </section>

  <section class="kart" v-if="!grafikVar && !notlar.length && !pilOzet && !yakalamalar.length">
    <p class="ipucu">{{ m.veriYok }}</p>
  </section>

  <section class="kart" v-if="grafikVar">
    <h2>{{ m.grafik }}</h2>
    <div class="gosterge yazdirma-yok">
      <label><input type="checkbox" v-model="goster.v"> <span class="cizgi kg-cizgi-v"></span> {{ m.gerilim }}</label>
      <label>{{ m.sagEksen }}
        <select v-model="goster.sag" class="kg-secim">
          <option value="akim">{{ m.akim }}</option>
          <option value="guc">{{ m.guc }}</option>
          <option value="yok">{{ m.yok }}</option>
        </select>
      </label>
      <label v-if="goster.v">{{ m.olcekSol }}
        <select data-olcek="sol" v-model="yOlcek.v.kip" style="width:auto">
          <option value="oto">{{ m.olcekOto }}</option>
          <option value="sifir">{{ m.olcekSifir }}</option>
          <option value="elle">{{ m.olcekElle }}</option>
        </select>
        <template v-if="yOlcek.v.kip === 'elle'">
          <input type="number" step="any" v-model="yOlcek.v.min" :placeholder="m.olcekEnAz" :aria-label="m.olcekEnAz" style="width:5.5em">
          <input type="number" step="any" v-model="yOlcek.v.maks" :placeholder="m.olcekEnCok" :aria-label="m.olcekEnCok" style="width:5.5em">
        </template>
      </label>
      <label v-if="goster.sag !== 'yok'">{{ m.olcekSag }}
        <select data-olcek="sag" v-model="yOlcek[goster.sag].kip" style="width:auto">
          <option value="oto">{{ m.olcekOto }}</option>
          <option value="sifir">{{ m.olcekSifir }}</option>
          <option value="elle">{{ m.olcekElle }}</option>
        </select>
        <template v-if="yOlcek[goster.sag].kip === 'elle'">
          <input type="number" step="any" v-model="yOlcek[goster.sag].min" :placeholder="m.olcekEnAz" :aria-label="m.olcekEnAz" style="width:5.5em">
          <input type="number" step="any" v-model="yOlcek[goster.sag].maks" :placeholder="m.olcekEnCok" :aria-label="m.olcekEnCok" style="width:5.5em">
        </template>
      </label>
      <label v-if="zarfVar"><input type="checkbox" v-model="goster.zarf"> {{ m.zarf }}</label>
      <span class="bosluk"></span>
      <button type="button" @click="tumunuGoster">{{ m.tumu }}</button>
      <button type="button" @click="imlecTemizle" :disabled="!okuma">{{ m.imlecSil }}</button>
    </div>
    <div class="kg-tuval" :data-pencere="pencereJson">
      <canvas ref="tuval" class="kg-grafik" role="img" :aria-label="m.grafikEtiket"></canvas>
    </div>
    <canvas ref="gezgin" class="kg-gezgin yazdirma-yok" role="img" :aria-label="m.gezginEtiket"></canvas>
    <p class="ipucu yazdirma-yok">{{ m.grafikIpucu }}</p>
    <!-- WIG: imlec klavyeyle de (A/B, Shift+ok) tasiniyor; izgara canli bolge DEGIL (her
         tusta ~20 deger), ~300 ms durulunca tek satirlik ozet burada duyurulur. -->
    <p class="gorunmez" aria-live="polite">{{ duyuru }}</p>
    <div class="kg-okuma" :data-okuma="okumaMetni">
      <div v-if="okuma" class="kg-okuma-izgara">
        <div class="kg-okuma-oge" v-for="o in okumaSatirlari" :key="o.a">
          <span class="kpi-ad">{{ o.etiket }}</span><span class="kpi-deger">{{ o.deger }}</span>
        </div>
      </div>
      <p v-else class="ipucu">{{ m.imlecYok }}</p>
    </div>
  </section>

  <section class="kart" v-if="notlar.length">
    <h2>{{ m.notlar }}</h2>
    <p class="ipucu yazdirma-yok">{{ m.notIpucu }}</p>
    <ul class="kg-notlar">
      <li v-for="n in notlar" :key="n.sira">
        <button type="button" class="kg-not" :disabled="n.x === null || !grafikVar" @click="notaGit(n)">
          <span class="kg-not-zaman">{{ n.genel ? m.genelNot : sure(n.gecenMs) }}</span>
          <span class="kg-not-metin">{{ n.metin }}</span>
        </button>
      </li>
    </ul>
  </section>

  <section class="kart" v-if="pilOzet">
    <h2>{{ m.pil }}</h2>
    <div class="kg-kpiler">
      <div class="kpi" v-for="k in pilOzet.kpi" :key="k.a">
        <span class="kpi-ad">{{ k.etiket }}</span><span class="kpi-deger">{{ k.deger }}</span>
      </div>
    </div>
    <div class="kg-tablo-sarmal" v-if="pilOzet.dcir.length">
      <table class="kg-tablo">
        <thead><tr><th v-for="b in pilOzet.dcirBaslik" :key="b">{{ b }}</th></tr></thead>
        <tbody><tr v-for="d in pilOzet.dcir" :key="d.no"><td v-for="(h, j) in d.hucre" :key="j">{{ h }}</td></tr></tbody>
      </table>
    </div>
  </section>

  <section class="kart" v-if="yakalamalar.length">
    <h2>{{ m.yakalamalar }}</h2>
    <p class="ipucu">{{ m.skopIpucu }}</p>
    <div class="kg-tablo-sarmal">
      <table class="kg-tablo">
        <thead><tr>
          <th>{{ m.sutunNo }}</th><th>{{ m.sutunZaman }}</th><th>{{ m.sutunOrnek }}</th>
          <th>{{ m.sutunHz }}</th><th>{{ m.sutunTdiv }}</th><th>{{ m.sutunTetik }}</th>
          <th>{{ m.sutunTam }}</th><th class="yazdirma-yok"></th>
        </tr></thead>
        <tbody>
          <tr v-for="y in gorunenYakalamalar" :key="y.sira" :data-sira="y.sira">
            <td>{{ y.no }}</td><td>{{ y.zaman }}</td><td>{{ y.toplam }}</td><td>{{ y.hz }}</td>
            <td>{{ y.tdiv }}</td><td>{{ y.tetik }}</td><td>{{ y.tam ? m.evet : m.eksikYakalama }}</td>
            <td class="yazdirma-yok"><button type="button" v-if="y.tam" @click="indir('skop', y.sira)" data-disari="skop">{{ m.skopCsv }}</button>
              <a v-if="y.tam" :href="skopAdresi(y.sira)" class="kg-skop-ac" data-skop-ac>{{ m.osiloskoptaAc }}</a></td>
          </tr>
        </tbody>
      </table>
    </div>
    <button v-if="gorunenYakalamalar.length < yakalamalar.length" type="button" class="yazdirma-yok"
            style="margin-top:10px" @click="yakalamaSinir += 100">{{ dahaFazlaYazi }}</button>
  </section>

  <section class="kart yazdirma-yok" v-if="!rapor">
    <h2>{{ m.disari }}</h2>
    <div class="dugme-grup">
      <button v-for="d in disariSecenekleri" :key="d.tur" type="button" :data-disari="d.tur"
              @click="indir(d.tur)">{{ d.etiket }}</button>
    </div>
    <p class="ipucu">{{ m.disariIpucu }}</p>
    <p v-if="hata" class="hata" role="alert">{{ hata }}</p>
  </section>

  <section class="kart kg-rapor" v-if="rapor && raporVeri">
    <h2>{{ et('istatistik') }}</h2>
    <div class="kg-tablo-sarmal">
      <table class="kg-tablo">
        <thead><tr><th></th><th v-for="s in raporSutunlar" :key="s">{{ et(s) }}</th></tr></thead>
        <tbody>
          <tr v-for="k in raporKanallar" :key="k.a"><th>{{ et(k.a) }}</th><td v-for="(h, j) in k.hucre" :key="j">{{ h }}</td></tr>
        </tbody>
      </table>
    </div>
    <h2>{{ et('enerji') }}</h2>
    <div class="kg-kpiler">
      <div class="kpi" v-for="k in raporOzet" :key="k.a"><span class="kpi-ad">{{ k.etiket }}</span><span class="kpi-deger">{{ k.deger }}</span></div>
    </div>
    <h2>{{ et('kalibrasyon') }}</h2>
    <p class="ipucu">{{ et('kalNo') }}: {{ raporVeri.kalibrasyon.kalNo === null ? '—' : raporVeri.kalibrasyon.kalNo }} · {{ raporVeri.kalibrasyon.durum ? raporVeri.kalibrasyon.durum.metin : '' }}</p>
    <template v-if="raporVeri.uyarilar.length">
      <h2>{{ et('uyarilar') }}</h2>
      <ul class="kg-uyarilar"><li v-for="u in raporVeri.uyarilar" :key="u.kod">{{ u.metin }}</li></ul>
    </template>
  </section>
</div>`;

const vueAl = () => globalThis.Vue;

export const KayitGorunumu = {
  name: 'KayitGorunumu',
  props: {
    veri: { type: Object, required: true },     // markRaw {oturum, kayitlar, kimlik, kal, satir}
    rapor: { type: Boolean, default: false },
    etkin: { type: Boolean, default: true },
    dil: { type: String, default: 'tr' },
    listeAdresi: { type: String, default: '#/kayitlar' },
    kayitAdresi: { type: String, default: '' },
    raporAdresi: { type: String, default: '' },
  },
  template: SABLON,
  data() {
    return { goster: { v: true, sag: 'akim', zarf: true }, yOlcek: olcekOku(), okuma: null, pencereJson: '', hata: '',
      duyuru: '', yakalamaSinir: YAKALAMA_SINIR };
  },
  created() {
    /* Agir veri reaktif DEGIL (markRaw / bilesen alani). */
    const { markRaw } = vueAl();
    this._h = markRaw(grafikSerileri(this.veri.oturum, { kayitlar: this.veri.kayitlar }));
    /* Ozet piramitleri BIR kez: gorunurluk degisince seriHazirla ayni t/y'de
       piramidi yeniden kurmaz (yalniz `gizli` degisir). */
    this._hazir = markRaw(this._h.seriler.map(seriHazirla));
    this._g = null;
    this._gz = null;
    this._sonImlec = '';
  },
  computed: {
    m() { return metinler(KG_METIN, this.dil); },
    oturum() { return this.veri.oturum; },
    tur() { return oturumTuru(this.oturum); },
    grafikVar() { return this._h.tur !== 'yok'; },
    zarfVar() { return this._h.tur === 'nokta'; },
    adMetni() {
      const t = ceviri(TUR_METIN[this.tur], this.dil);
      return this.oturum.ad ? this.oturum.ad : `${t} #${this.oturum.id}`;
    },
    etiketler() { return [...this.oturum.etiketler]; },
    raporVeri() {
      if (!this.rapor && this.tur !== 'pil' && !this.oturum.skoplar.size) return null;
      return oturumRaporu(this.oturum, { kalibrasyonGecmisi: this.veri.kal, kayitlar: this.veri.kayitlar, dil: this.dil });
    },
    kimlikSatirlari() {
      const o = this.oturum;
      const b = o.basla;
      const m = this.m;
      const sat = this.veri.satir || {};
      const s = [
        { a: 'tur', etiket: m.tur, deger: ceviri(TUR_METIN[this.tur], this.dil) },
        { a: 'no', etiket: m.no, deger: '#' + o.id + (sat.eskiKart ? ' @' + this.veri.kimlik : '') },
        { a: 'bas', etiket: m.baslangic, deger: (b && tarihYaz(b.unix_s)) || m.saatYok },
        { a: 'sure', etiket: m.sure, deger: sureYaz(sat.sureMs) },
      ];
      if (this._h.tur === 'nokta') s.push({ a: 'nokta', etiket: m.nokta, deger: String(this._h.adet) });
      if (this._h.tur === 'ayrinti') s.push({ a: 'ornek', etiket: m.ornek, deger: String(this._h.adet) });
      if (o.skoplar.size) s.push({ a: 'yak', etiket: m.yakalama, deger: String(o.skoplar.size) });
      if (b) {
        s.push({ a: 'hiz', etiket: m.hiz, deger: b.hiz_ms ? b.hiz_ms + ' ms' : m.herOrnek });
        s.push({ a: 'fw', etiket: m.firmware, deger: b.surum || '—' });
        s.push({ a: 'kal', etiket: m.kalNo, deger: b.kal_no ? '#' + b.kal_no : '—' });
      }
      s.push({ a: 'durum', etiket: m.durum,
        deger: o.bitir ? ceviriKod('sebep.', o.bitir.sebep, this.dil) : m.acik });
      if (sat.nerede) s.push({ a: 'nerede', etiket: m.nerede, deger: ceviriKlPc(NEREDE_METIN[sat.nerede], this.dil) });
      return s;
    },
    uyarilar() {
      const u = [];
      const sat = this.veri.satir || {};
      if (this._h.tahmini && this._h.tahmini.length) u.push(ceviri(KG_METIN.uyariTahmini, this.dil, { sayi: this._h.tahmini.length }));
      if (sat.eksik) u.push(this.m.uyariEksik);
      if (sat.eskiKart) u.push(this.m.uyariEski);
      return u;
    },
    notlar() { return notListesi(this.oturum, this._h); },
    okumaMetni() { return this.okuma ? okumaJson(this.okuma) : ''; },
    okumaSatirlari() {
      const o = this.okuma;
      if (!o) return [];
      const m = this.m;
      const s = [{ a: 'ta', etiket: 'A', deger: sureYaz(o.tA) }, { a: 'tb', etiket: 'B', deger: sureYaz(o.tB) },
        { a: 'dt', etiket: m.okumaDt, deger: sureYaz(o.dt) }];
      const kanal = (k, hane, kip) => {
        if (!k) return;
        s.push({ a: k.ad + 'a', etiket: `${k.ad} (A)`, deger: sayiYaz(k.a, hane) + ' ' + k.birim });
        s.push({ a: k.ad + 'b', etiket: `${k.ad} (B)`, deger: sayiYaz(k.b, hane) + ' ' + k.birim });
        if (!Number.isFinite(o.dt)) return;
        s.push({ a: k.ad + 'f', etiket: `${m.okumaFark} ${k.ad}`, deger: sayiYaz(k.fark, hane) + ' ' + k.birim });
        s.push({ a: k.ad + 'o', etiket: `${m.okumaOrt} ${k.ad}`, deger: sayiYaz(k.ort, hane) + ' ' + k.birim });
        if (kip) {
          s.push({ a: k.ad + 'n', etiket: `${m.okumaMin} ${k.ad}`, deger: sayiYaz(k.min, hane) + ' ' + k.birim });
          s.push({ a: k.ad + 'x', etiket: `${m.okumaMaks} ${k.ad}`, deger: sayiYaz(k.maks, hane) + ' ' + k.birim });
        }
      };
      kanal(o.v, 4, true);
      kanal(o.i, 5, true);
      kanal(o.w, 4, false);
      if (o.enerji) {
        s.push({ a: 'mah', etiket: m.okumaMah, deger: sayiYaz(o.enerji.mah, 4) + ' mAh' });
        s.push({ a: 'wh', etiket: m.okumaWh, deger: sayiYaz(o.enerji.wh, 6) + ' Wh' });
        s.push({ a: 'es', etiket: m.okumaSure, deger: sureYaz(o.enerji.sureS * 1000) });
      }
      return s;
    },
    pilOzet() {
      const r = this.raporVeri;
      if (!r || !r.pil) return null;
      const p = r.pil;
      const al = (k) => ceviri('alan.' + k, this.dil);
      const kpi = [];
      if (p.ayar) {
        kpi.push({ a: 'kv', etiket: al('kesme_v'), deger: sayiYaz(p.ayar.kesme_v, 3) });
        kpi.push({ a: 'ocv', etiket: al('ocv'), deger: sayiYaz(p.ayar.ocv, 3) });
      }
      if (p.sonuc) {
        kpi.push({ a: 'dr', etiket: al('durum'), deger: p.sonuc.durumMetin });
        kpi.push({ a: 'mah', etiket: al('mah'), deger: sayiYaz(p.sonuc.mah, 1) });
        kpi.push({ a: 'wh', etiket: al('wh'), deger: sayiYaz(p.sonuc.wh, 4) });
        kpi.push({ a: 'vs', etiket: al('v_son'), deger: sayiYaz(p.sonuc.v_son, 3) });
        kpi.push({ a: 'sm', etiket: this.m.sure, deger: sureYaz(p.sonuc.sure_ms) });   // ss:dd:sn — "(ms)" etiketi yaniltirdi
        if (p.sonuc.hata) kpi.push({ a: 'ht', etiket: al('hata'), deger: p.sonuc.hataMetin });
      }
      const dcirBaslik = ['no', 'v_once', 'i_once', 'r_ani', 'r_oturmus', 'mah'].map(al);
      const dcir = p.dcir.map((d) => ({ no: d.no, hucre: [String(d.no), sayiYaz(d.v_once, 3), sayiYaz(d.i_once, 3),
        sayiYaz(d.r_ani, 4), sayiYaz(d.r_oturmus, 4), sayiYaz(d.mah, 1)] }));
      return { kpi, dcir, dcirBaslik };
    },
    yakalamalar() {
      const r = this.raporVeri;
      if (!r) return [];
      const ev = this.m.evet;
      const hy = this.m.hayir;
      return r.skop.yakalamalar.map((y) => ({ sira: y.sira, no: y.no, toplam: y.toplam, tam: y.tam,
        zaman: sureYaz(y.gecenMs), hz: y.hz === null ? '—' : String(y.hz),
        tdiv: y.tdivUs === null ? '—' : y.tdivUs + ' µs', tetik: y.tetiklendi === null ? '—' : (y.tetiklendi ? ev : hy) }));
    },
    /** WIG: rapor (yazdirma) TAM tablo; ekranda ilk `yakalamaSinir` satir. */
    gorunenYakalamalar() {
      return this.rapor ? this.yakalamalar : this.yakalamalar.slice(0, this.yakalamaSinir);
    },
    dahaFazlaYazi() {
      return ceviri(KG_METIN.dahaFazla, this.dil, { kalan: this.yakalamalar.length - this.gorunenYakalamalar.length });
    },
    disariSecenekleri() {
      const ad = { csv_tr: 'csvTr', csv_en: 'csvEn', ayrinti_tr: 'ayrintiTr', ayrinti_en: 'ayrintiEn',
        pil_tr: 'pilTr', pil_en: 'pilEn', ham: 'ham' };
      return disariTurleri(this.oturum).map((tur) => ({ tur, etiket: this.m[ad[tur]] }));
    },
    raporSutunlar() { return ['adet', 'min', 'maks', 'ort', 'rms', 'tepeTepe']; },
    raporKanallar() {
      const r = this.raporVeri;
      if (!r) return [];
      return [['v', 4], ['i', 5], ['w', 4]].map(([a, hane]) => {
        const k = r.istatistik[a];
        return { a, hucre: [String(k.adet), sayiYaz(k.min, hane), sayiYaz(k.maks, hane), sayiYaz(k.ort, hane),
          sayiYaz(k.rms, hane), sayiYaz(k.tepeTepe, hane)] };
      });
    },
    raporOzet() {
      const r = this.raporVeri;
      if (!r) return [];
      return [
        { a: 'wh', etiket: this.et('wh'), deger: sayiYaz(r.enerji.wh, 6) },
        { a: 'mah', etiket: this.et('mah'), deger: sayiYaz(r.enerji.mah, 4) },
        { a: 'ol', etiket: this.et('olculenMs'), deger: sureYaz(r.zaman.olculenMs) },
        { a: 'top', etiket: this.et('toplamMs'), deger: sureYaz(r.zaman.toplamMs) },
        { a: 'bas', etiket: this.et('baslangic'), deger: r.zaman.baslangic ? r.zaman.baslangic.iso : '—' },
        { a: 'seb', etiket: this.et('sebep'), deger: r.bitis.sebep.metin },
      ];
    },
  },
  watch: {
    goster: { deep: true, handler() { this.gorunurlukUygula(); this.ciz(); } },
    yOlcek: { deep: true, handler(v) { olcekYaz(v); this.ciz(); } },
    etkin(v) { if (v) { this.olcekTazele(); this.$nextTick(() => this.ciz()); } },
    rapor() { this.$nextTick(() => this.ciz()); },
  },
  mounted() {
    if (this.grafikVar) this.grafikKur();
    /* Gorunum (tema) degisince tuvaller bit eslem: yeniden ciz. Tema app.js /
       tema.js'te; burada yalniz <html data-tema> izleniyor (app.js'e dokunmadan). */
    this._gozcu = new MutationObserver(() => this.ciz());
    this._gozcu.observe(document.documentElement, { attributes: true, attributeFilter: ['data-tema'] });
    this._boyut = () => this.ciz();
    /* Bilesen acik kalirken Canli'da degisen olcek (ayni sekme: 'olcum-yolcek' olayi) */
    this._olcekDinle = () => this.olcekTazele();
    window.addEventListener('olcum-yolcek', this._olcekDinle);
    this._once = () => this.yazdirmaOncesi();
    this._sonra = () => this.yazdirmaSonrasi();
    window.addEventListener('resize', this._boyut);
    window.addEventListener('beforeprint', this._once);
    window.addEventListener('afterprint', this._sonra);
    /* WIG: kayit acildi -> odak basliga (ekran gorunurse); klavye kullanicisi sayfa basina atilmaz. */
    if (this.etkin) {
      this.$nextTick(() => {
        const b = this.$refs.baslik;
        if (b && typeof b.focus === 'function') b.focus({ preventScroll: true });
      });
    }
  },
  beforeUnmount() {
    if (this._duyuruZaman) clearTimeout(this._duyuruZaman);
    if (this._gozcu) this._gozcu.disconnect();
    window.removeEventListener('resize', this._boyut);
    window.removeEventListener('olcum-yolcek', this._olcekDinle);
    window.removeEventListener('beforeprint', this._once);
    window.removeEventListener('afterprint', this._sonra);
    if (this._g) this._g.yokEt();
    if (this._gz) this._gz.yokEt();
    this._g = null;
    this._gz = null;
  },
  methods: {
    sure(ms) { return sureYaz(ms); },
    et(alan) { return ceviri(RAPOR_ETIKET[alan], this.dil); },
    renkCozucu(tuval) {
      const cs = cssRenk(tuval, window);
      return (ad) => cs(ad === 'imlec' ? 'yazi' : ad);          // K5
    },
    grafikKur() {
      const { markRaw } = vueAl();
      const t = this.$refs.tuval;
      const gz = this.$refs.gezgin;
      this._g = markRaw(new Grafik(t, { renk: this.renkCozucu(t), zamanKokeni: 0, gerilim: 'V', akim: 'I',
        yOlcek: yOlcekEksen(this.yOlcek, this.goster.sag),
        isaretler: yakalamaIsaretleri(this.oturum, this._h), onDegisim: (d) => this.degisti(d) }));
      this._gz = markRaw(new Grafik(gz, { gezgin: true, renk: this.renkCozucu(gz),
        onDegisim: (d) => { if (this._g) this._g.durumAyarla({ t0: d.t0, t1: d.t1 }); this.pencereYaz(); } }));
      this.gorunurlukUygula(false);
      this.pencereYaz();
    },
    gorunurlukUygula(koru = true) {
      if (!this._g) return;
      const s = gorunurluk(this._hazir, this.goster);
      this._g.veriAyarla(s, { koru });
      /* gezgin: yalniz ortalamalar, ana grafikle ayni gorunurluk */
      this._gz.veriAyarla(s.filter((x) => !x.zarf), { koru });
      this._gz.durumAyarla({ t0: this._g.durum.t0, t1: this._g.durum.t1 });
    },
    degisti(d) {
      if (this._gz) this._gz.durumAyarla({ t0: d.t0, t1: d.t1 });
      const A = d.imlecA;
      const B = d.imlecB;
      const anahtar = `${A}|${B}`;
      if (anahtar !== this._sonImlec) {            // kaydirma/yakinlastirmada yeniden hesap yok
        this._sonImlec = anahtar;
        this.okuma = Number.isFinite(A) || Number.isFinite(B) ? okumaHesapla(this._h, A, B) : null;
        this.duyuruZamanla();
      }
      this.pencereYaz();
    },
    /** WIG: okuma ~300 ms durulunca TEK satir (A · B · Δt · ilk kanalin A/B'si). */
    duyuruZamanla() {
      if (this._duyuruZaman) clearTimeout(this._duyuruZaman);
      this._duyuruZaman = setTimeout(() => {
        this.duyuru = this.okuma ? this.okumaSatirlari.slice(0, 5).map((o) => o.etiket + ' ' + o.deger).join(' · ') : '';
      }, 300);
    },
    pencereYaz() {
      if (!this._g) return;
      const d = this._g.durum;
      const c = this.$refs.tuval;
      const alan = yerlesim(this._g.seriler, { w: c.clientWidth, h: c.clientHeight });
      this.pencereJson = JSON.stringify({ t0: d.t0, t1: d.t1, veriT0: d.veriT0, veriT1: d.veriT1,
        imlecA: d.imlecA, imlecB: d.imlecB, alanX: alan.x, alanW: alan.w });
    },
    /* Ortak anahtardan yeniden oku; ayniysa atama yok (olay dongusu kurulmaz). */
    olcekTazele() {
      const y = olcekOku();
      if (JSON.stringify(y) !== JSON.stringify(this.yOlcek)) this.yOlcek = y;
    },
    ciz() {
      if (this._g) this._g.secenek.yOlcek = yOlcekEksen(this.yOlcek, this.goster.sag);
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
    notaGit(n) {
      if (!this._g || n.x === null) return;
      this._g.durumAyarla(notPenceresi(this._g.durum, n.x));
      this.degisti(this._g.durum);
    },
    /** 3E (OS6): yakalamanin osiloskop adresi (kimlik HER ZAMAN yazilir: eski kart kopyasinda da dogru akis). */
    skopAdresi(sira) {
      return skopRotaYaz({ oturum: this.oturum.id, sira, kimlik: this.veri.kimlik });
    },
    indir(tur, sira = null) {
      this.hata = '';
      let d = null;
      try {
        const y = sira === null ? null : this.oturum.skoplar.get(sira);
        d = disariUret(tur, this.oturum, this.veri.kayitlar, y);
      } catch (h) {
        this.hata = this.m.disariHata + ' ' + ((h && h.message) || h);
        return;
      }
      if (!d) { this.hata = this.m.disariHata; return; }
      const url = URL.createObjectURL(new Blob([d.bayt], { type: d.mime }));
      const a = document.createElement('a');
      a.href = url;
      a.download = d.ad;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    },
    yazdir() { window.print(); },
    yazdirmaOncesi() {                                            // K6
      if (!this.rapor) return;
      const k = document.documentElement;
      this._eskiTema = k.getAttribute('data-tema');
      k.setAttribute('data-tema', 'acik');
      this.ciz();
    },
    yazdirmaSonrasi() {
      if (this._eskiTema === undefined || this._eskiTema === null) return;
      document.documentElement.setAttribute('data-tema', this._eskiTema);
      this._eskiTema = null;
      this.ciz();
    },
  },
};
