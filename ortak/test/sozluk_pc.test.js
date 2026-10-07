// B73 / 4D — ortak/src/sozluk_pc.js: panelin PC koprusundeki ("bu PC'deki arsiv") metinleri ACILIS
// sozlugunden (sozluk.js) AYRI (EU30 deseni). sozluk.test.js / sozluk_es.test.js kurallari AYNEN: her
// anahtarda bos olmayan tr VE en, yer tutucular iki dilde ayni, kullanilmayan anahtar yok, kullanilan
// her anahtar var (ters yon), sozluklar ayrik; acilis kabugu (app.js) bu dosyayi istemez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC, ceviriPc } from "../src/sozluk_pc.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const PC_ANAHTAR = /^pc\.[a-z0-9_]+$/;

test("4D: her anahtar pc. ailesinden, ASCII; bos olmayan tr VE en metni var (yalniz bu iki dil)", () => {
  const anahtarlar = Object.keys(SOZLUK_PC);
  assert.ok(anahtarlar.length >= 15, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_PC));
  for (const a of anahtarlar) {
    assert.match(a, PC_ANAHTAR, `anahtar pc. ailesinden olmali: ${a}`);
    assert.deepEqual(Object.keys(SOZLUK_PC[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) {
      assert.equal(typeof SOZLUK_PC[a][d], "string", `${a}.${d}`);
      assert.ok(SOZLUK_PC[a][d].trim().length > 0, `${a}.${d} bos`);
    }
    assert.doesNotMatch(SOZLUK_PC[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("4D: yer tutucular iki dilde ayni", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_PC)) assert.equal(yer(g.tr), yer(g.en), a);
});

test("4D: sozluklar AYRIK — hicbir anahtar iki yerde yok; acilis sozlugunde pc. ailesi YOK", () => {
  assert.deepEqual(Object.keys(SOZLUK_PC).filter((a) => a in SOZLUK || a in SOZLUK_ES), []);
  assert.deepEqual(Object.keys(SOZLUK).filter((a) => PC_ANAHTAR.test(a)), []);
});

test("4D: panelin kullandigi HER pc. anahtari sozluk_pc.js'te; sozluk_pc.js'te kullanilmayan anahtar YOK", () => {
  if (!EKRANLAR.length) return;
  const { literal } = dizgeler([...APP, ...EKRANLAR].map(oku).join("\n"));
  const kullanilan = [...literal].filter((s) => PC_ANAHTAR.test(s));
  assert.ok(kullanilan.length >= 15, `yalniz ${kullanilan.length} anahtar bulundu — cozucu kaciriyor`);
  assert.deepEqual(kullanilan.filter((a) => !(a in SOZLUK_PC)), []);
  assert.deepEqual(Object.keys(SOZLUK_PC).filter((a) => !literal.has(a)), [], "sozluk_pc.js'te olup panelde kullanilmayan anahtar");
});

test("4D/4H: sozluk_pc'yi STATIK ice aktaranlar yalniz Kayitlar zinciri (kayitlar.js, kayit_gorunum.js) ve yalniz kopruda inen pc_kopru.js; app.js ve sozluk.js istemez", () => {
  if (!EKRANLAR.length) return;
  const statik = EKRANLAR.filter((y) => /^import \{[^}]*\} from '\/ortak\/sozluk_pc\.js';$/m.test(yorumsuz(oku(y))));
  assert.deepEqual(statik.map((y) => y.split("/").pop()), ["kayit_gorunum.js", "kayitlar.js", "pc_kopru.js"]);
  for (const y of APP) assert.doesNotMatch(yorumsuz(oku(y)), /sozluk_pc/, "app.js sozluk_pc'yi istememeli");
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_pc/, "acilis sozlugu ek sozlugu cekmemeli");
});

test("4D: icerik — PC arsivi salt okuma, onay durumu acik yazilir (iki dilde)", () => {
  assert.match(SOZLUK_PC["pc.kl_salt"].tr, /[Ss]alt okuma[\s\S]*yazmaz[\s\S]*silmez[\s\S]*onay/);
  assert.match(SOZLUK_PC["pc.kl_salt"].en, /[Rr]ead-only[\s\S]*never writes, deletes[\s\S]*acknowledgements/);
  assert.match(SOZLUK_PC["pc.onay_acik"].tr, /silebilir/);
  assert.match(SOZLUK_PC["pc.onay_acik"].en, /may delete/);
});

test("ceviriPc: pc. metni secili dilde; acilis sozlugundeki anahtarlar da cevrilir; bilinmeyen anahtar kendisi; atmaz", () => {
  assert.equal(ceviriPc("pc.nerede", "en"), SOZLUK_PC["pc.nerede"].en);
  assert.equal(ceviriPc("pc.nerede"), SOZLUK_PC["pc.nerede"].tr);
  /* EU32: kl.yenile / kl.nerede_kart sozluk_kayit.js'e gecti; acilista kalan ortak kl. metinleri */
  for (const a of ["kl.vazgec", "kl.sil"]) {
    assert.equal(ceviriPc(a, "en"), SOZLUK[a].en, a);
    assert.equal(ceviriPc(a, "tr"), SOZLUK[a].tr, a);
  }
  assert.equal(ceviriPc("pc.yok_boyle", "en"), "pc.yok_boyle");
  for (const a of [undefined, null, 42, {}, [], "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriPc(a, "tr"));
  }
  assert.ok(ceviriPc("pc.kl_ozet", "tr", { akis: 2, oturum: 44, boyut: "1.21 MB" }).includes("44"));
});
