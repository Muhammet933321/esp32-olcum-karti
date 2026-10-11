// B73 (5.12.118, 2026-10-10) — ortak/src/sozluk_skop.js: osiloskobun TEMBEL parcalarinin metinleri (on suzgec menusu
// SK1, eski skop arsivi B35 / 4D PC12). sozluk_pil.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer
// tutucu, ayrik, kullanilmayan yok) + YERLESIM: sz. anahtarlarini YALNIZ ekran/osiloskop.js'in bilesenleri (SkopSuz,
// SkopArsiv) kullanir; dosyayi YALNIZ o modul DINAMIK indirir (#/skop acilisi 14 dosyada; statik ice aktarma onu 15'e
// cikarirdi). app.js, index.html ve acilis sozlugu bu metinleri tasimaz (EU31 eslesmis acilis butcesi).
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
import { SOZLUK_SKOP, ceviriSkop } from "../src/sozluk_skop.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^sz\.[a-z0-9_]+$/;
const DOSYA = "sozluk_skop.js";
const MODUL = "osiloskop.js";

test("sz.: her anahtar sz. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(SOZLUK_SKOP);
  assert.ok(anahtarlar.length >= 6, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_SKOP));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_SKOP[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof SOZLUK_SKOP[a][d] === "string" && SOZLUK_SKOP[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(SOZLUK_SKOP[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("sz.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_SKOP)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC, SOZLUK_PIL, SOZLUK_HAT];
  assert.deepEqual(Object.keys(SOZLUK_SKOP).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "sz. ailesi baska sozlukte");
  /* tasinan metinler acilis sozlugune GERI donmez (EU31) */
  for (const a of ["os.suzgec", "os.suz_acik", "os.suz_ham", "os.suz_ipucu", "os.eski_arsiv", "os.eski_arsiv_ipucu"]) {
    assert.equal(a in SOZLUK, false, a);
  }
});

test("sz.: HER anahtari YALNIZ ekran/osiloskop.js kullanir; kullanilmayan yok; dosyayi yalniz o modul DINAMIK indirir", () => {
  if (!EKRANLAR.length) return;
  /* bilesen sablonlari `...` dizgesi — duz arama (sozluk_pil.test.js deseni) */
  const kod = oku(`../../arayuz3/ekran/${MODUL}`);
  const kullanilan = new Set([...kod.matchAll(/['"](sz\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  assert.deepEqual(Object.keys(SOZLUK_SKOP).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan sz. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in SOZLUK_SKOP)), [], "kullanilip sozlukte olmayan sz. anahtari");
  const baska = [];
  for (const y of [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA) && !x.endsWith(MODUL))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
    if (/['"]sz\.[a-z0-9_]+['"]/.test(oku(y))) baska.push(y.split("/").pop());
  }
  assert.deepEqual(baska, []);
  assert.equal(/['"]sz\.[a-z0-9_]+['"]/.test(HTML), false, "index.html sz. anahtari yazmaz");
  const ithal = [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_skop/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), [MODUL]);
  const m = yorumsuz(kod);
  assert.equal((m.match(/import\('\/ortak\/sozluk_skop\.js'\)/g) || []).length, 3, "SkopSuz + SkopArsiv + SkopSifir (SZ)");
  assert.doesNotMatch(m, /from '\/ortak\/sozluk_skop\.js'/);
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_skop/);
});

test("ceviriSkop: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(ceviriSkop("sz.suzgec"), "Süzgeç");
  assert.equal(ceviriSkop("sz.ham", "en"), "Raw");
  assert.equal(ceviriSkop("sz.acik", "xx"), "Açık");
  assert.equal(ceviriSkop("sz.yok_boyle", "en"), "sz.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriSkop(a, "tr"));
    assert.equal(typeof ceviriSkop(a, "en"), "string");
  }
});

test("sz.: icerik — Ham ADC'nin okudugu gibi; eski arsiv salt okuma, yeri olcum-karti/satir (bayat kopru/arsiv DEGIL)", () => {
  assert.match(SOZLUK_SKOP["sz.ipucu"].tr, /Ham: ADC'nin okuduğu gibi/);
  assert.match(SOZLUK_SKOP["sz.ipucu"].en, /Raw: as read by the ADC/);
  assert.match(SOZLUK_SKOP["sz.eski_arsiv"].tr, /^Eski arşiv/);
  assert.match(SOZLUK_SKOP["sz.eski_arsiv_ipucu"].tr, /Salt okuma, dönüştürülmez/);
  assert.match(SOZLUK_SKOP["sz.eski_arsiv_ipucu"].tr, /olcum-karti\/satir/);
  assert.doesNotMatch(SOZLUK_SKOP["sz.eski_arsiv_ipucu"].tr, /kopru\/arsiv/);
});

test("sz.: SZ (kullanici sifiri) — talimat kisa devreyi ve onayi soyler; kartin reddi AYNEN ({satir}); iki asama metinleri ayri", () => {
  assert.match(SOZLUK_SKOP["sz.talimat"].tr, /SKOP jakını COM'a kısa devre edin, sonra onaylayın/);
  assert.match(SOZLUK_SKOP["sz.talimat"].en, /Short the SCOPE jack to COM, then confirm/);
  assert.equal(ceviriSkop("sz.ret", "en", { satir: "! tz: x" }), "Board refused: ! tz: x");
  assert.notEqual(SOZLUK_SKOP["sz.sifirla"].tr, SOZLUK_SKOP["sz.onayla"].tr);
  assert.notEqual(SOZLUK_SKOP["sz.kaldir"].tr, SOZLUK_SKOP["sz.kaldir_onay"].tr);
});
