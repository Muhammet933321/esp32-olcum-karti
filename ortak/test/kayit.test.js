// B73 / 2A — ortak/src/kayit.js == kopru/kayit_bicim.py (BIT BIT).
// Vektorler: uretim/ortak_vektor_kayit.py -> test/vektor/kayit.json (Python'un cozdugu).
// Karsilastirma deepStrictEqual (Object.is): -0 / NaN / float32 -> double birebir.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as K from "../src/kayit.js";

const V = JSON.parse(readFileSync(new URL("./vektor/kayit.json", import.meta.url), "utf8"));

// ── yardimcilar ──────────────────────────────────────────────────────
const hex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
const hexten = (s) => Uint8Array.from(s.match(/../g) ?? [], (h) => parseInt(h, 16));
const deve = (ad) => ad.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());   // akis_coz -> akisCoz

/** JS degerini vektordeki JSON bicimine cevir (Python tarafindaki j() ile ayni kurallar). */
function jsonla(x) {
  if (x === null) return null;
  if (x === undefined) throw new Error("undefined: Python'da karsiligi yok");
  if (typeof x === "number") {
    if (Number.isNaN(x)) return { $f: "nan" };
    if (!Number.isFinite(x)) return { $f: x > 0 ? "inf" : "-inf" };
    return x;
  }
  if (typeof x === "boolean" || typeof x === "string") return x;
  if (x instanceof Uint8Array) return { $b: hex(x) };
  if (x instanceof Map) return { $map: [...x].map(([k, v]) => [jsonla(k), jsonla(v)]) };
  if (Array.isArray(x)) return x.map(jsonla);
  if (typeof x === "object") return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, jsonla(v)]));
  throw new Error("bilinmeyen tur: " + typeof x);
}

/** Vektordeki JSON'dan JS degeri (girdi olarak). */
function jsden(x) {
  if (Array.isArray(x)) return x.map(jsden);
  if (x && typeof x === "object") {
    if ("$b" in x) return hexten(x.$b);
    if ("$f" in x) return { nan: NaN, inf: Infinity, "-inf": -Infinity }[x.$f];
    if ("$map" in x) return new Map(x.$map.map(([k, v]) => [k, jsden(v)]));
    return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, jsden(v)]));
  }
  return x;
}

// Her Python islevi icin: kac anlamli (bos olmayan) cikti ve kac ret karsilastirildi
const kapsam = new Map();
function say(fn, tur) {
  const s = kapsam.get(fn) ?? { cikti: 0, hata: 0 };
  s[tur] += 1;
  kapsam.set(fn, s);
}
function anlamli(py) {
  if (py === null) return false;
  if (Array.isArray(py)) {
    if (py.length === 0) return false;
    if (py.length === 2 && Array.isArray(py[0]) && typeof py[1] === "number") return py[0].length > 0;
    return true;
  }
  if (py && typeof py === "object" && "$map" in py) return py.$map.length > 0;
  return true;
}
function esit(fn, js, py, ne) {
  assert.deepStrictEqual(jsonla(js), py, `${fn}: ${ne}`);
  if (anlamli(py)) say(fn, "cikti");
}
const COZUCU = /(_coz|^akis_|^oturumlari_kur$)/;
function ret(fn, cagri, py, ne) {
  // Python'un cozuculerdeki struct.error / ValueError'u -> KayitHatasi; paketleyici / birim -> RangeError
  const sinif = COZUCU.test(fn) ? K.KayitHatasi : RangeError;
  assert.throws(cagri, (e) => e instanceof sinif && (py.mesaj === undefined || e.message === py.mesaj),
    `${fn}: ${ne} — Python ${py.hata} verdi, JS ${sinif.name} firlatmali`);
  say(fn, "hata");
}

// ── API ve sabitler ─────────────────────────────────────────────────
test("api: her Python islevinin JS karsiligi var, fazlasi yok", () => {
  for (const ad of V.api) assert.equal(typeof K[deve(ad)], "function", `${ad} -> ${deve(ad)} yok`);
  const beklenen = new Set(V.api.map(deve));
  const fazla = Object.entries(K)
    .filter(([ad, f]) => typeof f === "function" && ad !== "KayitHatasi" && !beklenen.has(ad))
    .map(([ad]) => ad);
  assert.deepEqual(fazla, [], "Python'da karsiligi olmayan JS islevi (eslemeyi guncelle)");
});

test("sabitler Python'la ayni (SEBEP Map olarak)", () => {
  for (const [ad, py] of Object.entries(V.sabitler)) {
    assert.ok(ad in K, `sabit ${ad} JS'de yok`);
    assert.deepStrictEqual(jsonla(K[ad]), py, ad);
  }
  const fazla = Object.keys(K).filter((ad) => /^[A-Z][A-Z0-9_]*$/.test(ad) && !(ad in V.sabitler));
  assert.deepEqual(fazla, [], "Python'da olmayan JS sabiti");
});

// ── capraz vektorler ────────────────────────────────────────────────
test("crc vektorleri", () => {
  for (const v of V.crc) esit("crc", K.crc(jsden(v.veri), v.onceki), v.cikti, hex(jsden(v.veri)));
});

test("toplam_bayt vektorleri", () => {
  for (const [n, c] of V.toplam_bayt) esit("toplam_bayt", K.toplamBayt(n), c, String(n));
});

for (const a of V.akislar) {
  test(`akis: ${a.ad}`, () => {
    const veri = jsden(a.veri);
    esit("akis_onek", K.akisOnek(veri), a.akis_onek, a.ad);
    if (Array.isArray(a.akis_coz)) esit("akis_coz", K.akisCoz(veri), a.akis_coz, a.ad);
    else ret("akis_coz", () => K.akisCoz(veri), a.akis_coz, a.ad);
    const [kayitlar] = K.akisOnek(veri);
    if (a.oturumlari_kur.hata) {
      ret("oturumlari_kur", () => K.oturumlariKur(kayitlar), a.oturumlari_kur, a.ad);
      return;
    }
    const ot = K.oturumlariKur(kayitlar);
    esit("oturumlari_kur", ot, a.oturumlari_kur, a.ad);
    // S5: atlanan kisa kayitlar (vektorde yalniz doluysa var)
    esit("oturumlari_kur", ot.uyarilar, a.oturumlari_kur_uyarilar ?? [], `${a.ad} uyarilar`);
    for (const [id, py] of a.ayrinti_ornekler) {
      esit("ayrinti_ornekler", K.ayrintiOrnekler(ot.get(id)), py, `${a.ad} oturum ${id}`);
    }
    for (const [id, sira, py] of a.skop_ikili) {
      esit("skop_ikili", K.skopIkili(ot.get(id).skoplar.get(sira)), py, `${a.ad} ${id}/${sira}`);
    }
    // W1: yakalamanin yeri (Y7) ve hizali guc (bit bit)
    for (const [id, py] of a.skop_yerleri) {
      esit("skop_yerleri", K.skopYerleri(ot.get(id)), py, `${a.ad} oturum ${id}`);
    }
    for (const [id, py] of a.ayrinti_guc) {
      esit("ayrinti_guc", K.ayrintiGuc(ot.get(id)), py, `${a.ad} oturum ${id}`);
    }
  });
}

for (const f of V.flaslar) {
  test(`flas: ${f.ad}`, () => {
    const veri = jsden(f.veri);
    if (f.flas_coz.hata) {
      ret("flas_coz", () => K.flasCoz(veri, f.sektor), f.flas_coz, f.ad);
      return;
    }
    esit("flas_coz", K.flasCoz(veri, f.sektor), f.flas_coz, f.ad);
    const [kayitlar] = K.flasCoz(veri, f.sektor);
    if (f.oturumlari_kur.hata) ret("oturumlari_kur", () => K.oturumlariKur(kayitlar), f.oturumlari_kur, f.ad);
    else {
      const ot = K.oturumlariKur(kayitlar);
      esit("oturumlari_kur", ot, f.oturumlari_kur, f.ad);
      esit("oturumlari_kur", ot.uyarilar, f.oturumlari_kur_uyarilar ?? [], `${f.ad} uyarilar`);
    }
  });
}

const vakaFn = [...new Set(V.vakalar.map((v) => v.fn))];
for (const fn of vakaFn) {
  test(`vakalar: ${fn}`, () => {
    const f = K[deve(fn)];
    V.vakalar.filter((v) => v.fn === fn).forEach((v, i) => {
      const arg = jsden(v.arg);
      if (v.hata) ret(fn, () => f(...arg), v, `vaka ${i}`);
      else esit(fn, f(...arg), v.cikti, `vaka ${i}`);
    });
  });
}

test("birimler: volt / amper", () => {
  const kallar = jsden(V.birim_kallar);
  V.birimler.forEach((v, i) => {
    const k = v.kanal ? kallar[v.kal][v.kanal] : kallar[v.kal];
    const cagri = () => K[v.fn](jsden(v.kod), k, v.tamsayi);
    if (v.hata) ret(v.fn, cagri, v, `vaka ${i}`);
    else esit(v.fn, cagri(), v.cikti, `vaka ${i} kod ${JSON.stringify(v.kod)} tamsayi ${v.tamsayi}`);
  });
});

test("unix_zaman", () => {
  for (const [s, iso] of V.unix_zaman) {
    const d = K.unixZaman(s);
    if (iso === null) assert.equal(d, null);
    else {
      assert.equal(d.getTime(), Date.parse(iso), String(s));
      say("unix_zaman", "cikti");
    }
  }
});

// ── kapsam bekcisi: sessizce sinanmayan cozucu kalmasin ─────────────
test("kapsam: her Python islevi en az bir anlamli vektorle karsilastirildi", () => {
  const eksik = V.api.filter((ad) => !(kapsam.get(ad)?.cikti > 0));
  assert.deepEqual(eksik, [], "vektoru olmayan (ya da hep bos cikti veren) islev");
  // Python'un REDDETTIGI girdiyi JS de reddediyor mu: her *_coz icin en az bir ret
  const retsiz = V.api.filter((ad) => /_coz$/.test(ad) && !(kapsam.get(ad)?.hata > 0) && ad !== "flas_coz");
  assert.deepEqual(retsiz, [], "ret vakasi olmayan cozucu");
});

test("kapsam: her kayit turu, olay turu, NOT alani, bicim surumu, oturum turu vektorlerde", () => {
  const turler = new Set();
  const olaylar = new Set();
  const alanlar = new Set();
  const bicim = new Set();
  const oturumTur = new Set();
  for (const a of V.akislar) {
    const [kayitlar] = K.akisOnek(jsden(a.veri));
    for (const k of kayitlar) {
      turler.add(k.tur);
      try {
        if (k.tur === K.T_OLAY) olaylar.add(K.olayCoz(k.yuk).tur);
        if (k.tur === K.T_NOT) alanlar.add(K.notCoz(k.yuk).alan);
        if (k.tur === K.T_BASLA || k.tur === K.T_TEKRAR) {
          const b = K.baslaCoz(k.yuk);
          bicim.add(b.bicim_surum);
          oturumTur.add(b.oturum_turu);
        }
      } catch (e) {
        if (!(e instanceof K.KayitHatasi)) throw e;
      }
    }
  }
  const ad = (on) => Object.entries(K).filter(([n]) => n.startsWith(on)).map(([, v]) => v);
  for (const t of ad("T_")) assert.ok(turler.has(t), `kayit turu ${t} hicbir akista yok`);
  for (const t of ad("KO_")) assert.ok(olaylar.has(t), `olay turu ${t} yok`);
  for (const t of ad("KNT_")) assert.ok(alanlar.has(t), `NOT alani ${t} yok`);
  for (const t of ad("OTURUM_")) assert.ok(oturumTur.has(t), `oturum turu ${t} yok`);
  assert.ok(bicim.has(1) && bicim.has(2), "BASLA bicim surum 1 ve 2");
  assert.ok([...turler].some((t) => !ad("T_").includes(t)), "bilinmeyen kayit turu da var");
});

// ── dogrudan birim testleri ─────────────────────────────────────────
const yazi = (s) => new TextEncoder().encode(s);

test("crc: bilinen deger ve zincirleme", () => {
  assert.equal(K.crc(yazi("123456789")), 0xCBF43926);
  assert.equal(K.crc(new Uint8Array(0)), 0);
  const a = yazi("olcum");
  const b = yazi("karti");
  const ab = new Uint8Array([...a, ...b]);
  assert.equal(K.crc(b, K.crc(a)), K.crc(ab));
});

test("toplamBayt: baslik + yuk, 4'un katina", () => {
  assert.deepEqual([0, 1, 3, 4, 5, 102].map(K.toplamBayt), [16, 20, 20, 20, 24, 120]);
});

test("kayitPaketle -> akisCoz gidis-donus; bilinmeyen tur gecerli", () => {
  const y = Uint8Array.from([1, 2, 3, 4, 5]);
  const b = K.kayitPaketle(42, 7, 9, y);
  assert.equal(b.length, 24);
  assert.equal(b[0], K.IMZA);
  const [k] = K.akisCoz(b);
  assert.deepEqual({ ...k, yuk: [...k.yuk] }, { tur: 42, sira: 7, oturum: 9, yuk: [1, 2, 3, 4, 5], adres: 0 });
  // ArrayBuffer ve DataView girdisi de kabul
  assert.equal(K.akisCoz(b.slice().buffer).length, 1);
  assert.equal(K.akisCoz(new DataView(b.slice().buffer)).length, 1);
});

function akis(...parcalar) {
  return Uint8Array.from(parcalar.flatMap((p) => [...p]));
}
const devamYuk = (a, u, k, n) => {
  const b = new Uint8Array(16);
  const v = new DataView(b.buffer);
  [a, u, k, n].forEach((x, i) => v.setUint32(4 * i, x, true));
  return b;
};

test("bozuk CRC / kesik kuyruk / FF: akisOnek on eki verir, akisCoz KayitHatasi firlatir", () => {
  const k1 = K.kayitPaketle(K.T_DEVAM, 1, 1, devamYuk(1, 2, 3, 4));
  const k2 = K.kayitPaketle(K.T_DEVAM, 2, 1, devamYuk(5, 6, 7, 8));
  const bozuk = k2.slice();
  bozuk[20] ^= 1;
  for (const [ad, veri] of [["crc", akis(k1, bozuk, k1)], ["kesik", akis(k1, k2.subarray(0, 30))],
    ["ff", akis(k1, new Uint8Array(16).fill(0xFF))],
    ["tur0", akis(k1, K.kayitPaketle(0, 3, 1, new Uint8Array(0)))]]) {
    const [kayitlar, n] = K.akisOnek(veri);
    assert.equal(kayitlar.length, 1, ad);
    assert.equal(n, 32, ad);
    assert.throws(() => K.akisCoz(veri), (e) => e instanceof K.KayitHatasi && e.message === "32. baytta gecersiz kayit", ad);
  }
});

test("akisOnek ve sektor katli flasCoz rastgele copte ASLA firlatmaz", () => {
  let s = 0x2A2A2A2A;
  const rnd = () => ((s = (Math.imul(s, 1103515245) + 12345) >>> 0) >>> 16) & 0xFF;
  const gecerli = akis(K.kayitPaketle(K.T_DEVAM, 1, 1, devamYuk(1, 2, 3, 4)),
    K.kayitPaketle(K.T_BITIR, 2, 1, new Uint8Array(8)));
  for (let i = 0; i < 300; i++) {
    const n = 16 * (1 + (rnd() % 16));
    const b = Uint8Array.from({ length: n }, rnd);
    if (i % 3 === 0) b.set(gecerli.subarray(0, Math.min(n, gecerli.length)));
    if (i % 5 === 0) b[rnd() % n] ^= 1 << (rnd() % 8);
    const [k, a] = K.akisOnek(b);
    assert.ok(a <= b.length && k.every((x) => x.adres < a));
    K.flasCoz(b, 16);
    K.flasCoz(b, n);
  }
});

test("flasCoz: sektor 0 RangeError, negatif sektor bos (Python range)", () => {
  assert.throws(() => K.flasCoz(new Uint8Array(32), 0), RangeError);
  assert.deepEqual(K.flasCoz(new Uint8Array(32), -16), [[], 0]);
});

test("volt / amper: bilinen sayilar, int16 kirpmasi yalniz tamsayi kodda", () => {
  const k = { n: 1, pga: 32768, kazanc: 1, sifir_ham: -10, tau: 0 };
  assert.equal(K.volt(-10, k, true), 0);
  assert.equal(K.volt(32767, k, true), 32767);          // 32777 -> int16 kirpmasi
  assert.equal(K.volt(32767, k, false), 32777);         // doymus float ortalama: kirpma YOK
  assert.equal(K.volt(-32768, { ...k, sifir_ham: 10 }, true), -32768);
  const k2 = { n: 21, pga: 4.096, kazanc: 1, sifir_ham: 0, tau: 0 };
  assert.ok(Math.abs(K.volt(8000, k2, true) - 21.0) < 1e-12);
  const kal = { i_ofset: 5, i_pga: 0.256, sont_ohm: 0.005, i_duzeltme: 1 };
  assert.ok(Math.abs(K.amper(5 + 6400, kal, true) - 10.0) < 1e-12);   // 6400 x 7.8125 uV / 5 mOhm
  assert.equal(Object.is(K.volt(-10, { ...k, n: -1 }, true), -0), true);
  // S6: sont_ohm 0 / -0 -> NaN (akim bilinmiyor), firlatmaz
  for (const so of [0, -0]) {
    for (const [kod, ts] of [[1, true], [5, true], [1.5, false], [-40000, true]]) {
      assert.ok(Number.isNaN(K.amper(kod, { ...kal, sont_ohm: so }, ts)), `sont ${Object.is(so, -0) ? "-0" : so} kod ${kod}`);
    }
  }
  assert.throws(() => K.amper(1, { ...kal, sont_ohm: 0 }), TypeError);   // tamsayi yine zorunlu
  assert.throws(() => K.volt(1, k), TypeError);         // tamsayi zorunlu
  assert.throws(() => K.volt(1.5, k, true), TypeError);
});

test("oturumlariKur: iki ic ice oturum, NOT, DEVAM, Y5 tekrari, sira karisik", () => {
  const nokta = (ms) => K.noktaPaketle({ kart_ms: ms, n: 1, bayrak: 0, v_ort_kod: 1.5, v_min_kod: -1,
    v_maks_kod: 2, i_ort_kod: 0.25, i_min_kod: 0, i_maks_kod: 1, w_ort: 0.5, w_min: 0, w_maks: 1 });
  const noktaYuk = (ilk, ...ms) => {
    const b = new Uint8Array(4);
    new DataView(b.buffer).setUint32(0, ilk, true);
    return akis(b, ...ms.map(nokta));
  };
  const kanal = { n: 21, pga: 4.096, kazanc: 1, sifir_ham: 3, tau: 0.1 };
  const basla = (tur, hiz) => K.baslaPaketle({ oturum_turu: tur, kal_bicim: 1, hiz_ms: hiz, unix_s: 0,
    kart_ms: 5, acilis: 1, surum: "A3-test", kal_no: 2,
    kal: { normal: kanal, yuksek: kanal, i_ofset: 0, i_pga: 0.256, sont_ohm: 0.005, i_duzeltme: 1,
      sebeke_hz: 50, faz_kal_us: [0, 0] } });
  const not = (hedef, alan, ms, dg, m) => K.notPaketle(hedef, alan, ms, dg, yazi(m));
  const veri = akis(
    K.kayitPaketle(K.T_NOKTA, 6, 2, noktaYuk(0, 10)),
    K.kayitPaketle(K.T_BASLA, 1, 1, basla(K.OTURUM_OLCUM, 100)),
    K.kayitPaketle(K.T_BASLA, 2, 2, basla(K.OTURUM_PIL, 1000)),
    K.kayitPaketle(K.T_NOKTA, 3, 1, noktaYuk(0, 1, 2)),
    K.kayitPaketle(K.T_NOKTA, 4, 1, noktaYuk(1, 99, 3)),          // 1 tekrar: ilki kalir
    K.kayitPaketle(K.T_NOT, 5, 0, not(2, K.KNT_AD, 0, 0, "pil")),
    K.kayitPaketle(K.T_NOT, 7, 0, not(1, K.KNT_NOT, 40, 0, "not")),
    K.kayitPaketle(K.T_NOT, 8, 0, not(1, K.KNT_NOT, 0, 7, "duzeltildi")),
    K.kayitPaketle(K.T_NOT, 9, 0, not(1, K.KNT_ETIKET, 0, 0, " a ,\u0085b\u0085,,")),
    K.kayitPaketle(K.T_DEVAM, 10, 1, devamYuk(2, 0, 0, 3)),
    K.kayitPaketle(K.T_BITIR, 11, 2, Uint8Array.from([1, 0, 0, 0, 4, 0, 0, 0])),
  );
  const ot = K.oturumlariKur(K.akisCoz(veri));
  assert.deepEqual([...ot.keys()], [1, 2]);
  const o1 = ot.get(1);
  const o2 = ot.get(2);
  assert.equal(o1.basla.hiz_ms, 100);
  assert.equal(o1.basla.kal_no, 2);
  assert.equal(o1.basi_eksik, false);
  assert.deepEqual(o1.noktalar.map(([s, p]) => [s, p.kart_ms]), [[0, 1], [1, 2], [2, 3]]);
  assert.deepEqual(o1.devamlar, [{ acilis: 2, unix_s: 0, kart_ms: 0, nokta_sira: 3 }]);
  assert.deepEqual([...o1.notlar], [[7, { nokta_ms: 40, metin: "duzeltildi" }]]);
  assert.deepEqual(o1.etiketler, ["a", "b"]);
  assert.equal(o2.ad, "pil");
  assert.equal(o2.basla.oturum_turu, K.OTURUM_PIL);
  assert.deepEqual(o2.noktalar.map(([s]) => s), [0]);
  assert.deepEqual(o2.bitir, { nokta_adedi: 1, sebep: 4 });
  assert.equal(K.SEBEP.get(o2.bitir.sebep), "pil testi bitti");
});

test("ayrintiOrnekler: esit uzaklikta Python round (cifte), Math.round degil", () => {
  const y = K.ayrintiPaketle({ ilk: 0, t0_ms: 2147484, t0_us: 352, bayrak: 0, ornekler: [[1, 2, 1, 3]] });
  const o = { devamlar: [], ayrinti: [{ ...K.ayrintiCoz(y), sira: 1 }] };
  assert.deepEqual(K.ayrintiOrnekler(o), [[0, 352 + 4, 1, 2, 3, 0]]);   // k = round(0.5) = 0
});

test("W1 inceleme: ayrintiOrnekler(o, true) sira ile sirali; ayrintiGuc {orn, dizi} ve skopYerleri(o, orn) ayni sonuc", () => {
  let denenen = 0;
  let skoplu = 0;
  for (const a of V.akislar) {
    if (a.oturumlari_kur.hata) continue;
    for (const o of K.oturumlariKur(K.akisOnek(jsden(a.veri))[0]).values()) {
      if (o.ayrinti.length < 2) continue;
      // kayit sirasini ters cevir: ornekler ayrintiOrnekler'den sira DISI cikar
      const n = o.ayrinti.length;
      const ters = { ...o, ayrinti: o.ayrinti.map((r, k) => ({ ...r, sira: o.ayrinti[n - 1 - k].sira })) };
      const ham = K.ayrintiOrnekler(ters).map((r) => r[0]);
      // ortusen kayit (Y5) varsa ters sira hangi kopyanin kalacagini degistirir: karsilastirilamaz
      if (o.ayrinti.reduce((t, r) => t + r.ornekler.length, 0) !== ham.length) continue;
      if (ham.every((s, k) => !k || ham[k - 1] < s)) continue;
      denenen++;
      const orn = K.ayrintiOrnekler(ters, true);
      assert.deepEqual(orn.map((r) => r[0]), [...ham].sort((x, y) => x - y), `${a.ad}: sira ile sirali degil`);
      const cift = K.ayrintiGuc(ters);
      assert.deepEqual(cift, K.ayrintiGuc(o), `${a.ad}: guc kayit sirasina bagli`);
      assert.deepEqual(Array.from(K.ayrintiGuc(ters, { orn, dizi: true })), cift.map(([, w]) => w));
      assert.ok(K.ayrintiGuc(ters, { orn, dizi: true }) instanceof Float64Array);
      if (o.skoplar.size) {
        skoplu++;
        assert.deepEqual(K.skopYerleri(ters, orn), K.skopYerleri(o), `${a.ad}: skopYerleri orn ile farkli`);
      }
    }
  }
  assert.ok(denenen >= 2 && skoplu >= 1, `denenen ${denenen}, skoplu ${skoplu}: test bos`);
});

test("skopIkili: eksik yakalama null, tam yakalama S3B basligi", () => {
  assert.equal(K.skopIkili({ tam: false, kodlar: null }), null);
  const meta = { hz: 1000, adim: 0.5, ofset: -1, tdiv_us: 100, tetik: 70000, kip: 0x1FF, tetiklendi: 2 };
  const b = K.skopIkili({ tam: true, no: 2 ** 32 + 5, meta, kodlar: [1, 65535] });
  assert.equal(b.length, 36);
  assert.deepEqual([...b.subarray(0, 4)], [0x53, 0x33, 0x42, 1]);
  const v = new DataView(b.buffer);
  assert.deepEqual([v.getUint16(4, true), v.getUint16(24, true), b[26], b[27], v.getUint32(28, true)],
    [2, 0xFFFF, 0xFF, 1, 5]);
});

// ── S5 / S6 saglamlik: kural kural, vektorden BAGIMSIZ ──────────────────
// (vektorler JS == Python der; Python ile JS AYNI hatayi yapsa da yesil kalirdi)
const EN_AZ_BAGIMSIZ = [[K.T_BASLA, 98], [K.T_TEKRAR, 98], [K.T_NOKTA, 4], [K.T_DEVAM, 16],
  [K.T_BITIR, 8], [K.T_SAAT, 12], [K.T_OLAY, 8], [K.T_NOT, 16], [K.T_AYRINTI, 16], [K.T_SKOP, 12]];
const kyt = (tur, sira, oturum, yuk) => ({ tur, sira, oturum, yuk, adres: null });
const kuyruk = (y, n) => akis(y, Uint8Array.from({ length: n }, (_, i) => (0x5A + 7 * i) & 0xFF));
const KANAL_T = { n: 21, pga: 4.096, kazanc: 1, sifir_ham: 3, tau: 0.1 };
const KAL_T = { normal: KANAL_T, yuksek: KANAL_T, i_ofset: 0, i_pga: 0.256, sont_ohm: 0.005, i_duzeltme: 1,
  sebeke_hz: 50, faz_kal_us: [0, 0] };
const baslaT = K.baslaPaketle({ oturum_turu: K.OTURUM_OLCUM, kal_bicim: 1, hiz_ms: 100, unix_s: 0,
  kart_ms: 5, acilis: 1, surum: "A3-test", kal_no: 2, kal: KAL_T });
const baslaV1 = (() => {
  const b = baslaT.slice(0, K.BASLA_V1_BAYT);
  b[2] = 1;
  return b;
})();
const noktaT = (ms) => K.noktaPaketle({ kart_ms: ms, n: 1, bayrak: 0, v_ort_kod: 1.5, v_min_kod: -1,
  v_maks_kod: 2, i_ort_kod: 0.25, i_min_kod: 0, i_maks_kod: 1, w_ort: 0.5, w_min: 0, w_maks: 1 });
const metaT = { t_ms: 1, sure_ms: 2, hz: 1000, tdiv_us: 100, adim: 0.5, ofset: -1, tetik: 3, esik: 4,
  histerezis: 5, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 10, onay: 2 };

test("S5: her sabit boylu tur bilinen boydan UZUNSA on eki cozulur, uyari yok", () => {
  const tam = [
    [K.T_BASLA, baslaT, [1, 3, 4, 35]], [K.T_BASLA, baslaV1, [1, 3]],     // 102 B'tan itibaren surum 2
    [K.T_TEKRAR, baslaT, [1, 3, 4, 35]], [K.T_TEKRAR, baslaV1, [1, 3]],
    [K.T_NOKTA, akis(new Uint8Array(4), noktaT(1), noktaT(2)), [1, 3, 35]],   // 36 B = yeni nokta
    [K.T_DEVAM, devamYuk(2, 3, 4, 5), [1, 3, 4, 35]],
    [K.T_BITIR, Uint8Array.from([6, 0, 0, 0, 1, 0, 0, 0]), [1, 3, 4, 35]],
    [K.T_SAAT, new Uint8Array(12).fill(7), [1, 3, 4, 35]],
    [K.T_OLAY, K.olayPaketle({ tur: K.KO_PLAN, kart_ms: 10, bas_unix: 1, sure_s: 2, hiz_ms: 3, plan_no: 4 }), [1, 4, 35]],
    [K.T_OLAY, K.olayPaketle({ tur: K.KO_SKOP_KAL, kart_ms: 11, mv: Array.from({ length: 17 }, (_, i) => i - 8) }), [1, 35]],
    [K.T_AYRINTI, K.ayrintiPaketle({ ilk: 0, t0_ms: 1, t0_us: 1000, bayrak: 0, ornekler: [[1, 2, 3, 0], [4, 5, 6, 1]] }), [1, 5, 6, 35]],
    [K.T_SKOP, K.skopPaketle({ no: 1, ilk: 0, toplam: 4, parca: 0, meta: metaT, kodlar: [1, 2, 3, 4] }), [1, 3, 35]],
    [K.T_SKOP, K.skopPaketle({ no: 1, ilk: 4, toplam: 8, parca: 1, meta: null, kodlar: [5, 6] }), [1, 2, 35]],
  ];
  for (const [tur, y, ekler] of tam) {
    const a = K.oturumlariKur([kyt(tur, 1, 9, y)]);
    assert.deepEqual([...a.keys()], [9], `tur ${tur}`);
    for (const ek of ekler) {
      const b = K.oturumlariKur([kyt(tur, 1, 9, kuyruk(y, ek))]);
      assert.deepStrictEqual(jsonla(b), jsonla(a), `tur ${tur} +${ek} B: on ek ayni cozulmeli`);
      assert.deepEqual(b.uyarilar, [], `tur ${tur} +${ek} B: uyari olmamali`);
    }
  }
  // dogrudan cozuculer de on eki cozer
  assert.deepEqual(K.devamCoz(kuyruk(devamYuk(1, 2, 3, 4), 8)), { acilis: 1, unix_s: 2, kart_ms: 3, nokta_sira: 4 });
  assert.deepEqual(K.bitirCoz(kuyruk(Uint8Array.from([9, 0, 0, 0, 2, 0, 0, 0]), 1)), { nokta_adedi: 9, sebep: 2 });
  assert.deepEqual(K.saatCoz(kuyruk(Uint8Array.from([1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0]), 4)),
    { unix_s: 1, kart_ms: 2, acilis: 3 });
});

test("S5: en kisa boydan KISA kayit atlanir, oturum ACMAZ, uyari (sira/tur/oturum/bayt/en_az); firlatmaz", () => {
  for (const [tur, n] of EN_AZ_BAGIMSIZ) {
    for (const m of new Set([0, n - 1])) {
      const ot = K.oturumlariKur([kyt(tur, 5, 9, new Uint8Array(m).fill(0x33)),
        kyt(K.T_DEVAM, 6, 3, devamYuk(1, 2, 3, 4))]);
      assert.deepEqual([...ot.keys()], [3], `tur ${tur} ${m} B: oturum 9 acilmamali`);
      assert.deepEqual(ot.uyarilar, [{ sira: 5, tur, oturum: 9, bayt: m, en_az: n }], `tur ${tur} ${m} B`);
    }
    assert.deepEqual(K.oturumlariKur([kyt(tur, 5, 9, new Uint8Array(n))]).uyarilar, [], `tur ${tur} tam ${n} B`);
  }
  // baslik oturumu 0 olan kisa kayit da uyarir; uyarilar KAYIT SIRASIYLA
  const ot = K.oturumlariKur([kyt(K.T_NOT, 8, 0, new Uint8Array(15)), kyt(K.T_SAAT, 7, 0, new Uint8Array(11))]);
  assert.deepEqual(ot.uyarilar.map((u) => [u.sira, u.tur]), [[7, K.T_SAAT], [8, K.T_NOT]]);
  assert.equal(ot.size, 0);
});

test("S5: uyarilar SAYILAMAZ ozellik — Map'in kendisi ve karsilastirmasi degismez", () => {
  const ot = K.oturumlariKur([]);
  assert.ok(ot instanceof Map && Array.isArray(ot.uyarilar));
  assert.deepStrictEqual(ot, new Map());
  assert.deepEqual(Object.keys(ot), []);
});

test("S6: oturum numarali bilinmeyen tur oturum ACMAZ, oturum sirasini etkilemez, uyarmaz", () => {
  const ot = K.oturumlariKur([kyt(77, 1, 50, Uint8Array.of(1, 2, 3)), kyt(K.T_DEVAM, 2, 51, devamYuk(0, 0, 0, 0)),
    kyt(K.T_DEVAM, 3, 50, devamYuk(0, 0, 0, 0)), kyt(200, 4, 52, new Uint8Array(0))]);
  assert.deepEqual([...ot.keys()], [51, 50]);
  assert.deepEqual(ot.uyarilar, []);
});

test("S6: flasCoz her uzunlukta kesilen goruntude firlatmaz; tam kayitlar aynen, yarim kayit bozuk, < 16 B kuyruk bos", () => {
  const S = 112;                                  // 3 kayit (96 B) + 16 B silinmis
  const parcalar = [];
  for (let s = 0; s < 2; s++) {
    const sek = akis(K.kayitPaketle(K.T_DEVAM, 10 * s + 1, 1, devamYuk(1, 0, 0, 0)),
      K.kayitPaketle(K.T_DEVAM, 10 * s + 2, 1, devamYuk(2, 0, 0, 0)),
      K.kayitPaketle(K.T_SAAT, 10 * s + 3, 1, new Uint8Array(13)));
    parcalar.push(sek, new Uint8Array(S - sek.length).fill(0xFF));
  }
  const img = akis(...parcalar);
  const [tum, bz0] = K.flasCoz(img, S);
  assert.equal(bz0, 0);
  assert.equal(tum.length, 6);
  for (let L = 0; L <= img.length; L++) {
    const [kay, bz] = K.flasCoz(img.subarray(0, L), S);
    const son = (k) => k.adres + K.toplamBayt(k.yuk.length);
    const bek = tum.filter((k) => son(k) <= L).map((k) => k.sira);
    const yarim = tum.some((k) => k.adres + 16 <= L && L < son(k));
    assert.deepEqual(kay.map((k) => k.sira), bek, `L ${L}`);
    assert.equal(bz, yarim ? 1 : 0, `L ${L} bozuk`);
  }
  // sektor sinirsiz rastgele boy (sektor kati DEGIL) + cop kuyruk: firlatmaz
  let s = 0x5EED;
  const rnd = () => ((s = (Math.imul(s, 1103515245) + 12345) >>> 0) >>> 16) & 0xFF;
  for (let i = 0; i < 300; i++) {
    const n = 1 + (rnd() * 3 + rnd()) % 300;
    const b = Uint8Array.from({ length: n }, rnd);
    if (i % 2) b.set(img.subarray(0, Math.min(n, img.length)));    // gecerli kayitla baslayan
    K.flasCoz(b, 16);
    K.flasCoz(b, 64);
    K.flasCoz(b, S);
  }
});

test("kapsam S5/S6: hicbir vektor cokme degil; her bilinen tur icin kisa-kayit uyarisi; uzun kayit akisi uyarisiz", () => {
  assert.deepEqual(V.akislar.filter((a) => a.oturumlari_kur.hata).map((a) => a.ad), [],
    "oturumlari_kur gecerli CRC'li akista cokmemeli (S5)");
  assert.deepEqual(V.flaslar.filter((f) => f.flas_coz.hata || f.oturumlari_kur?.hata).map((f) => f.ad), [],
    "flas_coz / oturumlari_kur hicbir goruntude cokmemeli (S6)");
  const turler = new Set(V.akislar.flatMap((a) => (a.oturumlari_kur_uyarilar ?? []).map((u) => u.tur)));
  for (const [tur] of EN_AZ_BAGIMSIZ) assert.ok(turler.has(tur), `tur ${tur} icin kisa-kayit uyarisi vektoru yok`);
  const uzun = V.akislar.find((a) => a.ad === "uzun_kayitlar");
  assert.ok(uzun && !uzun.oturumlari_kur_uyarilar && uzun.oturumlari_kur.$map.map(([i]) => i).join() === "60,61,62");
  const kuyruklu = V.flaslar.filter((f) => f.ad.startsWith("flas_kuyruk") && jsden(f.veri).length % f.sektor !== 0);
  assert.ok(kuyruklu.length >= 4, "tam sektor olmayan flas goruntusu vektoru az");
  assert.ok(V.birimler.some((v) => v.fn === "amper" && V.birim_kallar[v.kal].sont_ohm === 0
    && v.cikti?.$f === "nan"), "sont_ohm 0 -> NaN vektoru yok");
});
