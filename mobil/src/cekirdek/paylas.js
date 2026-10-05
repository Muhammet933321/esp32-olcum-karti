// Dosya paylasimi (5F; tasarim A41): uretilen dosya (CSV / ham .kyt / rapor) Paylas eklentisine PARCA PARCA
// verilir (kopru base64 tasir; parca basina en cok PARCA bayt), eklenti onu uygulamanin ONBELLEGINE yazar ve
// Android'in paylasim penceresini acar. Dosya nereye gidecegini KULLANICI secer; bu modul aga cikmaz.
//
//   const p = paylasKur({ eklenti });
//   await p.gonder({ ad, mime, bayt })      // hata: PaylasHatasi(tur)
//
// Ad burada da denetlenir (eklenti ayrica denetler): yalniz harf / rakam / . _ - ve bilinen uzanti.

export const PARCA = 512 * 1024;
export const AD_DESENI = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.(csv|kyt|txt)$/;
const MIME = /^(text\/csv|text\/plain|application\/octet-stream)(;charset=utf-8)?$/;
const TUR = /^[a-z][a-z-]{0,23}$/;

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

  return { gonder };
}
