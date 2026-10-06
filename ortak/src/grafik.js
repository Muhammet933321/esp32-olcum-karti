/**
 * ortak/src/grafik.js — grafik çekirdeği: çok kanallı zaman grafiği, `<canvas>`,
 * bağımlılık yok (alt proje 3, dilim 3B).
 *
 * Bağlayıcı kararlar: tasarim/2026-10-02-alt-proje-3-panel.md P3 (uPlot YERİNE kendi
 * çekirdeğimiz) ve 3B; alt proje 2 O1 (bağımlılıksız ES modülü), D1–D5 (seri, piramit,
 * pencere sorgusu, istatistik HAM veriden); üst tasarım §9 "Çizim kuralı" ve Ö1.
 * Görünüş: seçilen maket (iki imleç A/B + okuma satırı, altta gezgin şeridi + seçili
 * pencere, ızgara; lejant çağıranın HTML'inde — `lejantOgeleri`).
 *
 * ── KATMANLAR ─────────────────────────────────────────────────────────────
 * SAF (Node'da sınanır; DOM yok):
 *   1. Ölçek — guzelAdim/guzelAdimlar (1-2-5), zamanAdimlari, eksenAraligi, yerlesim,
 *      pencereHesapla: x = zaman penceresi → piksel; y = sol/sağ eksen (kanal bir eksene
 *      bağlı); OTO ÖLÇEK görünür verinin TAM min/maks'ından.
 *   2. cizimPlani(seriler, durum, boyut) → düz komut listesi (ızgara, eksen yazıları,
 *      kanal çizgileri boşlukta bölünmüş, imleç çizgileri, seçim bandı, gezgin penceresi).
 *   3. etkilesim(durum, olay) → yeni durum (saf indirgeyici): tekerlek (işaretçi
 *      altında), sürükleyerek kaydırma, iki parmak, klavye, imleç sürükleme, gezgin.
 *   4. imlecOkuma(seriler, tA, tB) → imleçteki değerler (en yakın HAM örnek, ikili arama)
 *      + aralık istatistiği ve enerji/yük istatistik.js ile HAM veriden.
 * İNCE ÇİZİCİ: `class Grafik` planı ctx'e uygular. DOM'a YALNIZ verilen canvas ve
 * `pencere` (varsayılan globalThis: devicePixelRatio, getComputedStyle,
 * requestAnimationFrame) üzerinden dokunur → Node testleri sahte verir.
 *
 * ── KARARLAR ──────────────────────────────────────────────────────────────
 * G1 Ö1 ÇİZİMDE: özet kipte her piksel sütunu (ozet.js sütun sözleşmesi) sütun
 *    ortasında (x = alan.x + c + 0.5) min→maks DİKEY bir parçadır ve komşu sütunlara
 *    bağlanır; sütuna önceki noktaya yakın uçtan girilir. Tek örneklik sıçrama
 *    sütunun ucu olduğundan (ozet.js Ö1 b) her yakınlaştırmada görünür dikey çizgidir.
 *    min = maks olan sütun tek köşe; tek köşeli parça 'nokta' komutu olur.
 * G2 BOŞLUK (D1): ham kipte `bolumler` (boslukBolumleri) ve NaN değer çizgiyi keser;
 *    özet kipte NaN sütun ve `kesik[c]` keser (ozet.js sözleşmesi: çizici NaN'ı kesik
 *    sayar). `boslukMs` kanal başına ÇAĞIRANDAN gelir (kayıtta DEVAM sınırı ya da
 *    hız × 2.5); tahmin edilmez — yanlış tahmin enerjiyi de keserdi.
 * G3 OTO ÖLÇEK: eksen başına GÖRÜNÜR pencerenin TAM min/maks'ı (özet kipte sütun uçları
 *    zaten tam; ham kipte [a, b) döngüsü) — örnekleme DEĞİL, sıçramalar dahil.
 *    %5 pay; sabit veri ±%5·|v| (0 ise ±1); veri yoksa [0, 1] — sıfıra bölme yok.
 *    İsteğe bağlı `seri.enAzAralik` (birim cinsinden): eksen bundan dar olmaz, ortası
 *    korunur (1 A ± %0.2'lik düz akım bütün yüksekliği gürültü bandıyla kaplamasın —
 *    başsız tarayıcıda görüldü). Verilmezse ölçek TAM veridir; uçlar daima içeride.
 * G4 PENCERE: [veriT0, veriT1]'e kırpılır; en dar pencere EN_AZ_ORNEK (10) × tipik
 *    örnek aralığı (ortanca), en geniş bütün veri. Yakınlaştırma işaretçi altındaki
 *    zamanı SABİT tutar; yalnız uca dayanınca pencere kayar.
 * G5 İMLEÇ: A ≤ B daima (kesişince takas, sürükleme aynı çizgide sürer); veri aralığına
 *    kırpılır. Değer = en yakın NaN'sız HAM örnek; aralık istatistiği ve enerji HAM
 *    (D4); enerji/yük yalnız V ve A kanalları aynı zaman dizisini paylaşıyorsa,
 *    boşluğun üstünden integral yok.
 * G6 GEZGİN: aynı `durum` (t0, t1 = ana grafiğin penceresi); x ekseni bütün veri.
 *    Gövdeyi sürükle = taşı, kenar = boyutla, dışarı tıkla = oraya ortala.
 *    Grafikler arası eşleme `onDegisim` + `durumAyarla` ile (yalnız t0, t1, imleçler).
 * G7 ÇİZİCİ: plan CSS pikselinde; ctx.setTransform(dpr). Renkler HER `ciz()`'de
 *    yeniden okunur (görünüm değişince çağıran `ciz()` der). Klavye yalnız canvas'ın
 *    dinleyicisinde (odak varken; canvas tabIndex 0 yapılır) — global keydown YOK.
 *    touch-action: none + işaretçi yakalama (iki parmak için).
 * G8 METİN: plan dil metni taşımaz (P7) — yalnız sayı, birim, 'A'/'B'. Zaman ekseni
 *    `zamanKokeni`nden (varsayılan veri başı) geçen süre, ss:dd:sn[.kesir]; gün yok,
 *    saat 24'ü geçebilir (dil bağımsız).
 * G9 CANLI veri: `veriAyarla` piramidi O(n) yeniden kurar; artımlı ekleme 3D'nin işi.
 *
 * ── SERİ ──────────────────────────────────────────────────────────────────
 * { ad, t: Float64Array (ms, azalmayan, sonlu), y: Float64Array (NaN = eksik),
 *   birim?: 'V'|'A'|'W'|…, renk?: CSS değişkeni adı ('volt' → --volt),
 *   eksen?: 'sol'|'sag', boslukMs?, enAzAralik?, kalinlik?, gizli?, oz? (ozetKur sonucu),
 *   desen?: number[] (kesik çizgi, ctx.setLineDash; 3G — renk körlüğüne karşı ikinci ayırt edici) }
 */

import { altSinir, ustSinir, ozetKur, ozetPencere } from './ozet.js';
import { istatistik, enerji } from './istatistik.js';

/** En dar pencere kaç tipik örnek aralığı (G4). */
export const EN_AZ_ORNEK = 10;
/** İmleç / gezgin kenarı yakalama uzaklığı (CSS px). */
export const YAKALAMA_PX = 8;
/** Tekerlek: oran = exp(dy · k); dy = 100 px → ×1.16. */
export const TEKERLEK_KATSAYI = 0.0015;
/** Klavye +/−: pencere bu oranla daralır / genişler. */
export const TUS_ORAN = 1.25;
/** Klavye ok: pencerenin bu kesri kadar kaydırma. */
export const TUS_KAYDIR = 0.1;
/** Shift + ok: etkin imleci pencerenin bu kesri kadar taşır. */
export const IMLEC_TUS_ADIM = 0.01;
/** İki parmak arası bundan darsa ölçek hesaplanmaz (sıfıra bölme / titreme). */
export const KISKAC_EN_AZ_PX = 10;
/** Oto ölçek payı (her iki yana). */
export const PAY = 0.05;
/** Varsayılan yazı tipi (P2: sistem yazı tipi). */
export const YAZI_TIPI = '11px ui-monospace, "Cascadia Mono", Consolas, monospace';

/** CSS değişkeni bulunamazsa (koyu görünüm değerleri, maket). */
export const RENK_YEDEK = Object.freeze({
  volt: '#6ea8fe', amper: '#f2a33c', watt: '#35d39a', izgara: '#1f2b37', soluk: '#94a3b3',
  imlec: '#f5a524', vurgu: '#4cc4e0', gezgin: '#0e151d', yazi: '#dee7ef',
});
/** `--<ad>` yoksa sırayla denenen eşdeğer değişkenler (arayuz3/style.css adları). */
export const RENK_ESDEGER = Object.freeze({
  izgara: ['kenar-c', 'kenar'], gezgin: ['zemin'],
});

const KENAR_GEZGIN = Object.freeze({ ust: 1, alt: 1, sol: 0, sag: 0 });
/** Ham kipte pencere dışındaki komşu köşe kenardan en çok bu kadar taşar (px). */
const KENAR_TASMA = 4;

// ── 1. ÖLÇEK ──────────────────────────────────────────────────────────────

/** Kayan nokta kırıntısını siler (0.30000000000000004 → 0.3). */
function temiz(v) {
  return Number(v.toPrecision(12));
}

/** `aralik`'ı yaklaşık `hedef` parçaya bölen 1-2-5 adımı. */
export function guzelAdim(aralik, hedef = 5) {
  if (!(aralik > 0) || !Number.isFinite(aralik)) return 1;
  const kaba = aralik / Math.max(1, hedef);
  const taban = 10 ** Math.floor(Math.log10(kaba));
  const m = kaba / taban;
  const c = m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10;
  return temiz(c * taban);
}

/** [min, maks] içindeki 1-2-5 adımlı çentikler. maks ≤ min ise çentik yok. */
export function guzelAdimlar(min, maks, hedef = 5) {
  if (!(maks > min) || !Number.isFinite(min) || !Number.isFinite(maks)) return { adim: NaN, degerler: [] };
  const adim = guzelAdim(maks - min, hedef);
  const k0 = Math.ceil(min / adim - 1e-9);
  const k1 = Math.floor(maks / adim + 1e-9);
  const pay = adim * 1e-6;
  const degerler = [];
  for (let k = k0; k <= k1 && degerler.length < 1000; k++) {
    const v = temiz(k * adim);
    if (v >= min - pay && v <= maks + pay) degerler.push(v === 0 ? 0 : v); // -0 yok
  }
  return { adim, degerler };
}

/** Saniye ve üstü zaman adımları (ms); altı 1-2-5 ms. */
const ZAMAN_ADIMLARI = [1000, 2000, 5000, 10000, 15000, 30000, 60000, 120000, 300000, 600000,
  900000, 1800000, 3600000, 7200000, 10800000, 21600000, 43200000, 86400000, 172800000, 604800000];

/** Zaman ekseni adımı (ms): < 1 s → 1-2-5; üstü saat/dakika dostu liste; > 1 hafta gün × 1-2-5. */
export function zamanAdimi(aralik, hedef = 6) {
  if (!(aralik > 0) || !Number.isFinite(aralik)) return 1;
  const kaba = aralik / Math.max(1, hedef);
  if (kaba < 1000) return guzelAdim(aralik, hedef);
  for (const a of ZAMAN_ADIMLARI) if (a >= kaba) return a;
  return guzelAdim(aralik / 86400000, hedef) * 86400000;
}

/** [t0, t1] içindeki zaman çentikleri; `koken`e göre yuvarlak (geçen süre). */
export function zamanAdimlari(t0, t1, hedef = 6, koken = 0) {
  if (!(t1 > t0)) return { adim: NaN, degerler: [] };
  const adim = zamanAdimi(t1 - t0, hedef);
  const k0 = Math.ceil((t0 - koken) / adim - 1e-9);
  const k1 = Math.floor((t1 - koken) / adim + 1e-9);
  const pay = adim * 1e-6;
  const degerler = [];
  for (let k = k0; k <= k1 && degerler.length < 1000; k++) {
    const t = koken + k * adim;
    if (t >= t0 - pay && t <= t1 + pay) degerler.push(t);
  }
  return { adim, degerler };
}

/**
 * Eksen aralığı (G3): [enk − %5, enb + %5]. Sabit veri → ±%5·|v| (0 → ±1);
 * sonlu değilse (veri yok) [0, 1]. Dönüş daima maks > min.
 */
export function eksenAraligi(enk, enb, pay = PAY) {
  if (!Number.isFinite(enk) || !Number.isFinite(enb)) return [0, 1];
  if (enb < enk) [enk, enb] = [enb, enk];
  const aralik = enb - enk;
  if (aralik <= Math.max(Math.abs(enk), Math.abs(enb)) * 1e-12) { // SABİT veri
    const p = enk !== 0 ? Math.abs(enk) * PAY : 1;
    return [enk - p, enb + p];
  }
  return [enk - aralik * pay, enb + aralik * pay];
}

/**
 * KULLANICI ÖLÇEĞİ (yOlcek, 2026-10-06 kullanıcı isteği): eksen başına
 *   { kip: 'oto' }                      — otomatik (eksenAraligi + enAz), varsayılan
 *   { kip: 'sifir' }                    — 0 her zaman eksende; uzak uç otomatik (+%5 pay)
 *   { kip: 'elle', min, maks }          — sabit; geçersizse (sayı değil / maks ≤ min) otomatiğe düşer
 * Veri sınırın dışına taşarsa çizim alanı kırpar (cizimPlani 'kirp'). SAF fonksiyon.
 */
export function olcekUygula(otoMin, otoMaks, veriMin, veriMaks, ayar) {
  const kip = ayar && ayar.kip;
  if (kip === 'elle') {
    const a = Number(ayar.min);
    const b = Number(ayar.maks);
    if (ayar.min !== '' && ayar.maks !== '' && Number.isFinite(a) && Number.isFinite(b) && b > a) return [a, b];
    return [otoMin, otoMaks];
  }
  if (kip === 'sifir' && Number.isFinite(veriMin) && Number.isFinite(veriMaks)) {
    const lo = Math.min(veriMin, 0);
    const hi = Math.max(veriMaks, 0);
    let [min, maks] = eksenAraligi(lo, hi);
    if (lo === 0) min = 0;
    if (hi === 0) maks = 0;
    if (!(maks > min)) maks = min + 1;
    return [min, maks];
  }
  return [otoMin, otoMaks];
}

/**
 * Ölçek tercihi kanal başına saklanır (`olcum.yOlcek` = { v, akim, guc }): sağ eksen
 * akımdan güce geçince akımın elle sınırları güce taşınmaz. `yOlcekNormal` bozuk /
 * eski kaydı varsayılana çeker; `yOlcekEksen` kaydı eksen adlarına (sol/sag) eşler.
 */
export function yOlcekNormal(kayit) {
  const s = {};
  const sayi = (x) => (x === '' || x === null || x === undefined || !Number.isFinite(Number(x)) ? '' : x);
  for (const k of ['v', 'akim', 'guc']) {
    const a = kayit && typeof kayit === 'object' ? kayit[k] : null;
    const kip = a && ['oto', 'sifir', 'elle'].includes(a.kip) ? a.kip : 'oto';
    s[k] = { kip, min: a ? sayi(a.min) : '', maks: a ? sayi(a.maks) : '' };
  }
  return s;
}

export function yOlcekEksen(kayit, sagEksen) {
  if (!kayit) return null;
  return { sol: kayit.v || null, sag: sagEksen && sagEksen !== 'yok' ? kayit[sagEksen] || null : null };
}

const iki = (v) => (v < 10 ? '0' : '') + v;

/**
 * Geçen süre yazısı (G8): ss:dd:sn, adım < 1 s ise ondalıklı saniye. Saat 24'ü geçebilir.
 * Eksi süre '−' ile.
 */
export function zamanYazi(ms, adim = 1000) {
  if (!Number.isFinite(ms)) return '';
  const ondalik = adim < 1000 ? Math.min(6, Math.max(1, Math.ceil(-Math.log10(adim / 1000) - 1e-9))) : 0;
  const olcek = 10 ** ondalik;
  let birim = Math.round(Math.abs(ms) / 1000 * olcek); // tamsayı: 10^-ondalik s
  const kesir = birim % olcek;
  birim = (birim - kesir) / olcek; // tam saniye
  const sn = birim % 60;
  const dk = ((birim - sn) / 60) % 60;
  const sa = Math.floor(birim / 3600);
  let yazi = `${iki(sa)}:${iki(dk)}:${iki(sn)}`;
  if (ondalik) yazi += '.' + String(kesir).padStart(ondalik, '0');
  return (ms < 0 && (birim > 0 || kesir > 0) ? '−' : '') + yazi;
}

/**
 * X EKSENİ SEÇENEĞİ (3E, karar OS2): `secenek.xEksen = { tur: 'sayi', yazi(deger, adim) }`.
 * Verilirse x çentikleri zaman listesi (1-2-5 ms, sonra 1/2/5/10/15/30 s …) DEĞİL düz 1-2-5
 * (guzelAdimlar) olur ve yazı `yazi(t − koken, adim)` ile basılır — örn. spektrumda x = Hz
 * ("12.5 kHz"). Verilmezse G8 (geçen süre) aynen. `t` dizisi yine azalmayan sayı; birimi
 * çağıranın (grafik.js x'i yalnız sayı olarak görür).
 */
export function xSayiEkseni(secenek) {
  return !!(secenek && secenek.xEksen && secenek.xEksen.tur === 'sayi');
}

/** [t0, t1] içindeki düz 1-2-5 çentikler, `koken`e göre (sayı ekseni). */
export function sayiAdimlari(t0, t1, hedef = 6, koken = 0) {
  const r = guzelAdimlar(t0 - koken, t1 - koken, hedef);
  return { adim: r.adim, degerler: r.degerler.map((v) => v + koken) };
}

/** X yazıcısı: `xEksen.yazi` (işlevse) yoksa zamanYazi. Atan yazıcı boş metin verir. */
export function xYazici(secenek) {
  const y = secenek && secenek.xEksen && secenek.xEksen.yazi;
  if (typeof y !== 'function') return zamanYazi;
  return (v, adim) => {
    try {
      const m = y(v, adim);
      return m === null || m === undefined ? '' : String(m);
    } catch {
      return '';
    }
  };
}

/** Eksen sayısı: adımın gerektirdiği kadar ondalık; eksi '−' (maket). */
export function sayiYazi(v, adim) {
  if (!Number.isFinite(v)) return '';
  const ondalik = Number.isFinite(adim) && adim > 0
    ? Math.min(9, Math.max(0, Math.ceil(-Math.log10(adim) - 1e-9))) : 3;
  const s = Math.abs(v).toFixed(ondalik);
  return (v < 0 && Number(s) !== 0 ? '−' : '') + s;
}

/**
 * Çizim alanı (CSS px): kenar boşlukları kullanılan eksenlere göre. Genişlik/yükseklik
 * tamsayı (özet sütun sayısı = alan.w).
 */
export function yerlesim(seriler, boyut, secenek = {}) {
  let sol = false;
  let sag = false;
  for (const s of seriler) {
    if (s.gizli) continue;
    if (s.eksen === 'sag') sag = true;
    else sol = true;
  }
  const varsayilan = secenek.gezgin ? KENAR_GEZGIN
    : { ust: 16, alt: 22, sol: sol ? 56 : 10, sag: sag ? 56 : 10 };
  const k = { ...varsayilan, ...(secenek.kenar || {}) };
  return {
    x: k.sol,
    y: k.ust,
    w: Math.max(0, Math.floor((Number(boyut && boyut.w) || 0) - k.sol - k.sag)),
    h: Math.max(0, Math.floor((Number(boyut && boyut.h) || 0) - k.ust - k.alt)),
  };
}

/**
 * Ölçekler + kanal başına pencere sorgusu (katman 1).
 * x alanı: ana grafikte [durum.t0, durum.t1], gezginde bütün veri.
 * @returns {{alan, gezgin, x: {t0, t1, adim, degerler, koken}, eksenler: {sol?, sag?},
 *            sorgular: Array<object|null>}}  eksen = {min, maks, adim, degerler, birim}
 */
export function pencereHesapla(seriler, durum, boyut, secenek = {}) {
  const gezgin = !!secenek.gezgin;
  const alan = yerlesim(seriler, boyut, secenek);
  const x0 = gezgin ? durum.veriT0 : durum.t0;
  const x1 = gezgin ? durum.veriT1 : durum.t1;
  const koken = Number.isFinite(secenek.zamanKokeni) ? secenek.zamanKokeni : durum.veriT0;
  const sonuc = {
    alan, gezgin, x: { t0: x0, t1: x1, adim: NaN, degerler: [], koken }, eksenler: {}, sorgular: [],
  };
  if (alan.w < 1 || alan.h < 1 || !(x1 > x0)) return sonuc;
  const xHedef = Math.max(2, Math.floor(alan.w / 110));
  const xt = xSayiEkseni(secenek) ? sayiAdimlari(x0, x1, xHedef, koken) : zamanAdimlari(x0, x1, xHedef, koken);
  sonuc.x.adim = xt.adim;
  sonuc.x.degerler = xt.degerler;

  const uc = {};
  for (const s of seriler) {
    if (s.gizli || !s.oz || s.t.length === 0) {
      sonuc.sorgular.push(null);
      continue;
    }
    const q = ozetPencere(s.oz, x0, x1, alan.w, { boslukMs: s.boslukMs });
    sonuc.sorgular.push(q);
    const ad = s.eksen === 'sag' ? 'sag' : 'sol';
    const e = uc[ad] || (uc[ad] = { enk: Infinity, enb: -Infinity, komsuK: Infinity, komsuB: -Infinity, birim: '', enAz: 0 });
    if (!e.birim && s.birim) e.birim = s.birim;
    if (s.enAzAralik > e.enAz) e.enAz = s.enAzAralik;
    if (q.tur === 'ozet') {
      // Sütunlar penceredeki BÜTÜN ham örneklerin tam min/maks'ı (ozet.js Ö1 a).
      const st = q.sutunlar;
      for (let c = 0; c < st.length; c += 2) {
        const altUc = st[c], ustUc = st[c + 1];
        if (altUc < e.enk) e.enk = altUc; // NaN karşılaştırması yanlış: boş sütun atlanır
        if (ustUc > e.enb) e.enb = ustUc;
      }
    } else {
      const a = altSinir(s.t, x0);
      const b = ustSinir(s.t, x1, a);
      for (let i = a; i < b; i++) {
        const v = s.y[i];
        if (v < e.enk) e.enk = v;
        if (v > e.enb) e.enb = v;
      }
      for (let i = q.i0; i < q.i1; i++) { // pencere boşsa komşulara göre ölçeklenir
        const v = s.y[i];
        if (v < e.komsuK) e.komsuK = v;
        if (v > e.komsuB) e.komsuB = v;
      }
    }
  }
  const hedefY = Math.max(2, Math.floor(alan.h / 40));
  for (const ad of ['sol', 'sag']) {
    const e = uc[ad];
    if (!e) continue;
    const bos = !(e.enb >= e.enk);
    let [min, maks] = eksenAraligi(bos ? e.komsuK : e.enk, bos ? e.komsuB : e.enb);
    if (maks - min < e.enAz) { // ENAZ ARALIK: düz sinyalin gürültüsü bütün yüksekliği kaplamasın
      const orta = (min + maks) / 2;
      min = orta - e.enAz / 2;
      maks = orta + e.enAz / 2;
    }
    const ayar = secenek.yOlcek && secenek.yOlcek[ad];
    if (ayar && ayar.kip && ayar.kip !== 'oto') {
      [min, maks] = olcekUygula(min, maks, bos ? e.komsuK : e.enk, bos ? e.komsuB : e.enb, ayar);
    }
    const { adim, degerler } = guzelAdimlar(min, maks, hedefY);
    sonuc.eksenler[ad] = { min, maks, adim, degerler, birim: e.birim };
  }
  return sonuc;
}

// ── 2. ÇİZİM PLANI ────────────────────────────────────────────────────────

/** Köşe biriktirir; kesikte (bitir) 'cizgi' ya da tek köşeyse 'nokta' komutu üretir. */
class CizgiYapici {
  constructor(komutlar, alan, ozellik, hamKip) {
    this.komutlar = komutlar;
    this.alan = alan;
    this.ozellik = ozellik;
    this.hamKip = hamKip;
    this.p = [];
    this.sonY = NaN;
  }

  ekle(x, y) {
    this.p.push(x, y);
    this.sonY = y;
  }

  /** Ham kipte pencere dışındaki komşu köşeyi kenara çeker (doğru üstünde, eğim aynı). */
  kenarCek() {
    const p = this.p;
    const n = p.length;
    const L = this.alan.x - KENAR_TASMA;
    const R = this.alan.x + this.alan.w + KENAR_TASMA;
    const [x0, y0, x1, y1] = [p[0], p[1], p[2], p[3]];
    const [xa, ya, xb, yb] = [p[n - 4], p[n - 3], p[n - 2], p[n - 1]];
    if (x0 < L && x1 > L) {
      p[1] = y0 + (y1 - y0) * (L - x0) / (x1 - x0);
      p[0] = L;
    }
    if (xb > R && xa < R) {
      p[n - 1] = ya + (yb - ya) * (R - xa) / (xb - xa);
      p[n - 2] = R;
    }
  }

  bitir() {
    const p = this.p;
    if (p.length >= 4) {
      if (this.hamKip) this.kenarCek();
      this.komutlar.push({ tur: 'cizgi', rol: 'seri', noktalar: Float64Array.from(p), ...this.ozellik });
    } else if (p.length === 2) {
      const x = p[0];
      if (x >= this.alan.x - 1 && x <= this.alan.x + this.alan.w + 1) {
        this.komutlar.push({
          tur: 'nokta', rol: 'seri', x, y: p[1], r: Math.max(1, this.ozellik.kalinlik), renk: this.ozellik.renk,
          kanal: this.ozellik.kanal,
        });
      }
    }
    this.p = [];
    this.sonY = NaN;
  }
}

/** y ekseni dönüştürücüsü (eksen = {min, maks}). */
function yCevirici(alan, eks) {
  const olcek = alan.h / (eks.maks - eks.min);
  const taban = alan.y + alan.h;
  return (v) => taban - (v - eks.min) * olcek;
}

/**
 * Çizim planı (katman 2): düz komut listesi, CSS px.
 * Komutlar: {tur:'cizgi', noktalar: Float64Array [x0,y0,x1,y1,…], renk, kalinlik, desen?, rol, kanal?}
 *           {tur:'nokta', x, y, r, renk, rol, kanal} · {tur:'dikdortgen', x, y, w, h, dolgu?, saydamlik?, kenar?, kalinlik?, rol}
 *           {tur:'yazi', x, y, metin, renk, hiza, taban, rol} · {tur:'kirp', x, y, w, h} · {tur:'kirpBitir'}
 * `renk`/`dolgu`/`kenar` CSS değişkeni ADI (çizici çözer). Sıra: zemin/ızgara → seçim bandı →
 * kanallar (kırpılmış) → gezgin penceresi → olay işaretleri → imleçler → eksen yazıları.
 * @returns {{alan, gezgin, x, eksenler, kanallar: Array<{ad, kip, duzey, eksen}|null>, komutlar}}
 */
/**
 * OLAY İŞARETLERİ (3F, karar PL3): `secenek.isaretler = [{ t, metin?, renk? }]` — ana grafikte
 * x = t'de kesik dikey çizgi (rol 'isaret') + alt köşede kısa etiket. Etiket ÇAĞIRANDAN ve
 * yalnız simge/numara olmalı (G8: plan dil metni taşımaz; ör. DCIR için "R3"). Sonlu olmayan t
 * atılır; pencere dışındakiler çizilmez; gezginde çizilmez.
 */
export function isaretListesi(secenek) {
  const l = secenek && Array.isArray(secenek.isaretler) ? secenek.isaretler : [];
  return l.filter((s) => s && Number.isFinite(s.t));
}

export function cizimPlani(seriler, durum, boyut, secenek = {}) {
  const p = pencereHesapla(seriler, durum, boyut, secenek);
  const { alan, gezgin } = p;
  const komutlar = [];
  const kanallar = [];
  const plan = { alan, gezgin, x: p.x, eksenler: p.eksenler, kanallar, komutlar };
  const { t0: x0, t1: x1 } = p.x;
  if (alan.w < 1 || alan.h < 1 || !(x1 > x0)) return plan;
  const xOlcek = alan.w / (x1 - x0);
  const tx = (t) => alan.x + (t - x0) * xOlcek;
  const izgaraEks = p.eksenler.sol || p.eksenler.sag;

  if (gezgin) {
    komutlar.push({ tur: 'dikdortgen', rol: 'zemin', x: alan.x, y: alan.y, w: alan.w, h: alan.h, dolgu: 'gezgin', saydamlik: 1 });
  } else {
    for (const t of p.x.degerler) {
      const x = Math.round(tx(t)) + 0.5;
      komutlar.push({ tur: 'cizgi', rol: 'izgara', renk: 'izgara', kalinlik: 1, noktalar: Float64Array.of(x, alan.y, x, alan.y + alan.h) });
    }
    if (izgaraEks) {
      const ty = yCevirici(alan, izgaraEks);
      for (const v of izgaraEks.degerler) {
        const y = Math.round(ty(v)) + 0.5;
        komutlar.push({ tur: 'cizgi', rol: 'izgara', renk: 'izgara', kalinlik: 1, noktalar: Float64Array.of(alan.x, y, alan.x + alan.w, y) });
      }
    }
    const A = durum.imlecA;
    const B = durum.imlecB;
    if (Number.isFinite(A) && Number.isFinite(B)) {
      const sa = Math.max(A, x0);
      const sb = Math.min(B, x1);
      if (sb > sa) {
        komutlar.push({ tur: 'dikdortgen', rol: 'secim', x: tx(sa), y: alan.y, w: tx(sb) - tx(sa), h: alan.h, dolgu: 'imlec', saydamlik: 0.07 });
      }
    }
  }

  komutlar.push({ tur: 'kirp', x: alan.x, y: alan.y, w: alan.w, h: alan.h });
  for (let k = 0; k < seriler.length; k++) {
    const s = seriler[k];
    const q = p.sorgular[k];
    if (!q) {
      kanallar.push(null);
      continue;
    }
    const eksen = s.eksen === 'sag' ? 'sag' : 'sol';
    const ty = yCevirici(alan, p.eksenler[eksen]);
    kanallar.push({ ad: s.ad, kip: q.tur, duzey: q.tur === 'ozet' ? q.duzey : 0, eksen });
    const ozellik = { renk: s.renk || 'volt', kalinlik: s.kalinlik ?? (gezgin ? 1 : 1.5), kanal: k };
    if (Array.isArray(s.desen) && s.desen.length) ozellik.desen = s.desen; // 3G: renge ek ayirt edici (KR2)
    const ciz = new CizgiYapici(komutlar, alan, ozellik, q.tur === 'ham');
    if (q.tur === 'ham') {
      const bolumler = q.bolumler ?? [[q.i0, q.i1]];
      for (const [bas, son] of bolumler) {
        for (let i = bas; i < son; i++) {
          const v = s.y[i];
          if (v !== v) { // NaN: eksik örnek, çizgi kesilir
            ciz.bitir();
            continue;
          }
          ciz.ekle(tx(s.t[i]), ty(v));
        }
        ciz.bitir(); // BOŞLUK: bölüm sonu çizgiyi keser
      }
    } else {
      const st = q.sutunlar;
      const kesik = q.kesik;
      for (let c = 0; c < alan.w; c++) {
        if (kesik !== undefined && kesik[c] === 1) ciz.bitir();
        const mn = st[2 * c];
        const mx = st[2 * c + 1];
        if (mn !== mn) { // boş sütun (veri yok / hepsi NaN): kesik
          ciz.bitir();
          continue;
        }
        const x = alan.x + c + 0.5;
        const yMin = ty(mn);
        const yMaks = ty(mx);
        if (yMin === yMaks) ciz.ekle(x, yMin);
        else if (Math.abs(yMin - ciz.sonY) <= Math.abs(yMaks - ciz.sonY)) {
          ciz.ekle(x, yMin);
          ciz.ekle(x, yMaks);
        } else {
          ciz.ekle(x, yMaks);
          ciz.ekle(x, yMin);
        }
      }
      ciz.bitir();
    }
  }
  komutlar.push({ tur: 'kirpBitir' });

  if (gezgin) {
    let xa = tx(Math.max(durum.t0, x0));
    let xb = tx(Math.min(durum.t1, x1));
    if (xb - xa < 2) { // çok dar pencere de görünsün
      const m = (xa + xb) / 2;
      xa = m - 1;
      xb = m + 1;
    }
    komutlar.push({
      tur: 'dikdortgen', rol: 'pencere', x: xa, y: alan.y + 0.75, w: xb - xa, h: alan.h - 1.5,
      dolgu: 'vurgu', saydamlik: 0.12, kenar: 'vurgu', kalinlik: 1.5,
    });
    return plan;
  }

  for (const s of isaretListesi(secenek)) {
    if (s.t < x0 || s.t > x1) continue;
    const x = Math.round(tx(s.t)) + 0.5;
    const renk = s.renk || 'soluk';
    komutlar.push({ tur: 'cizgi', rol: 'isaret', renk, kalinlik: 1, desen: [3, 3], noktalar: Float64Array.of(x, alan.y, x, alan.y + alan.h) });
    if (s.metin) komutlar.push({ tur: 'yazi', rol: 'isaret', x: x + 3, y: alan.y + alan.h - 2, metin: String(s.metin), renk, hiza: 'left', taban: 'bottom' });
  }

  for (const [ad, t, desen] of [['A', durum.imlecA, null], ['B', durum.imlecB, [6, 4]]]) {
    if (!Number.isFinite(t) || t < x0 || t > x1) continue;
    const x = tx(t);
    const cizgi = { tur: 'cizgi', rol: 'imlec', renk: 'imlec', kalinlik: 1.5, noktalar: Float64Array.of(x, alan.y, x, alan.y + alan.h) };
    if (desen) cizgi.desen = desen;
    komutlar.push(cizgi);
    komutlar.push({ tur: 'yazi', rol: 'imlec', x: x + 4, y: alan.y + 2, metin: ad, renk: 'imlec', hiza: 'left', taban: 'top' });
  }

  for (const t of p.x.degerler) {
    komutlar.push({
      tur: 'yazi', rol: 'eksen', x: tx(t), y: alan.y + alan.h + 5, metin: xYazici(secenek)(t - p.x.koken, p.x.adim),
      renk: 'soluk', hiza: 'center', taban: 'top',
    });
  }
  for (const ad of ['sol', 'sag']) {
    const eks = p.eksenler[ad];
    if (!eks) continue;
    const ty = yCevirici(alan, eks);
    const x = ad === 'sol' ? alan.x - 6 : alan.x + alan.w + 6;
    const hiza = ad === 'sol' ? 'right' : 'left';
    for (const v of eks.degerler) {
      komutlar.push({ tur: 'yazi', rol: 'eksen', x, y: ty(v), metin: sayiYazi(v, eks.adim), renk: 'soluk', hiza, taban: 'middle' });
    }
    if (eks.birim) komutlar.push({ tur: 'yazi', rol: 'eksen', x, y: 2, metin: eks.birim, renk: 'soluk', hiza, taban: 'top' });
  }
  return plan;
}

/** Lejant (çağıranın HTML'i için; erişilebilir metin kanvasta değil). */
export function lejantOgeleri(seriler) {
  return seriler.filter((s) => !s.gizli).map((s) => ({
    ad: s.ad, birim: s.birim || '', renk: s.renk || 'volt', eksen: s.eksen === 'sag' ? 'sag' : 'sol',
  }));
}

// ── 3. DURUM + ETKİLEŞİM (saf indirgeyici) ────────────────────────────────

/** Tipik örnek aralığı: en çok 2049 eşit aralıklı farkın (> 0) ortancası; yoksa NaN. */
export function tipikAralik(t) {
  const n = t.length;
  if (n < 2) return NaN;
  const adet = Math.min(n - 1, 2049);
  const farklar = [];
  for (let j = 0; j < adet; j++) {
    const i = Math.floor(j * (n - 1) / adet);
    const d = t[i + 1] - t[i];
    if (d > 0) farklar.push(d);
  }
  if (!farklar.length) return NaN;
  farklar.sort((p, q) => p - q);
  return farklar[farklar.length >> 1];
}

/**
 * Başlangıç durumu: pencere = bütün veri, imleç yok.
 * durum = {veriT0, veriT1, enAzPencere, t0, t1, imlecA, imlecB, etkinImlec, fareT,
 *          isaretciler: {id: {x}}, suruklenen}
 */
export function durumKur(seriler = []) {
  let veriT0 = Infinity;
  let veriT1 = -Infinity;
  let tipik = Infinity;
  for (const s of seriler) {
    const t = s && s.t;
    const n = t ? t.length : 0;
    if (!n) continue;
    if (t[0] < veriT0) veriT0 = t[0];
    if (t[n - 1] > veriT1) veriT1 = t[n - 1];
    const d = tipikAralik(t);
    if (d < tipik) tipik = d;
  }
  if (!(veriT1 >= veriT0)) {
    veriT0 = 0;
    veriT1 = 1;
  }
  let enAzPencere = Number.isFinite(tipik) ? EN_AZ_ORNEK * tipik : 1;
  if (!(veriT1 > veriT0)) { // tek zaman damgası: yapay genişlik
    veriT0 -= enAzPencere / 2;
    veriT1 += enAzPencere / 2;
  }
  if (enAzPencere > veriT1 - veriT0) enAzPencere = veriT1 - veriT0;
  return {
    veriT0, veriT1, enAzPencere, t0: veriT0, t1: veriT1,
    imlecA: null, imlecB: null, etkinImlec: null, fareT: null, isaretciler: {}, suruklenen: null,
  };
}

/** Pencere genişliğini [enAzPencere, bütün veri] aralığına sınırlar (NaN → en dar). */
export function aralikSinirla(durum, aralik) {
  const tam = durum.veriT1 - durum.veriT0;
  if (!(aralik >= durum.enAzPencere)) aralik = durum.enAzPencere; // EN AZ PENCERE
  return aralik > tam ? tam : aralik;
}

/** Pencereyi veri aralığına kırpar (G4); genişlik sınırlanırsa orta korunur. */
export function pencereKirp(durum, t0, t1) {
  if (!Number.isFinite(t0) || !Number.isFinite(t1)) return { t0: durum.t0, t1: durum.t1 };
  const { veriT0, veriT1 } = durum;
  const aralik = aralikSinirla(durum, t1 - t0);
  let bas = aralik === t1 - t0 ? t0 : (t0 + t1) / 2 - aralik / 2;
  if (bas + aralik > veriT1) bas = veriT1 - aralik; // KIRP: sağ uç
  if (bas < veriT0) bas = veriT0; // KIRP: sol uç
  return { t0: bas, t1: Math.min(bas + aralik, veriT1) };
}

/** `tOdak` ekranda yerinde kalarak pencereyi `oran` kadar ölçekler (oran < 1 yakınlaştırır). */
export function yakinlastir(durum, tOdak, oran) {
  const aralik = durum.t1 - durum.t0;
  const yeni = aralikSinirla(durum, aralik * oran);
  if (yeni === aralik) return { t0: durum.t0, t1: durum.t1 }; // sınırda: kayma birikmesin
  const kesir = (tOdak - durum.t0) / aralik;
  const t0 = tOdak - kesir * yeni; // ODAK SABİT
  return pencereKirp(durum, t0, t0 + yeni);
}

function pencereYaz(durum, w) {
  if (w.t0 === durum.t0 && w.t1 === durum.t1) return durum;
  return { ...durum, t0: w.t0, t1: w.t1 };
}

const veriyeKirp = (durum, t) => Math.min(durum.veriT1, Math.max(durum.veriT0, t));
const alanVar = (olay) => !!(olay && olay.alan && olay.alan.w > 0);

/** Olayın x alanı: ana grafikte pencere, gezginde bütün veri. */
function xAlani(durum, olay) {
  return olay.gezgin ? [durum.veriT0, durum.veriT1] : [durum.t0, durum.t1];
}

function xdenT(durum, olay, x = olay.x) {
  const [d0, d1] = xAlani(durum, olay);
  return d0 + (x - olay.alan.x) / olay.alan.w * (d1 - d0);
}

function tdenX(durum, olay, t) {
  const [d0, d1] = xAlani(durum, olay);
  return olay.alan.x + (t - d0) / (d1 - d0) * olay.alan.w;
}

/** İmleci yazar; A ≤ B bozulursa takas eder (G5), sürüklenen çizgi ve etkin imleç izler. */
function imlecYaz(d, hangi, t) {
  let A = hangi === 'A' ? t : d.imlecA;
  let B = hangi === 'B' ? t : d.imlecB;
  let etkin = hangi;
  let s = d.suruklenen;
  if (Number.isFinite(A) && Number.isFinite(B) && A > B) { // SIRALA: A ≤ B
    [A, B] = [B, A];
    etkin = hangi === 'A' ? 'B' : 'A';
    if (s && (s.tur === 'imlecA' || s.tur === 'imlecB')) s = { ...s, tur: s.tur === 'imlecA' ? 'imlecB' : 'imlecA' };
  }
  if (A === d.imlecA && B === d.imlecB && etkin === d.etkinImlec && s === d.suruklenen) return d;
  return { ...d, imlecA: A, imlecB: B, etkinImlec: etkin, suruklenen: s };
}

function imlecYakala(durum, olay) {
  let en = null;
  let enMesafe = YAKALAMA_PX;
  for (const [ad, t] of [['imlecA', durum.imlecA], ['imlecB', durum.imlecB]]) {
    if (!Number.isFinite(t) || t < durum.t0 || t > durum.t1) continue;
    const m = Math.abs(tdenX(durum, olay, t) - olay.x);
    if (m <= enMesafe) {
      en = ad;
      enMesafe = m;
    }
  }
  return en;
}

function gezginBasla(durum, olay, id) {
  const xs = tdenX(durum, olay, durum.t0);
  const xe = tdenX(durum, olay, durum.t1);
  const x = olay.x;
  const genis = xe - xs >= 3 * YAKALAMA_PX;
  if (genis ? Math.abs(x - xs) <= YAKALAMA_PX : (x < xs && xs - x <= YAKALAMA_PX)) {
    return { suruklenen: { tur: 'gezginSol', id } };
  }
  if (genis ? Math.abs(x - xe) <= YAKALAMA_PX : (x > xe && x - xe <= YAKALAMA_PX)) {
    return { suruklenen: { tur: 'gezginSag', id } };
  }
  let { t0, t1 } = durum;
  if (x < xs || x > xe) { // dışarı tıklama: pencere oraya ortalanır, sürükleme sürer
    const t = xdenT(durum, olay);
    const yarim = (t1 - t0) / 2;
    ({ t0, t1 } = pencereKirp(durum, t - yarim, t + yarim));
  }
  return { t0, t1, suruklenen: { tur: 'gezginTasi', id, xBas: x, t0Bas: t0, t1Bas: t1 } };
}

function basla(durum, olay) {
  if (!alanVar(olay)) return durum;
  const id = String(olay.id);
  const isaretciler = { ...durum.isaretciler, [id]: { x: olay.x } };
  const idler = Object.keys(isaretciler);
  if (idler.length >= 2) {
    if (olay.gezgin) return { ...durum, isaretciler };
    const a = idler.find((k) => k !== id);
    const tA = xdenT(durum, olay, isaretciler[a].x);
    const tB = xdenT(durum, olay);
    return { ...durum, isaretciler, suruklenen: { tur: 'kiskac', a, b: id, tA, tB } };
  }
  if (olay.gezgin) return { ...durum, isaretciler, ...gezginBasla(durum, olay, id) };
  const hedef = imlecYakala(durum, olay);
  if (hedef) {
    return { ...durum, isaretciler, suruklenen: { tur: hedef, id }, etkinImlec: hedef === 'imlecA' ? 'A' : 'B' };
  }
  return { ...durum, isaretciler, suruklenen: { tur: 'kaydir', id, xBas: olay.x, t0Bas: durum.t0, t1Bas: durum.t1 } };
}

function hareket(durum, olay) {
  if (!alanVar(olay)) return durum;
  const id = String(olay.id);
  if (!durum.isaretciler[id]) { // basılı değil: yalnız fare konumu (klavye A/B için)
    if (olay.gezgin) return durum;
    const fareT = xdenT(durum, olay);
    return fareT === durum.fareT ? durum : { ...durum, fareT };
  }
  const isaretciler = { ...durum.isaretciler, [id]: { x: olay.x } };
  const d = { ...durum, isaretciler };
  const s = durum.suruklenen;
  if (!s) return d;
  const w = olay.alan.w;
  switch (s.tur) {
    case 'kaydir': {
      if (s.id !== id) return d;
      const kayma = (olay.x - s.xBas) / w * (s.t1Bas - s.t0Bas);
      return { ...d, ...pencereKirp(durum, s.t0Bas - kayma, s.t1Bas - kayma) };
    }
    case 'imlecA':
    case 'imlecB': {
      if (s.id !== id) return d;
      return imlecYaz(d, s.tur === 'imlecA' ? 'A' : 'B', veriyeKirp(durum, xdenT(durum, olay)));
    }
    case 'kiskac': {
      const pa = isaretciler[s.a];
      const pb = isaretciler[s.b];
      if (!pa || !pb) return d;
      const dx = pb.x - pa.x;
      const dt = s.tB - s.tA;
      if (Math.abs(dx) < KISKAC_EN_AZ_PX || dt === 0 || (dx > 0) !== (dt > 0)) return d;
      const aralik = aralikSinirla(durum, dt * w / dx);
      const tOrta = (s.tA + s.tB) / 2; // iki parmağın ortasındaki zaman yerinde kalır
      const t0 = tOrta - ((pa.x + pb.x) / 2 - olay.alan.x) / w * aralik;
      return { ...d, ...pencereKirp(durum, t0, t0 + aralik) };
    }
    case 'gezginTasi': {
      if (s.id !== id) return d;
      const kayma = (olay.x - s.xBas) / w * (durum.veriT1 - durum.veriT0);
      return { ...d, ...pencereKirp(durum, s.t0Bas + kayma, s.t1Bas + kayma) };
    }
    case 'gezginSol': {
      if (s.id !== id) return d;
      const t = Math.min(xdenT(durum, olay), durum.t1 - durum.enAzPencere);
      return { ...d, ...pencereKirp(durum, Math.max(t, durum.veriT0), durum.t1) };
    }
    case 'gezginSag': {
      if (s.id !== id) return d;
      const t = Math.max(xdenT(durum, olay), durum.t0 + durum.enAzPencere);
      return { ...d, ...pencereKirp(durum, durum.t0, Math.min(t, durum.veriT1)) };
    }
    default:
      return d;
  }
}

function bitir(durum, olay) {
  const id = String(olay.id);
  if (!durum.isaretciler[id]) return durum;
  const isaretciler = { ...durum.isaretciler };
  delete isaretciler[id];
  const kalan = Object.keys(isaretciler);
  let s = durum.suruklenen;
  if (s && s.tur === 'kiskac') { // bir parmak kalırsa sıçramadan kaydırmaya geçilir
    s = kalan.length === 1 && !olay.gezgin
      ? { tur: 'kaydir', id: kalan[0], xBas: isaretciler[kalan[0]].x, t0Bas: durum.t0, t1Bas: durum.t1 }
      : null;
  } else if (s && s.id === id) s = null;
  if (kalan.length === 0) s = null;
  return { ...durum, isaretciler, suruklenen: s };
}

function tekerlek(durum, olay) {
  if (!alanVar(olay)) return durum;
  const dy = Number(olay.dy) || 0;
  const dx = Number(olay.dx) || 0;
  if (Math.abs(dx) > Math.abs(dy)) { // yatay tekerlek / dokunmatik yüzey: kaydır
    const [d0, d1] = xAlani(durum, olay);
    const kayma = dx / olay.alan.w * (d1 - d0);
    return pencereYaz(durum, pencereKirp(durum, durum.t0 + kayma, durum.t1 + kayma));
  }
  if (dy === 0) return durum;
  const oran = Math.exp(dy * TEKERLEK_KATSAYI);
  const tOdak = olay.gezgin ? (durum.t0 + durum.t1) / 2 : xdenT(durum, olay);
  return pencereYaz(durum, yakinlastir(durum, tOdak, oran));
}

function tus(durum, olay) {
  const k = olay.tus;
  const aralik = durum.t1 - durum.t0;
  const orta = (durum.t0 + durum.t1) / 2;
  switch (k) {
    case '+':
    case '=':
      return pencereYaz(durum, yakinlastir(durum, orta, 1 / TUS_ORAN));
    case '-':
    case '_':
      return pencereYaz(durum, yakinlastir(durum, orta, TUS_ORAN));
    case 'ArrowLeft':
    case 'ArrowRight': {
      const yon = k === 'ArrowLeft' ? -1 : 1;
      const hangi = durum.etkinImlec;
      const tImlec = hangi === 'A' ? durum.imlecA : hangi === 'B' ? durum.imlecB : NaN;
      if (olay.shift && !olay.gezgin && Number.isFinite(tImlec)) {
        return imlecYaz(durum, hangi, veriyeKirp(durum, tImlec + yon * IMLEC_TUS_ADIM * aralik));
      }
      const kayma = yon * TUS_KAYDIR * aralik;
      return pencereYaz(durum, pencereKirp(durum, durum.t0 + kayma, durum.t1 + kayma));
    }
    case 'Home':
      return pencereYaz(durum, { t0: durum.veriT0, t1: durum.veriT1 });
    case 'Escape':
      if (durum.imlecA === null && durum.imlecB === null) return durum;
      return { ...durum, imlecA: null, imlecB: null, etkinImlec: null };
    case 'a':
    case 'A':
    case 'b':
    case 'B': {
      if (olay.gezgin) return durum;
      const hangi = k.toUpperCase();
      const fare = durum.fareT;
      const t = Number.isFinite(fare) && fare >= durum.t0 && fare <= durum.t1
        ? fare : durum.t0 + aralik * (hangi === 'A' ? 1 / 3 : 2 / 3);
      return imlecYaz(durum, hangi, veriyeKirp(durum, t));
    }
    default:
      return durum;
  }
}

function imlecKoy(durum, olay) {
  let t = Number.isFinite(olay.t) ? olay.t : alanVar(olay) ? xdenT(durum, olay) : NaN;
  if (!Number.isFinite(t)) return durum;
  t = veriyeKirp(durum, t);
  let hangi = olay.hangi;
  if (hangi !== 'A' && hangi !== 'B') {
    if (!Number.isFinite(durum.imlecA)) hangi = 'A';
    else if (!Number.isFinite(durum.imlecB)) hangi = 'B';
    else hangi = Math.abs(t - durum.imlecA) <= Math.abs(t - durum.imlecB) ? 'A' : 'B';
  }
  return imlecYaz(durum, hangi, t);
}

/**
 * Saf indirgeyici (katman 3). Değişiklik yoksa AYNI nesneyi döndürür.
 * Olaylar (x CSS px, `alan` = plan.alan, `gezgin` = gezgin şeridi mi):
 *   {tur:'tekerlek', x, dy, dx?, alan, gezgin?}        dy > 0 uzaklaştırır
 *   {tur:'basla'|'hareket'|'bitir', id, x, alan, gezgin?}  işaretçi (fare/parmak/kalem);
 *       basılı değilken 'hareket' yalnız `fareT`'yi günceller
 *   {tur:'ayril'}                                        işaretçi grafikten çıktı
 *   {tur:'tus', tus, shift?, alan, gezgin?}              + − ← → (Shift: etkin imleç) A B Home Escape
 *   {tur:'imlecKoy', hangi?: 'A'|'B', t? | x + alan}     hangi yoksa boş olana / en yakına
 *   {tur:'pencere', t0, t1}                              programdan pencere (kırpılır)
 */
export function etkilesim(durum, olay) {
  if (!olay || typeof olay.tur !== 'string') return durum;
  switch (olay.tur) {
    case 'tekerlek': return tekerlek(durum, olay);
    case 'basla': return basla(durum, olay);
    case 'hareket': return hareket(durum, olay);
    case 'bitir': return bitir(durum, olay);
    case 'ayril': return durum.fareT === null ? durum : { ...durum, fareT: null };
    case 'tus': return tus(durum, olay);
    case 'imlecKoy': return imlecKoy(durum, olay);
    case 'pencere': return pencereYaz(durum, pencereKirp(durum, olay.t0, olay.t1));
    default: return durum;
  }
}

/**
 * Dışarıdan gelen ortak alanları (t0, t1, imlecA, imlecB) bu grafiğin verisine kırparak
 * uygular — eş imleç / gezgin ↔ ana grafik eşlemesi. Etkileşim durumu (işaretçiler) korunur.
 */
export function durumBirlestir(durum, parca = {}) {
  let d = durum;
  if (Number.isFinite(parca.t0) && Number.isFinite(parca.t1)) d = pencereYaz(d, pencereKirp(d, parca.t0, parca.t1));
  if ('imlecA' in parca || 'imlecB' in parca) {
    let A = 'imlecA' in parca ? parca.imlecA : d.imlecA;
    let B = 'imlecB' in parca ? parca.imlecB : d.imlecB;
    A = Number.isFinite(A) ? veriyeKirp(d, A) : null;
    B = Number.isFinite(B) ? veriyeKirp(d, B) : null;
    if (A !== null && B !== null && A > B) [A, B] = [B, A];
    if (A !== d.imlecA || B !== d.imlecB) d = { ...d, imlecA: A, imlecB: B };
  }
  return d;
}

// ── 4. İMLEÇ OKUMASI (HAM veri) ───────────────────────────────────────────

/** x'e en yakın NaN'sız HAM örnek (ikili arama + NaN'ları atlayarak). Yoksa null. */
export function enYakinOrnek(t, y, x) {
  const n = t.length;
  if (!n || !Number.isFinite(x)) return null;
  const i = altSinir(t, x);
  let sag = i;
  while (sag < n && y[sag] !== y[sag]) sag++;
  let sol = i - 1;
  while (sol >= 0 && y[sol] !== y[sol]) sol--;
  let k = -1;
  if (sol >= 0 && sag < n) k = x - t[sol] <= t[sag] - x ? sol : sag;
  else if (sol >= 0) k = sol;
  else if (sag < n) k = sag;
  return k < 0 ? null : { i: k, t: t[k], deger: y[k] };
}

function seriBul(seriler, ad, birim) {
  if (ad !== undefined && ad !== null) return seriler.find((s) => s.ad === ad) || null;
  return seriler.find((s) => s.birim === birim) || null;
}

function ayniZaman(p, q) {
  if (p === q) return true;
  if (!p || !q || p.length !== q.length) return false;
  for (let i = 0; i < p.length; i++) if (p[i] !== q[i]) return false;
  return true;
}

/**
 * İmleç okuması (katman 4, G5) — HER ŞEY HAM veriden (D4):
 *   kanallar[k] = {ad, birim, a: {i, t, deger}|null, b, fark (= b − a), istat (A–B aralığı)}
 *   enerji = {wh, mah, sureS} | null — gerilim ('V') ve akım ('A') kanalları varsa ve aynı
 *            zaman dizisindeyse; boşluk (boslukMs) üstünden integral yok.
 *   dV (gerilim kanalının farkı), ortI (akım kanalının A–B ortalaması) okuma satırı için.
 * tA > tB verilirse sıralanır. Tek imleç: yalnız değerler, istatistik null.
 * @param {{gerilim?: string, akim?: string}} [secenek] kanal adları (yoksa birimden bulunur)
 */
export function imlecOkuma(seriler, tA, tB, { gerilim, akim } = {}) {
  const varA = Number.isFinite(tA);
  const varB = Number.isFinite(tB);
  if (varA && varB && tA > tB) [tA, tB] = [tB, tA];
  const ikisi = varA && varB;
  const kanallar = seriler.map((s) => {
    const a = varA ? enYakinOrnek(s.t, s.y, tA) : null;
    const b = varB ? enYakinOrnek(s.t, s.y, tB) : null;
    const istat = ikisi ? istatistik(s.t, s.y, tA, tB) : null; // HAM (D4)
    return { ad: s.ad, birim: s.birim || '', a, b, fark: a && b ? b.deger - a.deger : NaN, istat };
  });
  const v = seriBul(seriler, gerilim, 'V');
  const i = seriBul(seriler, akim, 'A');
  let enerjiSonuc = null;
  if (ikisi && v && i && v !== i && ayniZaman(v.t, i.t)) {
    const boslukMs = v.boslukMs ?? i.boslukMs;
    enerjiSonuc = enerji(v.t, v.y, i.y, tA, tB, { boslukMs });
  }
  const kv = v ? kanallar[seriler.indexOf(v)] : null;
  const ki = i ? kanallar[seriler.indexOf(i)] : null;
  return {
    tA: varA ? tA : NaN,
    tB: varB ? tB : NaN,
    dt: ikisi ? tB - tA : NaN,
    kanallar,
    enerji: enerjiSonuc,
    dV: kv ? kv.fark : NaN,
    ortI: ki && ki.istat ? ki.istat.ort : NaN,
  };
}

// ── İNCE ÇİZİCİ ───────────────────────────────────────────────────────────

/** Seriyi çizime hazırlar: eksen adı düzelir, piramit (yoksa) bir kez kurulur. */
export function seriHazirla(s) {
  if (!s || !s.t || !s.y || s.t.length !== s.y.length) {
    throw new RangeError(`seriHazirla: t ve y aynı uzunlukta olmalı (${s && s.ad})`);
  }
  const oz = s.oz && s.oz.t === s.t && s.oz.y === s.y ? s.oz : ozetKur(s.t, s.y);
  return { ...s, eksen: s.eksen === 'sag' ? 'sag' : 'sol', oz };
}

/** Varsayılan renk okuyucu: canvas'ın hesaplanmış stilinden `--<ad>` (ve eşdeğerleri). */
export function cssRenk(eleman, pencere = globalThis) {
  return (ad) => {
    const gcs = pencere && pencere.getComputedStyle;
    if (typeof gcs !== 'function') return '';
    const stil = gcs.call(pencere, eleman);
    if (!stil || typeof stil.getPropertyValue !== 'function') return '';
    for (const aday of [ad, ...(RENK_ESDEGER[ad] || [])]) {
      const v = stil.getPropertyValue('--' + aday);
      if (v && v.trim()) return v.trim();
    }
    return '';
  };
}

/** Planı bir 2B bağlamına uygular. `renk(ad)` çözülmüş renk dizgisi döndürür. */
export function planUygula(ctx, plan, renk, yaziTipi = YAZI_TIPI) {
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.font = yaziTipi;
  for (const k of plan.komutlar) {
    switch (k.tur) {
      case 'cizgi': {
        const p = k.noktalar;
        ctx.strokeStyle = renk(k.renk);
        ctx.lineWidth = k.kalinlik;
        ctx.setLineDash(k.desen || []);
        ctx.beginPath();
        ctx.moveTo(p[0], p[1]);
        for (let i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]);
        ctx.stroke();
        break;
      }
      case 'nokta':
        ctx.fillStyle = renk(k.renk);
        ctx.beginPath();
        ctx.arc(k.x, k.y, k.r, 0, 2 * Math.PI);
        ctx.fill();
        break;
      case 'dikdortgen':
        if (k.dolgu) {
          ctx.globalAlpha = k.saydamlik ?? 1;
          ctx.fillStyle = renk(k.dolgu);
          ctx.fillRect(k.x, k.y, k.w, k.h);
          ctx.globalAlpha = 1;
        }
        if (k.kenar) {
          ctx.strokeStyle = renk(k.kenar);
          ctx.lineWidth = k.kalinlik ?? 1;
          ctx.setLineDash([]);
          ctx.strokeRect(k.x, k.y, k.w, k.h);
        }
        break;
      case 'yazi':
        ctx.fillStyle = renk(k.renk);
        ctx.textAlign = k.hiza;
        ctx.textBaseline = k.taban;
        ctx.fillText(k.metin, k.x, k.y);
        break;
      case 'kirp':
        ctx.save();
        ctx.beginPath();
        ctx.rect(k.x, k.y, k.w, k.h);
        ctx.clip();
        break;
      case 'kirpBitir':
        ctx.restore();
        break;
      default:
        break;
    }
  }
  ctx.setLineDash([]);
}

const OLAYLAR = ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'pointerleave', 'dblclick', 'wheel', 'keydown'];

/**
 * İnce çizici (G7). Kullanım:
 *   const g = new Grafik(canvas, { onDegisim: (durum) => …, gezgin: false });
 *   canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', …)  // ÇAĞIRAN
 *   g.veriAyarla([{ ad: 'V', t, y, birim: 'V', renk: 'volt' }, …]);
 *   g.durumAyarla({ t0, t1, imlecA, imlecB });  // eşleme (onDegisim ÇAĞRILMAZ)
 *   g.okuma();  // imlecOkuma
 *   g.ciz();    // görünüm (renk) değişince
 *   g.yokEt();
 * secenek: { gezgin, renk(ad), onDegisim(durum, grafik), pencere, kenar, zamanKokeni,
 *            yaziTipi, gerilim, akim, xEksen, isaretler }   (isaretler: 3F — sonradan
 *            `g.secenek.isaretler = …; g.ciz()` ile de değişir)
 */
export class Grafik {
  constructor(canvas, secenek = {}) {
    if (!canvas || typeof canvas.getContext !== 'function') throw new TypeError('Grafik: canvas gerekli');
    this.canvas = canvas;
    this.secenek = { ...secenek };
    this.gezgin = !!secenek.gezgin;
    this.pencere = secenek.pencere || globalThis;
    this.renk = typeof secenek.renk === 'function' ? secenek.renk : cssRenk(canvas, this.pencere);
    this.onDegisim = typeof secenek.onDegisim === 'function' ? secenek.onDegisim : null;
    this.ctx = canvas.getContext('2d');
    this.seriler = [];
    this.durum = durumKur([]);
    this.sonPlan = null;
    this._bekleyen = 0;
    this._yok = false;
    if (canvas.style) canvas.style.touchAction = 'none';
    if (typeof canvas.tabIndex === 'number' && canvas.tabIndex < 0) canvas.tabIndex = 0; // klavye için odaklanabilir
    this._dinle = {
      pointerdown: (e) => this._isaretci('basla', e),
      pointermove: (e) => this._isaretci('hareket', e),
      pointerup: (e) => this._isaretci('bitir', e),
      pointercancel: (e) => this._isaretci('bitir', e),
      pointerleave: () => this._uygula(etkilesim(this.durum, { tur: 'ayril' })),
      dblclick: (e) => this._cift(e),
      wheel: (e) => this._tekerlek(e),
      keydown: (e) => this._tus(e),
    };
    for (const tur of OLAYLAR) {
      canvas.addEventListener(tur, this._dinle[tur], tur === 'wheel' ? { passive: false } : false);
    }
  }

  /** Kanalları ayarlar; piramitler kurulur. koru: pencere ve imleçler (kırpılarak) kalır. */
  veriAyarla(seriler, { koru = false } = {}) {
    if (this._yok) return;
    this.seriler = (seriler || []).map(seriHazirla);
    const yeni = durumKur(this.seriler);
    const eski = this.durum;
    this.durum = koru
      ? durumBirlestir(yeni, { t0: eski.t0, t1: eski.t1, imlecA: eski.imlecA, imlecB: eski.imlecB })
      : yeni;
    this.istek();
  }

  /** Dışarıdan ortak alanlar (t0, t1, imlecA, imlecB); onDegisim ÇAĞRILMAZ (eşleme döngüsü yok). */
  durumAyarla(parca) {
    return this._uygula(durumBirlestir(this.durum, parca), true);
  }

  /** İmleç okuması (HAM veri). */
  okuma() {
    return imlecOkuma(this.seriler, this.durum.imlecA, this.durum.imlecB, this.secenek);
  }

  _planSecenek() {
    return { gezgin: this.gezgin, kenar: this.secenek.kenar, zamanKokeni: this.secenek.zamanKokeni,
      xEksen: this.secenek.xEksen, isaretler: this.secenek.isaretler, yOlcek: this.secenek.yOlcek };
  }

  _boyut() {
    return { w: Number(this.canvas.clientWidth) || 0, h: Number(this.canvas.clientHeight) || 0 };
  }

  _alan() {
    const alan = yerlesim(this.seriler, this._boyut(), this._planSecenek());
    return alan.w >= 1 && alan.h >= 1 ? alan : null;
  }

  /** Görünür değişiklik olduysa çizim ister ve (sessiz değilse) onDegisim'i çağırır. */
  _uygula(yeni, sessiz = false) {
    if (this._yok || yeni === this.durum) return false;
    const eski = this.durum;
    this.durum = yeni;
    const gorunur = eski.t0 !== yeni.t0 || eski.t1 !== yeni.t1 || eski.imlecA !== yeni.imlecA || eski.imlecB !== yeni.imlecB;
    if (gorunur) {
      this.istek();
      if (!sessiz && this.onDegisim) this.onDegisim(this.durum, this);
    }
    return gorunur;
  }

  _isaretci(tur, e) {
    const alan = this._alan();
    if (!alan) return;
    if (tur === 'basla') {
      if (typeof this.canvas.focus === 'function') this.canvas.focus({ preventScroll: true });
      try { this.canvas.setPointerCapture?.(e.pointerId); } catch { /* yakalama yoksa da çalışır */ }
    }
    this._uygula(etkilesim(this.durum, { tur, id: e.pointerId, x: e.offsetX, alan, gezgin: this.gezgin }));
  }

  _cift(e) {
    const alan = this._alan();
    if (!alan || this.gezgin) return;
    this._uygula(etkilesim(this.durum, { tur: 'imlecKoy', x: e.offsetX, alan }));
  }

  _tekerlek(e) {
    const alan = this._alan();
    if (!alan) return;
    const k = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? alan.h : 1;
    const yeni = etkilesim(this.durum, {
      tur: 'tekerlek', x: e.offsetX, dy: (e.deltaY || 0) * k, dx: (e.deltaX || 0) * k, alan, gezgin: this.gezgin,
    });
    if (yeni !== this.durum && typeof e.preventDefault === 'function') e.preventDefault(); // sayfa kaymasın
    this._uygula(yeni);
  }

  _tus(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return; // tarayıcı kısayolları (Ctrl + yakınlaştırma) kalır
    const alan = this._alan();
    if (!alan) return;
    const yeni = etkilesim(this.durum, { tur: 'tus', tus: e.key, shift: !!e.shiftKey, alan, gezgin: this.gezgin });
    if (yeni === this.durum) return;
    if (typeof e.preventDefault === 'function') e.preventDefault(); // oklar sayfayı kaydırmasın
    this._uygula(yeni);
  }

  /** Bir sonraki karede çizer (requestAnimationFrame yoksa hemen). */
  istek() {
    if (this._yok) return;
    const raf = this.pencere && this.pencere.requestAnimationFrame;
    if (typeof raf !== 'function') {
      this.ciz();
      return;
    }
    if (this._bekleyen) return;
    this._bekleyen = raf.call(this.pencere, () => {
      this._bekleyen = 0;
      this.ciz();
    });
  }

  /** Şimdi çizer; renkler YENİDEN okunur (görünüm değişimi). Planı döndürür. */
  ciz() {
    if (this._yok) return null;
    const oran = Number(this.pencere && this.pencere.devicePixelRatio);
    const dpr = oran > 0 ? oran : 1;
    const { w, h } = this._boyut();
    const gw = Math.max(0, Math.round(w * dpr));
    const gh = Math.max(0, Math.round(h * dpr));
    if (this.canvas.width !== gw) this.canvas.width = gw;
    if (this.canvas.height !== gh) this.canvas.height = gh;
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, gw, gh);
    if (!(w >= 1 && h >= 1)) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const plan = cizimPlani(this.seriler, this.durum, { w, h }, this._planSecenek());
    this.sonPlan = plan;
    const cozulmus = new Map(); // bu çizim için; sonraki ciz() yeniden okur
    const renk = (ad) => {
      let v = cozulmus.get(ad);
      if (v === undefined) {
        v = String(this.renk(ad) || '').trim() || RENK_YEDEK[ad] || '#888888';
        cozulmus.set(ad, v);
      }
      return v;
    };
    planUygula(ctx, plan, renk, this.secenek.yaziTipi || YAZI_TIPI);
    return plan;
  }

  /** Dinleyicileri kaldırır, bekleyen kareyi iptal eder. */
  yokEt() {
    if (this._yok) return;
    this._yok = true;
    for (const tur of OLAYLAR) {
      this.canvas.removeEventListener(tur, this._dinle[tur], tur === 'wheel' ? { passive: false } : false);
    }
    if (this._bekleyen && this.pencere && typeof this.pencere.cancelAnimationFrame === 'function') {
      this.pencere.cancelAnimationFrame(this._bekleyen);
    }
    this._bekleyen = 0;
    this.onDegisim = null;
    this.seriler = [];
  }
}
