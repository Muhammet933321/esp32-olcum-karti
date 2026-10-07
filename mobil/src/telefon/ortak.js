// "Bu telefon" bolumunun ortak yardimcilari (5P, K13): dil, ceviri, zaman yazisi, iki adimli onay.
// Saf; DOM'suz ve Vue'suz sinanir (test/telefon_bolum.test.js).
//
// Dil: panel bolume `dilSecim` verir ('tr' | 'en'; ileride 'sistem' gelebilir). 'sistem' ya da bilinmeyen
// deger telefonun diline bakar (en* -> en, gerisi tr). Sayi / zaman bicimi dile gore DEGISMEZ (panelin AY3'u).

import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";

function sistemDili() {
  try { return typeof navigator === "object" && navigator && typeof navigator.language === "string" ? navigator.language : ""; } catch { return ""; }
}

export function dilCoz(secim, sistem = sistemDili()) {
  if (secim === "tr" || secim === "en") return secim;
  return /^en\b/i.test(String(sistem || "")) ? "en" : "tr";
}

export function cevir(dil, anahtar, degerler = null) {
  return ceviriMobil(anahtar, dil === "en" ? "en" : "tr", degerler);
}

// { anahtar, degerler } | null -> metin
export function yazi(dil, o) {
  if (!o || typeof o.anahtar !== "string") return "";
  return cevir(dil, o.anahtar, o.degerler || null);
}

// Hata nesnesinden yalniz TUR adi (A45: mesaj, adres, imza ekrana cikmaz).
export function hataTuru(e) {
  return e && typeof e.tur === "string" && /^[a-z][a-z0-9-]{0,31}$/.test(e.tur) ? e.tur : "?";
}

// unix saniye -> yerel `YYYY-AA-GG SS:DD` (panelin eslesme ekraniyla ayni); gecersizse "—".
export function zamanYaz(s) {
  if (!(Number.isFinite(s) && s > 0)) return "—";
  const d = new Date(s * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  const i = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}`;
}

// Iki adimli onay (panelin deseni: ilk dokunus "Eminim" + "Vazgec" acar, ikincisi isi yapar).
// `onay`: o an silahli islemin anahtari ya da null. Yalniz SILAHLI anahtarin isi yapilir.
export function ikinciAdim(onay, anahtar) {
  return onay !== null && onay !== undefined && onay === anahtar;
}

// Bolum bilesenlerinin ortak karisimi: `dil` prop'u + `t()` / `yaz()`.
export const METIN_KARISIMI = Object.freeze({
  props: { dil: { type: String, default: "tr" } },
  methods: {
    t(anahtar, degerler = null) { return cevir(this.dil, anahtar, degerler); },
    yaz(o) { return yazi(this.dil, o); },
  },
});
