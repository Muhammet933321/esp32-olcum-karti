// 5A-3 — sahte kartin KRIPTOGRAFISI: 1D eslestirme + imza dogrulama, YALNIZ node:crypto ile.
//
// `ortak/src/imza.js` BILEREK ice aktarilmiyor: bu dosya protokolun bagimsiz ikinci
// uygulamasi (kaynak: tasarim/2026-10-01-1d-eslestirme.md K5-K10 ve kartin guvenlik.h'si).
// Iki uygulama uretim/vektor_guvenlik.json uzerinde uzlasmali (test: sahte-kart.test.js).
//
//   P       = PBKDF2-HMAC-SHA256(parola, tuz, tur, 32)
//   kanit   = HMAC(P, "OK1-istemci\n" kimlik "\n" nk "\n" nc "\n" ad)      (nk, nc hex)
//   kart    = HMAC(P, "OK1-kart\n"    kimlik "\n" nk "\n" nc "\n" n)
//   K       = HMAC(P, "OK1-anahtar\n" kimlik "\n" nk "\n" nc "\n" n)
//   kanonik = "OK1\n" yontem "\n" yol ["?" a=d&..] "\n" acilis "\n" sayac "\n" hex(sha256(govde))
//   imza    = hex(HMAC(K, kanonik))

import { createHash, createHmac, pbkdf2Sync, timingSafeEqual } from "node:crypto";

export const PENCERE = 64n;             // kartta GUV_PENCERE
export const AD_AZAMI = 24;             // kartta GUV_AD_AZAMI (bayt)
export const PAROLA_EN_AZ = 12;         // kartta GUV_PAROLA_EN_AZ (bayt)

function ozet(veri) {
  return createHash("sha256").update(veri).digest();
}

export function hmac(anahtar, veri) {
  return createHmac("sha256", anahtar).update(veri).digest();
}

/** PBKDF2-HMAC-SHA256; parola metin (UTF-8) ya da bayt. */
export function pbkdf2(parola, tuz, tur, uzunluk = 32) {
  const p = typeof parola === "string" ? Buffer.from(parola, "utf8") : Buffer.from(parola);
  return pbkdf2Sync(p, Buffer.from(tuz), tur, uzunluk, "sha256");
}

/** guv__ad_gecerli: 1-24 bayt UTF-8, kontrol karakteri yok. */
export function adGecerli(ad) {
  if (typeof ad !== "string") return false;
  const b = Buffer.from(ad, "utf8");
  if (b.length === 0 || b.length > AD_AZAMI) return false;
  for (const c of b) if (c < 0x20 || c === 0x7f) return false;
  return true;
}

function eslesmeHmac(P, etiket, kimlik, nk, nc, son) {
  const metin = [etiket, kimlik, Buffer.from(nk).toString("hex"), Buffer.from(nc).toString("hex"), son].join("\n");
  return hmac(P, Buffer.from(metin, "utf8"));
}

export function kanitIstemci(P, kimlik, nk, nc, ad) {
  return eslesmeHmac(P, "OK1-istemci", kimlik, nk, nc, ad);
}

export function kanitKart(P, kimlik, nk, nc, n) {
  return eslesmeHmac(P, "OK1-kart", kimlik, nk, nc, String(n));
}

export function anahtarTuret(P, kimlik, nk, nc, n) {
  return eslesmeHmac(P, "OK1-anahtar", kimlik, nk, nc, String(n));
}

/** RFC 3986: A-Z a-z 0-9 - . _ ~ aynen, gerisi UTF-8 baytlari %XX (buyuk harf). */
export function yuzdeKodla(s) {
  let c = "";
  for (const v of Buffer.from(String(s), "utf8")) {
    const ayrilmamis = (v >= 0x41 && v <= 0x5a) || (v >= 0x61 && v <= 0x7a) || (v >= 0x30 && v <= 0x39)
      || v === 0x2d || v === 0x2e || v === 0x5f || v === 0x7e;
    c += ayrilmamis ? String.fromCharCode(v) : "%" + v.toString(16).toUpperCase().padStart(2, "0");
  }
  return c;
}

/** argumanlar: [[ad, deger], ...] COZULMUS (yuzde kodsuz) metinler, gelis sirasiyla. */
export function kanonikMetin(yontem, yol, argumanlar, acilis, sayac, govde) {
  const sorgu = argumanlar.map(([a, d]) => `${yuzdeKodla(a)}=${yuzdeKodla(d)}`).join("&");
  const satirlar = [
    "OK1", yontem, yol + (sorgu ? "?" + sorgu : ""), acilis, BigInt(sayac).toString(),
    ozet(Buffer.from(govde)).toString("hex"),
  ];
  return Buffer.from(satirlar.join("\n"), "utf8");
}

export function imzaHesapla(K, yontem, yol, argumanlar, acilis, sayac, govde) {
  return hmac(Buffer.from(K), kanonikMetin(yontem, yol, argumanlar, acilis, sayac, govde)).toString("hex");
}

/** Sabit zamanli; `imzaHex` 64 onaltilik degilse yanlis (guv__hexten reddi). */
export function imzaDogru(K, yontem, yol, argumanlar, acilis, sayac, govde, imzaHex) {
  if (typeof imzaHex !== "string" || !/^[0-9a-fA-F]{64}$/.test(imzaHex)) return false;
  const beklenen = hmac(Buffer.from(K), kanonikMetin(yontem, yol, argumanlar, acilis, sayac, govde));
  return timingSafeEqual(beklenen, Buffer.from(imzaHex, "hex"));
}

export function baytEsit(a, b) {
  const x = Buffer.from(a), y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

/** Cihaz basina tekrar penceresi (kartta GuvCanli): bit i = (son - i) goruldu. */
export function pencereYeni() {
  return { son: 0n, bitler: 0n };
}

/** guv_imza_bit'in pencere bolumu. YALNIZ imza dogruysa cagrilir (sahte sayac ilerletemez).
 *  true = yeni sayac (kaydedildi); false = tekrar ya da pencerenin gerisi. */
export function pencereKabul(p, sayac) {
  const s = BigInt(sayac);
  if (s <= 0n) return false;
  if (s > p.son) {
    const d = s - p.son;
    p.bitler = d >= PENCERE ? 1n : BigInt.asUintN(64, (p.bitler << d) | 1n);
    p.son = s;
    return true;
  }
  const d = p.son - s;
  if (d >= PENCERE) return false;
  const bit = 1n << d;
  if (p.bitler & bit) return false;
  p.bitler |= bit;
  return true;
}
