// Panelin dosya uretimi ve yazdirma telefonda (5P K11, K12).
//   await dosyaVer({ ad, mime, bayt })   -> Android Paylas penceresi (cekirdek/paylas.js gonderGenis: csv, kyt,
//                                           txt, html, pdf; MIME uzantiya uymali). Hata: DosyaHatasi(tur)
//   await yazdir()                       -> Android yazdirma penceresi (Kotlin `Yazdir`: PrintManager +
//                                           WebView.createPrintDocumentAdapter; "PDF olarak kaydet" dahil)
// Tarayicidaki `a.download` / `window.print()` telefonda calismaz (WebView); panel ORTAM varsa bunlari cagirir.

import { dilSec, metin } from "./metin.js";

export class DosyaHatasi extends Error {
  constructor(tur, mesaj) {
    super(mesaj);
    this.name = "DosyaHatasi";
    this.tur = tur;
  }
}

const TUR = /^[a-z][a-z-]{0,23}$/;
const AD_AZAMI = 60;

// Yazdirma isinin adi (Android yazdirma kuyrugunda ve "PDF olarak kaydet"te dosya adi olur): belge
// basligindan, yalniz [A-Za-z0-9._-]. Saf.
export function isAdi(baslik) {
  const tr = { ç: "c", Ç: "C", ğ: "g", Ğ: "G", ı: "i", İ: "I", ö: "o", Ö: "O", ş: "s", Ş: "S", ü: "u", Ü: "U" };
  const s = String(baslik ?? "").replace(/[çÇğĞıİöÖşŞüÜ]/g, (h) => tr[h])
    .replace(/[^A-Za-z0-9._-]+/g, "-").replace(/-+/g, "-").replace(/^[-.]+|[-.]+$/g, "").slice(0, AD_AZAMI);
  return s || "olcum-karti";
}

function baytAl(b) {
  if (b instanceof Uint8Array) return b;
  if (b instanceof ArrayBuffer) return new Uint8Array(b);
  if (ArrayBuffer.isView(b)) return new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
  if (typeof b === "string") return new TextEncoder().encode(b);
  return null;
}

export function dosyaKur({ paylas, yazdirEklenti = null, belge = null, dilAl = () => "tr" }) {
  if (!paylas || typeof paylas.gonderGenis !== "function") throw new TypeError("paylas.gonderGenis gerekli");

  async function dosyaVer({ ad, mime, bayt } = {}) {
    const dil = dilSec(dilAl());
    const b = baytAl(bayt);
    try {
      await paylas.gonderGenis({ ad, mime, bayt: b });
    } catch (e) {
      const tur = e && typeof e.tur === "string" && TUR.test(e.tur) ? e.tur : "ic-hata";
      throw new DosyaHatasi(tur, `${metin("or.paylas", dil)} (${tur})`);
    }
    return true;
  }

  async function yazdir() {
    const dil = dilSec(dilAl());
    if (!yazdirEklenti || typeof yazdirEklenti.yazdir !== "function") throw new DosyaHatasi("ic-hata", `${metin("or.yazdir", dil)} (ic-hata)`);
    try {
      await yazdirEklenti.yazdir({ ad: isAdi(belge && belge.title) });
    } catch (e) {
      const tur = e && typeof e.code === "string" && TUR.test(e.code) ? e.code : "ic-hata";
      throw new DosyaHatasi(tur, `${metin("or.yazdir", dil)} (${tur})`);
    }
    return true;
  }

  return { dosyaVer, yazdir };
}
