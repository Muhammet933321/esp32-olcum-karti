// 2B — zarf.js: 1E bildirim zarfi + /bildirim/bilgi. Bagimsiz KAT vektorleri (cryptography
// kutuphanesiyle hesaplanip uretim/test_bildirim.py'ye sabitlenmis) + Python capraz vektorleri
// (ortak/test/vektor/kripto.json, kopru/bildirim.py) + bozuk girdi. Kosu: node --test ortak/test/zarf.test.js
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DegerHatasi, coz, hex, hexten, sifrele } from "../src/kripto.js";
import * as Z from "../src/zarf.js";

const V = JSON.parse(readFileSync(new URL("./vektor/kripto.json", import.meta.url), "utf8")).zarf;
const yazi = new TextEncoder();
const reddeder = (islev) => assert.throws(islev, DegerHatasi);
const A = hexten(V.anahtar);

describe("zarf: bagimsiz bilinen-cevap (KAT) vektorleri", () => {
  const K = Uint8Array.from({ length: 32 }, (_, i) => i);
  const nonce = Uint8Array.from({ length: 12 }, (_, i) => 0x40 + i);
  it("KAT 1: dizilim + kompakt JSON + AAD = konu", () => {
    const z = Z.zarfKur(K, "ok/00112233445566778899aabbccddeeff/durum", { c: 1, a: 7, f: "A3-1E" }, nonce);
    assert.equal(hex(z), "4f4b4231404142434445464748494a4b83761fa3487bc22339edcc3797cd0bef"
      + "8eee222b69cd044d8355fca4e3eb33ea5f335ec73080bc9959");
  });
  it("KAT 2: Turkce icerik ham UTF-8 (ensure_ascii=False)", () => {
    const z = Z.zarfKur(K, "ok/00112233445566778899aabbccddeeff/olay", { n: 2, s: "kayıt bitti: şarj ÇÖĞÜŞİ" }, nonce);
    assert.equal(hex(z), "4f4b4231404142434445464748494a4b837612a34878c2232bedcc22d08e1409"
      + "05b8437a2d883506c42c17c48b55504a33345ae6e2d5a16acff1ebf748293761"
      + "f856627411acd4c44d9d2a9f12dd");
  });
});

describe("zarf: Python capraz (kopru/bildirim.py)", () => {
  for (const v of V.kur) {
    it(`${v.ad}: jsonPython == json.dumps, zarfKur bayt bayt, zarfAc geri verir`, () => {
      assert.equal(Z.jsonPython(v.icerik), v.duz);
      const z = Z.zarfKur(A, v.konu, v.icerik, hexten(v.nonce));
      assert.equal(hex(z), v.zarf);
      assert.deepEqual(Z.zarfAc(A, v.konu, hexten(v.zarf)), v.icerik);
    });
  }
  it("tamsayi benzeri anahtarlar: Map ile Python sirasi; duz nesnede HATA (JS sirayi bozar)", () => {
    const s = V.sirali;
    const m = new Map(s.icerik_cifler);
    assert.equal(Z.jsonPython(m), s.duz);
    assert.equal(hex(Z.zarfKur(A, s.konu, m, hexten(s.nonce))), s.zarf);
    reddeder(() => Z.jsonPython(Object.fromEntries(s.icerik_cifler)));
    reddeder(() => Z.jsonPython({ a: { 0: 1 } }));
  });
  it(`bozuk zarflar (${V.red.length}): Python reddettigi her durumda JS de DegerHatasi`, () => {
    for (const v of V.red) reddeder(() => Z.zarfAc(hexten(v.anahtar), v.konu, hexten(v.zarf)));
  });
  it("bilgiAad", () => {
    const b = V.bilgi_aad;
    assert.equal(hex(Z.bilgiAad(b.kimlik, b.n)), b.aad);
  });
  it(`bilgiCoz (${V.bilgi.length} durum): gecerli olanlar ayni sonuc, gecersizler red`, () => {
    for (const v of V.bilgi) {
      const islev = () => Z.bilgiCoz(hexten(v.K), v.kimlik, v.n, hexten(v.govde));
      if (v.sonuc.hata) {
        reddeder(islev);
      } else {
        const r = islev();
        assert.deepEqual({ ...r, anahtar: hex(r.anahtar) }, v.sonuc, v.ad);
      }
    }
  });
});

describe("jsonPython: Python json.dumps(ensure_ascii=False, separators, allow_nan=False) kurallari", () => {
  it("kacislar: \\u00xx kucuk harf, U+2028/DEL/ASCII disi ham", () => {
    assert.equal(Z.jsonPython("\x01\x1f\x7f é\"\\"), "\"\\u0001\\u001f\x7f é\\\"\\\\\"");
  });
  it("ondalik: |x| < 1e-4 bilimsel, us en az iki basamak ve isaretli", () => {
    const d = [[1e-5, "1e-05"], [1.5e-7, "1.5e-07"], [-9.99e-5, "-9.99e-05"], [5e-324, "5e-324"],
      [1e-100, "1e-100"], [0.0001, "0.0001"], [0.1, "0.1"], [123.456, "123.456"], [-0.5, "-0.5"]];
    for (const [x, s] of d) assert.equal(Z.jsonPython(x), s, String(x));
  });
  it("tamsayi: guvenli Number, 2^60 TAM (String(2**60) degil), BigInt, -0", () => {
    assert.equal(Z.jsonPython(2 ** 60), "1152921504606846976");
    assert.equal(Z.jsonPython(1e20), "100000000000000000000");
    assert.equal(Z.jsonPython(12345678901234567890n), "12345678901234567890");
    assert.equal(Z.jsonPython(-0), "0");
  });
  it("NaN / Infinity / eslesmemis vekil DegerHatasi; undefined, islev, Date, typed array TypeError", () => {
    reddeder(() => Z.jsonPython(NaN));
    reddeder(() => Z.jsonPython({ a: [Infinity] }));
    reddeder(() => Z.jsonPython({ s: "a\ud800" }));
    reddeder(() => Z.jsonPython(new Map([["\udc00", 1]])));
    for (const x of [undefined, () => 1, new Date(0), new Uint8Array(1), Symbol("s")]) {
      assert.throws(() => Z.jsonPython({ x }), TypeError);
    }
    assert.throws(() => Z.jsonPython(new Map([[1, 2]])), TypeError);
  });
  it("ic ice Map + dizi + prototipsiz nesne", () => {
    const o = Object.create(null);
    o.z = 1;
    assert.equal(Z.jsonPython(new Map([["m", [o, null, true]]])), "{\"m\":[{\"z\":1},null,true]}");
  });
});

describe("zarf: bozuk girdi ve sinirlar", () => {
  const konu = "ok/a1b2c3d4e5f60718293a4b5c6d7e8f90/olay";
  it("anahtar 31/33 B ya da Uint8Array degil DegerHatasi (kur ve ac)", () => {
    for (const k of [A.subarray(0, 31), new Uint8Array(33), "x".repeat(32), A.buffer]) {
      reddeder(() => Z.zarfKur(k, konu, { n: 1 }));
      reddeder(() => Z.zarfAc(k, konu, new Uint8Array(40)));
    }
  });
  it("nonce 11/13 B DegerHatasi; verilmezse rastgele (iki zarf farkli, ikisi de acilir)", () => {
    reddeder(() => Z.zarfKur(A, konu, {}, new Uint8Array(11)));
    reddeder(() => Z.zarfKur(A, konu, {}, new Uint8Array(13)));
    const z1 = Z.zarfKur(A, konu, { n: 1 }), z2 = Z.zarfKur(A, konu, { n: 1 });
    assert.notDeepEqual(z1.subarray(4, 16), z2.subarray(4, 16));
    assert.deepEqual(Z.zarfAc(A, konu, z1), { n: 1 });
    assert.deepEqual(Z.zarfAc(A, konu, z2), { n: 1 });
  });
  it("uzunluk = 4 + 12 + JSON + 16; bas 'OKB1'", () => {
    const z = Z.zarfKur(A, konu, { s: "ş" });
    assert.equal(hex(z.subarray(0, 4)), "4f4b4231");
    assert.equal(z.length, 4 + 12 + yazi.encode("{\"s\":\"ş\"}").length + 16);
  });
  it("32 B (en kisa gecerli boy) ama etiket yanlis -> red; 31 B -> red", () => {
    const z = new Uint8Array(32);
    z.set([0x4f, 0x4b, 0x42, 0x31]);
    reddeder(() => Z.zarfAc(A, konu, z));
    reddeder(() => Z.zarfAc(A, konu, z.subarray(0, 31)));
  });
  it("NaN iceren JSON: JS REDDEDER (Python json.loads kabul eder — bilinen fark, JS daha kati)", () => {
    const n = new Uint8Array(12);
    const z = new Uint8Array([0x4f, 0x4b, 0x42, 0x31, ...n, ...sifrele(A, n, yazi.encode("{\"a\":NaN}"), yazi.encode(konu))]);
    assert.deepEqual(coz(A, n, z.subarray(16), yazi.encode(konu)), yazi.encode("{\"a\":NaN}"));
    reddeder(() => Z.zarfAc(A, konu, z));
  });
  it("onekDenetle", () => {
    assert.equal(Z.onekDenetle("a1b2c3d4e5f60718293a4b5c6d7e8f90"), "a1b2c3d4e5f60718293a4b5c6d7e8f90");
    for (const o of ["A1B2C3D4E5F60718293A4B5C6D7E8F90", "a1b2", "a1b2c3d4e5f60718293a4b5c6d7e8f90\n", 5]) {
      reddeder(() => Z.onekDenetle(o));
    }
  });
});
