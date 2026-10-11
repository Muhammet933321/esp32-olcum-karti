// B73 (5.12.121, 2026-10-11) — ortak/src/sozluk_osilo.js: osiloskop ekraninin kabuktaki (index.html + app.js) metinleri.
// sozluk_skop.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer tutucu, ayrik, kullanilmayan yok) +
// YERLESIM: sk. anahtarlarini YALNIZ app.js ve index.html kullanir; dosyayi YALNIZ app.js DINAMIK indirir (tek
// import() cagrisi; statik ice aktarma eslesmis acilisi (EU31, 15 dosya) / #/skop acilisini (14 dosya) bir dosya
// buyutur). Acilis sozlugu bu metinleri tasimaz (EU32).
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
import { SOZLUK_HAT } from "../src/sozluk_hat.js";
import { SOZLUK_SKOP } from "../src/sozluk_skop.js";
import { SOZLUK_KABUK } from "../src/sozluk_kabuk.js";
import { SOZLUK_OSILO, ceviriOsilo } from "../src/sozluk_osilo.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP_VAR = existsSync(new URL("../../arayuz3/app.js", import.meta.url));
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^sk\.[a-z0-9_]+$/;
const DOSYA = "sozluk_osilo.js";

test("sk.: her anahtar sk. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(SOZLUK_OSILO);
  assert.ok(anahtarlar.length >= 80, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_OSILO));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_OSILO[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof SOZLUK_OSILO[a][d] === "string" && SOZLUK_OSILO[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(SOZLUK_OSILO[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("sk.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_OSILO)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC, SOZLUK_PIL, SOZLUK_HAT, SOZLUK_SKOP, SOZLUK_KABUK];
  assert.deepEqual(Object.keys(SOZLUK_OSILO).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "sk. ailesi baska sozlukte");
});

test("sk.: HER anahtari YALNIZ app.js + index.html kullanir; kullanilmayan yok; dosyayi yalniz app.js DINAMIK indirir", () => {
  if (!APP_VAR) return;
  const app = oku("../../arayuz3/app.js");
  const deger = (s) => new Set([...s.matchAll(/['"](sk\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  const kullanilan = new Set([...deger(app), ...deger(HTML)]);
  assert.deepEqual(Object.keys(SOZLUK_OSILO).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan sk. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in SOZLUK_OSILO)), [], "kullanilip sozlukte olmayan sk. anahtari");
  const baska = [];
  for (const y of [...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
  }
  assert.deepEqual(baska, []);
  const ithal = [...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_osilo/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), []);
  const m = yorumsuz(app);
  assert.equal((m.match(/import\('\/ortak\/sozluk_osilo\.js'\)/g) || []).length, 1, "app.js tek dinamik import");
  assert.doesNotMatch(m, /from '\/ortak\/sozluk_osilo\.js'/);
  assert.doesNotMatch(HTML, /<(?:script|link)[^>]+sozluk_osilo/, "index.html betik olarak baglamaz");
});

test("ceviriOsilo: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(ceviriOsilo("sk.dikey"), "Dikey");
  assert.equal(ceviriOsilo("sk.dikey", "en"), "Vertical");
  assert.equal(ceviriOsilo("sk.bol", "xx"), "/böl");
  assert.equal(ceviriOsilo("sk.bol", "en"), "/div");
  assert.equal(ceviriOsilo("sk.yok_boyle", "en"), "sk.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriOsilo(a, "tr"));
    assert.equal(typeof ceviriOsilo(a, "en"), "string");
  }
});

test("sk.: olcum tablosu sozcukleri cevrilir, semboller kalir; menzil sayilari iki dilde AYNI", () => {
  const en = (a) => SOZLUK_OSILO[a].en;
  assert.deepEqual(["sk.periyot", "sk.vort", "sk.yukselme", "sk.dusme", "sk.cevrim"].map(en), ["Period", "Vmean", "Rise", "Fall", "Cycles"]);
  const sayi = (s) => s.match(/[−+]?\d+(\.\d+)?/g).join(" ");
  assert.equal(sayi(SOZLUK_OSILO["sk.menzil_1"].tr), sayi(SOZLUK_OSILO["sk.menzil_1"].en));
  assert.match(SOZLUK_OSILO["sk.menzil_1"].tr, /^Menzil −63\.5 … \+46\.8 V/);
  assert.match(SOZLUK_OSILO["sk.menzil_1"].en, /^Range −63\.5 … \+46\.8 V/);
});

