// Telefona ozel metinler (TR/EN). ortak/src/sozluk.js'ten AYRI (sozluk_pc.js deseni): ortak sozluk
// degistirilmez; burada yalniz telefon ekranlarinin metinleri durur. Anahtarlar "m." ile baslar.
// Kurallar (test/sozluk.test.js): her anahtarda bos olmayan tr VE en, yer tutucular iki dilde ayni,
// kullanilmayan anahtar yok, kullanilan her anahtar var, ortak sozlukle cakisma yok.
// ceviriMobil: once bu sozluk, yoksa ortak sozluk — HICBIR ZAMAN ATMAZ.

import { ceviri, sozluktenCeviri } from "@ortak/sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_MOBIL = Object.freeze({
  "m.uygulama": S("Ölçüm Kartı", "Measurement Board"),
});

export function ceviriMobil(anahtar, dil = "tr", degiskenler = null) {
  if (Object.hasOwn(SOZLUK_MOBIL, anahtar)) return sozluktenCeviri(SOZLUK_MOBIL, anahtar, dil, degiskenler);
  return ceviri(anahtar, dil, degiskenler);
}
