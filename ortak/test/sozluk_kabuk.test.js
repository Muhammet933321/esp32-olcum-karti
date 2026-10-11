// B73 (5.12.121, 2026-10-11) — ortak/src/sozluk_kabuk.js: kabugun tembel metinleri (ust seritler, hata metinleri, Canli ipucu, Pil kabugu).
// sozluk_skop.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer tutucu, ayrik, kullanilmayan yok) +
// YERLESIM: kk. anahtarlarini YALNIZ app.js ve index.html kullanir; dosyayi YALNIZ app.js DINAMIK indirir (tek
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
import { SOZLUK_OSILO } from "../src/sozluk_osilo.js";
import { SOZLUK_KABUK, ceviriKabuk } from "../src/sozluk_kabuk.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP_VAR = existsSync(new URL("../../arayuz3/app.js", import.meta.url));
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^kk\.[a-z0-9_]+$/;
const DOSYA = "sozluk_kabuk.js";

test("kk.: her anahtar kk. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(SOZLUK_KABUK);
  assert.ok(anahtarlar.length >= 40, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_KABUK));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_KABUK[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof SOZLUK_KABUK[a][d] === "string" && SOZLUK_KABUK[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(SOZLUK_KABUK[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("kk.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_KABUK)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC, SOZLUK_PIL, SOZLUK_HAT, SOZLUK_SKOP, SOZLUK_OSILO];
  assert.deepEqual(Object.keys(SOZLUK_KABUK).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "kk. ailesi baska sozlukte");
});

test("kk.: HER anahtari YALNIZ app.js + index.html kullanir; kullanilmayan yok; dosyayi yalniz app.js DINAMIK indirir", () => {
  if (!APP_VAR) return;
  const app = oku("../../arayuz3/app.js");
  const deger = (s) => new Set([...s.matchAll(/['"](kk\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  const kullanilan = new Set([...deger(app), ...deger(HTML)]);
  assert.deepEqual(Object.keys(SOZLUK_KABUK).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan kk. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in SOZLUK_KABUK)), [], "kullanilip sozlukte olmayan kk. anahtari");
  const baska = [];
  for (const y of [...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
  }
  assert.deepEqual(baska, []);
  const ithal = [...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_kabuk/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), []);
  const m = yorumsuz(app);
  assert.equal((m.match(/import\('\/ortak\/sozluk_kabuk\.js'\)/g) || []).length, 1, "app.js tek dinamik import");
  assert.doesNotMatch(m, /from '\/ortak\/sozluk_kabuk\.js'/);
  assert.doesNotMatch(HTML, /<(?:script|link)[^>]+sozluk_kabuk/, "index.html betik olarak baglamaz");
});

test("ceviriKabuk: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(ceviriKabuk("kk.devral"), "Sürücülüğü devral");
  assert.equal(ceviriKabuk("kk.devral", "en"), "Take over as driver");
  assert.equal(ceviriKabuk("kk.izleyici_2", "xx"), "izleyici");
  assert.equal(ceviriKabuk("kk.komut_red", "en", { kod: 403 }), "Command not sent (403)");
  assert.equal(ceviriKabuk("kk.yok_boyle", "en"), "kk.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriKabuk(a, "tr"));
    assert.equal(typeof ceviriKabuk(a, "en"), "string");
  }
});

test("kk.: icerik — eski Turkce metinler AYNEN (Turkce kip degismez); J7 emniyet uyarisi iki dilde J3 + 38.5 V", () => {
  const tr = (a) => SOZLUK_KABUK[a].tr;
  assert.equal(tr("kk.okuma_hatasi"), "Okuma hatası: {mesaj} — kablo çıkmış ya da kart yeniden başlamış olabilir; “Karta bağlan”a yeniden basın.");
  assert.equal(tr("kk.devral_409"), "Devralınamadı (409): Başka bir sürücü etkin — o sekmeyi kapatıp yeniden deneyin.");
  assert.equal(ceviriKabuk("kk.komut_baglanti_yok"), "Komut gönderilemedi — bağlantı yok");
  assert.match(tr("kk.j7_2"), /J3/);
  assert.match(SOZLUK_KABUK["kk.j7_2"].en, /J3/);
  assert.match(SOZLUK_KABUK["kk.j7_5"].en, /cut-off/);
});

