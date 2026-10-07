// B73 (PT7, 2026-10-07) — ortak/src/sozluk_pil.js: pil testi iyilestirmesinin metinleri + saf hesaplari (kayit
// hizi, tahmini sure, bos kayit yeri, farkli ayar) + ekran/pil.js PilPt'nin gosterdigi metinler (ptGorunum).
// sozluk_imlec.test.js kurallari AYNEN (tr VE en, EN'de Turkce harf yok, yer tutucu, ayrik, kullanilmayan yok) +
// YERLESIM: pt. anahtarlarini YALNIZ bu dosyanin kendi hesabi kullanir; dosyayi YALNIZ ekran/pil.js DINAMIK indirir
// (Karsilastirma pil.js'i statik indirir ama sozlugu degil — KU1); app.js, acilis sozlugu ve baska modul istemez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { SOZLUK, DILLER } from "../src/sozluk.js";
import { SOZLUK_ES } from "../src/sozluk_es.js";
import { SOZLUK_PC } from "../src/sozluk_pc.js";
import { SOZLUK_KAYIT } from "../src/sozluk_kayit.js";
import { SOZLUK_AY } from "../src/sozluk_ay.js";
import { SOZLUK_IMLEC } from "../src/sozluk_imlec.js";
import * as P from "../src/sozluk_pil.js";
import { dizgeler } from "./dizgeler.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const EKRAN_URL = new URL("../../arayuz3/ekran/", import.meta.url);
const EKRANLAR = existsSync(EKRAN_URL)
  ? readdirSync(EKRAN_URL).filter((a) => a.endsWith(".js")).sort().map((a) => `../../arayuz3/ekran/${a}`) : [];
const APP = existsSync(new URL("../../arayuz3/app.js", import.meta.url)) ? ["../../arayuz3/app.js"] : [];
const HTML = existsSync(new URL("../../arayuz3/index.html", import.meta.url)) ? oku("../../arayuz3/index.html") : "";
const ORTAK_SRC = readdirSync(new URL("../src/", import.meta.url)).filter((a) => a.endsWith(".js")).map((a) => `../src/${a}`);
const AILE = /^pt\.[a-z0-9_]+$/;
const DOSYA = "sozluk_pil.js";

test("pt.: her anahtar pt. ailesinden; bos olmayan tr VE en; EN'de Turkce harf yok; donmus", () => {
  const anahtarlar = Object.keys(P.SOZLUK_PIL);
  assert.ok(anahtarlar.length >= 15, `${anahtarlar.length}`);
  assert.ok(Object.isFrozen(P.SOZLUK_PIL));
  for (const a of anahtarlar) {
    assert.match(a, AILE, a);
    assert.deepEqual(Object.keys(P.SOZLUK_PIL[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) assert.ok(typeof P.SOZLUK_PIL[a][d] === "string" && P.SOZLUK_PIL[a][d].trim(), `${a}.${d}`);
    assert.doesNotMatch(P.SOZLUK_PIL[a].en, /[çğıöşüÇĞİÖŞÜ]/, `${a}.en Turkce harf`);
  }
});

test("pt.: yer tutucular iki dilde ayni; sozluklar AYRIK", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(P.SOZLUK_PIL)) assert.equal(yer(g.tr), yer(g.en), a);
  const obur = [SOZLUK, SOZLUK_ES, SOZLUK_PC, SOZLUK_KAYIT, SOZLUK_AY, SOZLUK_IMLEC];
  assert.deepEqual(Object.keys(P.SOZLUK_PIL).filter((a) => obur.some((s) => a in s)), []);
  for (const s of obur) assert.equal(Object.keys(s).filter((a) => AILE.test(a)).length, 0, "pt. ailesi baska sozlukte");
});

test("pt.: HER anahtari YALNIZ bu dosyanin hesabi kullanir; kullanilmayan yok; dosyayi yalniz ekran/pil.js DINAMIK indirir", () => {
  /* kendi kullanimi: sozlugun ALTINDAKI kod (hesap + bilesen sablonu; sablon bir `...` dizgesi — duz arama) */
  const kendi = oku(`../src/${DOSYA}`);
  const kod = kendi.slice(kendi.indexOf("// ── hesap"));
  const kullanilan = new Set([...kod.matchAll(/['"](pt\.[a-z0-9_]+)['"]/g)].map((x) => x[1]));
  assert.deepEqual(Object.keys(P.SOZLUK_PIL).filter((a) => !kullanilan.has(a)), [], "sozlukte olup kullanilmayan pt. anahtari");
  assert.deepEqual([...kullanilan].filter((a) => !(a in P.SOZLUK_PIL)), [], "kullanilip sozlukte olmayan pt. anahtari");
  /* baska hicbir dosya pt. anahtari yazmaz (bilesen inmeden anahtarin kendisi ekrana cikardi) */
  const baska = [];
  for (const y of [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((x) => !x.endsWith(DOSYA))) {
    for (const s of dizgeler(oku(y)).literal) if (AILE.test(s)) baska.push(`${y.split("/").pop()}:${s}`);
  }
  assert.deepEqual(baska, []);
  assert.equal(/['"]pt\.[a-z0-9_]+['"]/.test(HTML), false, "index.html pt. anahtari yazmaz");
  /* ice aktaranlar: YALNIZ ekran/pil.js ve YALNIZ dinamik (PilPt kurulunca) */
  const ithal = [...APP, ...EKRANLAR, ...ORTAK_SRC].filter((y) => !y.endsWith(DOSYA) && /sozluk_pil/.test(yorumsuz(oku(y))));
  assert.deepEqual(ithal.map((y) => y.split("/").pop()), EKRANLAR.length ? ["pil.js"] : []);
  for (const y of ithal) {
    assert.match(yorumsuz(oku(y)), /import\('\/ortak\/sozluk_pil\.js'\)/);
    assert.doesNotMatch(yorumsuz(oku(y)), /from '\/ortak\/sozluk_pil\.js'/);
  }
  assert.doesNotMatch(yorumsuz(oku("../src/sozluk.js")), /sozluk_pil/);
});

test("ceviriPil: secili dil; bilinmeyen kendisi; atmaz", () => {
  assert.equal(P.ceviriPil("pt.kapali", "en"), "off");
  assert.equal(P.ceviriPil("pt.kapali"), "kapalı");
  assert.equal(P.ceviriPil("pt.her_ornek", "tr", { n: 400 }), "Her örnek (~400/s)");
  assert.equal(P.ceviriPil("pt.yok_boyle", "en"), "pt.yok_boyle");
  for (const a of [undefined, null, 42, {}, "__proto__", "constructor"]) {
    assert.doesNotThrow(() => P.ceviriPil(a, "tr"));
    assert.equal(typeof P.ceviriPil(a, "en"), "string");
  }
});

// ── hesap ────────────────────────────────────────────────────────────────────
const PIL_H = oku("../../kod/olcum-karti-a3/pil_test.h");
const PART = oku("../../kod/olcum-karti-a3/partitions.csv");

test("PT3: hiz kumesi firmware'in pil_hz_izinli'siyle ayni; kayitHizNormal bozuk / bos tercihi 1/s yapar ('' ve null 'her ornek' DEGIL)", () => {
  const izin = (/static uint8_t pil_hz_izinli\(uint32_t hz\)\s*\{\s*return \(uint8_t\)\(([^;]*)\);/.exec(PIL_H) || ["", ""])[1];
  const fw = [...izin.matchAll(/hz == (\d+)u/g)].map((m) => Number(m[1])).sort((a, b) => a - b);
  assert.deepEqual([...P.PIL_KAYIT_HIZLARI].sort((a, b) => a - b), fw);
  assert.deepEqual([...P.PIL_KAYIT_HIZLARI], [1, 5, 20, 50, 0]);
  assert.equal(P.PIL_OCV_MS, Number((/#define PIL_OCV_MS\s+(\d+)u/.exec(PIL_H) || [])[1]));
  for (const [x, b] of [[0, 0], ["0", 0], [20, 20], ["50", 50], [5, 5], [1, 1]]) assert.equal(P.kayitHizNormal(x), b, String(x));
  for (const x of ["", " ", null, undefined, "x", 7, -1, 0.2, true, {}, []]) assert.equal(P.kayitHizNormal(x), 1, String(x));
});

test("PT4/PT7: tahmini sure — bolum partitions.csv'den; her ornek ~1 sa, 1/s gunlerce; bos yer G'nin onaysiz payindan; sure yazisi sa/dk", () => {
  const bolum = parseInt((/^kayit,\s*data,\s*0x40,\s*0x[0-9A-Fa-f]+,\s*(0x[0-9A-Fa-f]+)/m.exec(PART) || [])[1], 16);
  assert.equal(bolum, P.KAYIT_BOLUM_BAYT);
  const her = P.kayitSuresiS(0, bolum) / 3600;
  assert.ok(her > 0.9 && her < 1.6, `${her}`);
  assert.ok(P.kayitSuresiS(1, bolum) / 3600 > 24);
  const sira = [1, 5, 20, 50, 0].map((h) => P.kayitSuresiS(h, bolum));
  for (let k = 1; k < sira.length; k++) assert.ok(sira[k] < sira[k - 1], "hiz arttikca sure kisalir");
  assert.equal(P.kayitSuresiS(1, 0), 0);
  assert.equal(P.kayitSuresiS(1, NaN), 0);
  assert.equal(P.bosKayitBayt({ onaysiz: 250 }), bolum * 0.75);
  assert.equal(P.bosKayitBayt({ onaysiz: -5 }), bolum);
  assert.equal(P.bosKayitBayt({ onaysiz: 5000 }), 0);
  assert.equal(P.bosKayitBayt(null), null);
  assert.equal(P.bosKayitBayt({ onaysiz: undefined }), null);
  assert.deepEqual(P.sureKisa(4739), { anahtar: "pt.saat", n: "1.3" });
  assert.deepEqual(P.sureKisa(36000 * 9), { anahtar: "pt.saat", n: "90" });
  assert.deepEqual(P.sureKisa(1800), { anahtar: "pt.dakika", n: "30" });
  assert.deepEqual(P.sureKisa(10), { anahtar: "pt.dakika", n: "1" });
  assert.deepEqual(P.sureKisa(0), { anahtar: "pt.dakika", n: "0" });
});

test("PT7: ayarFarki — istenen yoksa null; once hiz, sonra DCIR; bilinmeyen kart degeri fark sayilmaz", () => {
  assert.equal(P.ayarFarki(null, 1, 0), null);
  assert.deepEqual(P.ayarFarki({ hz: 20, dcir: true }, 1, 1), { tur: "hz", kart: 1, istenen: 20 });
  assert.deepEqual(P.ayarFarki({ hz: 20, dcir: true }, 20, 0), { tur: "dcir", kart: 0, istenen: 1 });
  assert.equal(P.ayarFarki({ hz: 20, dcir: true }, 20, 1), null);
  assert.equal(P.ayarFarki({ hz: 0, dcir: false }, null, null), null);
  assert.equal(P.ayarFarki({ hz: 0, dcir: false }, NaN, NaN), null);
});

// ── ptGorunum (ekran/pil.js PilPt'nin metinleri) + tercih ───────────────────
const D = (o = {}) => ({ pilKayitHz: 1, pilDcirAcik: false, pilPtDestek: null, pilIstenen: null, pilKartHz: null,
  pilKartDcir: null, pilDurum: "BEKLEMEDE", pilKayitOzet: null, pilNokta: [], kayit: { g: null }, dil: "tr", ...o });

test("ptGorunum: hiz secenekleri, sure yazisi (dayanagi ile), her ornek uyarisi, destek, dil", () => {
  const d = D({ pilKayitHz: 0 });
  let g = P.ptGorunum(d);
  assert.deepEqual(g.hizlar.map((h) => [h.v, h.ad]), [[1, "1/s"], [5, "5/s"], [20, "20/s"], [50, "50/s"], [0, "Her örnek (~400/s)"]]);
  assert.match(g.sure, /^Bu hızda en çok ~1\.\d sa kayıt \(11\.9 MB kayıt bölümüne göre; kartın boş yeri bilinmiyor\)\.$/);
  assert.match(g.uyariHer, /1 saatte/);
  assert.equal(g.hizEtiket, "Kayıt hızı");
  assert.equal(g.desteklenmiyor, "");
  d.kayit.g = { onaysiz: 500 };
  d.pilKayitHz = 50;
  g = P.ptGorunum(d);
  assert.match(g.sure, /^Bu hızda en çok ~54 dk kayıt \(kartın boş kayıt yeri ~6\.0 MB\)\.$/);
  assert.equal(g.uyariHer, "");
  d.dil = "en";
  d.pilKayitHz = 1;
  d.pilPtDestek = false;
  g = P.ptGorunum(d);
  assert.match(g.sure, /^At this rate up to ~\d+ h of recording \(board's free recording space ~6\.0 MB\)\.$/);
  assert.match(g.desteklenmiyor, /A3-PT1/);
  assert.equal(g.evre, "Measuring OCV (load off) — first 5 s");
  for (const v of Object.values(P.ptGorunum(D()))) if (typeof v === "string") assert.doesNotMatch(v, /pt\./, "ham anahtar");
});

test("ptGorunum: farkli ayar (yalniz test surerken), OCV lejanti (yalniz bant varken), DCIR kapali", () => {
  const fd = D({ pilDurum: "CALISIYOR", pilIstenen: { hz: 0, dcir: false }, pilKartHz: 5 });
  assert.equal(P.ptGorunum(fd).fark, "Kart testi istenenden farklı ayarla sürdürüyor: kayıt 5/s (istenen Her örnek (~400/s)).");
  fd.pilKartHz = 0; fd.pilKartDcir = 1;
  assert.equal(P.ptGorunum(fd).fark, "Kart testi istenenden farklı ayarla sürdürüyor: DCIR açık (istenen kapalı).");
  fd.pilDurum = "BITTI";
  assert.equal(P.ptGorunum(fd).fark, "");
  const ld = D();
  assert.equal(P.ptGorunum(ld).lejant, "");
  ld.pilPtDestek = true;
  assert.equal(P.ptGorunum(ld).lejant, "", "nokta yokken bant yok");
  ld.pilNokta = [{ ms: 1000 }];
  assert.equal(P.ptGorunum(ld).lejant, "OCV · yük kapalı ilk 5 s");
  ld.pilKayitOzet = { ocv: null };
  assert.equal(P.ptGorunum(ld).lejant, "", "kayitta KN_OCV yoksa (eski oturum) bant yok");
  ld.pilKayitOzet = { ocv: [0, 5000] };
  assert.equal(P.ptGorunum(ld).lejant, "OCV · yük kapalı ilk 5 s");
  assert.equal(P.ptGorunum(ld).dcirKapali, "Bu testte iç direnç ölçümü kapalı — yük hiç kesilmiyor.");
  assert.equal(P.ptGorunum(ld).kapali, "kapalı");
});

test("tercih / tercihVer: secim tarayicida (olcum.<ad>, JSON); kayitli tercih app.js'tekinden farkliysa verilir (bozuk -> 1/s, DCIR yalniz true); depo yoksa atmaz", () => {
  const ls = new Map();
  const eski = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, writable: true,
    value: { getItem: (k) => (ls.has(k) ? ls.get(k) : null), setItem: (k, v) => ls.set(k, String(v)) } });
  try {
    assert.equal(P.tercih("pilKayitHz", 20), 20);
    assert.equal(P.tercih("pilDcir", true), true);
    assert.equal(ls.get("olcum.pilKayitHz"), "20");
    assert.equal(ls.get("olcum.pilDcir"), "true");
    const v1 = [];
    P.tercihVer(D(), (a, v) => v1.push([a, v]));
    assert.deepEqual(v1, [["hz", 20], ["dcir", true]]);
    const v2 = [];
    P.tercihVer(D({ pilKayitHz: 20, pilDcirAcik: true }), (a, v) => v2.push([a, v]));
    assert.deepEqual(v2, [], "ayniysa olay yok");
    ls.set("olcum.pilKayitHz", "\"\"");
    ls.set("olcum.pilDcir", "\"evet\"");
    const v3 = [];
    P.tercihVer(D({ pilKayitHz: 5, pilDcirAcik: true }), (a, v) => v3.push([a, v]));
    assert.deepEqual(v3, [["hz", 1], ["dcir", false]]);
  } finally {
    if (eski) Object.defineProperty(globalThis, "localStorage", eski);
    else delete globalThis.localStorage;
  }
  const bos = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("depo yok"); } });
  try {
    assert.equal(P.tercih("pilKayitHz", 5), 5);
    const v4 = [];
    P.tercihVer(D(), (a, v) => v4.push([a, v]));
    assert.deepEqual(v4, []);
  } finally {
    if (bos) Object.defineProperty(globalThis, "localStorage", bos);
    else delete globalThis.localStorage;
  }
});
