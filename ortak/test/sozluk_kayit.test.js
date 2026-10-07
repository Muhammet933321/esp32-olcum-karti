// B73 / EU32 (W3) — ortak/src/sozluk_kayit.js: Kayitlar zincirinin (kayitlar.js, kayit_gorunum.js,
// karsilastir.js) kl./kg./kr. metinleri ACILIS sozlugunden (sozluk.js) AYRI. sozluk.test.js / sozluk_pc.test.js
// kurallari AYNEN (tr VE en, yer tutucu, kullanilmayan yok, ters yon, ayrik) + YERLESIM kurali iki yonde:
//   (a) burada olan HER anahtari YALNIZ zincirin dosyalari kullanir — baska bir ekran (app.js, ayarlar.js…)
//       kullansaydi modul inmeden anahtarin kendisi ekrana cikardi;
//   (b) acilis sozlugunde YALNIZ zincirin kullandigi kl./kg./kr. anahtari KALMAZ — yeni metin acilisa
//       sessizce eklenip butceyi yemesin.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC } from "../src/sozluk_pc.js";
import { SOZLUK_AY } from "../src/sozluk_ay.js";
import { SOZLUK_KAYIT, ceviriKayit } from "../src/sozluk_kayit.js";
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
const ZINCIR = ["kayitlar.js", "kayit_gorunum.js", "karsilastir.js"];
const AILE = /^(kl|kg|kr)\.[a-z0-9_]+$/;

/** anahtar -> onu dizge olarak yazan dosyalar (kisa ad) */
function kullananlar() {
  const m = new Map();
  for (const y of [...APP, ...EKRANLAR, ...ORTAK_SRC]) {
    for (const s of dizgeler(oku(y)).literal) {
      if (!AILE.test(s)) continue;
      if (!m.has(s)) m.set(s, new Set());
      m.get(s).add(y.split("/").pop());
    }
  }
  return m;
}

test("EU32: her anahtar kl./kg./kr. ailesinden, ASCII; bos olmayan tr VE en metni var (yalniz bu iki dil)", () => {
  const anahtarlar = Object.keys(SOZLUK_KAYIT);
  assert.ok(anahtarlar.length >= 150, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_KAYIT));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_KAYIT[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) {
      assert.equal(typeof SOZLUK_KAYIT[a][d], "string", `${a}.${d}`);
      assert.ok(SOZLUK_KAYIT[a][d].trim().length > 0, `${a}.${d} bos`);
    }
  }
});

test("EU32: yer tutucular iki dilde ayni", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_KAYIT)) assert.equal(yer(g.tr), yer(g.en), a);
});

test("EU32: sozluklar AYRIK — hicbir anahtar iki sozlukte yok", () => {
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_AY];
  assert.deepEqual(Object.keys(SOZLUK_KAYIT).filter((a) => obur.some((s) => a in s)), []);
});

test("EU32 (a): sozluk_kayit.js'teki HER anahtari YALNIZ zincirin dosyalari kullanir; kullanilmayan anahtar YOK", () => {
  if (!EKRANLAR.length) return;
  const k = kullananlar();
  const disari = Object.keys(SOZLUK_KAYIT).filter((a) => !k.has(a) || [...k.get(a)].some((f) => !ZINCIR.includes(f))
    || HTML.includes(a));
  assert.deepEqual(disari, [], "zincir disinda kullanilan ya da hic kullanilmayan anahtar sozluk_kayit.js'te");
});

test("EU32 (b): acilis sozlugunde YALNIZ zincirin kullandigi kl./kg./kr. anahtari kalmadi; zincirin kullandigi her anahtar bir sozlukte (ters yon)", () => {
  if (!EKRANLAR.length) return;
  const k = kullananlar();
  const yalnizZincir = Object.keys(SOZLUK).filter((a) => AILE.test(a) && k.has(a)
    && [...k.get(a)].every((f) => ZINCIR.includes(f)) && !HTML.includes(a));
  assert.deepEqual(yalnizZincir, [], "bu anahtarlar sozluk_kayit.js'e tasinmali (acilis butcesi, EU32)");
  const zincirin = [...k.entries()].filter(([, f]) => [...f].some((x) => ZINCIR.includes(x))).map(([a]) => a);
  assert.ok(zincirin.length >= 180, `yalniz ${zincirin.length} anahtar bulundu — cozucu kaciriyor`);
  assert.deepEqual(zincirin.filter((a) => !(a in SOZLUK_KAYIT) && !(a in SOZLUK)), []);
});

test("EU32: sozluk_kayit.js'i STATIK ice aktaranlar yalniz zincir (kayitlar, kayit_gorunum, karsilastir); app.js ve sozluk.js istemez; zincir acilis sozlugunden ceviri() ALMAZ", () => {
  if (!EKRANLAR.length) return;
  const statik = EKRANLAR.filter((y) => /^import \{[^}]*\} from '\/ortak\/sozluk_kayit\.js';$/m.test(yorumsuz(oku(y))));
  assert.deepEqual(statik.map((y) => y.split("/").pop()).sort(), [...ZINCIR].sort());
  for (const y of EKRANLAR.filter((x) => ZINCIR.includes(x.split("/").pop()))) {
    assert.doesNotMatch(yorumsuz(oku(y)), /import \{[^}]*\bceviri\b[^}]*\} from '\/ortak\/sozluk\.js'/,
      `${y}: acilis sozlugunun ceviri()'si kl./kg./kr. metnini bulamaz`);
  }
  for (const y of APP) assert.doesNotMatch(yorumsuz(oku(y)), /sozluk_kayit/, "app.js sozluk_kayit'i istememeli");
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_kayit/, "acilis sozlugu ek sozlugu cekmemeli");
});

test("ceviriKayit: kendi metni secili dilde; acilis sozlugundekiler de cevrilir; bilinmeyen anahtar kendisi; atmaz", () => {
  assert.equal(ceviriKayit("kl.baslik", "en"), SOZLUK_KAYIT["kl.baslik"].en);
  assert.equal(ceviriKayit("kl.baslik"), SOZLUK_KAYIT["kl.baslik"].tr);
  for (const a of ["kl.vazgec", "sebep.1", "csv.v_ort"]) {
    assert.equal(ceviriKayit(a, "en"), SOZLUK[a].en, a);
    assert.equal(ceviriKayit(a, "tr"), SOZLUK[a].tr, a);
  }
  assert.equal(ceviriKayit("kl.yok_boyle", "en"), "kl.yok_boyle");
  for (const a of [undefined, null, 42, {}, [], "__proto__", "constructor", "hasOwnProperty"]) {
    assert.doesNotThrow(() => ceviriKayit(a, "tr"));
    assert.equal(typeof ceviriKayit(a, "en"), "string");
  }
  assert.ok(ceviriKayit("kl.bulunamadi", "tr", { oturum: 44 }).includes("44"));
});
