// B73 (5.12.121, 2026-10-11) — ortak/src/sozluk_yonetim.js: Ayarlar kartlarinin ve Konsol'un tembel metinleri (Oncelik 2).
// sozluk_skop.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer tutucu, ayrik, kullanilmayan yok) +
// YERLESIM: yn. anahtarlarini YALNIZ app.js ve index.html kullanir; dosyayi YALNIZ app.js DINAMIK indirir (tek
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
import { SOZLUK_KABUK } from "../src/sozluk_kabuk.js";
import { SOZLUK_YONETIM, ceviriYonetim } from "../src/sozluk_yonetim.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP_VAR = existsSync(new URL("../../arayuz3/app.js", import.meta.url));
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^yn\.[a-z0-9_]+$/;
const DOSYA = "sozluk_yonetim.js";

test("yn.: her anahtar yn. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(SOZLUK_YONETIM);
  assert.ok(anahtarlar.length >= 40, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(SOZLUK_YONETIM));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(SOZLUK_YONETIM[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof SOZLUK_YONETIM[a][d] === "string" && SOZLUK_YONETIM[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(SOZLUK_YONETIM[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("yn.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_YONETIM)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC, SOZLUK_PIL, SOZLUK_HAT, SOZLUK_SKOP, SOZLUK_OSILO, SOZLUK_KABUK];
  assert.deepEqual(Object.keys(SOZLUK_YONETIM).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "yn. ailesi baska sozlukte");
});

test("yn.: HER anahtari YALNIZ app.js + index.html kullanir; kullanilmayan yok; dosyayi yalniz app.js DINAMIK indirir", () => {
  if (!APP_VAR) return;
  const app = oku("../../arayuz3/app.js");
  const deger = (s) => new Set([...s.matchAll(/['"](yn\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  const kullanilan = new Set([...deger(app), ...deger(HTML)]);
  assert.deepEqual(Object.keys(SOZLUK_YONETIM).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan yn. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in SOZLUK_YONETIM)), [], "kullanilip sozlukte olmayan yn. anahtari");
  const baska = [];
  for (const y of [...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
  }
  assert.deepEqual(baska, []);
  const ithal = [...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_yonetim/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), []);
  const m = yorumsuz(app);
  assert.equal((m.match(/import\('\/ortak\/sozluk_yonetim\.js'\)/g) || []).length, 1, "app.js tek dinamik import");
  assert.doesNotMatch(m, /from '\/ortak\/sozluk_yonetim\.js'/);
  assert.doesNotMatch(HTML, /<(?:script|link)[^>]+sozluk_yonetim/, "index.html betik olarak baglamaz");
});

test("ceviriYonetim: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(ceviriYonetim("yn.gonder"), "Gönder");
  assert.equal(ceviriYonetim("yn.gonder", "en"), "Send");
  assert.equal(ceviriYonetim("yn.tema_koyu", "xx"), "Koyu");
  assert.equal(ceviriYonetim("yn.kart_sont", "en", { deger: "100.0 mΩ" }), "board: 100.0 mΩ");
  assert.equal(ceviriYonetim("yn.yok_boyle", "en"), "yn.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => ceviriYonetim(a, "tr"));
    assert.equal(typeof ceviriYonetim(a, "en"), "string");
  }
});

test("yn.: _html anahtarlari YALNIZ satir ici isaretleme (b strong em code) tasir, iki dilde AYNI etiketler; digerleri isaretlemesiz", () => {
  const etiket = (x) => [...x.matchAll(/<\/?([a-z]+)[^>]*>/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK_YONETIM)) {
    if (a.endsWith("_html")) {
      assert.ok(etiket(g.tr).length > 0, a);
      assert.equal(etiket(g.tr), etiket(g.en), a);
      assert.ok(etiket(g.tr).split(",").every((e) => ["b", "strong", "em", "code"].includes(e)), a);
      assert.doesNotMatch(g.tr + g.en, /on[a-z]+=|javascript:|<script/i, a);
    } else {
      assert.doesNotMatch(g.tr + g.en, /<[a-z\/]/i, a);
    }
  }
});

test("yn.: icerik — eski Turkce metinler AYNEN (Turkce kip degismez); tema kimlikleri tema.js'le ayni", () => {
  const tr = (a) => SOZLUK_YONETIM[a].tr;
  assert.equal(tr("yn.hata_parola"), "Parola boş olamaz — parolasız (açık) ağ için Konsol'dan Np gönderin.");
  assert.equal(tr("yn.sebeke_kapali"), "Ölçek düzeltmesi KAPALI (DC). AC ölçerken güç |H|² kadar düşük okunur — 50 Hz'te yaklaşık %45.");
  assert.equal(ceviriYonetim("yn.sebeke_carpan", "tr", { k: "1.000", f: "50" }), "Güce uygulanan ölçek çarpanı: ×1.000  (50 Hz ayarıyla)");
  assert.match(tr("yn.konsol_ipucu_html"), /^Karttan gelen her satır burada — saniyede 20 kez gelen <code>D<\/code>/);
  const tema = oku("../../arayuz3/ekran/tema.js");
  for (const id of ["sistem", "koyu", "acik", "onpanel"]) {
    assert.match(tema, new RegExp(`id: '${id}'`));
    assert.ok(SOZLUK_YONETIM[`yn.tema_${id}`] && SOZLUK_YONETIM[`yn.tema_${id}_alt`], id);
  }
});
