/* ═══════════════════════════════════════════════════════════════════════
   3E — OSILOSKOP: SPEKTRUM + KAYITLI YAKALAMA          (ekran/osiloskop.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3E kararlari" (OS1-OS8).
   Dalganin KENDISI (izgara, tetik isaretleri, zoom) app.js'in tuvalinde kalir
   (OS2: B42-B46'da kartla dogrulanmis cizim); yakalama durumu, `satirIsle`
   ve komutlar da app.js'te (tek ayristirici, B22.2). Bu modul:
     * SPEKTRUM (OS2/OS3): `ortak/fft.js` + `ortak/grafik.js` (x ekseni Hz —
       grafik.js `xEksen`). Kaynak HER ZAMAN yakalamanin butun ham kodlari
       (gorunen zoom penceresi DEGIL), volta app.js'in TEK cevirisiyle
       (`kodVolt`, egri dahil) cevrilir; DC cikarilir.
     * KAYITLI YAKALAMA (OS6): `#/skop/kayit/<oturum>/<sira>[@kimlik]` — bu
       tarayicinin IndexedDB kopyasindan (3C esitlemesi) okunur, olcumler
       `ortak/skop.js skopOlcKart` ile (OS4: kartin `M` satirinin hesabi).
   NEDEN TEMBEL: ekran ilk acilinca `import()` ile iner (U1/E1 deseni);
   esitleme zinciri (esitleme.js + ortak/esitle, imza, kayit, depo_idb) ise
   ancak bir kayitli yakalama acilinca — canli osiloskop onu hic indirmez.

   UYGULAMA KARARLARI (OS1-OS8 disinda):
   S1 Spektrum grafiginde 0. kutu (DC) CIZILMEZ, degeri metin olarak yazar:
      skop ofsetli (VREF referansli, ~63 V) — DC cubugu bilesenleri ekranin
      dibine ezerdi. FFT zaten DC'yi cikariyor (fft.js dcCikar).
   S2 Harmonikler n = 1 … 5 (1. harmonik = temel = tepe frekansi); THD yaklasigi
      2 … 5'ten (fft.js harmonikler). Temel tepe frekansidir (en buyuk AC bilesen).
   S3 Kayitli yakalamanin egrisi: oturumdaki OLAY KO_SKOP_KAL'larindan yakalamanin
      kayit sirasindan ONCEKI en son olan (Gt her basladiginda bir tane yazar);
      yoksa ilki. Gecersizse (kart egri kuramamis) egrisiz yol — kart da oyle olcmustu.
   S4 Rotada @kimlik yoksa: o oturumu tasiyan EN YENI akis (olusma zamani) —
      Kayitlar listesinin "guncel akis" kuralinin (rotaAkisi) tarayici-ici karsiligi.
   ═══════════════════════════════════════════════════════════════════════ */

import { Grafik, cssRenk } from '/ortak/grafik.js';
import { spektrum, tepeFrekans, harmonikler, dbv } from '/ortak/fft.js';
import { skopOlcKart, egriGecerli, kalDugumKod, KAL_N, KART_SABIT } from '/ortak/skop.js';

/** OLAY KO_SKOP_KAL (kayit_bicim.h). ortak/kayit.js'i statik indirmemek icin sayi. */
export const KO_SKOP_KAL = 4;
/** Harmonik sayisi (S2). */
export const HARMONIK_ADET = 5;
/** Spektrum genlik birimleri / pencereler. */
export const SPEKTRUM_BIRIMLER = Object.freeze(['v', 'dbv']);
export const SPEKTRUM_PENCERELER = Object.freeze(['hann', 'dikdortgen']);

/* ── ROTA (OS6) ─────────────────────────────────────────────────────── */

/** Hash -> {oturum, sira, kimlik}; kayitli yakalama rotasi degilse null. */
export function skopRotaCoz(hash) {
  const h = String(hash || '').replace(/^#\/?/, '');
  const m = /^skop\/kayit\/(\d+)\/(\d+)(?:@(\d+))?\/?$/.exec(h);
  if (!m) return null;
  const oturum = Number(m[1]);
  const sira = Number(m[2]);
  if (!(oturum > 0) || !(sira > 0)) return null;
  return { oturum, sira, kimlik: m[3] === undefined ? null : Number(m[3]) };
}

/* ── SPEKTRUM (OS2/OS3) ─────────────────────────────────────────────── */

/** X ekseni yazisi (Hz / kHz), adimin gerektirdigi kadar ondalik. */
export function hzYazi(v, adim = NaN) {
  if (!Number.isFinite(v)) return '';
  const a = Number.isFinite(adim) && adim > 0 ? adim : Math.abs(v) / 10 || 1;
  const kilo = Math.abs(v) >= 1000 || a >= 1000;
  const b = kilo ? a / 1000 : a;
  const ondalik = Math.min(3, Math.max(0, Math.ceil(-Math.log10(b) - 1e-9)));
  return (kilo ? (v / 1000).toFixed(ondalik) + ' kHz' : v.toFixed(ondalik) + ' Hz');
}

/**
 * Yakalamanin spektrumu. `veri` ham kodlarin TAMAMI (OS3), `kodVolt` app.js'in tek
 * cevirisi (egri dahil). Donus fft.spektrum + {tepe, harmonik: {harmonikler, thd}}.
 * Veri yoksa / hz gecersizse null.
 */
export function spektrumHesapla(veri, hz, { kodVolt = (k) => k, pencere = 'hann' } = {}) {
  const n = veri ? veri.length : 0;
  if (n < 2 || !(hz > 0) || !Number.isFinite(hz)) return null;
  const y = new Float64Array(n);
  for (let i = 0; i < n; i++) y[i] = kodVolt(veri[i]);
  const sp = spektrum(y, hz, { pencere: SPEKTRUM_PENCERELER.includes(pencere) ? pencere : 'hann' });
  const tepe = tepeFrekans(sp);
  const harmonik = tepe ? harmonikler(sp, tepe.f, HARMONIK_ADET) : { harmonikler: [], thd: NaN };
  return { ...sp, tepe, harmonik };
}

/** Grafik serisi: x = Hz (DC kutusu YOK, S1), y = V tepe ya da dBV. */
export function spektrumSerisi(sp, birim = 'v') {
  const m = sp && sp.f ? sp.f.length : 0;
  const n = Math.max(0, m - 1);
  const t = new Float64Array(n);
  const y = new Float64Array(n);
  const dB = birim === 'dbv';
  for (let k = 1; k < m; k++) {
    t[k - 1] = sp.f[k];
    y[k - 1] = dB ? dbv(sp.genlik[k]) : sp.genlik[k];
  }
  return { ad: 'S', t, y, birim: dB ? 'dBV' : 'V', renk: 'volt', eksen: 'sol', kalinlik: 1.25 };
}

/** Renk cozucu: imlec -> --yazi (3C K5 / 3D K5 ile ayni). */
function renkCozucu(eleman, pencere) {
  const cs = cssRenk(eleman, pencere);
  return (ad) => cs(ad === 'imlec' ? 'yazi' : ad);
}

/**
 * Spektrum grafigi (grafik.js; P3 tek cekirdek). `ciz(d)` her yeni yakalamada ve
 * pencere/birim/tema degisince:  d = { veri, hz, kodVolt, pencere, birim }.
 * `degisti(bilgi)`: bilgi = { var, n, nfft, df, dc, pencere, birim, tepe, harmonikler, thd }.
 */
export class SpektrumGrafik {
  constructor(canvas, { pencere = globalThis, degisti = null } = {}) {
    this.canvas = canvas;
    this.degisti = typeof degisti === 'function' ? degisti : null;
    this.g = new Grafik(canvas, {
      renk: renkCozucu(canvas, pencere), zamanKokeni: 0, pencere,
      xEksen: { tur: 'sayi', yazi: hzYazi },
      kenar: { sag: 30 },          // en sagdaki "… kHz" yazisi tuvalden tasmasin (ortali yazi)
      /* imlec / yakinlastirma degisince okuma (A/B: Hz + genlik) yeniden bildirilsin */
      onDegisim: () => { if (this._secim) this._bildir(this._secim.birim, this._secim.pencere); },
    });
    this._anahtar = '';
    this.son = null;
    this._secim = null;
  }

  ciz(d) {
    const veri = d && d.veri;
    const birim = SPEKTRUM_BIRIMLER.includes(d && d.birim) ? d.birim : 'v';
    const pencere = SPEKTRUM_PENCERELER.includes(d && d.pencere) ? d.pencere : 'hann';
    /* ayni yakalama + ayni secim: yalniz yeniden ciz (tema) — FFT tekrar edilmez */
    const anahtar = veri ? `${veri.length}:${d.hz}:${pencere}:${birim}` : '';
    if (veri !== this._veri || anahtar !== this._anahtar || d.zorla) {
      this._veri = veri;
      this._anahtar = anahtar;
      const sp = veri ? spektrumHesapla(veri, d.hz, { kodVolt: d.kodVolt, pencere }) : null;
      this.son = sp;
      this.g.veriAyarla(sp ? [spektrumSerisi(sp, birim)] : []);
    }
    this.g.ciz();
    this._secim = { birim, pencere };
    return this._bildir(birim, pencere);
  }

  _bildir(birim, pencere) {
    const sp = this.son;
    /* imlec okumasi (grafik.js; cift tik / A, B tuslari): en yakin HAM kutu — Hz ve genlik */
    const dur = this.g.durum;
    const imlec = [];
    if (sp && (Number.isFinite(dur.imlecA) || Number.isFinite(dur.imlecB))) {
      const o = this.g.okuma();
      const k = o.kanallar[0];
      for (const [ad, u] of [['A', k && k.a], ['B', k && k.b]]) if (u) imlec.push({ ad, f: u.t, deger: u.deger });
    }
    const bilgi = sp ? {
      var: true, n: sp.n, nfft: sp.nfft, df: sp.df, dc: sp.dc, pencere, birim,
      tepe: sp.tepe, harmonikler: sp.harmonik.harmonikler, thd: sp.harmonik.thd, imlec,
    } : { var: false, pencere, birim, tepe: null, harmonikler: [], thd: NaN, imlec };
    if (this.degisti) this.degisti(bilgi);
    return bilgi;
  }

  yokEt() {
    this.g.yokEt();
    this.son = null;
    this._veri = null;
  }
}

/* ── KAYITLI YAKALAMA (OS6) ─────────────────────────────────────────── */

/** Oturumdaki egri (S3): yakalamanin kayit sirasindan once yazilmis en son KO_SKOP_KAL. */
export function yakalamaEgrisi(oturum, sira) {
  const egriler = (oturum && oturum.olaylar ? oturum.olaylar : [])
    .filter((o) => o.tur === KO_SKOP_KAL && o.mv && o.mv.length === KAL_N)
    .sort((a, b) => a.sira - b.sira);
  if (!egriler.length) return null;
  let sec = egriler[0];
  for (const e of egriler) if (e.sira < sira) sec = e;
  return Array.from(sec.mv);
}

/**
 * Oturumun `sira`daki yakalamasi -> app.js'in `osilo` yapisi + kartin olcumu (OS4).
 * @returns {{osilo, olcum, bilgi} | {hata: string, d?: object}}
 *   osilo.kal: egri GECERLIYSE app.js `kodVolt`un tablosu ({oran, kod, mv}), degilse null
 *   (kart o yakalamayi egrisiz olcmustu; eksen de egrisiz). olcum = skopOlcKart.
 */
export function yakalamaKur(oturum, sira) {
  const y = oturum && oturum.skoplar ? oturum.skoplar.get(sira) : null;
  if (!y) return { hata: 'os.hata_yakalama_yok', d: { oturum: oturum ? oturum.id : '?', sira } };
  if (!y.tam || !y.meta || !y.kodlar) return { hata: 'os.hata_yakalama_eksik', d: { no: y.no } };
  const m = y.meta;
  const egri = yakalamaEgrisi(oturum, sira);
  const egriVar = egriGecerli(egri);
  const olcum = skopOlcKart(y.kodlar, { adim: m.adim, ofset: m.ofset, hz: m.hz, egri: egriVar ? egri : null });
  const kal = egriVar ? {
    oran: KART_SABIT.ORAN, ofset: m.ofset, tavanMv: KART_SABIT.ADC_TAVAN * 1000,
    kod: Array.from({ length: KAL_N }, (_, k) => kalDugumKod(k)), mv: egri,
  } : null;
  const osilo = {
    adet: y.kodlar.length, hz: m.hz, voltAdim: m.adim, voltOfset: m.ofset,
    tetikIdx: m.tetik, tdivUs: m.tdiv_us, kip: m.kip, tetiklendi: m.tetiklendi === 1,
    veri: Array.from(y.kodlar), olcum, olcumKaynak: 'panel', kal,
  };
  return { osilo, olcum, bilgi: { no: y.no, tMs: m.t_ms, sureMs: m.sure_ms, egri: egriVar, sira } };
}

/**
 * Rotadaki yakalamayi bu tarayicinin kopyasindan ac (OS6). Esitleme zinciri ANCAK burada
 * iner. `denetciKur` testte sahte depo vermek icin; varsayilan esitleme.js'in denetcisi.
 * @returns {Promise<{osilo, olcum, bilgi} | {hata, d}>}  bilgi += {oturum, kimlik, ad, gecenMs, unixMs}
 */
export async function kayitliYakalamaAc(rota, { kartAdres = (y) => y, denetciKur = null } = {}) {
  if (!rota) return { hata: 'os.hata_yakalama_yok', d: { oturum: '?', sira: '?' } };
  let den;
  let disari;
  try {
    disari = await import('/ortak/disari.js');
    if (denetciKur) den = await denetciKur();
    else {
      const es = await import('./esitleme.js');
      den = new es.EsitlemeDenetcisi({ kartAdres });
    }
  } catch (h) {
    return { hata: 'os.hata_modul', d: { mesaj: (h && h.message) || String(h) } };
  }
  let veri = null;
  try {
    const akislar = [...await den.akislar()].sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
    const adaylar = rota.kimlik === null ? akislar.map((a) => a.kimlik) : [rota.kimlik];
    for (const k of adaylar) {
      if (!akislar.some((a) => a.kimlik === k)) continue;
      const v = await den.akisVerisi(k);
      if (v && v.oturumlar && v.oturumlar.has(rota.oturum)) { veri = v; break; }
    }
  } catch (h) {
    return { hata: 'os.hata_depo', d: { mesaj: (h && h.message) || String(h) } };
  }
  if (!veri) return { hata: 'os.hata_yakalama_yok', d: { oturum: rota.oturum, sira: rota.sira } };
  const o = veri.oturumlar.get(rota.oturum);
  const r = yakalamaKur(o, rota.sira);
  if (r.hata) return r;
  let z = null;
  try {
    z = disari.anZamani(disari.zamanEkseni(o, veri.kayitlar), null, r.bilgi.tMs, rota.sira);
  } catch { z = null; }
  r.bilgi = { ...r.bilgi, oturum: rota.oturum, kimlik: veri.kimlik, ad: o.ad || null,
    gecenMs: z ? z.gecenMs : null, unixMs: z ? z.unixMs : null };
  return r;
}
