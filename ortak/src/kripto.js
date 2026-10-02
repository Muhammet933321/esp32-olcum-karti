// 2B — saf JS kriptografi (bagimliliksiz): SHA-256, HMAC-SHA256, PBKDF2-HMAC-SHA256,
// ChaCha20, Poly1305, ChaCha20-Poly1305 IETF AEAD (RFC 8439).
//
// Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md (O1, O6). `crypto.subtle` KULLANILMAZ:
// kart yerel agda duz http ile konusur, tarayici orada guvenli baglam vermez (spec §6).
// Tarayici, Node ve Capacitor ayni dosyayi yukler (Uint8Array + TextEncoder/TextDecoder).
//
// Python baslangici (bayt bayt ayni sonuc, ortak/test/vektor/kripto.json ile sinanir):
//   sha256 / Sha256            hashlib.sha256
//   hmacSha256 / HmacSha256    hmac.new(k, m, hashlib.sha256)
//   pbkdf2HmacSha256           hashlib.pbkdf2_hmac("sha256", ...)
//   ceyrekTur, ceyrekTurDurum, baslangicDurumu, blok, akisSifrele, poly1305,
//   poly1305AnahtarUret, sifrele, coz        kopru/chacha.py (ayni adlar)
//   sabitZamanliEsit           hmac.compare_digest
//
// Hata siniflari: DegerHatasi = Python ValueError (yanlis uzunluk, etiket tutmadi, bozuk hex,
// UTF-8'e cevrilemeyen metin). Tip hatalari TypeError.
// Not: etiket karsilastirmasi sabit zamanli; Poly1305 13 bitlik uzuvlarla (BigInt yok) ve dalsiz
// son indirgemeyle yazildi. JS motorunun kendisi sabit zaman garantisi vermez — tehdit modeli
// (1E K5) aracinin icerik okuyamamasi / sahte olay uretememesi, yerel yan kanal degil.

export class DegerHatasi extends Error {
  constructor(mesaj) {
    super(mesaj);
    this.name = "DegerHatasi";
  }
}

// ── yardimcilar ──────────────────────────────────────────────────────────
export function bayt(x, ad = "veri") {
  if (x instanceof Uint8Array) return x;
  if (x instanceof ArrayBuffer) return new Uint8Array(x);
  if (ArrayBuffer.isView(x)) return new Uint8Array(x.buffer, x.byteOffset, x.byteLength);
  throw new TypeError(`${ad} Uint8Array (ya da ArrayBuffer) olmali`);
}

export function birlestir(...parcalar) {
  let n = 0;
  for (const p of parcalar) n += bayt(p).length;
  const c = new Uint8Array(n);
  let o = 0;
  for (const p of parcalar) {
    const b = bayt(p);
    c.set(b, o);
    o += b.length;
  }
  return c;
}

const _HEX = "0123456789abcdef";

export function hex(b) {
  b = bayt(b);
  let s = "";
  for (let i = 0; i < b.length; i++) s += _HEX[b[i] >> 4] + _HEX[b[i] & 15];
  return s;
}

// Kati: cift uzunluk, yalniz hex (buyuk/kucuk). Python bytes.fromhex bosluga izin verir; burada yok.
export function hexten(s) {
  if (typeof s !== "string") throw new TypeError("hex metin bekleniyordu");
  if (s.length % 2 || !/^[0-9a-fA-F]*$/.test(s)) throw new DegerHatasi("gecersiz hex metin");
  const b = new Uint8Array(s.length / 2);
  for (let i = 0; i < b.length; i++) b[i] = parseInt(s.substr(2 * i, 2), 16);
  return b;
}

function _iyiBicimli(s) {
  if (typeof s.isWellFormed === "function") return s.isWellFormed();
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const d = s.charCodeAt(i + 1);
      if (!(d >= 0xdc00 && d <= 0xdfff)) return false;
      i++;
    } else if (c >= 0xdc00 && c <= 0xdfff) {
      return false;
    }
  }
  return true;
}

const _KODLAYICI = new TextEncoder();

// Python str.encode("utf-8") gibi: eslesmemis vekil (lone surrogate) HATA verir
// (TextEncoder sessizce U+FFFD yazardi; o zaman imza/etiket Python'dan ayrisirdi).
export function utf8Kodla(s) {
  if (typeof s !== "string") throw new TypeError("metin bekleniyordu");
  if (!_iyiBicimli(s)) throw new DegerHatasi("metinde eslesmemis vekil karakter var: UTF-8'e cevrilemez");
  return _KODLAYICI.encode(s);
}

// Python bytes.decode("utf-8") gibi kati; BOM SOYULMAZ (ignoreBOM: true), json.loads onu reddeder.
export function utf8Coz(b) {
  const v = bayt(b);
  try {
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(v);
  } catch {
    throw new DegerHatasi("gecersiz UTF-8");
  }
}

// hmac.compare_digest: uzunluk farkliysa false; esit uzunlukta erken cikis yok.
export function sabitZamanliEsit(a, b) {
  a = bayt(a);
  b = bayt(b);
  if (a.length !== b.length) return false;
  let f = 0;
  for (let i = 0; i < a.length; i++) f |= a[i] ^ b[i];
  return f === 0;
}

// ── SHA-256 (FIPS 180-4) ─────────────────────────────────────────────────
const _K = new Int32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);
const _H0 = new Int32Array([
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]);

// Tek blok sikistirma; `h` (8 sozcuk) yerinde guncellenir, `w`nin ilk 16 sozcugu blok.
// w[16..63] uzerine yazilir, w[0..15] DEGISMEZ (PBKDF2 hizli yolu buna dayanir).
function _sikistir(h, w) {
  for (let i = 16; i < 64; i++) {
    const x = w[i - 15], y = w[i - 2];
    const s0 = ((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3);
    const s1 = ((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10);
    w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
  }
  let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], k = h[7];
  for (let i = 0; i < 64; i++) {
    const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
    const ch = (e & f) ^ (~e & g);
    const t1 = (k + S1 + ch + _K[i] + w[i]) | 0;
    const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
    const maj = (a & b) ^ (a & c) ^ (b & c);
    k = g;
    g = f;
    f = e;
    e = (d + t1) | 0;
    d = c;
    c = b;
    b = a;
    a = (t1 + S0 + maj) | 0;
  }
  h[0] = (h[0] + a) | 0;
  h[1] = (h[1] + b) | 0;
  h[2] = (h[2] + c) | 0;
  h[3] = (h[3] + d) | 0;
  h[4] = (h[4] + e) | 0;
  h[5] = (h[5] + f) | 0;
  h[6] = (h[6] + g) | 0;
  h[7] = (h[7] + k) | 0;
}

function _sozcukYaz(h, c, o, n) {
  for (let i = 0; i < n; i++) {
    const v = h[i];
    c[o + 4 * i] = v >>> 24;
    c[o + 4 * i + 1] = (v >>> 16) & 255;
    c[o + 4 * i + 2] = (v >>> 8) & 255;
    c[o + 4 * i + 3] = v & 255;
  }
}

// Artimli SHA-256 (guvenlik.h sha_bas / sha_ekle / sha_bit / sha_kopya karsiligi).
export class Sha256 {
  constructor() {
    this._h = Int32Array.from(_H0);
    this._w = new Int32Array(64);
    this._blok = new Uint8Array(64);
    this._n = 0;
    this._toplam = 0;
    this._bitti = false;
  }

  _isle(b, o) {
    const w = this._w;
    for (let j = 0; j < 16; j++, o += 4) w[j] = (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3];
    _sikistir(this._h, w);
  }

  ekle(veri) {
    veri = bayt(veri);
    if (this._bitti) throw new Error("SHA-256 bitti; yeni ozet icin yeni nesne");
    const L = veri.length;
    let i = 0;
    this._toplam += L;
    if (this._n) {
      const al = Math.min(64 - this._n, L);
      this._blok.set(veri.subarray(0, al), this._n);
      this._n += al;
      i = al;
      if (this._n < 64) return this;
      this._isle(this._blok, 0);
      this._n = 0;
    }
    for (; i + 64 <= L; i += 64) this._isle(veri, i);
    if (i < L) {
      this._blok.set(veri.subarray(i), 0);
      this._n = L - i;
    }
    return this;
  }

  bitir() {
    if (this._bitti) throw new Error("SHA-256 zaten bitti");
    this._bitti = true;
    const b = this._blok;
    const bitUzunluk = this._toplam * 8;
    let n = this._n;
    b[n++] = 0x80;
    if (n > 56) {
      b.fill(0, n);
      this._isle(b, 0);
      n = 0;
    }
    b.fill(0, n, 56);
    const yuksek = Math.floor(bitUzunluk / 0x100000000), dusuk = bitUzunluk >>> 0;
    b[56] = yuksek >>> 24;
    b[57] = (yuksek >>> 16) & 255;
    b[58] = (yuksek >>> 8) & 255;
    b[59] = yuksek & 255;
    b[60] = dusuk >>> 24;
    b[61] = (dusuk >>> 16) & 255;
    b[62] = (dusuk >>> 8) & 255;
    b[63] = dusuk & 255;
    this._isle(b, 0);
    const c = new Uint8Array(32);
    _sozcukYaz(this._h, c, 0, 8);
    return c;
  }

  kopya() {
    const k = new Sha256();
    k._h.set(this._h);
    k._blok.set(this._blok);
    k._n = this._n;
    k._toplam = this._toplam;
    k._bitti = this._bitti;
    return k;
  }
}

export function sha256(veri) {
  return new Sha256().ekle(veri).bitir();
}

// ── HMAC-SHA256 (RFC 2104) ───────────────────────────────────────────────
export class HmacSha256 {
  constructor(anahtar) {
    anahtar = bayt(anahtar, "anahtar");
    if (anahtar.length > 64) anahtar = sha256(anahtar);       // RFC 2104: uzun anahtar once ozetlenir
    const ped = new Uint8Array(64);
    ped.set(anahtar);
    for (let i = 0; i < 64; i++) ped[i] ^= 0x36;
    this._ic = new Sha256().ekle(ped);
    for (let i = 0; i < 64; i++) ped[i] ^= 0x36 ^ 0x5c;
    this._dis = new Sha256().ekle(ped);
    ped.fill(0);
  }

  ekle(veri) {
    this._ic.ekle(veri);
    return this;
  }

  bitir() {
    return this._dis.kopya().ekle(this._ic.bitir()).bitir();
  }

  kopya() {
    const k = Object.create(HmacSha256.prototype);
    k._ic = this._ic.kopya();
    k._dis = this._dis.kopya();
    return k;
  }
}

export function hmacSha256(anahtar, veri) {
  return new HmacSha256(anahtar).ekle(veri).bitir();
}

// ── PBKDF2-HMAC-SHA256 (RFC 8018) ────────────────────────────────────────
// Kartin guv_pbkdf2'si gibi: HMAC'in ipad/opad SHA durumu BIR KEZ kurulur, her turda
// kopyalanir (tur basina 2 sikistirma). Ustune: 32 baytlik U hep ayni dolguyla tek blok
// oldugundan blok sozcuk duzeyinde kurulur (bayt cevrimi yok).
export function pbkdf2HmacSha256(parola, tuz, tur, uzunluk = 32) {
  parola = bayt(parola, "parola");
  tuz = bayt(tuz, "tuz");
  if (!Number.isSafeInteger(tur) || tur < 1) throw new DegerHatasi("PBKDF2 turu en az 1 olmali");
  if (!Number.isSafeInteger(uzunluk) || uzunluk < 1) throw new DegerHatasi("PBKDF2 cikis uzunlugu en az 1 olmali");
  const hm = new HmacSha256(parola);
  const icH = hm._ic._h, disH = hm._dis._h;                  // birer 64 B blok islenmis durumlar
  const cikis = new Uint8Array(uzunluk);
  const w = new Int32Array(64), h = new Int32Array(8), u = new Int32Array(8), t = new Int32Array(8);
  const ara = new Uint8Array(32);
  for (let blokNo = 1, yer = 0; yer < uzunluk; blokNo++, yer += 32) {
    const sira = new Uint8Array([blokNo >>> 24, (blokNo >>> 16) & 255, (blokNo >>> 8) & 255, blokNo & 255]);
    const u1 = hm.kopya().ekle(tuz).ekle(sira).bitir();
    for (let j = 0; j < 8; j++) {
      u[j] = (u1[4 * j] << 24) | (u1[4 * j + 1] << 16) | (u1[4 * j + 2] << 8) | u1[4 * j + 3];
      t[j] = u[j];
    }
    // 96 baytlik ic/dis mesajin ikinci blogu: U (32 B) || 0x80 || sifir || bit uzunlugu 768
    w.fill(0, 8, 16);
    w[8] = 0x80000000 | 0;
    w[15] = 768;
    for (let i = 1; i < tur; i++) {
      h.set(icH);
      for (let j = 0; j < 8; j++) w[j] = u[j];
      _sikistir(h, w);
      for (let j = 0; j < 8; j++) w[j] = h[j];
      h.set(disH);
      _sikistir(h, w);
      for (let j = 0; j < 8; j++) {
        u[j] = h[j];
        t[j] ^= h[j];
      }
    }
    _sozcukYaz(t, ara, 0, 8);
    cikis.set(ara.subarray(0, Math.min(32, uzunluk - yer)), yer);
  }
  ara.fill(0);
  return cikis;
}

// ── ChaCha20 (RFC 8439 §2.1–2.4) ─────────────────────────────────────────
export const ANAHTAR_UZUNLUK = 32;
export const NONCE_UZUNLUK = 12;
export const ETIKET_UZUNLUK = 16;
const _SABIT = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574];   // "expand 32-byte k"

function _rotl(v, n) {
  return (v << n) | (v >>> (32 - n));
}

// 16 sozcuklu Int32Array uzerinde ceyrek tur (yerinde) — tek gercekleme, digerleri bunu kullanir.
function _qr(x, a, b, c, d) {
  x[a] = (x[a] + x[b]) | 0; x[d] = _rotl(x[d] ^ x[a], 16);
  x[c] = (x[c] + x[d]) | 0; x[b] = _rotl(x[b] ^ x[c], 12);
  x[a] = (x[a] + x[b]) | 0; x[d] = _rotl(x[d] ^ x[a], 8);
  x[c] = (x[c] + x[d]) | 0; x[b] = _rotl(x[b] ^ x[c], 7);
}

// RFC 8439 2.1: (a, b, c, d) -> [a, b, c, d], isaretsiz 32 bit sayilar.
export function ceyrekTur(a, b, c, d) {
  const x = Int32Array.of(a, b, c, d);
  _qr(x, 0, 1, 2, 3);
  return [x[0] >>> 0, x[1] >>> 0, x[2] >>> 0, x[3] >>> 0];
}

// RFC 8439 2.2: 16 sozcuklu durumda dort indisin ceyrek turu (yerinde; dizi ya da Uint32Array).
export function ceyrekTurDurum(durum, a, b, c, d) {
  [durum[a], durum[b], durum[c], durum[d]] = ceyrekTur(durum[a], durum[b], durum[c], durum[d]);
}

function _denetle(anahtar, nonce) {
  if (anahtar.length !== ANAHTAR_UZUNLUK) {
    throw new DegerHatasi(`anahtar ${ANAHTAR_UZUNLUK} bayt olmali (${anahtar.length} verildi)`);
  }
  if (nonce.length !== NONCE_UZUNLUK) {
    throw new DegerHatasi(`nonce ${NONCE_UZUNLUK} bayt olmali (${nonce.length} verildi)`);
  }
}

function _sayacDenetle(sayac) {
  if (!Number.isInteger(sayac) || sayac < 0 || sayac > 0xffffffff) throw new DegerHatasi("blok sayaci 32 bit olmali");
}

function _le32(b, o) {
  return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24);
}

function _durum(anahtar, sayac, nonce) {
  anahtar = bayt(anahtar, "anahtar");
  nonce = bayt(nonce, "nonce");
  _denetle(anahtar, nonce);
  _sayacDenetle(sayac);
  const d = new Int32Array(16);
  for (let i = 0; i < 4; i++) d[i] = _SABIT[i];
  for (let i = 0; i < 8; i++) d[4 + i] = _le32(anahtar, 4 * i);
  d[12] = sayac;
  for (let i = 0; i < 3; i++) d[13 + i] = _le32(nonce, 4 * i);
  return d;
}

// RFC 8439 2.3: sabit(4) + anahtar(8) + sayac(1) + nonce(3), isaretsiz sozcukler.
export function baslangicDurumu(anahtar, sayac, nonce) {
  return Array.from(_durum(anahtar, sayac, nonce), (v) => v >>> 0);
}

function _blokYaz(ilk, x, cikis) {
  x.set(ilk);
  for (let i = 0; i < 10; i++) {
    _qr(x, 0, 4, 8, 12);
    _qr(x, 1, 5, 9, 13);
    _qr(x, 2, 6, 10, 14);
    _qr(x, 3, 7, 11, 15);
    _qr(x, 0, 5, 10, 15);
    _qr(x, 1, 6, 11, 12);
    _qr(x, 2, 7, 8, 13);
    _qr(x, 3, 4, 9, 14);
  }
  for (let i = 0, o = 0; i < 16; i++) {
    const v = (x[i] + ilk[i]) | 0;
    cikis[o++] = v & 255;
    cikis[o++] = (v >>> 8) & 255;
    cikis[o++] = (v >>> 16) & 255;
    cikis[o++] = (v >>> 24) & 255;
  }
}

// RFC 8439 2.3: 20 turluk blok fonksiyonu, 64 baytlik anahtar akisi blogu.
export function blok(anahtar, sayac, nonce) {
  const c = new Uint8Array(64);
  _blokYaz(_durum(anahtar, sayac, nonce), new Int32Array(16), c);
  return c;
}

// RFC 8439 2.4: ChaCha20 sifreleme (XOR; ayni islev cozer). Sayac `sayac`tan baslar;
// son blogun sayaci 2^32 - 1'i asarsa DegerHatasi (Python blok() da ayni yerde reddeder).
export function akisSifrele(anahtar, sayac, nonce, duz) {
  duz = bayt(duz, "duz");
  const ilk = _durum(anahtar, sayac, nonce);
  const bloklar = Math.ceil(duz.length / 64);
  if (bloklar && sayac + bloklar - 1 > 0xffffffff) throw new DegerHatasi("blok sayaci 32 bit olmali");
  const cikis = new Uint8Array(duz.length);
  const x = new Int32Array(16), akis = new Uint8Array(64);
  for (let i = 0; i < duz.length; i += 64) {
    _blokYaz(ilk, x, akis);
    const n = Math.min(64, duz.length - i);
    for (let j = 0; j < n; j++) cikis[i + j] = duz[i + j] ^ akis[j];
    ilk[12] = (ilk[12] + 1) | 0;
  }
  return cikis;
}

// ── Poly1305 (RFC 8439 §2.5) ─────────────────────────────────────────────
// 130 bitlik sayilar 10 x 13 bitlik uzuvda: carpim terimleri < 2^31, satir toplamlari < 2^34,
// hepsi cift duyarlikta TAM (BigInt yok). 2^130 = 5 (mod p).
const _UST_BIT = 1 << 11;                // 16 baytlik tam blokta 2^128 biti (uzuv 9'un 11. biti)

function _uzuv13(b, o, ust) {
  const t0 = b[o] | (b[o + 1] << 8), t1 = b[o + 2] | (b[o + 3] << 8);
  const t2 = b[o + 4] | (b[o + 5] << 8), t3 = b[o + 6] | (b[o + 7] << 8);
  const t4 = b[o + 8] | (b[o + 9] << 8), t5 = b[o + 10] | (b[o + 11] << 8);
  const t6 = b[o + 12] | (b[o + 13] << 8), t7 = b[o + 14] | (b[o + 15] << 8);
  return [
    t0 & 0x1fff,
    ((t0 >>> 13) | (t1 << 3)) & 0x1fff,
    ((t1 >>> 10) | (t2 << 6)) & 0x1fff,
    ((t2 >>> 7) | (t3 << 9)) & 0x1fff,
    ((t3 >>> 4) | (t4 << 12)) & 0x1fff,
    (t4 >>> 1) & 0x1fff,
    ((t4 >>> 14) | (t5 << 2)) & 0x1fff,
    ((t5 >>> 11) | (t6 << 5)) & 0x1fff,
    ((t6 >>> 8) | (t7 << 8)) & 0x1fff,
    (t7 >>> 5) | ust,
  ];
}

export class Poly1305 {
  constructor(anahtar) {
    anahtar = bayt(anahtar, "anahtar");
    if (anahtar.length !== 32) throw new DegerHatasi("Poly1305 anahtari 32 bayt olmali");
    const rb = anahtar.slice(0, 16);                     // r &= 0x0ffffffc0ffffffc0ffffffc0fffffff
    rb[3] &= 15; rb[7] &= 15; rb[11] &= 15; rb[15] &= 15;
    rb[4] &= 252; rb[8] &= 252; rb[12] &= 252;
    this._r = _uzuv13(rb, 0, 0);
    this._s = [];
    for (let i = 0; i < 8; i++) this._s.push(anahtar[16 + 2 * i] | (anahtar[17 + 2 * i] << 8));
    this._h = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    this._tampon = new Uint8Array(16);
    this._n = 0;
    this._bitti = false;
  }

  _isle(b, o, ust) {
    const m = _uzuv13(b, o, ust), h = this._h, r = this._r;
    for (let i = 0; i < 10; i++) h[i] += m[i];
    const d = [];
    for (let i = 0; i < 10; i++) {
      let s = 0;
      for (let j = 0; j < 10; j++) s += h[j] * (j <= i ? r[i - j] : 5 * r[i - j + 10]);
      d.push(s);
    }
    let c = 0;
    for (let i = 0; i < 10; i++) {
      const v = d[i] + c;
      c = Math.floor(v / 8192);
      h[i] = v - c * 8192;
    }
    h[0] += c * 5;                                       // 2^130'un ustu: x 5
    c = h[0] >>> 13;
    h[0] &= 0x1fff;
    h[1] += c;
  }

  ekle(mesaj) {
    mesaj = bayt(mesaj, "mesaj");
    if (this._bitti) throw new Error("Poly1305 bitti");
    const L = mesaj.length;
    let i = 0;
    if (this._n) {
      const al = Math.min(16 - this._n, L);
      this._tampon.set(mesaj.subarray(0, al), this._n);
      this._n += al;
      i = al;
      if (this._n < 16) return this;
      this._isle(this._tampon, 0, _UST_BIT);
      this._n = 0;
    }
    for (; i + 16 <= L; i += 16) this._isle(mesaj, i, _UST_BIT);
    if (i < L) {
      this._tampon.set(mesaj.subarray(i), 0);
      this._n = L - i;
    }
    return this;
  }

  bitir() {
    if (this._bitti) throw new Error("Poly1305 zaten bitti");
    this._bitti = true;
    if (this._n) {                                       // son kisa blok: 0x01 + sifir, ust bit yok
      const b = this._tampon;
      b[this._n] = 1;
      b.fill(0, this._n + 1);
      this._isle(b, 0, 0);
    }
    const h = this._h.slice();
    // tam tasima, iki tur (ilk turun 2^130 tasmasi x5 ile basa doner; ikincide tasma olmaz)
    for (let tur = 0; tur < 2; tur++) {
      let c = 0;
      for (let i = 0; i < 10; i++) {
        h[i] += c;
        c = h[i] >>> 13;
        h[i] &= 0x1fff;
      }
      h[0] += c * 5;
    }
    // g = h + 5 - 2^130; tasma (c = 1) varsa h >= p ve sonuc g. Dalsiz secim.
    const g = [];
    let c = 5;
    for (let i = 0; i < 10; i++) {
      const v = h[i] + c;
      c = v >>> 13;
      g.push(v & 0x1fff);
    }
    const maske = -c;
    for (let i = 0; i < 10; i++) h[i] = (h[i] & ~maske) | (g[i] & maske);
    // alt 128 bit, 16 bitlik sozcuklere
    const w = [
      (h[0] | (h[1] << 13)) & 0xffff,
      ((h[1] >>> 3) | (h[2] << 10)) & 0xffff,
      ((h[2] >>> 6) | (h[3] << 7)) & 0xffff,
      ((h[3] >>> 9) | (h[4] << 4)) & 0xffff,
      ((h[4] >>> 12) | (h[5] << 1) | (h[6] << 14)) & 0xffff,
      ((h[6] >>> 2) | (h[7] << 11)) & 0xffff,
      ((h[7] >>> 5) | (h[8] << 8)) & 0xffff,
      ((h[8] >>> 8) | (h[9] << 5)) & 0xffff,
    ];
    // (h + s) mod 2^128
    const cikis = new Uint8Array(16);
    let f = 0;
    for (let i = 0; i < 8; i++) {
      f = w[i] + this._s[i] + (f >>> 16);
      cikis[2 * i] = f & 255;
      cikis[2 * i + 1] = (f >>> 8) & 255;
    }
    return cikis;
  }
}

// RFC 8439 2.5: tek kullanimlik MAC; anahtar 32 B (r || s), cikis 16 B.
export function poly1305(anahtar, mesaj) {
  return new Poly1305(anahtar).ekle(mesaj).bitir();
}

// RFC 8439 2.6: Poly1305 anahtari = ChaCha20 blogu (sayac 0) ilk 32 bayti.
export function poly1305AnahtarUret(anahtar, nonce) {
  return blok(anahtar, 0, nonce).slice(0, 32);
}

// ── ChaCha20-Poly1305 IETF AEAD (RFC 8439 §2.8) ──────────────────────────
const _SIFIR = new Uint8Array(16);

function _dolgu(n) {
  return _SIFIR.subarray(0, (16 - (n % 16)) % 16);
}

function _u64le(b, o, n) {
  const dusuk = n >>> 0, yuksek = Math.floor(n / 0x100000000);
  for (let i = 0; i < 4; i++) {
    b[o + i] = (dusuk >>> (8 * i)) & 255;
    b[o + 4 + i] = (yuksek >>> (8 * i)) & 255;
  }
}

// aad || dolgu || sifreli || dolgu || len(aad) u64 LE || len(sifreli) u64 LE
function _etiket(otk, aad, sifreli) {
  const p = new Poly1305(otk);
  p.ekle(aad);
  p.ekle(_dolgu(aad.length));
  p.ekle(sifreli);
  p.ekle(_dolgu(sifreli.length));
  const uzunluklar = new Uint8Array(16);
  _u64le(uzunluklar, 0, aad.length);
  _u64le(uzunluklar, 8, sifreli.length);
  p.ekle(uzunluklar);
  return p.bitir();
}

// AEAD sifreleme. Donus = sifreli metin + 16 B etiket.
export function sifrele(anahtar, nonce, duz, aad = new Uint8Array(0)) {
  anahtar = bayt(anahtar, "anahtar");
  nonce = bayt(nonce, "nonce");
  duz = bayt(duz, "duz");
  aad = bayt(aad, "aad");
  _denetle(anahtar, nonce);
  const otk = poly1305AnahtarUret(anahtar, nonce);
  const sifreli = akisSifrele(anahtar, 1, nonce, duz);
  const cikis = new Uint8Array(sifreli.length + ETIKET_UZUNLUK);
  cikis.set(sifreli);
  cikis.set(_etiket(otk, aad, sifreli), sifreli.length);
  return cikis;
}

// AEAD cozme. Etiket tutmazsa (bozuk veri, yanlis anahtar/nonce/aad) DegerHatasi;
// etiket DOGRULANMADAN hicbir duz metin dondurulmez.
export function coz(anahtar, nonce, sifreliEtiket, aad = new Uint8Array(0)) {
  anahtar = bayt(anahtar, "anahtar");
  nonce = bayt(nonce, "nonce");
  sifreliEtiket = bayt(sifreliEtiket, "sifreli metin");
  aad = bayt(aad, "aad");
  _denetle(anahtar, nonce);
  if (sifreliEtiket.length < ETIKET_UZUNLUK) throw new DegerHatasi("sifreli metin etiketten kisa");
  const sinir = sifreliEtiket.length - ETIKET_UZUNLUK;
  const sifreli = sifreliEtiket.subarray(0, sinir), etiket = sifreliEtiket.subarray(sinir);
  const beklenen = _etiket(poly1305AnahtarUret(anahtar, nonce), aad, sifreli);
  if (!sabitZamanliEsit(beklenen, etiket)) {
    throw new DegerHatasi("etiket tutmadi (bozuk veri, yanlis anahtar ya da yanlis konu)");
  }
  return akisSifrele(anahtar, 1, nonce, sifreli);
}

// Rastgele bayt: crypto.getRandomValues guvenli baglam ISTEMEZ (yalniz subtle ister).
export function rastgeleBayt(n) {
  const c = globalThis.crypto;
  if (!c || typeof c.getRandomValues !== "function") throw new Error("crypto.getRandomValues yok");
  const b = new Uint8Array(n);
  for (let i = 0; i < n; i += 65536) c.getRandomValues(b.subarray(i, Math.min(n, i + 65536)));
  return b;
}
