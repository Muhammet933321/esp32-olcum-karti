// 2B — kripto.js: NIST/RFC vektorleri + Python capraz vektorleri (ortak/test/vektor/kripto.json,
// uretim/ortak_vektor_kripto.py) + bozuk girdi. Kosu: node --test ortak/test/kripto.test.js
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as K from "../src/kripto.js";

const V = JSON.parse(readFileSync(new URL("./vektor/kripto.json", import.meta.url), "utf8"));
const G = JSON.parse(readFileSync(new URL("../../uretim/vektor_guvenlik.json", import.meta.url), "utf8"));
const yazi = new TextEncoder();
const hx = (s) => K.hexten(s.replace(/\s+/g, ""));
const reddeder = (islev) => assert.throws(islev, K.DegerHatasi);

function cevir(b, i, maske = 1) {
  const c = b.slice();
  c[i] ^= maske;
  return c;
}

// ── SHA-256 ──────────────────────────────────────────────────────────────
describe("SHA-256: NIST (FIPS 180-2 ornekleri)", () => {
  const nist = [
    ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
    ["abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
      "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"],
    ["abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
      "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"],
  ];
  for (const [m, h] of nist) {
    it(`"${m.slice(0, 12)}..." (${m.length} B)`, () => assert.equal(K.hex(K.sha256(yazi.encode(m))), h));
  }
  it("1 000 000 x 'a' (parca parca 997 B)", () => {
    const s = new K.Sha256();
    const parca = new Uint8Array(997).fill(97);
    let kalan = 1_000_000;
    while (kalan > 0) {
      const n = Math.min(kalan, parca.length);
      s.ekle(parca.subarray(0, n));
      kalan -= n;
    }
    assert.equal(K.hex(s.bitir()), "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
  });
});

describe("SHA-256: Python capraz (hashlib)", () => {
  it(`${V.sha256.length} uzunluk (0..4096; 55/56/63/64/65 dolgu sinirlari) tek seferde`, () => {
    for (const v of V.sha256) assert.equal(K.hex(K.sha256(K.hexten(v.veri))), v.ozet, `n=${v.n}`);
  });
  it("artimli: 1/7/63/64/65 baytlik parcalar tek seferle ayni", () => {
    for (const v of V.sha256) {
      const veri = K.hexten(v.veri);
      for (const adim of [1, 7, 63, 64, 65]) {
        const s = new K.Sha256();
        for (let i = 0; i < veri.length; i += adim) s.ekle(veri.subarray(i, i + adim));
        assert.equal(K.hex(s.bitir()), v.ozet, `n=${v.n} adim=${adim}`);
      }
    }
  });
  it("kopya: ortak onekten iki dal bagimsiz", () => {
    const a = new K.Sha256().ekle(yazi.encode("ortak-onek-"));
    const b = a.kopya();
    a.ekle(yazi.encode("A"));
    b.ekle(yazi.encode("B"));
    assert.equal(K.hex(a.bitir()), K.hex(K.sha256(yazi.encode("ortak-onek-A"))));
    assert.equal(K.hex(b.bitir()), K.hex(K.sha256(yazi.encode("ortak-onek-B"))));
  });
  it("bitmis ozete ekleme / ikinci bitir hata", () => {
    const s = new K.Sha256();
    s.bitir();
    assert.throws(() => s.ekle(new Uint8Array(1)));
    assert.throws(() => s.bitir());
  });
  it("metin girdi TypeError (bayt bekler)", () => assert.throws(() => K.sha256("abc"), TypeError));
});

// ── HMAC ─────────────────────────────────────────────────────────────────
describe("HMAC-SHA256", () => {
  it(`RFC 4231 (uretim/vektor_guvenlik.json, ${G.hmac.length} durum)`, () => {
    for (const v of G.hmac) assert.equal(K.hex(K.hmacSha256(K.hexten(v.anahtar), K.hexten(v.veri))), v.hmac);
  });
  it("RFC 4231 durum 5 (128 bite kesilmis)", () => {
    const m = K.hmacSha256(new Uint8Array(20).fill(0x0c), yazi.encode("Test With Truncation"));
    assert.equal(K.hex(m.subarray(0, 16)), "a3b6167473100ee06e0c796c2955552b");
  });
  it(`Python capraz: anahtar 0..200 B (64 B blok siniri, uzun anahtar ozetlenir), ${V.hmac.length} durum`, () => {
    for (const v of V.hmac) {
      assert.equal(K.hex(K.hmacSha256(K.hexten(v.anahtar), K.hexten(v.veri))), v.hmac, `k=${v.anahtar.length / 2}`);
    }
  });
  it("artimli + kopya tek seferle ayni", () => {
    const v = V.hmac[V.hmac.length - 1];
    const veri = K.hexten(v.veri);
    const h = new K.HmacSha256(K.hexten(v.anahtar));
    h.ekle(veri.subarray(0, 10));
    const k = h.kopya();
    h.ekle(veri.subarray(10));
    k.ekle(veri.subarray(10));
    assert.equal(K.hex(h.bitir()), v.hmac);
    assert.equal(K.hex(k.bitir()), v.hmac);
  });
});

// ── PBKDF2 ───────────────────────────────────────────────────────────────
describe("PBKDF2-HMAC-SHA256", () => {
  it("RFC 7914 §11 (vektor_guvenlik.json; 1 ve 80 000 tur, 64 B)", () => {
    for (const v of G.pbkdf2) {
      const dk = K.pbkdf2HmacSha256(yazi.encode(v.parola), K.hexten(v.tuz), v.tur, v.dk.length / 2);
      assert.equal(K.hex(dk), v.dk, `tur=${v.tur}`);
    }
  });
  it("RFC 6070 bicimli SHA-256 vektorleri (1/2/4096 tur, 40 ve 16 B, NUL bayti)", () => {
    const d = [
      ["password", "salt", 1, 32, "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b"],
      ["password", "salt", 2, 32, "ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43"],
      ["password", "salt", 4096, 32, "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a"],
      ["passwordPASSWORDpassword", "saltSALTsaltSALTsaltSALTsaltSALTsalt", 4096, 40,
        "348c89dbcbd32b2f32d814b8116e84cf2b17347ebc1800181c4e2a1fb8dd53e1c635518c7dac47e9"],
      ["pass\0word", "sa\0lt", 4096, 16, "89b69d0516f829893c696226650a8687"],
    ];
    for (const [p, s, c, n, h] of d) assert.equal(K.hex(K.pbkdf2HmacSha256(yazi.encode(p), yazi.encode(s), c, n)), h);
  });
  it(`Python capraz (hashlib): ${V.pbkdf2.length} durum — bos parola/tuz, 64/65 B parola, 33/40/64 B cikis`, () => {
    for (const v of V.pbkdf2) {
      const dk = K.pbkdf2HmacSha256(K.hexten(v.parola_hex), K.hexten(v.tuz), v.tur, v.uzunluk);
      assert.equal(K.hex(dk), v.dk, v.ad);
    }
  });
  it("projenin gercek ayari: 20 000 tur, 16 B tuz, 12 karakter parola — sure", (t) => {
    const v = V.pbkdf2.find((x) => x.ad === "proje");
    assert.equal(v.tur, 20000);
    const p = K.hexten(v.parola_hex), s = K.hexten(v.tuz);
    K.pbkdf2HmacSha256(p, s, 1000, 32);                            // isinma (JIT)
    const t0 = performance.now();
    const dk = K.pbkdf2HmacSha256(p, s, v.tur, 32);
    const ms = performance.now() - t0;
    assert.equal(K.hex(dk), v.dk);
    t.diagnostic(`PBKDF2 20 000 tur: ${ms.toFixed(1)} ms (Node ${process.version})`);
    assert.ok(ms < 2000, `20 000 tur ${ms} ms — telefon olcutu (< 1 s) icin cok yavas`);
  });
  it("tur < 1 ya da uzunluk < 1 DegerHatasi", () => {
    reddeder(() => K.pbkdf2HmacSha256(new Uint8Array(1), new Uint8Array(1), 0, 32));
    reddeder(() => K.pbkdf2HmacSha256(new Uint8Array(1), new Uint8Array(1), 1, 0));
    reddeder(() => K.pbkdf2HmacSha256(new Uint8Array(1), new Uint8Array(1), 1.5, 32));
  });
});

// ── ChaCha20 / Poly1305 / AEAD: RFC 8439 ─────────────────────────────────
const RFC_ANAHTAR = Uint8Array.from({ length: 32 }, (_, i) => i);
const RFC_METIN = yazi.encode("Ladies and Gentlemen of the class of '99: If I could offer you only "
  + "one tip for the future, sunscreen would be it.");
const AEAD_ANAHTAR = Uint8Array.from({ length: 32 }, (_, i) => 0x80 + i);
const AEAD_NONCE = hx("07 00 00 00 40 41 42 43 44 45 46 47");
const AEAD_AAD = hx("50 51 52 53 c0 c1 c2 c3 c4 c5 c6 c7");
const AEAD_SIFRELI = hx(`
  d3 1a 8d 34 64 8e 60 db 7b 86 af bc 53 ef 7e c2 a4 ad ed 51 29 6e 08 fe a9 e2 b5 a7 36 ee 62 d6
  3d be a4 5e 8c a9 67 12 82 fa fb 69 da 92 72 8b 1a 71 de 0a 9e 06 0b 29 05 d6 a5 b6 7e cd 3b 36
  92 dd bd 7f 2d 77 8b 8c 98 03 ae e3 28 09 1b 58 fa b3 24 e4 fa d6 75 94 55 85 80 8b 48 31 d7 bc
  3f f4 de f0 8e 4b 7a 9d e5 76 d2 65 86 ce c6 4b 61 16`);
const AEAD_ETIKET = hx("1a e1 0b 59 4f 09 e2 6a 7e 90 2e cb d0 60 06 91");
const AEAD_TAM = K.birlestir(AEAD_SIFRELI, AEAD_ETIKET);

describe("ChaCha20-Poly1305: RFC 8439", () => {
  it("2.1.1 ceyrek tur", () => {
    assert.deepEqual(K.ceyrekTur(0x11111111, 0x01020304, 0x9b8d6f43, 0x01234567),
      [0xea2a92f4, 0xcb1cf8ce, 0x4581472e, 0x5881c4bb]);
  });
  it("2.2.1 durum uzerinde ceyrek tur (2, 7, 8, 13)", () => {
    const d = [0x879531e0, 0xc5ecf37d, 0x516461b1, 0xc9a62f8a, 0x44c20ef3, 0x3390af7f, 0xd9fc690b, 0x2a5f714c,
      0x53372767, 0xb00a5631, 0x974c541a, 0x359e9963, 0x5c971061, 0x3d631689, 0x2098d9d6, 0x91dbd320];
    K.ceyrekTurDurum(d, 2, 7, 8, 13);
    assert.equal(d[2], 0xbdb886dc);
    assert.equal(d[7], 0xcfacafd2);
    assert.equal(d[8], 0xe46bea80);
    assert.equal(d[13], 0xccc07c79);
    assert.equal(d[0], 0x879531e0);
    assert.equal(d[15], 0x91dbd320);
  });
  it("2.3.2 baslangic durumu + blok (sayac 1)", () => {
    const n = hx("00 00 00 09 00 00 00 4a 00 00 00 00");
    assert.deepEqual(K.baslangicDurumu(RFC_ANAHTAR, 1, n), [
      0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c,
      0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]);
    assert.equal(K.hex(K.blok(RFC_ANAHTAR, 1, n)), "10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4e"
      + "d2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e");
  });
  it("2.4.2 ChaCha20 sifreleme (114 B, 2 blok) + ayni islev cozer", () => {
    const n = hx("00 00 00 00 00 00 00 4a 00 00 00 00");
    const c = K.akisSifrele(RFC_ANAHTAR, 1, n, RFC_METIN);
    assert.equal(K.hex(c), "6e2e359a2568f98041ba0728dd0d6981e97e7aec1d4360c20a27afccfd9fae0bf91b65c5524733ab"
      + "8f593dabcd62b3571639d624e65152ab8f530c359f0861d807ca0dbf500d6a6156a38e088a22b65e52bc514d16ccf806"
      + "818ce91ab77937365af90bbf74a35be6b40b8eedf2785e42874d");
    assert.deepEqual(K.akisSifrele(RFC_ANAHTAR, 1, n, c), RFC_METIN);
  });
  it("2.5.2 Poly1305 etiketi", () => {
    const k = hx("85 d6 be 78 57 55 6d 33 7f 44 52 fe 42 d5 06 a8 01 03 80 8a fb 0d b2 fd 4a bf f6 af 41 49 f5 1b");
    assert.equal(K.hex(K.poly1305(k, yazi.encode("Cryptographic Forum Research Group"))),
      "a8061dc1305136c6c22b8baf0c0127a9");
  });
  it("2.6.2 Poly1305 anahtar uretimi", () => {
    assert.equal(K.hex(K.poly1305AnahtarUret(AEAD_ANAHTAR, hx("00 00 00 00 00 01 02 03 04 05 06 07"))),
      "8ad5a08b905f81cc815040274ab29471a833b637e3fd0da508dbb8e2fdd1a646");
  });
  it("2.8.2 AEAD sifreleme (metin + etiket) ve cozme", () => {
    const s = K.sifrele(AEAD_ANAHTAR, AEAD_NONCE, RFC_METIN, AEAD_AAD);
    assert.deepEqual(s.subarray(0, s.length - 16), AEAD_SIFRELI);
    assert.deepEqual(s.subarray(s.length - 16), AEAD_ETIKET);
    assert.deepEqual(K.coz(AEAD_ANAHTAR, AEAD_NONCE, AEAD_TAM, AEAD_AAD), RFC_METIN);
  });
  it("Ek A.3 Poly1305 tasima kenarlari (#1, #5-#11) RFC etiketleriyle", () => {
    const z = "00".repeat(16), r10 = "01000000000000000400000000000000";
    const m10 = "e33594d7505e43b900000000000000003394d7505e4379cd0100000000000000"
      + "0000000000000000000000000000000001000000000000000000000000000000";
    const d = [
      [z + z, "00".repeat(64), "00000000000000000000000000000000"],
      ["02" + "00".repeat(15) + z, "ff".repeat(16), "03000000000000000000000000000000"],
      ["02" + "00".repeat(15) + "ff".repeat(16), "02" + "00".repeat(15), "03000000000000000000000000000000"],
      ["01" + "00".repeat(15) + z, "ff".repeat(16) + "f0" + "ff".repeat(15) + "11" + "00".repeat(15),
        "05000000000000000000000000000000"],
      ["01" + "00".repeat(15) + z, "ff".repeat(16) + "fb" + "fe".repeat(15) + "01".repeat(16),
        "00000000000000000000000000000000"],
      ["02" + "00".repeat(15) + z, "fd" + "ff".repeat(15), "faffffffffffffffffffffffffffffff"],
      [r10 + z, m10, "14000000000000005500000000000000"],
      [r10 + z, m10.slice(0, 96), "13000000000000000000000000000000"],
    ];
    for (const [k, m, e] of d) assert.equal(K.hex(K.poly1305(K.hexten(k), K.hexten(m))), e, m.slice(0, 20));
  });
});

describe("ChaCha20-Poly1305: Python capraz (kopru/chacha.py)", () => {
  it(`blok: ${V.chacha.blok.length} durum (sayac 0, 1, 7, 2^32-2, 2^32-1)`, () => {
    for (const v of V.chacha.blok) {
      assert.equal(K.hex(K.blok(K.hexten(v.anahtar), v.sayac, K.hexten(v.nonce))), v.blok, `sayac=${v.sayac}`);
    }
  });
  it(`akis: ${V.chacha.akis.length} durum (0..200 B, sayac 2^32-2'den iki blok)`, () => {
    for (const v of V.chacha.akis) {
      const c = K.akisSifrele(K.hexten(v.anahtar), v.sayac, K.hexten(v.nonce), K.hexten(v.duz));
      assert.equal(K.hex(c), v.sifreli, `n=${v.duz.length / 2}`);
    }
  });
  it(`poly1305: ${V.poly1305.length} durum (A.3 kenarlari, r=s=ff..ff, rastgele 0..1000 B)`, () => {
    for (const v of V.poly1305) assert.equal(K.hex(K.poly1305(K.hexten(v.anahtar), K.hexten(v.mesaj))), v.etiket, v.ad);
  });
  it("poly1305 artimli (1/3/16/17 B parcalar) tek seferle ayni", () => {
    for (const v of V.poly1305) {
      const m = K.hexten(v.mesaj);
      for (const adim of [1, 3, 16, 17]) {
        const p = new K.Poly1305(K.hexten(v.anahtar));
        for (let i = 0; i < m.length; i += adim) p.ekle(m.subarray(i, i + adim));
        assert.equal(K.hex(p.bitir()), v.etiket, `${v.ad} adim=${adim}`);
      }
    }
  });
  it(`AEAD: ${V.aead.length} durum (duz 0..1000 B x AAD 0..100 B) muhurle + ac`, () => {
    for (const v of V.aead) {
      const [k, n, a, d] = [v.anahtar, v.nonce, v.aad, v.duz].map(K.hexten);
      assert.equal(K.hex(K.sifrele(k, n, d, a)), v.sifreli, `duz=${d.length} aad=${a.length}`);
      assert.equal(K.hex(K.coz(k, n, K.hexten(v.sifreli), a)), v.duz);
    }
  });
});

// Yalniz sinama: BigInt ile dogrudan Poly1305 (uzuv gerceklemesinin bagimsiz karsiligi)
function polyBigInt(anahtar, mesaj) {
  const le = (b) => b.reduceRight((a, x) => (a << 8n) | BigInt(x), 0n);
  const P = (1n << 130n) - 5n;
  const r = le(anahtar.subarray(0, 16)) & 0x0ffffffc0ffffffc0ffffffc0fffffffn;
  const s = le(anahtar.subarray(16));
  let a = 0n;
  for (let i = 0; i < mesaj.length; i += 16) {
    const p = mesaj.subarray(i, i + 16);
    a = ((a + le(p) + (1n << BigInt(8 * p.length))) * r) % P;
  }
  let t = (a + s) & ((1n << 128n) - 1n);
  const c = new Uint8Array(16);
  for (let i = 0; i < 16; i++, t >>= 8n) c[i] = Number(t & 255n);
  return c;
}

describe("Poly1305: BigInt karsiligiyla fark sinamasi", () => {
  it("1500 rastgele (anahtar, mesaj) + uc anahtarlar (r/s hep ff, hep 00)", () => {
    let x = 0x2b7e1516;                                          // belirlenimci xorshift
    const rb = () => {
      x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
      return x & 255;
    };
    for (let i = 0; i < 1500; i++) {
      const k = Uint8Array.from({ length: 32 }, rb);
      if (i % 5 === 0) k.fill(0xff, 0, 16);
      if (i % 7 === 0) k.fill(0xff, 16);
      if (i % 11 === 0) k.fill(0, 0, 16);
      const m = Uint8Array.from({ length: (rb() * 3 + rb()) % 300 }, i % 3 ? rb : () => 0xff);
      assert.equal(K.hex(K.poly1305(k, m)), K.hex(polyBigInt(k, m)), `i=${i} n=${m.length}`);
    }
  });
});

describe("AEAD: bozulma her halde reddedilir", () => {
  const ac = (s = AEAD_TAM, k = AEAD_ANAHTAR, n = AEAD_NONCE, a = AEAD_AAD) => K.coz(k, n, s, a);
  it("kontrol: bozulmamis veri cozulur", () => assert.deepEqual(ac(), RFC_METIN));
  it("sifreli metnin bir biti", () => reddeder(() => ac(cevir(AEAD_TAM, 5))));
  it("sifreli metnin SON bayti", () => reddeder(() => ac(cevir(AEAD_TAM, AEAD_SIFRELI.length - 1))));
  it("etiketin ilk bayti", () => reddeder(() => ac(cevir(AEAD_TAM, AEAD_TAM.length - 16))));
  it("etiketin yalniz SON bayti (0x80) — sabit zamanli karsilastirma sonuna dek bakar", () => {
    reddeder(() => ac(cevir(AEAD_TAM, AEAD_TAM.length - 1, 0x80)));
  });
  it("yanlis AAD / bos AAD / bir bayt fazla AAD", () => {
    reddeder(() => ac(undefined, undefined, undefined, cevir(AEAD_AAD, 0)));
    reddeder(() => ac(undefined, undefined, undefined, new Uint8Array(0)));
    reddeder(() => ac(undefined, undefined, undefined, K.birlestir(AEAD_AAD, new Uint8Array(1))));
  });
  it("yanlis anahtar (1 bit) / yanlis nonce (1 bit)", () => {
    reddeder(() => ac(undefined, cevir(AEAD_ANAHTAR, 0)));
    reddeder(() => ac(undefined, undefined, cevir(AEAD_NONCE, 11)));
  });
  it("bir bayt eklenmis / eksik / 15 B / bos", () => {
    reddeder(() => ac(K.birlestir(AEAD_TAM, new Uint8Array(1))));
    reddeder(() => ac(AEAD_TAM.subarray(0, AEAD_TAM.length - 1)));
    reddeder(() => ac(AEAD_TAM.subarray(0, 15)));
    reddeder(() => ac(new Uint8Array(0)));
  });
  it("Python capraz AEAD vektorlerinde etiketin her bayti tek tek bozulunca red", () => {
    for (const v of V.aead) {
      const [k, n, a] = [v.anahtar, v.nonce, v.aad].map(K.hexten);
      const s = K.hexten(v.sifreli);
      for (let i = s.length - 16; i < s.length; i++) reddeder(() => K.coz(k, n, cevir(s, i, 0x40), a));
      if (s.length > 16) reddeder(() => K.coz(k, n, cevir(s, 0), a));
    }
  });
  it("anahtar 31/33 B, nonce 8/13 B DegerHatasi (sifrele, coz, blok)", () => {
    const k31 = AEAD_ANAHTAR.subarray(0, 31), k33 = K.birlestir(AEAD_ANAHTAR, new Uint8Array(1));
    for (const k of [k31, k33]) {
      reddeder(() => K.sifrele(k, AEAD_NONCE, RFC_METIN));
      reddeder(() => K.coz(k, AEAD_NONCE, AEAD_TAM));
      reddeder(() => K.blok(k, 0, AEAD_NONCE));
    }
    for (const n of [AEAD_NONCE.subarray(0, 8), K.birlestir(AEAD_NONCE, new Uint8Array(1))]) {
      reddeder(() => K.sifrele(AEAD_ANAHTAR, n, RFC_METIN));
      reddeder(() => K.coz(AEAD_ANAHTAR, n, AEAD_TAM));
    }
    reddeder(() => K.poly1305(AEAD_ANAHTAR.subarray(0, 16), RFC_METIN));
  });
  it("blok sayaci: 2^32 ve -1 red; 2^32-1'den 65 B (iki blok) red, 64 B kabul", () => {
    reddeder(() => K.blok(AEAD_ANAHTAR, 2 ** 32, AEAD_NONCE));
    reddeder(() => K.blok(AEAD_ANAHTAR, -1, AEAD_NONCE));
    reddeder(() => K.akisSifrele(AEAD_ANAHTAR, 0xffffffff, AEAD_NONCE, new Uint8Array(65)));
    assert.equal(K.akisSifrele(AEAD_ANAHTAR, 0xffffffff, AEAD_NONCE, new Uint8Array(64)).length, 64);
  });
  it("metin (Uint8Array olmayan) girdi TypeError", () => {
    assert.throws(() => K.sifrele(AEAD_ANAHTAR, AEAD_NONCE, "duz metin"), TypeError);
  });
  it("gidis-donus: 0..1000 B x AAD 0/1/16/17 B (dolgu sinirlari)", () => {
    for (const n of [0, 1, 15, 16, 17, 63, 64, 65, 127, 128, 129, 1000]) {
      for (const an of [0, 1, 16, 17]) {
        const d = Uint8Array.from({ length: n }, (_, i) => (i * 7 + an) & 255);
        const a = Uint8Array.from({ length: an }, (_, i) => i ^ 0x5a);
        const nonce = Uint8Array.from({ length: 12 }, (_, i) => i + n);
        assert.deepEqual(K.coz(AEAD_ANAHTAR, nonce, K.sifrele(AEAD_ANAHTAR, nonce, d, a), a), d);
      }
    }
  });
});

// ── yardimcilar ──────────────────────────────────────────────────────────
describe("yardimcilar", () => {
  it("sabitZamanliEsit: esit / ilk / orta / SON bayt farkli / uzunluk farkli / bos", () => {
    const a = Uint8Array.from({ length: 32 }, (_, i) => i);
    assert.equal(K.sabitZamanliEsit(a, a.slice()), true);
    assert.equal(K.sabitZamanliEsit(a, cevir(a, 0)), false);
    assert.equal(K.sabitZamanliEsit(a, cevir(a, 16)), false);
    assert.equal(K.sabitZamanliEsit(a, cevir(a, 31, 0x80)), false);
    assert.equal(K.sabitZamanliEsit(a, a.subarray(0, 31)), false);
    assert.equal(K.sabitZamanliEsit(new Uint8Array(0), new Uint8Array(0)), true);
  });
  it("hex / hexten gidis-donus; buyuk harf kabul; tek uzunluk ve hex olmayan red", () => {
    const b = Uint8Array.from({ length: 256 }, (_, i) => i);
    assert.deepEqual(K.hexten(K.hex(b)), b);
    assert.deepEqual(K.hexten("ABcd"), Uint8Array.of(0xab, 0xcd));
    reddeder(() => K.hexten("abc"));
    reddeder(() => K.hexten("zz"));
    reddeder(() => K.hexten("a b "));
    assert.throws(() => K.hexten(12), TypeError);
  });
  it("utf8Kodla: Turkce dogru, eslesmemis vekil DegerHatasi (Python encode hatasi)", () => {
    assert.deepEqual(K.utf8Kodla("şĞüİ🔋"), new Uint8Array(Buffer.from("şĞüİ🔋", "utf8")));
    reddeder(() => K.utf8Kodla("a\ud800b"));
    reddeder(() => K.utf8Kodla("\udc00"));
  });
  it("utf8Coz: gecersiz UTF-8 ve kodlanmis vekil red; BOM soyulmaz", () => {
    reddeder(() => K.utf8Coz(Uint8Array.of(0xff)));
    reddeder(() => K.utf8Coz(Uint8Array.of(0xed, 0xa0, 0x80)));
    assert.equal(K.utf8Coz(Uint8Array.of(0xef, 0xbb, 0xbf, 0x7b)), "﻿{");
  });
  it("rastgeleBayt: istenen uzunluk, iki cagri farkli", () => {
    const a = K.rastgeleBayt(70000), b = K.rastgeleBayt(32);
    assert.equal(a.length, 70000);
    assert.notDeepEqual(b, K.rastgeleBayt(32));
  });
});
