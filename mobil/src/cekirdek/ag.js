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
  "cleartext", "govde-buyuk", "mesgul", "ic-hata",
]);

export const SURE_PAYI_MS = 500;
export const P0_AZAMI_ADRES = 4;              // P0.kt AZAMI_ADRES ile ayni
export const P0_SURE_MS = 5000;               // P0.kt TOPLAM_SURE_MS (4400) + pay: eklenti donmezse de biter
export const AKIS_AC_SURE_MS = 3000;          // akisAc / akisKapat cagrisi hemen doner (baglanti kendi is parcaciginda)

// soz'u ms ile yaristirir; sure dolarsa KartAgHatasi("zaman-asimi").
export function sureli(soz, ms) {
  return new Promise((coz, reddet) => {
    const t = setTimeout(() => reddet(new KartAgHatasi("zaman-asimi")), ms);
    Promise.resolve(soz).then(
      (v) => { clearTimeout(t); coz(v); },
      (e) => { clearTimeout(t); reddet(e); },
    );
  });
}

export class KartAgHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KartAgHatasi";
    this.tur = tur;
  }
}

// Eklentinin p0 yaniti -> { tamam, adres, basarili, sureMs }. `basarili`: 204 veren adresler — yalniz
// GONDERILEN listedekiler sayilir (eklenti baska bir adres uyduramaz). Eski eklenti (yalniz `adres`)
// tek ogeli liste olur. Saf.
export function p0Sonucu(s, gonderilen, sureMs) {
  const tamam = Boolean(s) && s.tamam === true;
  const ham = tamam && Array.isArray(s.basarili) ? s.basarili : [];
  const basarili = [...new Set(ham.filter((a) => typeof a === "string" && gonderilen.includes(a)))];
  const adres = tamam && typeof s.adres === "string" ? s.adres : null;
  if (adres !== null && gonderilen.includes(adres) && !basarili.includes(adres)) basarili.push(adres);
  return { tamam, adres: adres !== null ? adres : (basarili[0] ?? null), basarili, sureMs };
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
  // Ad kisminda bosluk: hedefAyir kullanici girdisini kirpar, ama bir URL'nin icinde bosluk yazim
  // hatasidir (Kotlin tarafi da reddeder).
  if (!m || /[^\x21-\x7e]/.test(m[1])) throw new KartAgHatasi("bicim");
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

export function agKur(eklenti, { yerelDongu = false, zamanAsimiMs = 5000, azamiGovde = 64 * 1024, akisAcSureMs = AKIS_AC_SURE_MS } = {}) {
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
      // Sure eklentiye EMANET edilmez: eklenti hic donmezse de cagiran asili kalmaz.
      sonuc = await sureli(eklenti.istek(istek), istek.zamanAsimiMs + SURE_PAYI_MS);
    } catch (e) {
      if (e instanceof KartAgHatasi) throw e;
      const tur = e && typeof e.code === "string" && HATA_TURLERI.includes(e.code) ? e.code : "ic-hata";
      throw new KartAgHatasi(tur);
    }
    if (!sonuc || !Number.isInteger(sonuc.kod)) throw new KartAgHatasi("ic-hata");
    try {
      return yanitKur(sonuc);
    } catch {
      throw new KartAgHatasi("ic-hata");       // bozuk base64 vb.: ham istisna disari cikmaz
    }
  }

  // ACIL DURDURMA (A8–A11). ASLA atmaz, hicbir seyi beklemez: eklenti cagrisi bu islevin ICINDE,
  // ilk await'ten ONCE yapilir (kilit, kuyruk, imza, kimlik dogrulamasi araya giremez). Hedef kurali
  // yerel tarafta (HedefCoz); burada adres dogrulanmaz ki yeni bir hata yolu dogmasin.
  function p0(adresler) {
    const t0 = Date.now();
    const liste = [...new Set((Array.isArray(adresler) ? adresler : []).filter((a) => typeof a === "string" && a !== ""))].slice(0, P0_AZAMI_ADRES);
    const yok = () => ({ tamam: false, adres: null, basarili: [], sureMs: Date.now() - t0 });
    if (liste.length === 0 || typeof eklenti.p0 !== "function") return Promise.resolve(yok());
    let cagri;
    try { cagri = eklenti.p0({ adresler: liste }); } catch { return Promise.resolve(yok()); }
    return sureli(cagri, P0_SURE_MS).then(
      (s) => p0Sonucu(s, liste, Date.now() - t0),
      yok,
    );
  }

  // CANLI AKIS (A6, A7). Akis EventSource ile DEGIL, eklentinin kendi baglantisiyla okunur; satirlar
  // "akis", durum "akisDurum" olayiyla gelir (dinleme: canli.js). Adres imza tasir (_c _s _i): hicbir
  // hataya girmez, yalniz TUR doner. Hedef kurali ve yol (yalniz /akis) eklentiden ONCE denetlenir.
  async function akisAc(url) {
    urlDenetle(url, { yerelDongu });
    const yol = /^http:\/\/[^/?#]*(\/[\x21-\x7e]*)?$/.exec(url)[1] || "";
    if (yol !== "/akis" && !yol.startsWith("/akis?")) throw new KartAgHatasi("bicim");
    if (typeof eklenti.akisAc !== "function") throw new KartAgHatasi("ic-hata");
    let s;
    try {
      s = await sureli(eklenti.akisAc({ url }), akisAcSureMs);
    } catch (e) {
      if (e instanceof KartAgHatasi) throw e;
      const tur = e && typeof e.code === "string" && HATA_TURLERI.includes(e.code) ? e.code : "ic-hata";
      throw new KartAgHatasi(tur);
    }
    if (!s || typeof s.kimlik !== "string" || s.kimlik === "") throw new KartAgHatasi("ic-hata");
    return { kimlik: s.kimlik };
  }

  // ASLA atmaz: kapatma bir temizliktir, hatasi cagirani ilgilendirmez.
  async function akisKapat(kimlik) {
    try {
      if (typeof eklenti.akisKapat === "function") await sureli(eklenti.akisKapat({ kimlik }), akisAcSureMs);
    } catch { /* akis zaten kapali ya da eklenti yanit vermedi */ }
  }

  // Onceki sayfa yuklemesinden (WebView yeniden yuklendi) yerelde acik kalmis akislarin HEPSI kapanir:
  // kartin 4 yuvasindan birini sahipsiz tutmasinlar. ASLA atmaz.
  async function akislariKapat() {
    try {
      if (typeof eklenti.akisKapat === "function") await sureli(eklenti.akisKapat({ hepsi: true }), akisAcSureMs);
    } catch { /* eklenti yanit vermedi */ }
  }

  return { kartFetch, p0, akisAc, akisKapat, akislariKapat };
}
