// B73 / 2F — RAPOR ICERIGI: bir oturumun tek sayfalik raporunun VERISI (ust tasarim §9
// "Rapor": grafik + ozet tablo + kalibrasyon bilgisi + notlar). HTML YOK — arayuz (alt proje
// 3/5) cizer; etiketler sozlukten (RAPOR_ETIKET / ALAN_ETIKET -> ceviri). Donus duz JSON'a
// cevrilebilir nesne: Map / tipli dizi / NaN / undefined YOK (bilinmeyen = null).
//
// KURALLAR
//  * Istatistik ve enerji HER ZAMAN HAM veriden (D4; istatistik.js), ozet piramidinden degil.
//    Nokta oturumunda "ham" = kayittaki noktalar: ort/RMS nokta ORTALAMALARINDAN, min
//    noktalarin MIN'lerinden, maks MAKS'larindan (tek orneklik sicrama ortalamada erir, min/
//    maks'ta kalir — kullanicinin "sicramalari goz onunden alma" kurali). RMS burada nokta
//    ortalamalarinin RMS'idir (ornek RMS'i degil). Ayrintili oturumda her sey orneklerden.
//    tMin/tMaks yerine o noktanin sirasi + gecen_ms (bilinmiyorsa null).
//  * Enerji yamuk kuraliyla, ACILIS BASINA (DEVAM sinirinin ustunden integral YOK) ve acilis
//    icinde bosluk > hiz x 2.5 (ayrintili: > 16.38 ms) haric; acilis toplamlari sirayla
//    toplanir. Wh = ∫ W dt — nokta oturumunda kartin W'si (ornek basina V*I ortalamasi; ort V x
//    ort A DEGIL, dalgali yukte ayrisir); ayrintilida HIZALI W (W1: kayit.js ayrintiGuc — V
//    akim ornegi anina tasinir; ayni ornegin V x I'si DEGIL). mAh = ∫ A dt. pilCsv'nin son
//    satiriyla bit bit ayni.
//  * Sure: toplamMs = baslangictan (BASLA) son veriye (bosluklar DAHIL); olculenMs = enerjiye
//    giren sure; boslukMs = bosluk sayilan ardisik araliklarin toplami (acilis gecisi dahil;
//    gecis suresi bilinmiyorsa null).
//  * Olaylar KAYIT SIRASIYLA (gercek zaman sirasi). Zamanlar disari.js zaman ekseninden.
//  * Osiloskop yakalamalari ZAMAN SIRASIYLA (W1/Y7: kayit sirasi degil — kayit.js skopYerleri;
//    acilis yakalamanin kendi `acilis`'inden). META'siz yakalama sonda, kayit sirasiyla.
//    Olcumun icine dusen yakalama (oncesinde ve sonrasinda veri var) uyari `skop_bosluk`.
//  * Kalibrasyon: cevrim HER ZAMAN oturumun kendi kopyasiyla (kopya); kal_no gecmiste aranir.
//    Gecmis kaydi sifir ofsetleri haric (kalgec.h kgc__iz) kopyayla ayni degilse 'kal_farkli'.

import {
  OTURUM_PIL, KO_PIL_AYAR, KO_DCIR, KO_PIL_SONUC, skopYerleri,
  KN_V_HATA, KN_I_HATA, KN_V_DOYDU, KN_DURAKLAMA, KN_KAYIP_ONCE,
  KAO_V_HATA, KAO_I_HATA, KAO_V_DOYDU, KA_KAYIP_ONCE, KA_SILME,
} from "./kayit.js";
import { istatistik, enerji } from "./istatistik.js";
import { ceviri, ceviriKod } from "./sozluk.js";
import {
  zamanEkseni, noktaSerileri, ayrintiSerileri, anZamani, noktaBoslukMs, AYRINTI_BOSLUK_MS,
} from "./disari.js";

export const RAPOR_SURUM = 1;

/** Rapor alan adi -> sozluk anahtari (arayuz: ceviri(RAPOR_ETIKET[alan], dil)). */
export const RAPOR_ETIKET = Object.freeze({
  kimlik: "rapor.kimlik", oturumNo: "rapor.oturum_no", tur: "rapor.tur", ad: "rapor.ad",
  etiketler: "rapor.etiketler", notlar: "rapor.notlar", firmware: "rapor.firmware",
  hizMs: "rapor.hiz", ayrintili: "rapor.ayrintili", basiEksik: "rapor.basi_eksik",
  zaman: "rapor.zaman", baslangic: "rapor.baslangic", bitis: "rapor.bitis",
  toplamMs: "rapor.toplam_sure", olculenMs: "rapor.olculen_sure", boslukMs: "rapor.bosluk_sure",
  boslukAdet: "rapor.bosluk_adet", sayac: "rapor.sayac", nokta: "rapor.nokta_adet",
  ayrintiOrnek: "rapor.ayrinti_adet", devam: "rapor.devam_adet", olay: "rapor.olay_adet",
  not: "rapor.not_adet", skopAdet: "rapor.skop_adet", sebep: "rapor.sebep",
  noktaAdedi: "rapor.bitir_nokta", istatistik: "rapor.istatistik", v: "rapor.gerilim",
  i: "rapor.akim", w: "rapor.guc", adet: "rapor.adet", min: "rapor.min", maks: "rapor.maks",
  ort: "rapor.ort", rms: "rapor.rms", tepeTepe: "rapor.tepe_tepe", minSira: "rapor.min_sira",
  maksSira: "rapor.maks_sira", minGecenMs: "rapor.min_zaman", maksGecenMs: "rapor.maks_zaman",
  enerji: "rapor.enerji", wh: "rapor.wh", mah: "rapor.mah", pil: "rapor.pil",
  ayar: "rapor.pil_ayar", sonuc: "rapor.pil_sonuc", dcir: "rapor.dcir",
  kalibrasyon: "rapor.kalibrasyon", kalNo: "rapor.kal_no", durum: "rapor.kal_durum",
  kayit: "rapor.kal_kayit", kopya: "rapor.kal_kopya", olaylar: "rapor.olaylar",
  skop: "rapor.skop", yakalamalar: "rapor.yakalamalar", tam: "rapor.skop_tam",
  eksik: "rapor.skop_eksik", uyarilar: "rapor.uyarilar", gecenMs: "rapor.gecen",
  unixS: "rapor.unix", iso: "rapor.iso", acilis: "rapor.acilis",
});

/** Olay / pil alan adi (kayit.js OLAY alanlari) -> sozluk anahtari. */
export const ALAN_ETIKET = Object.freeze({
  kesme_v: "alan.kesme_v", ocv: "alan.ocv", azami_s: "alan.azami_s",
  dcir_aralik_ms: "alan.dcir_aralik_ms", dcir_ms: "alan.dcir_ms", kayit_hz: "alan.kayit_hz",
  no: "alan.no", v_once: "alan.v_once", i_once: "alan.i_once", v_ani: "alan.v_ani",
  v_oturmus: "alan.v_oturmus", r_ani: "alan.r_ani", r_oturmus: "alan.r_oturmus",
  mah: "alan.mah", wh: "alan.wh", durum: "alan.durum", hata: "alan.hata",
  v_son: "alan.v_son", sure_ms: "alan.sure_ms", dcir_sayisi: "alan.dcir_sayisi",
  mv: "alan.mv", bas_unix: "alan.bas_unix", sure_s: "alan.sure_s", hiz_ms: "alan.hiz_ms",
  plan_no: "alan.plan_no", ham: "alan.ham",
});

const nn = (x) => (typeof x === "number" && Number.isFinite(x) ? x : null);

/** Duz JSON'a guvenli kopya: sonlu olmayan sayi -> null, Uint8Array -> hex. */
function jsonla(x) {
  if (x === null || x === undefined) return null;
  if (typeof x === "number") return nn(x);
  if (typeof x === "string" || typeof x === "boolean") return x;
  if (x instanceof Uint8Array) return Array.from(x, (b) => b.toString(16).padStart(2, "0")).join("");
  if (ArrayBuffer.isView(x)) return Array.from(x, nn);
  if (Array.isArray(x)) return x.map(jsonla);
  if (x instanceof Map) return [...x].map(([k, v]) => [jsonla(k), jsonla(v)]);
  const o = {};
  for (const [k, v] of Object.entries(x)) o[k] = jsonla(v);
  return o;
}

function an(z) {
  const u = z ? z.unixMs : null;
  return {
    acilis: z ? z.acilis : null,
    gecenMs: z ? z.gecenMs : null,
    unixS: u === null ? null : u / 1000,
    iso: u === null ? null : new Date(u).toISOString(),
  };
}

/** Ham seri uzerinden kanal istatistigi (istatistik.js). ort/rms `ort`tan, min `min`den, maks `maks`tan. */
function kanal(ort, min, maks, sira, gecen) {
  const t = new Float64Array(ort.length).map((_, k) => k);
  const so = istatistik(t, ort);
  const smin = istatistik(t, min);
  const smaks = istatistik(t, maks);
  const yer = (s, alan) => (s.adet ? s[alan] : null);
  const iMin = yer(smin, "tMin");
  const iMaks = yer(smaks, "tMaks");
  return {
    adet: so.adet,
    min: nn(smin.min), maks: nn(smaks.maks), ort: nn(so.ort), rms: nn(so.rms),
    tepeTepe: nn(smaks.maks - smin.min),
    minSira: iMin === null ? null : sira[iMin], maksSira: iMaks === null ? null : sira[iMaks],
    minGecenMs: iMin === null ? null : nn(gecen[iMin]), maksGecenMs: iMaks === null ? null : nn(gecen[iMaks]),
  };
}

/** Acilis basina [bas, son) indis araliklari (satirlar acilis sirasinda bitisik). */
function acilisParcalari(acilis) {
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

/** Kalibrasyon gecmisi kaydi oturumun kopyasiyla (sifir ofsetleri HARIC) ayni mi. */
function kalAyni(kayit, kopya) {
  const f = (a, b) => (a === null || a === undefined ? !Number.isFinite(b) : Object.is(Math.fround(a), b));
  const k = kayit.kal || {};
  for (const ad of ["normal", "yuksek"]) {
    const x = k[ad] || {};
    for (const a of ["n", "pga", "kazanc", "tau"]) if (!f(x[a], kopya[ad][a])) return false;
  }
  return f(k.i_pga, kopya.i_pga) && f(k.sont_ohm, kopya.sont_ohm) && f(k.i_duzeltme, kopya.i_duzeltme)
    && f(k.sebeke_hz, kopya.sebeke_hz) && f(k.faz0, kopya.faz_kal_us[0]) && f(k.faz1, kopya.faz_kal_us[1]);
}

function kalibrasyonBolumu(oturum, gecmis, dil, uyar) {
  const b = oturum.basla;
  const durum = (kod) => ({ kod, metin: ceviri(`kal.durum.${kod}`, dil) });
  if (!b) return { kalNo: null, durum: durum("kopya_yok"), kayit: null, kopya: null };
  const no = b.kal_no;
  const sonuc = { kalNo: no, durum: null, kayit: null, kopya: b.kal };
  if (!no) {
    sonuc.durum = durum("numarasiz");
  } else if (!gecmis || !Array.isArray(gecmis.kayitlar)) {
    sonuc.durum = durum("gecmis_yok");
  } else {
    const e = gecmis.kayitlar.find((x) => x && x.no === no);
    if (!e) {
      sonuc.durum = durum("yok");
    } else if (e.bozuk && !e.kal) {
      sonuc.durum = durum("bozuk");
      sonuc.kayit = e;
    } else {
      sonuc.durum = durum("bulundu");
      sonuc.kayit = { ...e, turMetin: ceviriKod("kal.tur.", e.tur, dil),
        kaynakMetin: ceviriKod("kal.kaynak.", e.kaynak, dil) };
      if (!kalAyni(e, b.kal)) uyar("kal_farkli", 1, { no });
    }
  }
  if (b.kal.sont_ohm === 0) uyar("kal_gecersiz", 1);
  return sonuc;
}

function olayAlanlari(o) {
  const a = {};
  for (const [k, v] of Object.entries(o)) if (k !== "tur" && k !== "kart_ms" && k !== "sira") a[k] = v;
  return a;
}

/**
 * Oturum raporu. secenek: { kalibrasyonGecmisi (kalibrasyon.json nesnesi / /kal/liste),
 * kayitlar (ham kayitlar: DEVAM'li oturumda olay/skop zamanini acilisa baglar), dil ('tr'|'en';
 * enum metinleri icin; sayilar SI) }.
 */
export function oturumRaporu(oturum, secenek = {}) {
  const { kalibrasyonGecmisi = null, kayitlar = null, dil = "tr" } = secenek || {};
  const b = oturum.basla;
  const uyarilar = new Map();
  const uyar = (kod, sayi, deg = {}) => {
    if (!sayi) return;
    const u = uyarilar.get(kod);
    if (u) u.sayi += sayi;
    else uyarilar.set(kod, { kod, sayi, deg });
  };

  const eksen = zamanEkseni(oturum, kayitlar);
  const ayrintili = oturum.ayrinti.length > 0 && oturum.noktalar.length === 0;
  let seri;
  let ist;
  let en = { wh: 0, mah: 0, sureS: 0 };
  let bosluk = { adet: 0, ms: 0 };
  let araliklar;
  let satir;   // {acilis, relMs, gecenMs, unixMs, adet}
  if (ayrintili) {
    seri = ayrintiSerileri(oturum, { eksen });
    araliklar = seri.araliklar;
    const gecen = Float64Array.from(seri.gecenUs, (u) => u / 1000);
    const unix = Float64Array.from(seri.unixUs, (u) => u / 1000);
    satir = { acilis: seri.acilis, relMs: seri.relMs, gecenMs: gecen, unixMs: unix, adet: seri.adet };
    ist = { v: kanal(seri.v, seri.v, seri.v, seri.sira, gecen), i: kanal(seri.i, seri.i, seri.i, seri.sira, gecen),
      w: kanal(seri.w, seri.w, seri.w, seri.sira, gecen) };
    const birler = new Float64Array(seri.adet).fill(1);
    for (const [p, q] of acilisParcalari(seri.acilis)) {
      const t = seri.relMs.subarray(p, q);
      const ew = enerji(t, seri.w.subarray(p, q), birler.subarray(p, q),
        -Infinity, Infinity, { boslukMs: AYRINTI_BOSLUK_MS });
      const ei = enerji(t, seri.v.subarray(p, q), seri.i.subarray(p, q),
        -Infinity, Infinity, { boslukMs: AYRINTI_BOSLUK_MS });
      en.wh += ew.wh;
      en.mah += ei.mah;
      en.sureS += ei.sureS;
    }
    for (let k = 0; k < seri.adet; k++) {
      if (seri.kayitBayrak[k] & KA_KAYIP_ONCE) uyar("kayip_once", 1);
      if (seri.kayitBayrak[k] & KA_SILME) uyar("silme", 1);
      if (seri.ornekBayrak[k] & KAO_V_HATA) uyar("v_hata", 1);
      if (seri.ornekBayrak[k] & KAO_I_HATA) uyar("i_hata", 1);
      if (seri.ornekBayrak[k] & KAO_V_DOYDU) uyar("v_doydu", 1);
    }
    bosluk = bosluklar(satir, AYRINTI_BOSLUK_MS);
  } else {
    seri = noktaSerileri(oturum, { eksen });
    araliklar = seri.araliklar;
    satir = { acilis: seri.acilis, relMs: seri.relMs, gecenMs: seri.gecenMs, unixMs: seri.unixMs, adet: seri.adet };
    ist = {
      v: kanal(seri.vOrt, seri.vMin, seri.vMaks, seri.sira, seri.gecenMs),
      i: kanal(seri.iOrt, seri.iMin, seri.iMaks, seri.sira, seri.gecenMs),
      w: kanal(seri.wOrt, seri.wMin, seri.wMaks, seri.sira, seri.gecenMs),
    };
    const sinir = noktaBoslukMs(oturum);
    for (const [p, q] of acilisParcalari(seri.acilis)) {
      const t = seri.relMs.subarray(p, q);
      const ew = enerji(t, seri.wOrt.subarray(p, q), new Float64Array(q - p).fill(1),
        -Infinity, Infinity, { boslukMs: sinir });
      const ei = enerji(t, seri.vOrt.subarray(p, q), seri.iOrt.subarray(p, q),
        -Infinity, Infinity, { boslukMs: sinir });
      en.wh += ew.wh;
      en.mah += ei.mah;
      en.sureS += ew.sureS;
    }
    for (let k = 0; k < seri.adet; k++) {
      const f = seri.bayrak[k];
      if (seri.n[k] === 0) uyar("bos_nokta", 1);
      if (f & KN_KAYIP_ONCE) uyar("kayip_once", 1);
      if (f & KN_DURAKLAMA) uyar("duraklama", 1);
      if (f & KN_V_HATA) uyar("v_hata", 1);
      if (f & KN_I_HATA) uyar("i_hata", 1);
      if (f & KN_V_DOYDU) uyar("v_doydu", 1);
    }
    bosluk = bosluklar(satir, sinir);
  }

  // ── kimlik, notlar
  const tur = b ? b.oturum_turu : null;
  const notlar = [...oturum.notlar.entries()].sort((x, y) => x[0] - y[0]).map(([sira, nt]) => {
    const genel = !nt.nokta_ms;
    const z = genel ? null : anZamani(eksen, araliklar, nt.nokta_ms, null);
    if (z && z.acilis === null) uyar("not_belirsiz", 1);
    return { sira, noktaMs: nt.nokta_ms, metin: nt.metin, genel, ...an(z) };
  });

  // ── olaylar (kayit sirasiyla)
  const olaylar = [...oturum.olaylar].sort((x, y) => x.sira - y.sira).map((o) => {
    const z = anZamani(eksen, araliklar, o.kart_ms, o.sira);
    if (z.acilis === null) uyar("zaman_belirsiz", 1);
    if ("ham" in o) uyar("olay_bilinmeyen", 1);
    return { sira: o.sira, tur: { kod: o.tur, metin: ceviriKod("olay.", o.tur, dil) }, kartMs: o.kart_ms,
      ...an(z), alanlar: olayAlanlari(o) };
  });

  // ── pil
  let pil = null;
  const pilOlay = oturum.olaylar.filter((o) => [KO_PIL_AYAR, KO_DCIR, KO_PIL_SONUC].includes(o.tur) && !("ham" in o))
    .sort((x, y) => x.sira - y.sira);
  if (tur === OTURUM_PIL || pilOlay.length) {
    const ayar = pilOlay.filter((o) => o.tur === KO_PIL_AYAR)[0];
    const sonuc = pilOlay.filter((o) => o.tur === KO_PIL_SONUC).pop();
    pil = {
      ayar: ayar ? olayAlanlari(ayar) : null,
      sonuc: sonuc ? { ...olayAlanlari(sonuc), durumMetin: ceviriKod("pil.durum.", sonuc.durum, dil),
        hataMetin: ceviriKod("pil.hata.", sonuc.hata, dil) } : null,
      dcir: pilOlay.filter((o) => o.tur === KO_DCIR).map((o) => ({ sira: o.sira, ...olayAlanlari(o),
        kartMs: o.kart_ms, ...an(anZamani(eksen, araliklar, o.kart_ms, o.sira)) })),
    };
  }

  // ── skop
  const yerler = seri ? seri.yerler : skopYerleri(oturum);   // W1 inceleme: seriler hesapladi
  const yeri = new Map(yerler.map((x) => [x.sira, x]));
  uyar("skop_bosluk", yerler.filter((x) => x.once !== null && x.sonra !== null).length);
  const skopSira = [...yerler.map((x) => x.sira),
    ...[...oturum.skoplar.keys()].filter((k) => !yeri.has(k)).sort((x, y) => x - y)];
  const yakalamalar = skopSira.map((sira) => [sira, oturum.skoplar.get(sira)]).map(([sira, y]) => {
    const m = y.meta;
    const z = m ? anZamani(eksen, araliklar, m.t_ms, sira, y.acilis) : null;
    if (z && z.acilis === null) uyar("zaman_belirsiz", 1);
    if (!y.tam) uyar("skop_eksik", 1);
    return { sira, no: y.no, toplam: y.toplam, tam: y.tam, hz: m ? m.hz : null, tdivUs: m ? m.tdiv_us : null,
      tetiklendi: m ? !!m.tetiklendi : null, kartMs: m ? m.t_ms : null, sureMs: m ? m.sure_ms : null, ...an(z) };
  });

  // ── zaman
  const s0 = eksen.segmentler[0];
  let bitisZ = null;
  if (satir.adet) {
    const k = satir.adet - 1;
    bitisZ = { acilis: satir.acilis[k], gecenMs: nn(satir.gecenMs[k]), unixMs: nn(satir.unixMs[k]) };
  } else if (yakalamalar.length) {
    const y = yakalamalar[yakalamalar.length - 1];
    const sure = y.sureMs || 0;
    bitisZ = { acilis: y.acilis, gecenMs: y.gecenMs === null ? null : y.gecenMs + sure,
      unixMs: y.unixS === null ? null : y.unixS * 1000 + sure };
  }
  if (!b) uyar("baslik_yok", 1);
  else if (oturum.basi_eksik) uyar("basi_eksik", 1);
  if (!oturum.bitir) uyar("acik", 1);
  uyar("devam", oturum.devamlar.length);
  if (b && s0.unixMs === null) uyar("saat_yok", 1);
  let bilinmeyen = 0;
  for (let k = 0; k < satir.adet; k++) if (!Number.isFinite(satir.gecenMs[k])) bilinmeyen++;
  uyar("gecen_bilinmiyor", bilinmeyen);
  let beklenen = 0;
  if (oturum.bitir) beklenen = oturum.bitir.nokta_adedi;
  else for (const s of seri.sira) beklenen = Math.max(beklenen, s + 1);
  uyar("nokta_eksik", Math.max(0, beklenen - satir.adet));

  const kalibrasyon = kalibrasyonBolumu(oturum, kalibrasyonGecmisi, dil, uyar);

  const rapor = {
    surum: RAPOR_SURUM,
    dil,
    kimlik: {
      oturumNo: oturum.id,
      tur: { kod: tur, metin: tur === null ? null : ceviriKod("oturum.tur.", tur, dil) },
      ad: oturum.ad, etiketler: [...oturum.etiketler],
      firmware: b ? b.surum : null, hizMs: b ? b.hiz_ms : null, ayrintili,
      bicimSurum: b ? b.bicim_surum : null, basiEksik: oturum.basi_eksik, tekrarAdet: oturum.tekrar_adet,
    },
    notlar,
    zaman: {
      baslangic: s0.unixMs === null ? null : { unixS: s0.unixMs / 1000, iso: new Date(s0.unixMs).toISOString() },
      bitis: bitisZ ? an(bitisZ) : null,
      toplamMs: bitisZ ? bitisZ.gecenMs : null,
      olculenMs: en.sureS * 1000,
      boslukMs: bosluk.ms,
      boslukAdet: bosluk.adet,
    },
    sayac: {
      nokta: oturum.noktalar.length, ayrintiOrnek: ayrintili ? seri.adet : 0,
      devam: oturum.devamlar.length, olay: oturum.olaylar.length, not: oturum.notlar.size,
      skopAdet: oturum.skoplar.size,
    },
    bitis: oturum.bitir
      ? { sebep: { kod: oturum.bitir.sebep, metin: ceviriKod("sebep.", oturum.bitir.sebep, dil) },
        noktaAdedi: oturum.bitir.nokta_adedi }
      : { sebep: { kod: null, metin: ceviri("sebep.acik", dil) }, noktaAdedi: null },
    istatistik: ist,
    enerji: { wh: en.wh, mah: en.mah, sureS: en.sureS },
    pil,
    kalibrasyon,
    olaylar,
    skop: { adet: yakalamalar.length, tam: yakalamalar.filter((y) => y.tam).length,
      eksik: yakalamalar.filter((y) => !y.tam).length, yakalamalar },
    uyarilar: [...uyarilar.values()].map((u) => ({ kod: u.kod, sayi: u.sayi,
      metin: ceviri(`uyari.${u.kod}`, dil, { sayi: u.sayi, ...u.deg }) })),
  };
  return jsonla(rapor);
}

/** Ardisik satirlar arasi bosluk: acilis degisimi ya da (ayni acilista) dt > sinir. */
function bosluklar(satir, sinir) {
  let adet = 0;
  let ms = 0;
  for (let k = 1; k < satir.adet; k++) {
    let dt;
    if (satir.acilis[k] !== satir.acilis[k - 1]) {
      dt = satir.gecenMs[k] - satir.gecenMs[k - 1];
    } else {
      dt = satir.relMs[k] - satir.relMs[k - 1];
      if (!(dt > sinir)) continue;
    }
    adet++;
    ms = ms === null || !Number.isFinite(dt) ? null : ms + dt;
  }
  return { adet, ms };
}
