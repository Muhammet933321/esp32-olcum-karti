// 2B — 1E MQTT bildirim zarfi + /bildirim/bilgi cozumu (saf JS, bagimliliksiz).
//
// Baslangic: kopru/bildirim.py (zarf bolumu; bayt bayt ayni). Kart tarafi: bildirim.h.
// Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K5, K10).
//
//   bayt 0..3   "OKB1"
//   bayt 4..15  nonce (12 B)
//   bayt 16..   ChaCha20-Poly1305 sifreli metin, son 16 B etiket
//   AAD         konu adinin UTF-8 baytlari
//   duz metin   kompakt JSON (UTF-8) — Python json.dumps(..., ensure_ascii=False,
//               separators=(",", ":"), allow_nan=False) ile AYNI metin (jsonPython)
//
// /bildirim/bilgi (K10): ayni zarf, anahtar = cihaz anahtari K, AAD = "OK1-bildirim\n<kimlik>\n<n>",
// duz metin {"u","k","p","o","a"}.
//
// Python adlari -> JS: zarf_kur -> zarfKur · zarf_ac -> zarfAc · bilgi_aad -> bilgiAad ·
// bilgi_coz -> bilgiCoz · onek_denetle -> onekDenetle · json.dumps(...) -> jsonPython.
// Parola ve anahtar HICBIR hata mesajina yazilmaz.

import {
  DegerHatasi, ANAHTAR_UZUNLUK, ETIKET_UZUNLUK, NONCE_UZUNLUK, bayt, coz, hexten, rastgeleBayt,
  sifrele, utf8Coz, utf8Kodla,
} from "./kripto.js";

export const SIHIR = Object.freeze([0x4f, 0x4b, 0x42, 0x31]);     // "OKB1"
export const ZARF_EN_AZ = SIHIR.length + NONCE_UZUNLUK + ETIKET_UZUNLUK;
export const BILGI_YOLU = "/bildirim/bilgi";
export { ANAHTAR_UZUNLUK, NONCE_UZUNLUK, ETIKET_UZUNLUK };

const _ONEK_RE = /^[0-9a-f]{32}$/;
const _ANAHTAR_HEX_RE = /^[0-9a-fA-F]{64}$/;

// ── Python json.dumps(ensure_ascii=False, separators=(",", ":"), allow_nan=False) ──
// Kurallar:
//  * Nesne anahtar sirasi = ekleme sirasi. JS duz nesnede tamsayi benzeri anahtarlari ("1", "10")
//    ONE ALIR ve kucukten buyuge dizer; Python dizmez. Bu yuzden duz nesnede boyle bir anahtar
//    HATA verir; sira onemliyse Map kullanin (anahtarlar metin olmali).
//  * Tamsayi degerli Number (ve BigInt) Python int gibi yazilir ("2", "10000000000000000").
//    Python float 2.0 / 1e16 JS'te tamsayidan ayirt edilemez: onlar icin bu yazim Python'dan
//    ayrisir (kartin icerikleri tamsayi + metin).
//  * Tamsayi olmayan Number Python float repr'i gibi: en kisa gidis-donus basamaklari;
//    |x| < 1e-4 bilimsel ("1e-05", "1.5e-07"), gerisi sabit nokta.
//  * NaN / Infinity HATA (allow_nan=False). Eslesmemis vekil karakter HATA (Python UTF-8'e
//    cevirirken hata verir). undefined, islev, sembol, Date, typed array HATA.
//  * Metin kacislari JSON.stringify ile ayni: \" \\ \b \f \n \r \t, diger < 0x20 \u00xx
//    (kucuk harf); U+2028/2029, DEL ve ASCII disi HAM yazilir.
const _DIZIN_ANAHTAR = /^(0|[1-9][0-9]*)$/;

function _sayiYaz(x) {
  if (typeof x === "bigint") return x.toString();
  if (!Number.isFinite(x)) throw new DegerHatasi("NaN/Infinity JSON'a yazilamaz (allow_nan=False)");
  if (Number.isInteger(x)) {
    if (Object.is(x, -0)) return "0";
    // String(2**60) "1152921504606847000" verir (en kisa basamak + sifir); Python int tam deger
    return Number.isSafeInteger(x) ? String(x) : BigInt(x).toString();
  }
  const s = String(x);                                 // JS: en kisa + en yakin basamaklar (Python repr ile ayni)
  if (Math.abs(x) >= 1e-4) return s;                   // sabit nokta: iki dilde ayni yazim
  let t = s, isaret = "";
  if (t[0] === "-") {
    isaret = "-";
    t = t.slice(1);
  }
  let basamak, us;
  const e = t.indexOf("e");
  if (e >= 0) {                                        // "1.5e-7"
    basamak = t.slice(0, e).replace(".", "");
    us = Number(t.slice(e + 1));
  } else {                                             // "0.0000123"
    const kesir = t.slice(2);
    const ilk = kesir.search(/[1-9]/);
    basamak = kesir.slice(ilk);
    us = -(ilk + 1);
  }
  const mantis = basamak.length > 1 ? `${basamak[0]}.${basamak.slice(1)}` : basamak;
  return `${isaret}${mantis}e${us < 0 ? "-" : "+"}${String(Math.abs(us)).padStart(2, "0")}`;
}

function _metinYaz(s) {
  utf8Kodla(s);                                        // eslesmemis vekil -> DegerHatasi
  return JSON.stringify(s);
}

function _duzNesne(x) {
  if (typeof x !== "object") return false;
  const p = Object.getPrototypeOf(x);
  return p === Object.prototype || p === null;
}

export function jsonPython(deger) {
  if (deger === null) return "null";
  if (deger === true) return "true";
  if (deger === false) return "false";
  if (typeof deger === "string") return _metinYaz(deger);
  if (typeof deger === "number" || typeof deger === "bigint") return _sayiYaz(deger);
  if (Array.isArray(deger)) return "[" + deger.map(jsonPython).join(",") + "]";
  if (deger instanceof Map) {
    const parcalar = [];
    for (const [k, v] of deger) {
      if (typeof k !== "string") throw new TypeError("Map anahtarlari metin olmali");
      parcalar.push(_metinYaz(k) + ":" + jsonPython(v));
    }
    return "{" + parcalar.join(",") + "}";
  }
  if (_duzNesne(deger)) {
    const anahtarlar = Object.keys(deger);
    const kotu = anahtarlar.find((k) => _DIZIN_ANAHTAR.test(k) && Number(k) < 2 ** 32 - 1);
    if (kotu !== undefined) {
      throw new DegerHatasi(`tamsayi benzeri anahtar (${kotu}): JS sirayi korumaz, Map kullanin`);
    }
    return "{" + anahtarlar.map((k) => _metinYaz(k) + ":" + jsonPython(deger[k])).join(",") + "}";
  }
  throw new TypeError(`JSON'a yazilamaz: ${typeof deger}`);
}

// ── zarf ─────────────────────────────────────────────────────────────────
function _anahtarDenetle(anahtar) {
  if (!(anahtar instanceof Uint8Array) || anahtar.length !== ANAHTAR_UZUNLUK) {
    throw new DegerHatasi(`bildirim anahtari ${ANAHTAR_UZUNLUK} bayt olmali`);
  }
}

// Karttaki zarf bicimi: "OKB1" + nonce + sifreli metin + etiket; AAD = konu (UTF-8).
// `nonce` yalniz sinama icin verilir; verilmezse rastgele uretilir.
export function zarfKur(anahtar, konu, icerik, nonce) {
  _anahtarDenetle(anahtar);
  nonce = nonce === undefined || nonce === null ? rastgeleBayt(NONCE_UZUNLUK) : bayt(nonce, "nonce");
  if (nonce.length !== NONCE_UZUNLUK) throw new DegerHatasi(`nonce ${NONCE_UZUNLUK} bayt olmali`);
  const duz = utf8Kodla(jsonPython(icerik));
  const govde = sifrele(anahtar, nonce, duz, utf8Kodla(konu));
  const cikis = new Uint8Array(SIHIR.length + NONCE_UZUNLUK + govde.length);
  cikis.set(SIHIR, 0);
  cikis.set(nonce, SIHIR.length);
  cikis.set(govde, SIHIR.length + NONCE_UZUNLUK);
  return cikis;
}

function _zarfCoz(anahtar, aad, veri) {
  _anahtarDenetle(anahtar);
  veri = bayt(veri, "zarf");
  if (veri.length < ZARF_EN_AZ) throw new DegerHatasi(`zarf cok kisa (${veri.length} < ${ZARF_EN_AZ} bayt)`);
  for (let i = 0; i < SIHIR.length; i++) {
    if (veri[i] !== SIHIR[i]) throw new DegerHatasi("zarf sihri 'OKB1' degil");
  }
  const nonce = veri.subarray(SIHIR.length, SIHIR.length + NONCE_UZUNLUK);
  const duz = coz(anahtar, nonce, veri.subarray(SIHIR.length + NONCE_UZUNLUK), aad);  // etiket tutmazsa DegerHatasi
  let icerik;
  try {
    icerik = JSON.parse(utf8Coz(duz));
  } catch (h) {
    if (h instanceof DegerHatasi) throw h;
    throw new DegerHatasi("zarf icerigi gecerli JSON degil");
  }
  if (icerik === null || typeof icerik !== "object" || Array.isArray(icerik)) {
    throw new DegerHatasi("zarf icerigi JSON nesnesi degil");
  }
  return icerik;
}

// Zarfi ac. Yanlis sihir / kisa / etiket tutmuyor (yanlis anahtar, bozuk veri, YANLIS KONU) /
// JSON bozuk -> DegerHatasi.
export function zarfAc(anahtar, konu, veri) {
  return _zarfCoz(anahtar, utf8Kodla(konu), veri);
}

// ── /bildirim/bilgi ──────────────────────────────────────────────────────
export function bilgiAad(kimlik, n) {
  return utf8Kodla(`OK1-bildirim\n${kimlik}\n${n}`);
}

// Kartin /bildirim/bilgi yanitini coz (anahtar = cihaz anahtari K). Donus:
// { uri, kullanici, parola, onek, anahtar: Uint8Array(32) }. Bicim hatasi -> DegerHatasi.
export function bilgiCoz(K, kimlik, n, govde) {
  const d = _zarfCoz(K, bilgiAad(kimlik, n), govde);
  for (const alan of ["u", "k", "p", "o", "a"]) {
    if (!Object.hasOwn(d, alan) || typeof d[alan] !== "string") {
      throw new DegerHatasi(`bilgide '${alan}' alani yok ya da metin degil`);
    }
  }
  if (!d.u) throw new DegerHatasi("bilgide araci adresi bos");
  if (!_ONEK_RE.test(d.o)) throw new DegerHatasi("onek 32 kucuk harfli hex olmali");
  if (!_ANAHTAR_HEX_RE.test(d.a)) throw new DegerHatasi("bildirim anahtari 64 hex olmali");
  return { uri: d.u, kullanici: d.k, parola: d.p, onek: d.o, anahtar: hexten(d.a) };
}

export function onekDenetle(onek) {
  if (typeof onek !== "string" || !_ONEK_RE.test(onek)) throw new DegerHatasi("onek 32 kucuk harfli hex olmali");
  return onek;
}
