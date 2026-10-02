// B73 / 3H-2 (EU30) — ortak/src/sozluk_es.js: Eslestirme metinleri ACILIS sozlugunden (sozluk.js) AYRI.
// Ayarlar > Eslestirme ekrani (arayuz3/ekran/eslesme_ekran.js) bu dosyayi kendisiyle birlikte indirir;
// acilis kabugu (app.js) yalniz sozluk.js'teki es.* anahtarlarini kullanir (serit uyarisi, akis hatasi,
// "modul yuklenemedi"). sozluk.test.js'in kurallari AYNEN: her anahtarda bos olmayan tr VE en, yer
// tutucular iki dilde ayni, kullanilmayan anahtar yok, kullanilan her anahtar var (ters yon).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES, ceviriEs } from "../src/sozluk_es.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const ES_ANAHTAR = /^es\.[a-z0-9_]+$/;

test("EU30: her anahtar es. ailesinden, ASCII; bos olmayan tr VE en metni var (yalniz bu iki dil)", () => {
  const anahtarlar = Object.keys(SOZLUK_ES);
  assert.ok(anahtarlar.length >= 70, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_ES));
  for (const a of anahtarlar) {
    assert.match(a, ES_ANAHTAR, `anahtar es. ailesinden olmali: ${a}`);
    assert.deepEqual(Object.keys(SOZLUK_ES[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) {
      assert.equal(typeof SOZLUK_ES[a][d], "string", `${a}.${d}`);
      assert.ok(SOZLUK_ES[a][d].trim().length > 0, `${a}.${d} bos`);
    }
  }
});

test("EU30: yer tutucular iki dilde ayni", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_ES)) assert.equal(yer(g.tr), yer(g.en), a);
});

test("EU30: iki sozluk AYRIK — hicbir anahtar iki yerde yok (hangisinin kazandigi belirsiz kalmasin)", () => {
  assert.deepEqual(Object.keys(SOZLUK_ES).filter((a) => a in SOZLUK), []);
});

test("EU30: acilis sozlugundeki es. anahtarlari TAM OLARAK acilis kabugunun (app.js) kullandiklari", () => {
  if (!APP.length) return;
  const { literal } = dizgeler(APP.map(oku).join("\n"));
  const kabuk = [...literal].filter((s) => ES_ANAHTAR.test(s)).sort();
  assert.ok(kabuk.length >= 4, `yalniz ${kabuk.length} anahtar — cozucu kaciriyor`);
  /* kabugun kullandigi her es. anahtari ACILISTA olmali (modul inmeden once / inmezse de yazilir) */
  assert.deepEqual(kabuk.filter((a) => !(a in SOZLUK)), [], "app.js'in es. anahtari acilis sozlugunde yok");
  /* ve acilista BASKA es. metni yok: eslestirme ekraninin metinleri sozluk_es.js'te */
  assert.deepEqual(Object.keys(SOZLUK).filter((a) => /^es\./.test(a)).sort(), kabuk, "acilis sozlugunde kabugun kullanmadigi es. metni");
  assert.ok(kabuk.includes("es.uyari_modul") && kabuk.includes("es.uyari_depo"), "modul / depo uyarisi acilista olmali");
});

test("EU30: panelin kullandigi HER es. anahtari iki sozlukten birinde; sozluk_es.js'te kullanilmayan anahtar YOK", () => {
  if (!APP.length || !EKRANLAR.length) return;
  const { literal } = dizgeler([...APP, ...EKRANLAR].map(oku).join("\n"));
  const kullanilan = [...literal].filter((s) => ES_ANAHTAR.test(s));
  assert.ok(kullanilan.length >= 70, `yalniz ${kullanilan.length} anahtar bulundu — cozucu kaciriyor`);
  assert.deepEqual(kullanilan.filter((a) => !(a in SOZLUK) && !(a in SOZLUK_ES)), []);
  assert.deepEqual(Object.keys(SOZLUK_ES).filter((a) => !literal.has(a)), [], "sozluk_es.js'te olup panelde kullanilmayan anahtar");
});

test("EU30: sozluk_es anahtarlarini kullanan HER ekran dosyasi sozluk_es.js'i ice aktarir; app.js ve sozluk.js aktarmaz", () => {
  if (!EKRANLAR.length) return;
  const kullanan = EKRANLAR.filter((y) => [...dizgeler(oku(y)).literal].some((s) => s in SOZLUK_ES));
  assert.deepEqual(kullanan.map((y) => y.split("/").pop()), ["eslesme_ekran.js"]);
  for (const y of kullanan) assert.match(yorumsuz(oku(y)), /^import \{[^}]*\bceviriEs\b[^}]*\} from '\/ortak\/sozluk_es\.js';$/m, y);
  for (const y of APP) assert.doesNotMatch(yorumsuz(oku(y)), /sozluk_es/, "app.js sozluk_es'i (statik ya da dinamik) istememeli");
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_es/, "acilis sozlugu ek sozlugu cekmemeli");
});

test("ES3 + EU25 / ES9 / ES1: eslestirme metinlerinin icerigi (iki dilde de DOGRU)", () => {
  /* ES3 + EU25: parola ag'a cikmaz ve PANEL saklamaz; tarayicinin kendi parola yoneticisi kaydetmeyi
     onerebilir (autocomplete current-password) */
  assert.match(SOZLUK_ES["es.parola_ipucu"].tr, /Ağa gönderilmez[\s\S]*panel saklamaz[\s\S]*parola yöneticisi/);
  assert.match(SOZLUK_ES["es.parola_ipucu"].en, /Never sent[\s\S]*panel does not store it[\s\S]*password manager/);
  assert.doesNotMatch(SOZLUK_ES["es.aciklama"].tr, /hiçbir yere kaydedilmez/);
  /* ES9 / ES1: zorunluluk ve bildirim yalniz USB — komutlar metinde (Ez1 / Em1, Q) */
  assert.match(SOZLUK_ES["es.guv_aciklama"].tr, /Ez1[\s\S]*Em1/);
  assert.match(SOZLUK_ES["es.bildirim_aciklama"].en, /USB/);
});

// ── ceviriEs ─────────────────────────────────────────────────────────
test("ceviriEs: es. metni secili dilde; acilis sozlugundeki anahtarlar (ay.yenile, kl.vazgec, es.uyari_git) da cevrilir", () => {
  assert.equal(ceviriEs("es.eslestir", "tr"), SOZLUK_ES["es.eslestir"].tr);
  assert.equal(ceviriEs("es.eslestir", "en"), SOZLUK_ES["es.eslestir"].en);
  assert.equal(ceviriEs("es.eslestir"), SOZLUK_ES["es.eslestir"].tr);
  for (const a of ["ay.yenile", "kl.vazgec", "es.uyari_git"]) {
    assert.equal(ceviriEs(a, "en"), SOZLUK[a].en, a);
    assert.equal(ceviriEs(a, "tr"), SOZLUK[a].tr, a);
  }
  for (const d of ["de", "", null, undefined, 3, "EN"]) assert.equal(ceviriEs("es.eslestir", d), SOZLUK_ES["es.eslestir"].tr, String(d));
});

test("ceviriEs: bilinmeyen anahtar ANAHTARIN KENDISI; degiskenler yerine konur; hicbir girdide atmaz", () => {
  assert.equal(ceviriEs("es.yok_boyle", "en"), "es.yok_boyle");
  for (const a of ["__proto__", "constructor", "toString", "hasOwnProperty"]) assert.equal(ceviriEs(a, "tr"), a);
  for (const a of [undefined, null, 42, {}, [], true, Symbol("x")]) {
    assert.doesNotThrow(() => ceviriEs(a, "tr"), String(typeof a));
    assert.equal(typeof ceviriEs(a, "en"), "string");
  }
  assert.ok(ceviriEs("es.ret_bekle", "tr", { kart: "k", sn: 8 }).includes("8"));
  assert.ok(ceviriEs("es.ret_bekle", "tr").includes("{sn}"));
  assert.equal(ceviriEs("es.ret_bekle", "tr", { kart: "$&", sn: 1 }).includes("$&"), true, "replace kalibi yorumlanmamali");
});
