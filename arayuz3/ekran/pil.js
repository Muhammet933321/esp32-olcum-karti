/* ═══════════════════════════════════════════════════════════════════════
   3F — PIL TESTI: EGRI + KAYIT KAYNAGI                      (ekran/pil.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3F kararlari" (PL1-PL7)
   ve "3F uygulama kararlari" (PU1-PU16). EMNIYET (`p0`, acil serit), durum
   makinesi, `/pil` yoklamasi, kartin pil satirlari ve komut ureticileri
   app.js'te (PU1): bu modul INMESE de DURDUR calisir. Burada yalniz:
     * EGRI (PL3): `ortak/grafik.js` — V (sol eksen) + I (sag eksen), x ekseni
       zaman ya da mAh; DCIR anlari grafikte isaret (grafik.js `isaretler`).
       Canli kaynak: app.js'in `/pil` nokta kopyasi (bosluk isareti = NaN, cizgi
       KOPAR — interpolasyon yok). Kayit kaynagi: kartin PIL oturumu.
     * mAh EKSENI (PU9): TARAYICI hesabi — noktalarin yamuk integrali. Okuma
       kartlarindaki mAh / Wh KARTIN sayaclari (app.js); eksen sonu ile kartin
       mAh'i yan yana yazilir. Bosluk ya da eksi akim varsa eksen KURULMAZ.
     * KAYIT KAYNAGI (PL4, PU11): test bitince bu tarayicinin IndexedDB kopyasi
       (3C esitlemesi); yoksa ve panel kartin adresinden acildiysa (C1) bir kez
       esitleme. Esitleme zinciri (esitleme.js + ortak/esitle, imza, kayit,
       depo_idb) ve disari.js ANCAK burada `import()` ile iner.
   NEDEN TEMBEL: Pil sekmesi ilk gorunur olunca `import()` (U1/E1 deseni);
   statik agaci yalniz grafik.js (+ ozet, istatistik) — Canli ile ortak.
   ⚠ Saf fonksiyonlar DOM'suz (B7 node'da sinar).
   ═══════════════════════════════════════════════════════════════════════ */

import { Grafik, cssRenk } from '/ortak/grafik.js';
import { ceviri, ceviriKod } from '/ortak/sozluk.js';

/* ortak/kayit.js sabitleri — kayit.js'i STATIK indirmemek icin sayi (B7 karsilastiriyor). */
export const OTURUM_PIL = 2;
export const KO_PIL_AYAR = 1;
export const KO_DCIR = 2;
export const KO_PIL_SONUC = 3;
/* Canli nokta araligi bilinmiyorsa (kart 1 Hz kaydediyor) bosluk esigi bunun 2.5 kati. */
export const CANLI_ARALIK_MS = 1000;
export const BOSLUK_KAT = 2.5;

/** ss:dd:sn (saat 24'u gecebilir). */
export function sureYaz(ms) {
  if (!Number.isFinite(ms)) return '—';
  const isaret = ms < 0 ? '−' : '';
  const s = Math.floor(Math.abs(ms) / 1000);
  const iki = (x) => String(x).padStart(2, '0');
  return `${isaret}${iki(Math.floor(s / 3600))}:${iki(Math.floor(s / 60) % 60)}:${iki(s % 60)}`;
}

/** mAh ekseni yazisi: adima gore ondalik. */
export function mahYazi(v, adim = NaN) {
  if (!Number.isFinite(v)) return '';
  const a = Number.isFinite(adim) && adim > 0 ? adim : Math.abs(v) / 10 || 1;
  const ondalik = Math.min(3, Math.max(0, Math.ceil(-Math.log10(a) - 1e-9)));
  return v.toFixed(ondalik) + ' mAh';
}

/**
 * Canli seri: app.js `pilNokta` ({sira, ms, v, i} ya da bosluk isareti {sira, bosluk}) ->
 * {t (ms, testin basindan), v, i}. Bosluk isareti NaN noktadir: cizgi KOPAR (G2), mAh ekseni
 * kurulmaz. Sirasi bozuk / azalan ms atilir (grafik.js azalmayan t ister).
 */
export function canliSeri(noktalar) {
  const l = noktalar || [];
  const t = [];
  const v = [];
  const i = [];
  let son = -Infinity;
  for (const n of l) {
    if (n && n.bosluk) {
      if (t.length) { t.push(son); v.push(NaN); i.push(NaN); }
      continue;
    }
    if (!n || !Number.isFinite(n.ms) || n.ms < son) continue;
    son = n.ms;
    t.push(n.ms);
    v.push(Number.isFinite(n.v) ? n.v : NaN);
    i.push(Number.isFinite(n.i) ? n.i : NaN);
  }
  return { t: Float64Array.from(t), v: Float64Array.from(v), i: Float64Array.from(i) };
}

/**
 * PU9 — mAh EKSENI (tarayici hesabi): yamuk integral, x[k] = Σ (i[k-1] + i[k]) / 2 · Δt.
 * A · ms / 3600 = mAh. Gecersiz ornek (NaN), `boslukMs`'yi asan ara ya da eksi akim varsa
 * eksen KURULMAZ (null + sebep anahtari): bosluk uzerinden integral uydurulmaz, azalan x
 * grafik.js'in azalmayan eksen sozlesmesini bozardi.
 */
export function mahEkseni(t, i, boslukMs = Infinity) {
  const n = t ? t.length : 0;
  const x = new Float64Array(n);
  let top = 0;
  for (let k = 0; k < n; k++) {
    if (!Number.isFinite(t[k]) || !Number.isFinite(i[k])) return { x: null, hata: 'pl.mah_bosluk' };
    if (i[k] < 0) return { x: null, hata: 'pl.mah_eksi' };
    if (k > 0) {
      const dt = t[k] - t[k - 1];
      if (dt > boslukMs) return { x: null, hata: 'pl.mah_bosluk' };
      top += (i[k - 1] + i[k]) / 2 * dt / 3600;
    }
    x[k] = top;
  }
  return { x, hata: null };
}

/** `t` (artan) icinde `hedef`e en yakin ornegin indisi (ikili arama); bos dizide -1. */
export function enYakin(t, hedef) {
  const n = t ? t.length : 0;
  if (!n || !Number.isFinite(hedef)) return -1;
  let a = 0;
  let b = n - 1;
  while (a < b) {
    const o = (a + b) >> 1;
    if (t[o] < hedef) a = o + 1;
    else b = o;
  }
  if (a > 0 && Math.abs(t[a - 1] - hedef) <= Math.abs(t[a] - hedef)) return a - 1;
  return a;
}

/**
 * PL3 — grafik serileri. eksen 'mah': x = mahEkseni (kurulamazsa ZAMAN eksenine dusulur ve
 * `eksenUyari` sebebi tasir). Donus {seriler: [V, I], x (mAh dizisi | null), eksen, eksenUyari}.
 */
export function pilSerileri(seri, { eksen = 'zaman', boslukMs = BOSLUK_KAT * CANLI_ARALIK_MS } = {}) {
  let x = null;
  let eksenUyari = null;
  if (eksen === 'mah') {
    const m = mahEkseni(seri.t, seri.i, boslukMs);
    if (m.hata) eksenUyari = m.hata;
    else x = m.x;
  }
  const t = x || seri.t;
  const bosluk = x ? Infinity : boslukMs;
  return {
    eksen: x ? 'mah' : 'zaman', x, eksenUyari,
    /* SIRA: once I, sonra V — dirençli yukte I ∝ V ve iki egri UST USTE biner; birincil olcum
       (V) ustte kalsin (T3F'de goruldu: V hic gorunmuyordu). */
    seriler: [
      { ad: 'I', t, y: seri.i, birim: 'A', renk: 'amper', eksen: 'sag', boslukMs: bosluk, kalinlik: 1.25 },
      { ad: 'V', t, y: seri.v, birim: 'V', renk: 'volt', eksen: 'sol', boslukMs: bosluk },
    ],
  };
}

/** PU10 — DCIR isaretleri (grafik.js `isaretler`): zaman ekseninde t = tMs; mAh ekseninde
 *  tMs'e EN YAKIN ornegin x'i (ara deger yok). Etiket "R<no>" (G8: dil metni yok). */
export function dcirIsaretleri(dcir, seri, x = null) {
  const l = [];
  for (const d of dcir || []) {
    if (!d || !Number.isFinite(d.tMs)) continue;
    if (!x) {
      l.push({ t: d.tMs, metin: 'R' + d.no });
      continue;
    }
    const k = enYakin(seri.t, d.tMs);
    if (k >= 0) l.push({ t: x[k], metin: 'R' + d.no });
  }
  return l;
}

/**
 * Imlec okumasi (grafik.js imlecOkuma) -> satirlar [{ad, d, renk}]. Zaman ekseninde A–B
 * araliginin mAh / Wh'si grafik.js'in HAM integrali (tarayici); mAh ekseninde fark dogrudan x.
 */
export function okumaSatirlari(o, eksen = 'zaman', dil = 'tr') {
  if (!o) return null;
  const x = (v) => (!Number.isFinite(v) ? '—' : eksen === 'mah' ? v.toFixed(2) + ' mAh' : sureYaz(v));
  const kn = (ad) => o.kanallar.find((k) => k.ad === ad) || null;
  const deger = (k, uc) => (k && k[uc] ? k[uc].deger : NaN);
  const s = [{ ad: 'A', d: x(o.tA) }, { ad: 'B', d: x(o.tB) }];
  if (Number.isFinite(o.dt)) {
    s.push({ ad: eksen === 'mah' ? ceviri('pl.okuma_dmah', dil) : 'Δt', d: eksen === 'mah' ? o.dt.toFixed(2) + ' mAh' : sureYaz(o.dt) });
  }
  for (const [ad, birim, renk, hane] of [['V', 'V', 'v', 3], ['I', 'A', 'i', 4]]) {
    const k = kn(ad);
    if (!k || !(Number.isFinite(deger(k, 'a')) || Number.isFinite(deger(k, 'b')))) continue;
    const f = (v) => (Number.isFinite(v) ? v.toFixed(hane) + ' ' + birim : '—');
    s.push({ ad: ad + ' A/B', d: f(deger(k, 'a')) + ' → ' + f(deger(k, 'b')), renk });
  }
  if (Number.isFinite(o.dV)) s.push({ ad: 'ΔV', d: o.dV.toFixed(4) + ' V', renk: 'v' });
  if (eksen !== 'mah' && o.enerji) {
    s.push({ ad: ceviri('pl.okuma_aralik_mah', dil), d: o.enerji.mah.toFixed(2) + ' mAh' });
    s.push({ ad: ceviri('pl.okuma_aralik_wh', dil), d: o.enerji.wh.toFixed(4) + ' Wh' });
  }
  return s;
}

/** Renk cozucu: imlec -> --yazi (3C K5 / 3D K5 ile ayni). */
function renkCozucu(eleman, pencere) {
  const cs = cssRenk(eleman, pencere);
  return (ad) => cs(ad === 'imlec' ? 'yazi' : ad);
}

/**
 * Pil egrisi (grafik.js; P3 tek cekirdek). `ciz(d)`: her yeni nokta / DCIR / eksen / tema
 * degisiminde. d = { nokta (canli), kayit (pilKaydiAc sonucu | null), eksen, dcir, dil }.
 * Kullanici yakinlastirmadiysa pencere verinin SONUNU izler; yakinlastirdiysa (pencere veri
 * sonunda degilse) yeni nokta pencereyi ve imlecleri BOZMAZ.
 * `degisti(bilgi)`: {var, n, eksen, eksenUyari, xSon (mAh eksen sonu), okuma (satirlar | null)}.
 */
export class PilGrafik {
  constructor(canvas, { pencere = globalThis, degisti = null } = {}) {
    this.canvas = canvas;
    this.degisti = typeof degisti === 'function' ? degisti : null;
    this.g = new Grafik(canvas, {
      renk: renkCozucu(canvas, pencere), zamanKokeni: 0, gerilim: 'V', akim: 'I', pencere,
      kenar: { sag: 40 },
      onDegisim: () => this._bildir(),
    });
    this._anahtar = '';
    this._son = null;
  }

  ciz(d = {}) {
    const kayit = d.kayit || null;
    const seri = kayit ? kayit.seri : canliSeri(d.nokta);
    const bosluk = kayit ? kayit.boslukMs : BOSLUK_KAT * CANLI_ARALIK_MS;
    const istenen = d.eksen === 'mah' ? 'mah' : 'zaman';
    const dcir = d.dcir || [];
    const anahtar = `${kayit ? 'k' + kayit.ozet.oturum : 'c'}:${seri.t.length}:${seri.t.length ? seri.t[seri.t.length - 1] : 0}`
      + `:${istenen}:${dcir.map((x) => x.no + (Number.isFinite(x.tMs) ? '' : '?')).join(',')}`;
    if (anahtar !== this._anahtar) {
      const once = this._son;
      const p = pilSerileri(seri, { eksen: istenen, boslukMs: bosluk });
      /* izleme: ayni kaynak + eksen ve onceki pencere verinin sonundaydiysa (yakinlastirma yok) bastan;
         degilse kullanicinin penceresi ve imlecleri korunur */
      const dur = this.g.durum;
      const ayniKaynak = once && once.kaynak === (kayit ? 'k' + kayit.ozet.oturum : 'c') && once.eksen === p.eksen;
      const sonda = !ayniKaynak || !(dur.veriT1 > dur.veriT0) || (dur.t1 >= dur.veriT1 - 1e-9 && dur.t0 <= dur.veriT0 + 1e-9);
      this.g.secenek.xEksen = p.eksen === 'mah' ? { tur: 'sayi', yazi: mahYazi } : undefined;
      this.g.secenek.isaretler = dcirIsaretleri(dcir, seri, p.x);
      this.g.veriAyarla(p.seriler, { koru: !sonda });
      this._son = { kaynak: kayit ? 'k' + kayit.ozet.oturum : 'c', eksen: p.eksen, eksenUyari: p.eksenUyari,
        n: seri.t.length, xSon: p.x && p.x.length ? p.x[p.x.length - 1] : NaN };
      this._anahtar = anahtar;
    }
    this._dil = d.dil || 'tr';
    this.g.ciz();
    return this._bildir();
  }

  _bildir() {
    const s = this._son || { n: 0, eksen: 'zaman', eksenUyari: null, xSon: NaN };
    const dur = this.g.durum;
    const imlec = Number.isFinite(dur.imlecA) || Number.isFinite(dur.imlecB);
    const bilgi = {
      var: s.n > 0, n: s.n, eksen: s.eksen, eksenUyari: s.eksenUyari, xSon: s.xSon,
      okuma: imlec && s.n ? okumaSatirlari(this.g.okuma(), s.eksen, this._dil) : null,
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
    this._son = null;
  }
}

/* ── KAYIT KAYNAGI (PL4, PU11) ──────────────────────────────────────── */

/**
 * PIL oturumu -> egri + DCIR + ozet (saf; `disari` = ortak/disari.js modulu).
 * Egri `disari.noktaSerileri` (kaydin kalibrasyonuyla V/A; nokta = kartin hiz araligi
 * ortalamasi), x = acilistan gecen ms (relMs). DCIR = OLAY KO_DCIR'in KENDI zamani ve
 * degerleri (kartin sayaci). Sonuc = son KO_PIL_SONUC; ayar = KO_PIL_AYAR; bitis sebebi BITIR'den.
 * @returns {{seri, boslukMs, ozet} | {hata, d?}}
 */
export function pilKayitKur(oturum, { disari, kayitlar = null, kimlik = null, dil = 'tr' } = {}) {
  if (!oturum) return { hata: 'pl.hata_kayit_yok', d: {} };
  if (!oturum.basla || oturum.basla.oturum_turu !== OTURUM_PIL) return { hata: 'pl.hata_kayit_tur', d: { no: oturum.id } };
  const s = disari.noktaSerileri(oturum, { kayitlar });
  const seri = { t: Float64Array.from(s.relMs), v: Float64Array.from(s.vOrt), i: Float64Array.from(s.iOrt) };
  const olaylar = [...oturum.olaylar].sort((a, b) => a.sira - b.sira);
  const dcir = olaylar.filter((o) => o.tur === KO_DCIR && 'no' in o).map((o) => {
    const z = disari.anZamani(s.eksen, s.araliklar, o.kart_ms, o.sira);
    return { no: o.no, tMs: z && Number.isFinite(z.relMs) ? z.relMs : NaN, rAni: o.r_ani, rOtr: o.r_oturmus,
      mah: o.mah, wh: o.wh, yaklasik: false };
  });
  const a = olaylar.find((o) => o.tur === KO_PIL_AYAR);
  const so = olaylar.filter((o) => o.tur === KO_PIL_SONUC).pop();
  const sebep = oturum.bitir ? oturum.bitir.sebep : null;
  const ozet = {
    oturum: oturum.id, kimlik, ad: oturum.ad || null, n: s.adet,
    ayar: a ? { kesme_v: a.kesme_v, ocv: a.ocv, azami_s: a.azami_s, dcir_aralik_ms: a.dcir_aralik_ms,
      dcir_ms: a.dcir_ms, kayit_hz: a.kayit_hz } : null,
    sonuc: so ? { durum: so.durum, hata: so.hata, mah: so.mah, wh: so.wh, ocv: so.ocv, v_son: so.v_son,
      sure_ms: so.sure_ms, dcir_sayisi: so.dcir_sayisi,
      durumMetin: ceviriKod('pil.durum.', so.durum, dil), hataMetin: ceviriKod('pil.hata.', so.hata, dil) } : null,
    sebep, sebepMetin: sebep === null ? '' : ceviriKod('sebep.', sebep, dil),
    dcir,
  };
  return { seri, boslukMs: disari.noktaBoslukMs(oturum), ozet };
}

async function denetci(kartAdres, denetciKur, kartIstek = null) {
  if (denetciKur) return denetciKur();
  const es = await import('./esitleme.js');
  /* 3H-2 (ES4): ag istekleri app.js'in TEK istek katmanindan (eslesmisse imzali) */
  return new es.EsitlemeDenetcisi({ kartAdres, istek: kartIstek });
}

/**
 * Bu tarayicinin kopyasindan PIL oturumunu ac. `rota.kimlik` yoksa oturumu TASIYAN ve turu
 * PIL olan EN YENI akis (3E S4 kurali; eski kart kopyasindaki ayni numarali olcum oturumu
 * acilmasin). Donus pilKayitKur + {kimlik, csv(bicim)} ya da {hata, d}.
 */
export async function pilKaydiAc(rota, { kartAdres = (y) => y, denetciKur = null, dil = 'tr' } = {}) {
  if (!rota || !(rota.oturum > 0)) return { hata: 'pl.hata_kayit_yok', d: { no: '?' } };
  let den;
  let disari;
  try {
    disari = await import('/ortak/disari.js');
    den = await denetci(kartAdres, denetciKur);
  } catch (h) {
    return { hata: 'pl.hata_modul', d: { mesaj: (h && h.message) || String(h) } };
  }
  let veri = null;
  try {
    const akislar = [...await den.akislar()].sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
    const adaylar = rota.kimlik === null || rota.kimlik === undefined ? akislar.map((a) => a.kimlik) : [rota.kimlik];
    for (const k of adaylar) {
      if (!akislar.some((a) => a.kimlik === k)) continue;
      const v = await den.akisVerisi(k);
      const o = v && v.oturumlar ? v.oturumlar.get(rota.oturum) : null;
      if (o && o.basla && o.basla.oturum_turu === OTURUM_PIL) { veri = v; break; }
    }
  } catch (h) {
    return { hata: 'pl.hata_depo', d: { mesaj: (h && h.message) || String(h) } };
  }
  if (!veri) return { hata: 'pl.hata_kayit_yok', d: { no: rota.oturum } };
  const o = veri.oturumlar.get(rota.oturum);
  const r = pilKayitKur(o, { disari, kayitlar: veri.kayitlar, kimlik: veri.kimlik, dil });
  if (r.hata) return r;
  r.csv = (bicim = 'tr') => disari.csvBayt(disari.pilCsv(o, { ...(bicim === 'en' ? disari.BICIM_EN : disari.BICIM_EXCEL_TR),
    kayitlar: veri.kayitlar }));
  return r;
}

/**
 * PU11: kartin kaydini bu tarayiciya esitle (Kayitlar'in denetcisi; C1 on kosulu ve C3 onay
 * kurali AYNEN — onay yalniz "bu tarayici arsivdir" seciliyse gider). Kopruda / USB'de /
 * baska kokende esitleme YOK.
 * @returns {Promise<{durum: 'tamam'} | {durum, mesaj?, neden?}>}
 */
export async function pilKaydiEsitle({ kartAdres = (y) => y, kartIstek = null, kartTaban = '', tasiyici = 'akis', kopruda = false,
  bagli = false, gonder = null, denetciKur = null } = {}) {
  let es;
  try {
    es = await import('./esitleme.js');
  } catch (h) {
    return { durum: 'modul', mesaj: (h && h.message) || String(h) };
  }
  const u = es.esitlemeUygunlugu({ kartTaban, tasiyici });
  if (!u.uygun || kopruda) return { durum: 'uygun_degil', neden: u.neden || 'kopru' };
  let den;
  try {
    den = await denetci(kartAdres, denetciKur, kartIstek);
  } catch (h) {
    return { durum: 'modul', mesaj: (h && h.message) || String(h) };
  }
  const l = await den.kartListesi();
  if (l.durum !== 'tamam') return { durum: l.durum, mesaj: l.mesaj || '' };
  const kimlik = l.liste.kimlik;
  const onay = es.onayIslevi({ arsiv: es.arsivOku(kimlik), bagli, gonder });
  return den.esitle({ kimlik, onay });
}
