// 2B — 1D cihaz eslestirmesi ve imzali istekler: istemci tarafi (saf JS, bagimliliksiz).
//
// Baslangic: kopru/imza.py (bayt bayt ayni; ortak/test/vektor/kripto.json ve
// uretim/vektor_guvenlik.json ile sinanir). Kart tarafi: kod/olcum-karti-a3/guvenlik.h.
// Tasarim: tasarim/2026-10-01-1d-eslestirme.md (K4-K11), tasarim/2026-10-02-alt-proje-2-ortak.md (O6, O7).
//
//   P       = PBKDF2-HMAC-SHA256(parola, tuz, tur, 32)
//   kanit   = HMAC(P, "OK1-istemci\n" kimlik "\n" nk_hex "\n" nc_hex "\n" ad)
//   kart    = HMAC(P, "OK1-kart\n"    kimlik "\n" nk_hex "\n" nc_hex "\n" n)
//   K       = HMAC(P, "OK1-anahtar\n" kimlik "\n" nk_hex "\n" nc_hex "\n" n)
//   kanonik = "OK1\n" yontem "\n" yol ["?" a=d&...] "\n" acilis "\n" sayac "\n" sha256(govde)_hex
//   imza    = HMAC(K, kanonik) (hex)
//
// Python adlari -> JS:
//   yuzde_kodla -> yuzdeKodla        ad_gecerli -> adGecerli        pbkdf2 -> pbkdf2
//   kanit_istemci -> kanitIstemci    kanit_kart -> kanitKart        cihaz_anahtari -> cihazAnahtari
//   kanonik -> kanonik               imzala -> imzala               taban_url -> tabanUrl
//   _url -> istekUrl                 _bilgi_denetle -> bilgiDenetle
//   Cihaz.sonraki_sayac -> sayacSec (saf) + sonrakiSayac (cihaz nesnesini gunceller)
//   Cihaz.basliklar -> imzaBasliklari (sayac disaridan)
//   ac -> istekKur (saf: url + secenekler) + ac (fetch enjeksiyonla, 401 + yeni X-Acilis'te BIR yeniden deneme)
//   akis_url -> akisUrlKur (saf) + akisUrl      bilgi -> bilgi      _post_acik -> acikPost
//   esles -> esles (fetch enjeksiyonla; anahtar SAKLANMAZ, cagirana doner)
// Disk/DPAPI saklama YOK (PC/Android'in isi): `ortam.kaydet(cihaz)` verilirse Python'un
// kaydet() cagirdigi her yerde cagrilir.
//
// Cihaz nesnesi: { kimlik: "16 hex", n, K: Uint8Array(32), ad, sayac, acilis: "32 hex" | "" }.
// Ortam: { fetch, simdiMs?: () => ms, kaydet?: async (cihaz) => void, rastgele?: (n) => Uint8Array }.

import {
  DegerHatasi, bayt, hex, hexten, hmacSha256, pbkdf2HmacSha256, rastgeleBayt, sabitZamanliEsit,
  sha256, utf8Coz, utf8Kodla,
} from "./kripto.js";

export const SURUM = "OK1";
export const AD_AZAMI = 24;          // bayt (UTF-8); kartta GUV_AD_AZAMI
export const PAROLA_EN_AZ = 12;      // kartta GUV_PAROLA_EN_AZ
// Tur ve tuz KARTTAN gelir; sahte kart tur=1 dayatip kaniti toplasaydi parola HMAC hizinda
// tahmin edilirdi. Istemci alt/ust siniri kendisi uygular (kartta GUV_TUR_EN_AZ 10 000).
export const TUR_EN_AZ = 10_000;
export const TUR_EN_COK = 1_000_000;

// Python RuntimeError karsiligi (kart kaniti yanlis, acik POST HTTP hatasi).
export class CalismaHatasi extends Error {
  constructor(mesaj) {
    super(mesaj);
    this.name = "CalismaHatasi";
  }
}

// Python urllib.error.HTTPError karsiligi: `durum` (kod) ve `yanit` (Response).
export class HttpHatasi extends Error {
  constructor(durum, yanit, url) {
    super(`HTTP ${durum}: ${url}`);
    this.name = "HttpHatasi";
    this.durum = durum;
    this.yanit = yanit;
  }
}

// ── saf cekirdek (kartla ayni bicim) ─────────────────────────────────────
const _AYRILMAMIS = new Set(
  Array.from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~", (c) => c.charCodeAt(0)),
);
const _HEX_BUYUK = "0123456789ABCDEF";

// RFC 3986: ayrilmamis karakterler aynen, gerisi UTF-8 baytlari %XX (buyuk harf).
export function yuzdeKodla(s) {
  const b = utf8Kodla(s);
  let c = "";
  for (let i = 0; i < b.length; i++) {
    const v = b[i];
    c += _AYRILMAMIS.has(v) ? String.fromCharCode(v) : "%" + _HEX_BUYUK[v >> 4] + _HEX_BUYUK[v & 15];
  }
  return c;
}

// 1-24 bayt UTF-8, kontrol karakteri yok (kanit metninde ayirici '\n').
export function adGecerli(ad) {
  const b = utf8Kodla(ad);
  if (b.length === 0 || b.length > AD_AZAMI) return false;
  for (let i = 0; i < b.length; i++) if (b[i] < 0x20 || b[i] === 0x7f) return false;
  return true;
}

export function pbkdf2(parola, tuz, tur) {
  return pbkdf2HmacSha256(utf8Kodla(parola), bayt(tuz, "tuz"), tur, 32);
}

function _tamsayiYazi(v, ad) {
  if (typeof v === "bigint") return v.toString();
  if (Number.isSafeInteger(v)) return String(v);
  throw new TypeError(`${ad} guvenli tamsayi ya da BigInt olmali`);
}

function _h(anahtar, metin) {
  return hmacSha256(bayt(anahtar, "anahtar"), utf8Kodla(metin));
}

function _ortak(kimlik, nk, nc) {
  return `\n${kimlik}\n${hex(nk)}\n${hex(nc)}\n`;
}

export function kanitIstemci(P, kimlik, nk, nc, ad) {
  return _h(P, `${SURUM}-istemci` + _ortak(kimlik, nk, nc) + ad);
}

export function kanitKart(P, kimlik, nk, nc, n) {
  return _h(P, `${SURUM}-kart` + _ortak(kimlik, nk, nc) + _tamsayiYazi(n, "n"));
}

export function cihazAnahtari(P, kimlik, nk, nc, n) {
  return _h(P, `${SURUM}-anahtar` + _ortak(kimlik, nk, nc) + _tamsayiYazi(n, "n"));
}

function _sorgu(argumanlar) {
  return Array.from(argumanlar, ([a, d]) => yuzdeKodla(a) + "=" + yuzdeKodla(d)).join("&");
}

// Govde bayt (Uint8Array); kolaylik icin metin de olur (UTF-8). Python yalniz bytes alir.
function _govde(govde) {
  return typeof govde === "string" ? utf8Kodla(govde) : bayt(govde, "govde");
}

export function kanonik(yontem, yol, argumanlar, acilis, sayac, govde) {
  const sorgu = _sorgu(argumanlar);
  return utf8Kodla(
    `${SURUM}\n${yontem}\n${yol}` + (sorgu ? `?${sorgu}` : "")
      + `\n${acilis}\n${_tamsayiYazi(sayac, "sayac")}\n${hex(sha256(_govde(govde)))}`,
  );
}

export function imzala(K, yontem, yol, argumanlar, acilis, sayac, govde) {
  return hex(hmacSha256(bayt(K, "K"), kanonik(yontem, yol, argumanlar, acilis, sayac, govde)));
}

// Python Cihaz.sonraki_sayac: max(son + 1, unix_ms) — yeni surec eskisinin altina inmez.
export function sayacSec(son, simdiMs) {
  return Math.max(son + 1, Math.floor(simdiMs));
}

export function sonrakiSayac(cihaz, simdiMs = Date.now()) {
  cihaz.sayac = sayacSec(cihaz.sayac, simdiMs);
  return cihaz.sayac;
}

// Python Cihaz.basliklar (sayac disaridan; saf).
export function imzaBasliklari(cihaz, yontem, yol, argumanlar, govde, sayac) {
  return {
    "X-Cihaz": _tamsayiYazi(cihaz.n, "n"),
    "X-Sayac": _tamsayiYazi(sayac, "sayac"),
    "X-Imza": imzala(cihaz.K, yontem, yol, argumanlar, cihaz.acilis, sayac, govde),
  };
}

// ── URL ve istek kurma (saf) ─────────────────────────────────────────────
export function tabanUrl(host) {
  return (host.startsWith("http") ? host : `http://${host}`).replace(/\/+$/, "");
}

export function istekUrl(taban, yol, argumanlar = []) {
  const q = _sorgu(argumanlar);
  return taban.replace(/\/+$/, "") + yol + (q ? `?${q}` : "");
}

// Python ac() icindeki istek: { url, secenekler } — `fetch(url, secenekler)` ile gonderilir.
// Govde yalniz POST'ta gider ama imza her zaman verilen govdeyle hesaplanir (Python gibi).
export function istekKur(cihaz, taban, yontem, yol, argumanlar = [], govde = new Uint8Array(0), sayac) {
  const b = _govde(govde);
  const basliklar = { "X-Olcum": "1", ...imzaBasliklari(cihaz, yontem, yol, argumanlar, b, sayac) };
  if (yontem === "POST") basliklar["Content-Type"] = "text/plain";
  const secenekler = { method: yontem, headers: basliklar };
  if (yontem === "POST") secenekler.body = b;
  return { url: istekUrl(taban, yol, argumanlar), secenekler };
}

// EventSource baslik tasiyamaz: imza `_c _s _i` sorgu argumanlarinda (kanonige girmez).
export function akisUrlKur(cihaz, taban, sayac) {
  return `${taban.replace(/\/+$/, "")}/akis?_c=${_tamsayiYazi(cihaz.n, "n")}&_s=${_tamsayiYazi(sayac, "sayac")}`
    + `&_i=${imzala(cihaz.K, "GET", "/akis", [], cihaz.acilis, sayac, new Uint8Array(0))}`;
}

// Python int(): sayi (kesirliyse sifira dogru), ondalik metin, bool. Baska her sey hata.
export function tamsayi(x) {
  if (typeof x === "boolean") return x ? 1 : 0;
  if (typeof x === "number") {
    if (!Number.isFinite(x)) throw new DegerHatasi("sonlu olmayan sayi tamsayiya cevrilemez");
    return Math.trunc(x) + 0;
  }
  if (typeof x === "string") {
    const t = x.trim();
    if (/^[+-]?[0-9]+(_[0-9]+)*$/.test(t)) return Number(t.replace(/_/g, "")) + 0;
    throw new DegerHatasi(`tamsayi degil: ${JSON.stringify(x.slice(0, 40))}`);
  }
  throw new TypeError("tamsayi bekleniyordu");
}

function _metin(v) {
  return typeof v === "string" ? v : String(v);
}

// Kartin (ya da kart taklidinin) /eslestir/bilgi yanitini dogrula: kimlik, tuz, tur, acilis.
// Tur ve tuz parolanin cevrimdisi tahmin maliyetini belirler.
export function bilgiDenetle(b) {
  if (b === null || typeof b !== "object" || Array.isArray(b)) throw new TypeError("bilgi JSON nesnesi olmali");
  const al = (k, v) => (Object.hasOwn(b, k) ? b[k] : v);
  // S7: kart kimlik/tuz/acilis'i METIN, turu JSON TAMSAYISI basar; String()/tamsayi() gevsekligi yok
  const kimlik = al("kimlik", ""), tuz = al("tuz", ""), acilis = al("acilis", "");
  if (![kimlik, tuz, acilis].every((x) => typeof x === "string")) {
    throw new DegerHatasi("kartin kimlik/tuz/acilis alanlari metin degil");
  }
  if (!/^[0-9a-f]{16}$/.test(kimlik)) throw new DegerHatasi(`kart kimligi bicimsiz: ${JSON.stringify(kimlik.slice(0, 40))}`);
  if (!/^[0-9a-f]{32}$/.test(tuz)) throw new DegerHatasi("kartin tuzu 16 bayt (32 hex) degil");
  if (!/^[0-9a-f]{32}$/.test(acilis)) throw new DegerHatasi("kartin acilis degeri bicimsiz");
  const tur = al("tur", null);
  if (typeof tur !== "number" || !Number.isInteger(tur)) {
    throw new DegerHatasi(`PBKDF2 turu JSON tamsayisi degil: ${JSON.stringify(String(tur).slice(0, 40))} — `
      + "eslestirme YAPILMADI");
  }
  if (!(TUR_EN_AZ <= tur && tur <= TUR_EN_COK)) {
    throw new DegerHatasi(`PBKDF2 turu ${tur} kabul edilmez (${TUR_EN_AZ}..${TUR_EN_COK}) — `
      + "sahte kart olabilir; eslestirme YAPILMADI");
  }
  return { kimlik, tuz: hexten(tuz), tur, acilis };
}

// ── ag (fetch enjeksiyonla, spec O7) ─────────────────────────────────────
function _fetch(ortam) {
  const f = ortam && ortam.fetch;
  if (typeof f !== "function") throw new TypeError("ortam.fetch islevi gerekli");
  return f;
}

async function _kaydet(ortam, cihaz) {
  if (ortam && typeof ortam.kaydet === "function") await ortam.kaydet(cihaz);
}

function _simdi(ortam) {
  return ortam && typeof ortam.simdiMs === "function" ? ortam.simdiMs() : Date.now();
}

function _rastgele(ortam, n) {
  return ortam && typeof ortam.rastgele === "function" ? bayt(ortam.rastgele(n)) : rastgeleBayt(n);
}

async function _jsonOku(yanit) {
  return JSON.parse(utf8Coz(new Uint8Array(await yanit.arrayBuffer())));
}

function _basarili(yanit) {
  return yanit.status >= 200 && yanit.status < 300;
}

// Python bilgi(taban)["acilis"]: alan yoksa hata (KeyError).
function _acilis(b) {
  if (b === null || typeof b !== "object" || !Object.hasOwn(b, "acilis")) throw new DegerHatasi("bilgide 'acilis' yok");
  return _metin(b.acilis);
}

export async function bilgi(taban, ortam) {
  const url = taban.replace(/\/+$/, "") + "/eslestir/bilgi";
  const y = await _fetch(ortam)(url, { method: "GET", headers: {} });
  if (!_basarili(y)) throw new HttpHatasi(y.status, y, url);
  return _jsonOku(y);
}

// Imzali istek; basarili (2xx) Response doner, digerinde HttpHatasi.
// 401 + YENI `X-Acilis` (kart yeniden basladi): acilis guncellenir, BIR KEZ yeniden denenir.
// Acilis ayniysa (cihaz silinmis, saat/sayac sorunu) hata.
export async function ac(cihaz, taban, yontem, yol, argumanlar = [], govde = new Uint8Array(0), ortam) {
  const f = _fetch(ortam);
  argumanlar = Array.from(argumanlar);
  if (!cihaz.acilis) {
    cihaz.acilis = _acilis(await bilgi(taban, ortam));
    await _kaydet(ortam, cihaz);
  }
  for (const deneme of [0, 1]) {
    const s = sonrakiSayac(cihaz, _simdi(ortam));
    await _kaydet(ortam, cihaz);
    const { url, secenekler } = istekKur(cihaz, taban, yontem, yol, argumanlar, govde, s);
    const y = await f(url, secenekler);
    if (_basarili(y)) return y;
    const yeni = y.status === 401 ? y.headers.get("X-Acilis") : null;
    if (deneme === 0 && yeni && yeni !== cihaz.acilis) {
      cihaz.acilis = yeni;
      await _kaydet(ortam, cihaz);
      continue;
    }
    throw new HttpHatasi(y.status, y, url);
  }
  throw new Error("erisilemez");
}

export async function akisUrl(cihaz, taban, ortam) {
  if (!cihaz.acilis) {
    cihaz.acilis = _acilis(await bilgi(taban, ortam));
    await _kaydet(ortam, cihaz);
  }
  const s = sonrakiSayac(cihaz, _simdi(ortam));
  await _kaydet(ortam, cihaz);
  return akisUrlKur(cihaz, taban, s);
}

export async function acikPost(taban, yol, argumanlar, ortam) {
  const url = istekUrl(taban, yol, argumanlar);
  const y = await _fetch(ortam)(url, {
    method: "POST", headers: { "X-Olcum": "1", "Content-Type": "text/plain" }, body: new Uint8Array(0),
  });
  if (!_basarili(y)) {
    let metin;
    try {
      metin = new TextDecoder("utf-8").decode(await y.arrayBuffer());   // Python: "replace"
    } catch {
      metin = "";
    }
    throw new CalismaHatasi(`${yol}: ${y.status} ${metin}`);
  }
  return _jsonOku(y);
}

// Parolali eslestirme (K5). Parola ve P aga CIKMAZ. Kartin kaniti dogrulanmadan anahtar
// DONDURULMEZ (karsilikli: sahte kart parolayi bilmez). Kisa parola, bicimsiz kimlik/tuz ve
// sinir disi tur HICBIR kanit yollanmadan reddedilir. Donus: yeni cihaz nesnesi (sayac 0).
export async function esles(taban, ad, parola, ortam) {
  if (!adGecerli(ad)) throw new DegerHatasi("ad 1-24 bayt olmali, kontrol karakteri yok");
  if (typeof parola !== "string") throw new TypeError("parola metin olmali");
  if (utf8Kodla(parola).length < PAROLA_EN_AZ) {          // S7: kart UTF-8 BAYT sayar
    throw new DegerHatasi(`parola en az ${PAROLA_EN_AZ} bayt (UTF-8) olmali (kart da reddeder)`);
  }
  const { kimlik, tuz, tur, acilis } = bilgiDenetle(await bilgi(taban, ortam));
  const nc = _rastgele(ortam, 16);
  let y = await acikPost(taban, "/eslestir/baslat", [["ad", ad], ["nc", hex(nc)]], ortam);
  const eno = tamsayi(y.eno), nk = hexten(y.nk);
  const P = pbkdf2(parola, tuz, tur);
  const kanit = kanitIstemci(P, kimlik, nk, nc, ad);
  y = await acikPost(taban, "/eslestir/kanit", [["eno", String(eno)], ["kanit", hex(kanit)]], ortam);
  const n = tamsayi(y.n);
  if (!sabitZamanliEsit(hexten(y.kart_kanit), kanitKart(P, kimlik, nk, nc, n))) {
    P.fill(0);
    throw new CalismaHatasi("kart kaniti YANLIS — bu kart parolayi bilmiyor (sahte kart?); cihaz KAYDEDILMEDI");
  }
  const cihaz = { kimlik, n, K: cihazAnahtari(P, kimlik, nk, nc, n), ad, sayac: 0, acilis };
  P.fill(0);
  await _kaydet(ortam, cihaz);
  return cihaz;
}
