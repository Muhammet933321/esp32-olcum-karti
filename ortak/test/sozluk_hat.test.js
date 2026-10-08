// B73 (HT5, 2026-10-08) — ortak/src/sozluk_hat.js: hat direnci duzelticisinin metinleri + saf hesaplari (elle giris,
// multimetre girisi, R onerisi, pil kutuplari gerilimi) + ekran/pil_hat.js PilHat'in gosterdigi metinler (hatGorunum) ve
// gonderim akisi (hatIslem; sahte $root ile). sozluk_pil.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer
// tutucu, ayrik, kullanilmayan yok) + YERLESIM: ht. anahtarlarini YALNIZ bu dosyanin hesabi kullanir; dosyayi YALNIZ
// ekran/pil_hat.js STATIK indirir (o da ekran/pil.js'ten DINAMIK iner); app.js, acilis sozlugu, sozluk_pil istemez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC } from "../src/sozluk_pc.js";
import { SOZLUK_KAYIT } from "../src/sozluk_kayit.js";
import { SOZLUK_AY } from "../src/sozluk_ay.js";
import { SOZLUK_IMLEC } from "../src/sozluk_imlec.js";
import { SOZLUK_PIL } from "../src/sozluk_pil.js";
import { pilVDuzelt } from "../src/kayit.js";
import * as H from "../src/sozluk_hat.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^ht\.[a-z0-9_]+$/;
const DOSYA = "sozluk_hat.js";
const PIL_H = existsSync(new URL("../../kod/olcum-karti-a3/pil_test.h", import.meta.url)) ? oku("../../kod/olcum-karti-a3/pil_test.h") : "";

test("ht.: her anahtar ht. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(H.SOZLUK_HAT);
  assert.ok(anahtarlar.length >= 15, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(H.SOZLUK_HAT));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(H.SOZLUK_HAT[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof H.SOZLUK_HAT[a][d] === "string" && H.SOZLUK_HAT[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(H.SOZLUK_HAT[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("ht.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(H.SOZLUK_HAT)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC, SOZLUK_PIL];
  assert.deepEqual(Object.keys(H.SOZLUK_HAT).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "ht. ailesi baska sozlukte");
});

test("ht.: HER anahtari YALNIZ bu dosyanin hesabi kullanir; kullanilmayan yok; dosyayi yalniz ekran/pil_hat.js indirir", () => {
  const kendi = oku(`../src/${DOSYA}`);
  const kod = kendi.slice(kendi.indexOf("// ── hesap"));
  const kullanilan = new Set([...kod.matchAll(/['"](ht\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  assert.deepEqual(Object.keys(H.SOZLUK_HAT).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan ht. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in H.SOZLUK_HAT)), [], "kullanilip sozlukte olmayan ht. anahtari");
  const baska = [];
  for (const y of [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
  }
  assert.deepEqual(baska, []);
  assert.equal(/['"]ht\.[a-z0-9_]+['"]/.test(HTML), false, "index.html ht. anahtari yazmaz");
  const ithal = [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_hat/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), EKRANLAR.length ? ["pil_hat.js"] : []);
  if (EKRANLAR.length) {
    assert.match(yorumsuz(oku("../../arayuz3/ekran/pil_hat.js")), /from '\/ortak\/sozluk_hat\.js'/);
    assert.match(yorumsuz(oku("../../arayuz3/ekran/pil.js")), /import\('\.\/pil_hat\.js'\)/);
    assert.doesNotMatch(yorumsuz(oku("../../arayuz3/ekran/pil.js")), /from '\.\/pil_hat\.js'/);
  }
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_hat/);
});

test("ceviriHat: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(H.ceviriHat("ht.yaz", "en"), "Set");
  assert.equal(H.ceviriHat("ht.yaz"), "Ayarla");
  assert.equal(H.ceviriHat("ht.onay", "tr", { n: 80 }), "Kart onayladı: hat direnci 80 mΩ.");
  assert.equal(H.ceviriHat("ht.yok_boyle", "en"), "ht.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => H.ceviriHat(a, "tr"));
    assert.equal(typeof H.ceviriHat(a, "en"), "string");
  }
});

// ── hesap ────────────────────────────────────────────────────────────────────
test("HT1: azami 1000 mΩ pil_test.h ile ayni; elle giris kartin pil_ph_ayir kurali", () => {
  if (PIL_H) assert.equal(H.PIL_HAT_AZAMI_MOHM, Number((/#define PIL_HAT_AZAMI_MOHM\s+(\d+)u/.exec(PIL_H) || [])[1]));
  for (const [x, n] of [["0", 0], ["1", 1], ["85", 85], [" 999 ", 999], ["1000", 1000], [7, 7]]) assert.deepEqual(H.hatGiris(x), { mohm: n }, String(x));
  for (const x of ["1001", "050", "00", "-1", "8.5", "1e2", "85 m", "", " ", null, undefined, {}, [], "10000", 1001]) {
    assert.deepEqual(H.hatGiris(x), { hata: "ht.hata_giris" }, String(x));
  }
});

test("HT2: hatDuzelt kayit.js pilVDuzelt (Python pil_v_duzelt) ile BIT BIT ayni; R <= 0 iken HAM aynen (I NaN olsa bile)", () => {
  for (const [v, i, r] of [[3.793, 1.128, 153], [4.1, -0.01, 50], [3.0, 0.5, 1000], [3.9, 0.95, 50], [1e-3, 3.3, 1], [2.5, NaN, 10]]) {
    assert.ok(Object.is(H.hatDuzelt(v, i, r), pilVDuzelt(v, i, r)), `${v} ${i} ${r}`);
  }
  for (const r of [0, -5, NaN, undefined, null]) {
    assert.equal(H.hatDuzelt(3.8, NaN, r), 3.8);
    assert.ok(Object.is(H.hatDuzelt(-0, 1, r), -0));
  }
});

test("HT5: multimetre girisi ve R onerisi (formul, yuvarlama, kirpma, I esigi)", () => {
  assert.equal(H.mmGiris("3,966"), 3.966);
  assert.equal(H.mmGiris(" 12.5 "), 12.5);
  for (const x of ["", "0", "0.0", "-3.9", "39", "3,9,6", "abc", "3.12345", null, undefined]) assert.equal(H.mmGiris(x), null, String(x));
  assert.deepEqual(H.hatOneri(50, 3.976, 3.9475, 0.95), { yeni: 80, ham: 80, kirpildi: false });
  assert.deepEqual(H.hatOneri(0, 3.966, 3.793, 1.128), { yeni: 153, ham: 153, kirpildi: false });
  assert.deepEqual(H.hatOneri(900, 5.0, 3.8, 1.0), { yeni: 1000, ham: 2100, kirpildi: true });
  assert.deepEqual(H.hatOneri(10, 3.0, 3.5, 1.0), { yeni: 0, ham: -490, kirpildi: true });
  assert.equal(H.hatOneri(50, 3.9, 3.8, 0.0999), null);
  assert.deepEqual(H.hatOneri(50, 3.85, 3.8, H.PIL_HAT_ENAZ_A), { yeni: 550, ham: 550, kirpildi: false }, "tam esikte gecer");
  for (const k of [[NaN, 3.9, 3.8, 1], [50, NaN, 3.8, 1], [50, 3.9, Infinity, 1], [50, 3.9, 3.8, Infinity]]) assert.equal(H.hatOneri(...k), null);
});

// ── hatGorunum + hatIslem (sahte $root) ───────────────────────────────────────
const KOK = (o = {}) => ({ dil: "tr", bagli: true, pilHat: "50", pilDurum: "CALISIYOR", volt: 3.9, amper: 0.95,
  voltGecersiz: false, amperGecersiz: false, veriYok: false, pilBaslatiliyor: false, ...o });
const Y = () => ({ hatGiris: "", mmGiris: "", oneri: null, mesgul: false, sonuc: null });

test("hatGorunum: metinler, multimetre kosulu, oneri / sonuc metni, dil", () => {
  const g = H.hatGorunum(KOK(), Y());
  assert.equal(g.mmAcik, true);
  assert.equal(g.duzelt, "Multimetreyle düzelt");
  assert.match(g.mmIpucu, /kutuplarına/);
  for (const o of [{ amper: 0.05 }, { pilDurum: "BITTI" }, { amperGecersiz: true }, { voltGecersiz: true }, { veriYok: true }, { volt: NaN }]) {
    const k = H.hatGorunum(KOK(o), Y());
    assert.equal(k.mmAcik, false, JSON.stringify(o));
    assert.match(k.mmIpucu, /yalnız test sürerken/);
  }
  const y = Y();
  y.oneri = { yeni: 1000, ham: 2100, kirpildi: true, eski: 900, v: 3.8, mm: 5, i: 1 };
  assert.match(H.hatGorunum(KOK({ dil: "en" }), y).oneri, /^New lead resistance 1000 mΩ \(now 900 mΩ\).* The result was 2100 mΩ, clipped to 0…1000\. Send it/);
  y.sonuc = { a: "ht.ret", d: { satir: "! Ph: 0..1000 mOhm" } };
  assert.equal(H.hatGorunum(KOK(), y).sonuc, "Kart reddetti: ! Ph: 0..1000 mOhm");
  assert.equal(H.hatGorunum(KOK(), y).sonucHata, true);
  y.sonuc = { a: "ht.onay", d: { n: 7 } };
  assert.equal(H.hatGorunum(KOK(), y).sonucHata, false);
  assert.equal(H.hatGorunum(KOK({ pilBaslatiliyor: true }), Y()).mesgul, true);
  for (const v of Object.values(H.hatGorunum(KOK(), Y()))) if (typeof v === "string") assert.doesNotMatch(v, /\bht\./, "ham anahtar");
});

test("hatIslem: elle / multimetre (tek onay) / ret / sessizlik / baska onay / bagli degil / mesgul", async () => {
  const kok = (yanit, o = {}) => {
    const giden = [];
    return { giden, u: { ...KOK(o), async pilAyarGonder(c) { giden.push(c); return yanit(c); } } };
  };
  const kabul = (c) => ({ tur: "ayar", s: `* pil hat direnci ${c.slice(2)} mOhm` });
  const a = kok(kabul);
  const y = Y();
  y.hatGiris = "1001";
  assert.equal(await H.hatIslem(a.u, y, "yaz", 50), false);
  assert.deepEqual(a.giden, []);
  assert.equal(y.sonuc.a, "ht.hata_giris");
  y.hatGiris = "0";
  assert.equal(await H.hatIslem(a.u, y, "yaz", 50), true);
  assert.deepEqual(a.giden, ["Ph0"]);
  assert.equal(a.u.pilHat, "0");
  assert.equal(y.hatGiris, "");
  y.mmGiris = "3,976";
  assert.equal(await H.hatIslem(a.u, y, "oner", 50), false);
  assert.equal(a.giden.length, 1, "oneri karta GITMEZ");
  assert.equal(y.oneri.yeni, 80);
  assert.equal(await H.hatIslem(a.u, y, "vazgec", 50), false);
  assert.equal(y.oneri, null);
  assert.equal(await H.hatIslem(a.u, y, "gonder", 50), false, "oneri yokken gonder bos");
  await H.hatIslem(a.u, y, "oner", 50);
  assert.equal(await H.hatIslem(a.u, y, "gonder", 50), true);
  assert.deepEqual(a.giden, ["Ph0", "Ph80"]);
  assert.equal(a.u.pilHat, "80");
  const b = kok(() => ({ tur: "ret", s: "! Ph: 0..1000 mOhm" }));
  const yb = Y();
  yb.hatGiris = "5";
  assert.equal(await H.hatIslem(b.u, yb, "yaz", 50), false);
  assert.deepEqual(yb.sonuc, { a: "ht.ret", d: { satir: "! Ph: 0..1000 mOhm" } });
  assert.equal(b.u.pilHat, "50");
  for (const yanit of [() => ({}), () => undefined, () => ({ tur: "ayar", s: "* pil kayit hizi 5 /s" }), () => ({ tur: "ayar", s: "* pil hat direnci 6 mOhm" })]) {
    const c = kok(yanit);
    const yc = Y();
    yc.hatGiris = "5";
    assert.equal(await H.hatIslem(c.u, yc, "yaz", 50), false);
    assert.equal(yc.sonuc.a, "ht.yanitsiz");
    assert.equal(c.u.pilHat, "50");
  }
  const t = kok(() => { throw new Error("ag yok"); });
  const yt = Y();
  yt.hatGiris = "5";
  assert.equal(await H.hatIslem(t.u, yt, "yaz", 50), false);
  assert.deepEqual(yt.sonuc, { a: "ht.ret", d: { satir: "ag yok" } });
  assert.equal(yt.mesgul, false);
  const d = kok(kabul, { bagli: false });
  const yd = Y();
  yd.hatGiris = "5";
  assert.equal(await H.hatIslem(d.u, yd, "yaz", 50), false);
  assert.deepEqual(d.giden, []);
  assert.equal(yd.sonuc.a, "ht.bagli_degil");
  const m = kok(kabul);
  const ym = Y();
  ym.mesgul = true;
  ym.hatGiris = "5";
  assert.equal(await H.hatIslem(m.u, ym, "yaz", 50), false);
  assert.deepEqual(m.giden, []);
  for (const o of [{ amper: 0.05 }, { pilDurum: "BEKLEMEDE" }]) {
    const k = kok(kabul, o);
    const yk = Y();
    yk.mmGiris = "3.9";
    await H.hatIslem(k.u, yk, "oner", 50);
    assert.equal(yk.oneri, null);
    assert.equal(yk.sonuc.a, "ht.kosul");
  }
  const yr = Y();
  yr.mmGiris = "3.9";
  await H.hatIslem(kok(kabul).u, yr, "oner", undefined);
  assert.equal(yr.sonuc.a, "ht.kosul", "kartin R'si bilinmeden oneri yok");
});
