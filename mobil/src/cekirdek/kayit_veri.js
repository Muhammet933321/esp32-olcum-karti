// Telefondaki kayit kopyasinin COZULMESI ve ekranlara hazirlanmasi (tasarim A24–A26, A41).
// Web Worker'da kosar (src/isci/kayit_isci.js); Worker yoksa ayni kod ana is parcaciginda (yedek).
// Hesap TEK KOPYA: akis cozme / oturum kurma ortak/src/kayit.js, zaman ekseni ve seriler
// ortak/src/disari.js, piramit ortak/src/ozet.js, aralik okumasi ortak/src/grafik.js + istatistik.js.
// Panelin SAF yardimcilari (liste birlestirme, grafik serileri, okuma) KOPYALANMADAN ice aktarilir
// (@panel = arayuz3/ekran): PC'de ve telefonda ayni kayit ayni sayilari verir.
//
//   const i = islemciKur({ getir });            // getir(url) -> Promise<ArrayBuffer | Uint8Array>
//   await i.isle("yukle", { url, akisKimlik }); // -> { kayit, oturum, bayt, gecerliBayt, uyari }
//   await i.isle("liste", { kart, arama, tur }) // -> [satir]   (kart: /kayit/liste govdesi | null)
//   await i.isle("oturum", { oturum })          // -> { tur, adet, t0, t1, seriler, baslik, notlar } | null
//   await i.isle("okuma", { oturum, tA, tB })   // -> { dt, v, i, w, enerji } | null
//   await i.isle("disariTurleri", { oturum })   // -> ["csv_tr", "csv_en", "ham", "rapor"] | null   (5F)
//   await i.isle("disari", { oturum, tur, dil }) // -> { ad, mime, bayt: Uint8Array } | null
//
// Dosyanin sonundaki YARIM kayit (esitleme o an yaziyor olabilir) sessizce disarida kalir
// (akisOnek); gecerli on ek cozulur. Bos / olmayan dosya: bos liste.
import { akisOnek, oturumlariKur } from "@ortak/kayit.js";
import { ozetKur } from "@ortak/ozet.js";
import { zamanYazi } from "@ortak/grafik.js";
import { oturumRaporu } from "@ortak/rapor.js";
import { disariTurleri, disariUret, dosyaAdi, grafikSerileri, notListesi, okumaHesapla, tarihYaz } from "@panel/kayit_gorunum.js";
import { listeBirlestir, satirSuz } from "@panel/kayitlar.js";
import { raporMetni } from "./rapor_metin.js";

export const TURLER = Object.freeze(["hepsi", "olcum", "pil", "skop"]);
export const YEREL_NEREDE = "telefon";
// Paylasilan dosyanin ust siniri: bundan buyugu kopruden (base64) gecirilmez — ham kayit oner.
export const DISARI_AZAMI = 48 * 1024 * 1024;
export const RAPOR_TURU = "rapor";

// Sure yazisi SANIYE cozunurlugunde (telefon ekrani dar; panel milisaniye yazar).
const sureYaz = (ms) => (Number.isFinite(ms) ? zamanYazi(ms, 1000) : null);

export class KayitVeriHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KayitVeriHatasi";
    this.tur = tur;
  }
}

// Ham baytlar -> cozulmus veri. Saf.
export function veriKur(baytlar, akisKimlik = null) {
  const b = baytlar instanceof Uint8Array ? baytlar : new Uint8Array(baytlar);
  const [kayitlar, gecerliBayt] = akisOnek(b);
  const oturumlar = oturumlariKur(kayitlar);
  const sonSira = new Map();
  for (const k of kayitlar) if (k.oturum && k.sira > (sonSira.get(k.oturum) || 0)) sonSira.set(k.oturum, k.sira);
  return {
    kimlik: akisKimlik, kayitlar, oturumlar, sonSira, bayt: b.length, gecerliBayt,
    uyari: oturumlar.uyarilar.length, onbellek: new Map(),
  };
}

// Liste satiri (ekrana giden, duz nesne). Saf.
function satirOzeti(s) {
  return {
    anahtar: s.anahtar, oturum: s.oturum, tur: s.tur, ad: typeof s.ad === "string" && s.ad !== "" ? s.ad : null,
    etiketler: [...s.etiketler], tarih: tarihYaz(s.unix), sure: s.sureMs === null ? null : sureYaz(s.sureMs),
    nokta: s.nokta, nerede: s.nerede, durum: s.durum, eksik: s.eksik === true, eskiKart: s.eskiKart === true,
    yerelde: s.yerelde === true,
  };
}

// veri (null olabilir) + kartin /kayit/liste govdesi (null olabilir) -> suzulmus satirlar. Saf.
export function listeKur(veri, { kart = null, arama = "", tur = "hepsi" } = {}) {
  const kartGecerli = kart && typeof kart === "object" && Array.isArray(kart.oturumlar) ? kart : null;
  const yereller = veri && veri.oturumlar.size > 0
    ? [{ kimlik: veri.kimlik !== null ? veri.kimlik : (kartGecerli ? kartGecerli.kimlik : 0), oturumlar: veri.oturumlar, sonSira: veri.sonSira }]
    : [];
  const satirlar = listeBirlestir({ kart: kartGecerli, yereller, yerelNerede: YEREL_NEREDE });
  return satirSuz(satirlar, { arama: typeof arama === "string" ? arama : "", tur: TURLER.includes(tur) ? tur : "hepsi" }).map(satirOzeti);
}

function hazirla(veri, oturumNo) {
  if (!veri) return null;
  const o = veri.oturumlar.get(oturumNo);
  if (!o) return null;
  let h = veri.onbellek.get(oturumNo);
  if (!h) {
    h = grafikSerileri(o, { kayitlar: veri.kayitlar });
    veri.onbellek.set(oturumNo, h);
  }
  return { o, h };
}

// Kayit gorunumunun verisi: seriler (piramitleriyle), zaman araligi, baslik, notlar. Saf.
export function oturumGorunumu(veri, oturumNo) {
  const p = hazirla(veri, oturumNo);
  if (!p) return null;
  const { o, h } = p;
  const satir = listeKur(veri).find((s) => s.oturum === oturumNo) || null;
  const seriler = h.seriler.map((s) => ({
    ad: s.ad, t: s.t, y: s.y, birim: s.birim, renk: s.renk, eksen: s.eksen, boslukMs: s.boslukMs, enAzAralik: s.enAzAralik,
    ...(s.zarf ? { zarf: true, kalinlik: s.kalinlik } : {}),
    oz: ozetKur(s.t, s.y),                       // piramit BURADA (arka plan iscisinde) kurulur: ana is parcacigi donmaz
  }));
  const n = h.t ? h.t.length : 0;
  // Gecerli (sonlu) olcum sayisi: ADC okunamadan kaydedilmis oturumda noktalar VAR ama deger YOK —
  // ekran bos grafik yerine bunu soyler.
  let gecerli = 0;
  if (seriler.length) {
    const v = seriler.find((s) => s.ad === "V"), i = seriler.find((s) => s.ad === "I");
    for (let k = 0; k < n; k++) if ((v && Number.isFinite(v.y[k])) || (i && Number.isFinite(i.y[k]))) gecerli += 1;
  }
  return {
    oturum: oturumNo, tur: h.tur, adet: h.adet, gecerli, t0: n ? h.t[0] : 0, t1: n ? h.t[n - 1] : 0,
    tahmini: Array.isArray(h.tahmini) && h.tahmini.some(Boolean),
    seriler, baslik: satir,
    notlar: h.tur === "yok" ? [...o.notlar.values()].map((x) => ({ metin: x.metin, genel: true, gecen: null }))
      : notListesi(o, h).map((x) => ({ metin: x.metin, genel: x.genel, gecen: x.gecenMs === null ? null : sureYaz(x.gecenMs) })),
  };
}

const sayi = (x) => (Number.isFinite(x) ? x : null);
const kanalOzeti = (k) => (k ? { birim: k.birim, adet: k.adet, ort: sayi(k.ort), min: sayi(k.min), maks: sayi(k.maks), rms: sayi(k.rms) } : null);

// [tA, tB] araliginin istatistigi (HAM veriden) ve enerjisi. Saf.
export function aralikOkuma(veri, oturumNo, tA, tB) {
  const p = hazirla(veri, oturumNo);
  if (!p || p.h.tur === "yok" || !Number.isFinite(tA) || !Number.isFinite(tB)) return null;
  const ok = okumaHesapla(p.h, tA, tB)                    // sinirlarin sirasini okumaHesapla duzeltir;
  if (!ok) return null;
  return {
    dt: sayi(ok.dt), sure: Number.isFinite(ok.dt) ? sureYaz(ok.dt) : null,
    v: kanalOzeti(ok.v), i: kanalOzeti(ok.i), w: kanalOzeti(ok.w),
    enerji: ok.enerji ? { wh: sayi(ok.enerji.wh), mah: sayi(ok.enerji.mah) } : null,
  };
}

// Oturumun paylasilabilir turleri: panelin disa aktarma turleri (CSV Excel-TR / EN, ham .kyt) + rapor metni.
export function paylasimTurleri(veri, oturumNo) {
  const o = veri ? veri.oturumlar.get(oturumNo) : null;
  return o ? [...disariTurleri(o), RAPOR_TURU] : null;
}

// Paylasilacak dosya: { ad, mime, bayt }. CSV ve ham kayit panelin urettigiyle BAYT BAYT ayni
// (`disariUret` kopyalanmadan ice aktarilir); rapor ortak `oturumRaporu`nun duz metni. Saf.
export function paylasimUret(veri, oturumNo, tur, dil = "tr", azami = DISARI_AZAMI) {
  const o = veri ? veri.oturumlar.get(oturumNo) : null;
  if (!o || !paylasimTurleri(veri, oturumNo).includes(tur)) return null;
  let d;
  if (tur === RAPOR_TURU) {
    const metin = raporMetni(oturumRaporu(o, { kayitlar: veri.kayitlar, dil: dil === "en" ? "en" : "tr" }), dil === "en" ? "en" : "tr");
    d = { ad: dosyaAdi(o, "rapor", "txt"), mime: "text/plain;charset=utf-8", bayt: new TextEncoder().encode(metin) };
  } else {
    d = disariUret(tur, o, veri.kayitlar);
  }
  if (!d || !(d.bayt instanceof Uint8Array)) return null;
  if (d.bayt.length > azami) throw new KayitVeriHatasi("cok-buyuk");
  return { ad: d.ad, mime: d.mime, bayt: d.bayt };
}

// Mesaj islemcisi: Worker'da ve yedekte AYNI. Durum (cozulmus veri) islemcinin icinde kalir.
export function islemciKur({ getir }) {
  if (typeof getir !== "function") throw new TypeError("getir gerekli");
  let veri = null;

  async function isle(is, a = {}) {
    switch (is) {
      case "yukle": {
        if (typeof a.url !== "string") throw new KayitVeriHatasi("bicim");
        let ham;
        try { ham = await getir(a.url); } catch { throw new KayitVeriHatasi("okunamadi"); }
        veri = veriKur(ham === null || ham === undefined ? new Uint8Array(0) : ham, Number.isInteger(a.akisKimlik) ? a.akisKimlik : null);
        return { kayit: veri.kayitlar.length, oturum: veri.oturumlar.size, bayt: veri.bayt, gecerliBayt: veri.gecerliBayt, uyari: veri.uyari };
      }
      case "bosalt":
        veri = null;
        return {};
      case "liste":
        return listeKur(veri, a);
      case "oturum":
        return oturumGorunumu(veri, a.oturum);
      case "okuma":
        return aralikOkuma(veri, a.oturum, a.tA, a.tB);
      case "disariTurleri":
        return paylasimTurleri(veri, a.oturum);
      case "disari":
        return paylasimUret(veri, a.oturum, a.tur, a.dil);
      default:
        throw new KayitVeriHatasi("bicim");
    }
  }

  return { isle };
}
