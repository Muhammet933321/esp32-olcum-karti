// KartAg sarmalayicisi: Kotlin eklentisini `ortak/` kodunun bekledigi fetch bicimine cevirir
// (ortak/src/imza.js ve esitle.js `ortam.fetch` alir — tasarim O7). WebView kendi basina aga CIKMAZ.
//
//   const ag = agKur(eklenti, { yerelDongu });
//   const y = await ag.kartFetch("http://192.168.1.7/eslestir/bilgi", { method: "GET", headers: {} });
//   y.status, y.ok, y.headers.get("X-Acilis"), await y.arrayBuffer(), await y.text(), await y.json()
//
// Hata: KartAgHatasi(tur). tur eklentinin soyledigi TUR adidir; baska hicbir ayrinti (adres, istisna
// metni) tasinmaz (A45).

import { hedefAyir, HedefHatasi } from "./hedef.js";

export const HATA_TURLERI = Object.freeze([
  "bicim", "ozel-degil", "ad-izinsiz", "ad-cozulmedi", "wifi-yok", "zaman-asimi", "baglanti",
  "cleartext", "govde-buyuk", "ic-hata",
]);

export class KartAgHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KartAgHatasi";
    this.tur = tur;
  }
}

function base64Kodla(b) {
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

function base64Coz(s) {
  const ham = atob(s);
  const b = new Uint8Array(ham.length);
  for (let i = 0; i < ham.length; i++) b[i] = ham.charCodeAt(i);
  return b;
}

function govdeBayt(govde) {
  if (govde == null) return null;
  if (typeof govde === "string") return new TextEncoder().encode(govde);
  if (govde instanceof Uint8Array) return govde;
  if (govde instanceof ArrayBuffer) return new Uint8Array(govde);
  throw new KartAgHatasi("bicim");
}

// "http://<ad>[:port][/yol...]" — URL sinifi KULLANILMAZ: o, tuhaf IP yazimlarini (0xC0A80101)
// sessizce normallestirir; kural ham yazima uygulanmali (Kotlin tarafi da oyle yapar).
export function urlDenetle(url, { yerelDongu = false } = {}) {
  const m = typeof url === "string" ? /^http:\/\/([^/?#]*)(\/[\x21-\x7e]*)?$/.exec(url) : null;
  if (!m) throw new KartAgHatasi("bicim");
  try {
    return hedefAyir(m[1], { yerelDongu });
  } catch (e) {
    if (e instanceof HedefHatasi) throw new KartAgHatasi(e.tur);
    throw e;
  }
}

function yanitKur(s) {
  const basliklar = new Map();
  for (const [ad, deger] of Object.entries(s.basliklar || {})) basliklar.set(ad.toLowerCase(), String(deger));
  const govde = base64Coz(s.govde || "");
  return {
    status: s.kod,
    ok: s.kod >= 200 && s.kod < 300,
    adres: s.adres || null,
    headers: { get: (ad) => (basliklar.has(ad.toLowerCase()) ? basliklar.get(ad.toLowerCase()) : null) },
    arrayBuffer: async () => govde.buffer.slice(govde.byteOffset, govde.byteOffset + govde.byteLength),
    text: async () => new TextDecoder().decode(govde),
    json: async () => JSON.parse(new TextDecoder().decode(govde)),
  };
}

export function agKur(eklenti, { yerelDongu = false, zamanAsimiMs = 5000, azamiGovde = 64 * 1024 } = {}) {
  if (!eklenti || typeof eklenti.istek !== "function") throw new TypeError("eklenti.istek gerekli");

  async function kartFetch(url, secenek = {}) {
    urlDenetle(url, { yerelDongu });
    const yontem = (secenek.method || "GET").toUpperCase();
    if (yontem !== "GET" && yontem !== "POST") throw new KartAgHatasi("bicim");
    const govde = govdeBayt(secenek.body);
    const istek = {
      url,
      yontem,
      basliklar: { ...(secenek.headers || {}) },
      zamanAsimiMs: secenek.zamanAsimiMs ?? zamanAsimiMs,
      azamiGovde: secenek.azamiGovde ?? azamiGovde,
    };
    if (govde) istek.govde = base64Kodla(govde);
    let sonuc;
    try {
      sonuc = await eklenti.istek(istek);
    } catch (e) {
      const tur = e && typeof e.code === "string" && HATA_TURLERI.includes(e.code) ? e.code : "ic-hata";
      throw new KartAgHatasi(tur);
    }
    if (!sonuc || !Number.isInteger(sonuc.kod)) throw new KartAgHatasi("ic-hata");
    return yanitKur(sonuc);
  }

  return { kartFetch };
}
