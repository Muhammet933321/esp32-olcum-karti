// B73 / 2F — ortak/src/sozluk.js: TR/EN sozluk kapsami ve ceviri() geri dusme kurallari.
// Kod aileleri FIRMWARE basliklarindan okunur (kayit_bicim.h KB_SEBEP_ / KAYIT_OTURUM_ / KO_,
// pil_test.h PilDurum / PilHata, kalgec.h KGT_ / KGK_): kart yeni bir kod eklerse sozluk
// eksik kalir ve bu test kirmiziya doner. "Kullanilmayan anahtar yok" disari.js + rapor.js
// KAYNAGINDAN (yorumlar atilarak) olculur.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as K from "../src/kayit.js";
import { SOZLUK, DILLER, ceviri, ceviriKod } from "../src/sozluk.js";
import { KOLONLAR, BAYRAKLAR } from "../src/disari.js";
import { RAPOR_ETIKET, ALAN_ETIKET } from "../src/rapor.js";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const BICIM_H = oku("../../kod/olcum-karti-a3/kayit_bicim.h");
const PIL_H = oku("../../kod/olcum-karti-a3/pil_test.h");
const KALGEC_H = oku("../../kod/olcum-karti-a3/kalgec.h");
const KAYNAK = ["../src/disari.js", "../src/rapor.js"].map((y) => yorumsuz(oku(y))).join("\n");

function tanimlar(metin, onek) {
  return [...metin.matchAll(new RegExp(`#define ${onek}\\w+\\s+(\\d+)u`, "g"))].map((m) => Number(m[1]));
}

function enumDegerleri(metin, ad) {
  const m = metin.match(new RegExp(`enum ${ad}[^{]*\\{([^}]*)\\}`));
  assert.ok(m, `enum ${ad} bulunamadi`);
  let son = -1;
  const d = [];
  for (const parca of yorumsuz(m[1]).split(",")) {
    const s = parca.trim();
    if (!s) continue;
    const e = s.match(/^\w+\s*(?:=\s*(\d+))?$/);
    assert.ok(e, `enum ${ad}: ${s}`);
    son = e[1] !== undefined ? Number(e[1]) : son + 1;
    d.push(son);
  }
  return d;
}

const AILELER = [
  { onek: "sebep.", kodlar: tanimlar(BICIM_H, "KB_SEBEP_"), js: [...K.SEBEP.keys()] },
  { onek: "oturum.tur.", kodlar: tanimlar(BICIM_H, "KAYIT_OTURUM_"), js: [K.OTURUM_OLCUM, K.OTURUM_PIL, K.OTURUM_SKOP] },
  { onek: "olay.", kodlar: tanimlar(BICIM_H, "KO_"), js: [K.KO_PIL_AYAR, K.KO_DCIR, K.KO_PIL_SONUC, K.KO_SKOP_KAL, K.KO_PLAN] },
  { onek: "pil.durum.", kodlar: enumDegerleri(PIL_H, "PilDurum") },
  { onek: "pil.hata.", kodlar: enumDegerleri(PIL_H, "PilHata") },
  { onek: "kal.tur.", kodlar: tanimlar(KALGEC_H, "KGT_") },
  { onek: "kal.kaynak.", kodlar: tanimlar(KALGEC_H, "KGK_") },
];

test("her anahtarda bos olmayan tr VE en metni var (yalniz bu iki dil)", () => {
  assert.deepEqual([...DILLER], ["tr", "en"]);
  const anahtarlar = Object.keys(SOZLUK);
  assert.ok(anahtarlar.length > 150, `${anahtarlar.length}`);
  for (const a of anahtarlar) {
    assert.match(a, /^[a-z0-9_.]+$/, `anahtar ASCII nokta ayrimli olmali: ${a}`);
    assert.deepEqual(Object.keys(SOZLUK[a]).sort(), ["en", "tr"], a);
    for (const d of DILLER) {
      assert.equal(typeof SOZLUK[a][d], "string", `${a}.${d}`);
      assert.ok(SOZLUK[a][d].trim().length > 0, `${a}.${d} bos`);
    }
  }
});

test("kod aileleri: firmware'deki HER kodun (+ 'bilinmeyen') tr/en metni var", () => {
  for (const f of AILELER) {
    assert.ok(f.kodlar.length >= 2, `${f.onek}: firmware'den kod okunamadi`);
    assert.equal(new Set(f.kodlar).size, f.kodlar.length, `${f.onek}: tekrar eden kod`);
    if (f.js) assert.deepEqual([...f.js].sort(), [...f.kodlar].sort(), `${f.onek}: kayit.js firmware'le ayni degil`);
    for (const k of [...f.kodlar, "bilinmeyen"]) assert.ok(`${f.onek}${k}` in SOZLUK, `${f.onek}${k} yok`);
  }
  assert.deepEqual(AILELER[0].kodlar, [1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(AILELER[3].kodlar, [0, 1, 2, 3, 4]);
  assert.deepEqual(AILELER[4].kodlar, [0, 1, 2, 3, 4, 5, 6]);
});

test("CSV basliklari: her sutunun anahtari var; ASCII snake_case; birim soneki iki dilde AYNI (SI); tablo icinde tekil", () => {
  const birim = (s) => (s.match(/_(V|A|W|ohm|mAh|Wh|s|ms|us)$/) || [null, ""])[1];
  for (const [tablo, kol] of Object.entries(KOLONLAR)) {
    for (const d of DILLER) {
      const b = kol.map((k) => {
        assert.ok(k in SOZLUK, `${tablo}: ${k}`);
        return ceviri(k, d);
      });
      assert.equal(new Set(b).size, b.length, `${tablo} ${d}: tekrar eden baslik`);
      for (const s of b) assert.match(s, /^[a-z][a-z0-9_]*(_(V|A|W|ohm|mAh|Wh))?$/, `${tablo} ${d}: ${s}`);
    }
    for (const k of kol) assert.equal(birim(SOZLUK[k].tr), birim(SOZLUK[k].en), `${k}: birim dile gore degismemeli`);
  }
  for (const k of ["csv.kayit.nokta", "csv.kayit.dcir"]) assert.ok(k in SOZLUK, k);
});

test("bayraklar: kayit.js'teki her KN_/KAO_/KA_ biti adlandirilmis, anahtarlar sozlukte", () => {
  const bitler = (re) => Object.entries(K).filter(([a]) => re.test(a)).map(([, v]) => v).sort((x, y) => x - y);
  const tablo = (t) => t.map(([b]) => b).sort((x, y) => x - y);
  assert.deepEqual(tablo(BAYRAKLAR.nokta), bitler(/^KN_/));
  assert.deepEqual(tablo(BAYRAKLAR.ornek), bitler(/^KAO_/));
  assert.deepEqual(tablo(BAYRAKLAR.kayit), bitler(/^KA_/));
  for (const t of Object.values(BAYRAKLAR)) for (const [, a] of t) assert.ok(a in SOZLUK, a);
});

test("rapor: RAPOR_ETIKET / ALAN_ETIKET, uyar(...) ve kal durumlarinin anahtari var", () => {
  for (const a of [...Object.values(RAPOR_ETIKET), ...Object.values(ALAN_ETIKET)]) assert.ok(a in SOZLUK, a);
  const uyari = [...KAYNAK.matchAll(/uyar\("(\w+)"/g)].map((m) => m[1]);
  assert.ok(uyari.length >= 15, `${uyari.length}`);
  for (const u of uyari) assert.ok(`uyari.${u}` in SOZLUK, `uyari.${u}`);
  const durum = [...KAYNAK.matchAll(/durum\("(\w+)"\)/g)].map((m) => m[1]);
  assert.ok(durum.length >= 5);
  for (const d of durum) assert.ok(`kal.durum.${d}` in SOZLUK, `kal.durum.${d}`);
});

/** Kucuk JS sozcuk cozucu: yorumlari atlar; '...', "..." icerigini ve `...${ oneklerini toplar.
 *  (Regex sabitlerinde tirnak yok varsayimi: kaynak boyle yazildi, bozulursa asagidaki
 *  "dizge sayisi" denetimi kirmiziya doner.) */
function dizgeler(src) {
  const literal = new Set();
  const sablon = new Set();
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === "/" && src[i + 1] === "/") { const j = src.indexOf("\n", i); i = j < 0 ? src.length : j; continue; }
    if (c === "/" && src[i + 1] === "*") { i = src.indexOf("*/", i + 2) + 2; continue; }
    if (c === '"' || c === "'" || c === "`") {
      let j = i + 1;
      let s = "";
      let onek = null;
      while (j < src.length && src[j] !== c) {
        if (src[j] === "\\") { s += src[j + 1]; j += 2; continue; }
        if (c === "`" && src[j] === "$" && src[j + 1] === "{" && onek === null) onek = s;
        if (src[j] === "\n" && c !== "`") throw new Error(`kapanmamis dizge: ${src.slice(i, i + 40)}`);
        s += src[j];
        j++;
      }
      if (c === "`") { if (onek !== null) sablon.add(onek); } else literal.add(s);
      i = j + 1;
      continue;
    }
    i++;
  }
  return { literal, sablon };
}

test("kullanilmayan anahtar YOK (disari.js + rapor.js kaynagindan)", () => {
  const ham = ["../src/disari.js", "../src/rapor.js"].map(oku).join("\n");
  const { literal, sablon } = dizgeler(ham);
  assert.ok(literal.has("csv.v_ort") && literal.has("rapor.kimlik") && literal.has("sebep."), "cozucu dizgeleri kaciriyor");
  assert.ok(sablon.has("kal.durum.") && sablon.has("uyari."), "cozucu sablonlari kaciriyor");
  const aile = [...AILELER.map((f) => f.onek), "kal.durum.", "uyari."];
  const kodu = new Map(AILELER.map((f) => [f.onek, new Set(f.kodlar.map(String))]));
  const kullanilmayan = Object.keys(SOZLUK).filter((a) => {
    if (literal.has(a)) return false;
    for (const p of aile) {
      if (!a.startsWith(p) || !(literal.has(p) || sablon.has(p))) continue;
      const son = a.slice(p.length);
      if (son === "bilinmeyen" && kodu.has(p)) return false;
      if ((kodu.get(p) && kodu.get(p).has(son)) || literal.has(son)) return false;
    }
    return true;
  });
  assert.deepEqual(kullanilmayan, []);
});

test("yer tutucular iki dilde ayni", () => {
  const yer = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const [a, g] of Object.entries(SOZLUK)) assert.equal(yer(g.tr), yer(g.en), a);
});

// ── ceviri ───────────────────────────────────────────────────────────
test("ceviri: dil secimi, varsayilan tr, bilinmeyen dil -> tr", () => {
  assert.equal(ceviri("sebep.1", "tr"), "kullanıcı durdurdu");
  assert.equal(ceviri("sebep.1", "en"), "stopped by user");
  assert.equal(ceviri("sebep.1"), "kullanıcı durdurdu");
  for (const d of ["de", "", null, undefined, 3, "EN"]) assert.equal(ceviri("sebep.1", d), "kullanıcı durdurdu", String(d));
});

test("ceviri: bilinmeyen anahtar ANAHTARIN KENDISI; hicbir girdide atmaz", () => {
  assert.equal(ceviri("yok.boyle.bir.anahtar", "en"), "yok.boyle.bir.anahtar");
  for (const a of ["__proto__", "constructor", "toString", "hasOwnProperty"]) assert.equal(ceviri(a, "tr"), a);
  for (const a of [undefined, null, 42, {}, [], true, Symbol("x")]) {
    assert.doesNotThrow(() => ceviri(a, "tr"), String(typeof a));
    assert.equal(typeof ceviri(a, "en"), "string");
  }
  assert.equal(ceviri(42), "42");
});

test("ceviri: degiskenler yerine konur; verilmeyen yer tutucu kalir; tuhaf degiskenler atmaz", () => {
  assert.equal(ceviri("uyari.devam", "tr", { sayi: 3 }), "Kart 3 kez yeniden başladı, kayıt sürdü (araya boşluk girdi).");
  assert.equal(ceviri("uyari.devam", "en", { sayi: 3 }), "The board restarted 3 time(s) and recording resumed (gaps in between).");
  assert.ok(ceviri("uyari.devam", "tr").includes("{sayi}"));
  assert.ok(ceviri("uyari.devam", "tr", { baska: 1 }).includes("{sayi}"));
  assert.equal(ceviri("uyari.kal_farkli", "en", { no: 7 }).includes("no 7"), true);
  for (const d of [null, 5, "x", [], { sayi: null }, { sayi: { a: 1 } }]) {
    assert.doesNotThrow(() => ceviri("uyari.devam", "tr", d));
  }
  assert.equal(ceviri("uyari.devam", "tr", { sayi: "$&" }).includes("$&"), true, "replace kalibi yorumlanmamali");
});

test("ceviriKod: bilinen kod -> metni, bilinmeyen -> '<onek>bilinmeyen' {kod}; atmaz", () => {
  assert.equal(ceviriKod("olay.", 2, "tr"), ceviri("olay.2", "tr"));
  assert.equal(ceviriKod("sebep.", 99, "en"), "unknown reason (99)");
  assert.equal(ceviriKod("pil.hata.", 77, "tr"), "bilinmeyen hata (77)");
  assert.equal(ceviriKod("yok.", 1, "tr"), "yok.bilinmeyen");
  assert.doesNotThrow(() => ceviriKod(undefined, undefined, undefined));
});
