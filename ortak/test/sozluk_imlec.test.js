// B73 (2026-10-07) — ortak/src/sozluk_imlec.js: imlec okumasinin aciklamasi ("ⓘ Bu değerler ne demek?").
// sozluk_ay.test.js / sozluk_kayit.test.js kurallari AYNEN (tr VE en, yer tutucu, ayrik, kullanilmayan yok) +
// YERLESIM: buradaki HER anahtari YALNIZ ekran/imlec_aciklama.js kullanir ve sozlugu YALNIZ o modul statik
// ice aktarir (app.js onu yalniz dinamik — Canli dondurulunca — indirir; acilis butcesine girmez).
// Icerik: metinler formullerle tutarli (isaretli integral, yamuk, zaman agirliksiz ortalama, bosluk).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC } from "../src/sozluk_pc.js";
import { SOZLUK_KAYIT } from "../src/sozluk_kayit.js";
import { SOZLUK_AY } from "../src/sozluk_ay.js";
import { SOZLUK_IMLEC, ceviriImlec } from "../src/sozluk_imlec.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js") && !a.startsWith("sozluk"))
  .map((a) => `../src/${a}`);
const AILE = /^ia\.[a-z0-9_]+$/;
const MODUL = "imlec_aciklama.js";

test("ia.: her anahtar ia. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(SOZLUK_IMLEC);
  assert.ok(anahtarlar.length >= 25, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_IMLEC));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_IMLEC[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof SOZLUK_IMLEC[a][d] === "string" && SOZLUK_IMLEC[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(SOZLUK_IMLEC[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("ia.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_IMLEC)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY];
  assert.deepEqual(Object.keys(SOZLUK_IMLEC).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "ia. ailesi baska sozlukte");
});

test("ia.: HER anahtari YALNIZ ekran/imlec_aciklama.js kullanir; kullanilmayan yok; sozlugu yalniz o modul ice aktarir", () => {
  if (!EKRANLAR.length) return;
  const m = new Map();
  for (const y of [...APP, ...EKRANLAR, ...ORTAK_SRC]) {
    for (const s of dizgeler(oku(y)).literal) {
      if (!AILE.test(s)) continue;
      if (!m.has(s)) m.set(s, new Set());
      m.get(s).add(y.split("/").pop());
    }
  }
  const disari = Object.keys(SOZLUK_IMLEC).filter((a) => !m.has(a) || [...m.get(a)].some((f) => f !== MODUL) || HTML.includes(a));
  assert.deepEqual(disari, []);
  assert.deepEqual([...m.keys()].filter((a) => !(a in SOZLUK_IMLEC)), [], "kullanilip sozlukte olmayan ia. anahtari");
  const ithal = [...APP, ...EKRANLAR].filter((y) => /sozluk_imlec/.test(yorumsuz(oku(y)))).map((y) => y.split("/").pop());
  assert.deepEqual(ithal, [MODUL]);
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_imlec/);
});

test("ia.: icerik formullerle tutarli (isaretli integral, yamuk, zaman agirliksiz ortalama, bosluk, B − A)", () => {
  const tr = (a) => SOZLUK_IMLEC[a].tr;
  const en = (a) => SOZLUK_IMLEC[a].en;
  assert.match(tr("ia.yuk"), /integral/);
  assert.match(tr("ia.yuk"), /İşaretli/);
  assert.match(tr("ia.yuk"), /yamuk/);
  assert.match(en("ia.yuk"), /Signed/);
  assert.match(tr("ia.enerji"), /V × I/);
  assert.match(tr("ia.ort"), /Zaman ağırlıklı değil/);
  assert.match(tr("ia.ort_i"), /amper/);
  assert.match(tr("ia.dt") + en("ia.dt"), /B − A/);
  assert.match(tr("ia.dv"), /eksi/);
  assert.match(tr("ia.bosluk"), /integral alınmaz/);
  assert.match(tr("ia.deger"), /ara değer üretilmez/);
});

test("ceviriImlec: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(ceviriImlec("ia.dugme", "en"), SOZLUK_IMLEC["ia.dugme"].en);
  assert.equal(ceviriImlec("ia.dugme"), SOZLUK_IMLEC["ia.dugme"].tr);
  assert.equal(ceviriImlec("ia.yok_boyle", "en"), "ia.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriImlec(a, "tr"));
    assert.equal(typeof ceviriImlec(a, "en"), "string");
  }
});
