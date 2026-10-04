// Ekranlarin ceviri kisayolu. Dil secimi Ayarlar'a gelene kadar sabit (A43); tek yerde dursun.
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";

export const DIL = "tr";

export function c(anahtar, degerler = null) {
  return ceviriMobil(anahtar, DIL, degerler);
}

// { anahtar, degerler } | { yazi } | null -> metin
export function yaz(o) {
  if (!o) return "";
  return typeof o.yazi === "string" ? o.yazi : c(o.anahtar, o.degerler || null);
}
