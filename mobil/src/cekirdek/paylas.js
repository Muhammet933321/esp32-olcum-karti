// Dosya paylasimi (5F; tasarim A41): uretilen dosya (CSV / ham .kyt / rapor) Paylas eklentisine PARCA PARCA
// verilir (kopru base64 tasir; parca basina en cok PARCA bayt), eklenti onu uygulamanin ONBELLEGINE yazar ve
// Android'in paylasim penceresini acar. Dosya nereye gidecegini KULLANICI secer; bu modul aga cikmaz.
//
//   const p = paylasKur({ eklenti });
//   await p.gonder({ ad, mime, bayt })      // hata: PaylasHatasi(tur)
//   await p.gonderGenis({ ad, mime, bayt }) // 5P (panel telefonda): ayni denetim; "; charset=utf-8" yazimi esnek
//
// Ad burada da denetlenir (eklenti ayrica denetler): yalniz harf / rakam / . _ - ve bilinen uzanti. Uzanti
// kumesi ve MIME kumesi Kotlin PaylasDeposu.AD / MIMELER ile AYNI (5P K11/K12: + html, pdf); ayrica MIME
// uzantiya UYMALI (UZANTI_MIME — eklentiden siki: k.csv + text/html reddedilir).

export const PARCA = 512 * 1024;
export const AD_DESENI = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.(csv|kyt|txt|html|pdf)$/;
const MIME = /^(text\/csv|text\/plain|application\/octet-stream|text\/html|application\/pdf)(;charset=utf-8)?$/;
const TUR = /^[a-z][a-z-]{0,23}$/;
// 5P: eski ad (gonderGenis'in deseni) — artik AD_DESENI'nin kendisi.
export const AD_DESENI_GENIS = AD_DESENI;
// Uzanti -> kabul edilen MIME'ler (karakter kumesi eki yalniz metin turlerinde, yalniz utf-8).
export const UZANTI_MIME = Object.freeze({
  csv: Object.freeze(["text/csv", "text/plain"]),
  txt: Object.freeze(["text/plain"]),
  kyt: Object.freeze(["application/octet-stream"]),
  html: Object.freeze(["text/html"]),
  pdf: Object.freeze(["application/pdf"]),
});
const METIN_TURU = new Set(["text/csv", "text/plain", "text/html"]);

// (ad, mime) -> eklentiye gidecek yalin MIME | null (gecersiz). Saf.
export function genisTurDenetle(ad, mime) {
  if (typeof ad !== "string" || !AD_DESENI_GENIS.test(ad) || ad.includes("..")) return null;
  if (typeof mime !== "string") return null;
  const m = /^([a-z]+\/[a-z0-9.+-]+)(?:; ?charset=utf-8)?$/i.exec(mime.trim());
  if (!m) return null;
  const tur = m[1].toLowerCase();
  if (m[0].length !== m[1].length && !METIN_TURU.has(tur)) return null;      // charset yalniz metin turunde
  const uzanti = ad.slice(ad.lastIndexOf(".") + 1);
  return UZANTI_MIME[uzanti].includes(tur) ? tur : null;
}

export class PaylasHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "PaylasHatasi";
    this.tur = tur;
  }
}

function base64Kodla(b) {
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

export function paylasKur({ eklenti }) {
  if (!eklenti) throw new TypeError("eklenti gerekli");
  let suruyor = false;

  async function cagir(ad, veri) {
    if (typeof eklenti[ad] !== "function") throw new PaylasHatasi("ic-hata");
    try {
      return (await eklenti[ad](veri)) || {};
    } catch (e) {
      throw new PaylasHatasi(e && typeof e.code === "string" && TUR.test(e.code) ? e.code : "ic-hata");
    }
  }

  async function gonder({ ad, mime, bayt } = {}) {
    if (typeof ad !== "string" || !AD_DESENI.test(ad) || ad.includes("..")) throw new PaylasHatasi("bicim");
    if (typeof mime !== "string" || !MIME.test(mime)) throw new PaylasHatasi("bicim");
    if (genisTurDenetle(ad, mime) === null) throw new PaylasHatasi("bicim");      // MIME uzantiya uymali
    return yolla(ad, mime, bayt);
  }

  // 5P: panelin dosyalari. Ad ve MIME birbirine uymali; eklentiye yalin MIME gider.
  async function gonderGenis({ ad, mime, bayt } = {}) {
    const tur = genisTurDenetle(ad, mime);
    if (tur === null) throw new PaylasHatasi("bicim");
    return yolla(ad, tur, bayt);
  }

  async function yolla(ad, mime, bayt) {
    if (!(bayt instanceof Uint8Array) || bayt.length === 0) throw new PaylasHatasi("bos");
    if (suruyor) throw new PaylasHatasi("mesgul");
    suruyor = true;
    try {
      await cagir("baslat", { ad });
      for (let i = 0; i < bayt.length; i += PARCA) {
        await cagir("yaz", { ad, parca: base64Kodla(bayt.subarray(i, Math.min(bayt.length, i + PARCA))) });
      }
      await cagir("gonder", { ad, mime: mime.split(";")[0], boy: bayt.length });
    } finally {
      suruyor = false;
    }
  }

  return { gonder, gonderGenis };
}
