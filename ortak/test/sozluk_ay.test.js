// B73 / EU32 (W3) — ortak/src/sozluk_ay.js: Ayarlar MODULUNUN (ekran/ayarlar.js) ay. metinleri ACILIS
// sozlugunden (sozluk.js) AYRI. Kurallar sozluk_kayit.test.js'inkiyle AYNI; yerlesim iki yonde:
//   (a) burada olan HER anahtari YALNIZ ekran/ayarlar.js kullanir (kabuk ya da baska ekran kullansaydi modul
//       inmeden anahtarin kendisi ekrana cikardi — or. Ayarlar'in bolum adlari kabukta);
//   (b) acilis sozlugunde YALNIZ ayarlar.js'in kullandigi ay. anahtari KALMAZ.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC } from "../src/sozluk_pc.js";
import { SOZLUK_KAYIT } from "../src/sozluk_kayit.js";
import { SOZLUK_AY, ceviriAy } from "../src/sozluk_ay.js";
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
const AILE = /^ay\.[a-z0-9_]+$/;

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

test("EU32: her anahtar ay. ailesinden, ASCII; bos olmayan tr VE en; EN'de Turkce harf yok", () => {
  const anahtarlar = Object.keys(SOZLUK_AY);
  assert.ok(anahtarlar.length >= 80, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_AY));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_AY[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) {
      assert.equal(typeof SOZLUK_AY[a][d], "string", `${a}.${d}`);
      assert.ok(SOZLUK_AY[a][d].trim().length > 0, `${a}.${d} bos`);
    }
    assert.doesNotMatch(SOZLUK_AY[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("EU32: yer tutucular iki dilde ayni", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_AY)) assert.equal(yer(g.tr), yer(g.en), a);
});

test("EU32: sozluklar AYRIK", () => {
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT];
  assert.deepEqual(Object.keys(SOZLUK_AY).filter((a) => obur.some((s) => a in s)), []);
});

test("EU32 (a): sozluk_ay.js'teki HER anahtari YALNIZ ekran/ayarlar.js kullanir; kullanilmayan anahtar YOK", () => {
  if (!EKRANLAR.length) return;
  const k = kullananlar();
  const disari = Object.keys(SOZLUK_AY).filter((a) => !k.has(a) || [...k.get(a)].some((f) => f !== "ayarlar.js")
    || HTML.includes(a));
  assert.deepEqual(disari, [], "ayarlar.js disinda kullanilan ya da hic kullanilmayan anahtar sozluk_ay.js'te");
});

test("EU32 (b): acilis sozlugunde YALNIZ ayarlar.js'in kullandigi ay. anahtari kalmadi; ayarlar.js'in kullandigi her anahtar bir sozlukte", () => {
  if (!EKRANLAR.length) return;
  const k = kullananlar();
  const yalniz = Object.keys(SOZLUK).filter((a) => AILE.test(a) && k.has(a)
    && [...k.get(a)].every((f) => f === "ayarlar.js") && !HTML.includes(a));
  assert.deepEqual(yalniz, [], "bu anahtarlar sozluk_ay.js'e tasinmali (acilis butcesi, EU32)");
  const ayarin = [...k.entries()].filter(([, f]) => f.has("ayarlar.js")).map(([a]) => a);
  assert.ok(ayarin.length >= 90, `yalniz ${ayarin.length} anahtar bulundu — cozucu kaciriyor`);
  assert.deepEqual(ayarin.filter((a) => !(a in SOZLUK_AY) && !(a in SOZLUK)), []);
  /* AY5: degerler tablosunun 17 alani modulle iner */
  assert.equal(Object.keys(SOZLUK_AY).filter((a) => a.startsWith("ay.kd_")).length, 17);
});

test("EU32: sozluk_ay.js'i STATIK ice aktaran YALNIZ ayarlar.js; ayarlar.js acilis sozlugunden ceviri() ALMAZ; app.js / sozluk.js istemez", () => {
  if (!EKRANLAR.length) return;
  const statik = EKRANLAR.filter((y) => /^import \{[^}]*\} from '\/ortak\/sozluk_ay\.js';$/m.test(yorumsuz(oku(y))));
  assert.deepEqual(statik.map((y) => y.split("/").pop()), ["ayarlar.js"]);
  assert.doesNotMatch(yorumsuz(oku("../../arayuz3/ekran/ayarlar.js")), /import \{[^}]*\bceviri\b[^}]*\} from '\/ortak\/sozluk\.js'/);
  for (const y of APP) assert.doesNotMatch(yorumsuz(oku(y)), /sozluk_ay/, "app.js sozluk_ay'i istememeli");
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_ay/);
});

test("ceviriAy: kendi metni secili dilde; acilistakiler de cevrilir; bilinmeyen anahtar kendisi; atmaz", () => {
  assert.equal(ceviriAy("ay.sifirla_aciklama", "en"), SOZLUK_AY["ay.sifirla_aciklama"].en);
  assert.match(SOZLUK_AY["ay.sifirla_aciklama"].tr, /eşleştirmesi/);
  for (const a of ["ay.yenile", "kl.vazgec", "kal.durum.bozuk"]) {
    assert.equal(ceviriAy(a, "en"), SOZLUK[a].en, a);
    assert.equal(ceviriAy(a, "tr"), SOZLUK[a].tr, a);
  }
  assert.equal(ceviriAy("ay.yok_boyle", "en"), "ay.yok_boyle");
  for (const a of [undefined, null, 42, {}, [], "__proto__", "constructor"]) assert.doesNotThrow(() => ceviriAy(a, "tr"));
  assert.ok(ceviriAy("ay.kal_saatsiz", "tr", { acilis: 4 }).includes("4"));
});
