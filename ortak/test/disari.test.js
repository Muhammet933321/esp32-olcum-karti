// B73 / 2F — ortak/src/disari.js: CSV (Excel-TR) + ham disa aktarma.
// Capraz vektorler: uretim/ortak_vektor_disari.py -> test/vektor/disari.json (Python
// kopru/kayit_bicim.py + bagimsiz Python zaman/enerji/bicim kodu). Altin dizgeler bu dosyada
// ELLE hesaplandi (kalibrasyon ikili kesir: volt = kod/8, amper = kod/1024).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import * as K from "../src/kayit.js";
import * as D from "../src/disari.js";
import { oturumRaporu } from "../src/rapor.js";
import { ceviri } from "../src/sozluk.js";

const V = JSON.parse(readFileSync(new URL("./vektor/disari.json", import.meta.url), "utf8"));

// ── yardimcilar ──────────────────────────────────────────────────────
const hexten = (s) => Uint8Array.from(s.match(/../g) ?? [], (h) => parseInt(h, 16));
const jsden = (x) => (x && typeof x === "object" && "$f" in x ? { nan: NaN, inf: Infinity, "-inf": -Infinity }[x.$f] : x);
const birlestir = (...p) => {
  const b = new Uint8Array(p.reduce((a, x) => a + x.length, 0));
  let a = 0;
  for (const x of p) { b.set(x, a); a += x.length; }
  return b;
};
const u32 = (...xs) => {
  const b = new Uint8Array(4 * xs.length);
  const v = new DataView(b.buffer);
  xs.forEach((x, i) => v.setUint32(4 * i, x, true));
  return b;
};
const bitirYuk = (n, s) => { const b = new Uint8Array(8); new DataView(b.buffer).setUint32(0, n, true); b[4] = s; return b; };
const utf8 = (s) => new TextEncoder().encode(s);

class Akis {
  constructor(sira = 0) { this.sira = sira; this.parca = []; }
  ekle(tur, oturum, yuk) { this.sira += 1; this.parca.push(K.kayitPaketle(tur, this.sira, oturum, yuk)); return this.sira; }
  bayt() { return birlestir(...this.parca); }
}

/** RFC 4180 ayristirici (test icin bagimsiz): BOM'u atar, CRLF/LF satir sonu. */
function csvAyristir(metin, ayrac) {
  let s = metin.startsWith("﻿") ? metin.slice(1) : metin;
  const satirlar = [];
  let satir = [];
  let alan = "";
  let tirnak = false;
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (tirnak) {
      if (c === '"' && s[i + 1] === '"') { alan += '"'; i += 2; continue; }
      if (c === '"') { tirnak = false; i++; continue; }
      alan += c; i++; continue;
    }
    if (c === '"' && alan === "") { tirnak = true; i++; continue; }
    if (c === ayrac) { satir.push(alan); alan = ""; i++; continue; }
    if (c === "\r" || c === "\n") {
      satir.push(alan); alan = ""; satirlar.push(satir); satir = [];
      i += c === "\r" && s[i + 1] === "\n" ? 2 : 1;
      continue;
    }
    alan += c; i++;
  }
  assert.equal(tirnak, false, "kapanmamis tirnak");
  assert.equal(alan === "" && satir.length === 0, true, "son satir satir sonuyla bitmeli");
  return satirlar;
}

// Altin oturum: volt = kod/8 (normal), kod/4 (yuksek); amper = kod/1024 — ikili kesir, elle hesap
const KAL = {
  normal: { n: 1, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
  yuksek: { n: 2, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
  i_ofset: 0, i_pga: 32, sont_ohm: 1, i_duzeltme: 1, sebeke_hz: 50, faz_kal_us: [0, 0],
};
const P = (ms, v, i, w, b = 0, n = 10) => ({ kart_ms: ms, n, bayrak: b, v_ort_kod: v,
  v_min_kod: Math.floor(v) - 1, v_maks_kod: Math.ceil(v) + 1, i_ort_kod: i, i_min_kod: Math.floor(i),
  i_maks_kod: Math.ceil(i), w_ort: w, w_min: w / 2, w_maks: w * 2 });
const BASLA = (tur, hiz, unix, kart, acilis, kalNo = 2) => K.baslaPaketle({ oturum_turu: tur, kal_bicim: 1,
  hiz_ms: hiz, unix_s: unix, kart_ms: kart, acilis, surum: "A3-2F", kal: KAL, kal_no: kalNo });

function altinAkis() {
  const a = new Akis(40);
  const id = a.ekle(K.T_BASLA, 41, BASLA(1, 1000, 1790000000, 5000, 3));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), K.noktaPaketle(P(6000, 12.5, 1000, 0.25)),
    K.noktaPaketle(P(7000, 13, 1001, 0.5, K.KN_YUKSEK)),
    K.noktaPaketle(P(8000, 0, 0, 0, K.KN_V_HATA | K.KN_I_HATA, 0))));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 0, 0, utf8("güç; 5 V")));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 6500, 0, utf8('=ölçüm "şarj"')));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 7000, 0, utf8("Ğİı, son")));
  a.ekle(K.T_BITIR, id, bitirYuk(3, 1));
  return [a.bayt(), id];
}

function oturumAl(veri, id) {
  const kay = K.akisCoz(veri);
  return [K.oturumlariKur(kay).get(id), kay];
}

// ── sayi yazimi ──────────────────────────────────────────────────────
test("sayiYaz == Python format(x, '.Nf') (yarida cifte, tam ikili deger) — capraz vektorler", () => {
  assert.ok(V.sayi.length > 1000);
  let ortada = 0;
  for (const [xj, b, beklenen] of V.sayi) {
    const x = jsden(xj);
    assert.equal(D.sayiYaz(x, b), beklenen, `${x} .${b}f`);
    assert.equal(D.sayiYaz(x, b, ","), beklenen.replace(".", ","), `${x} .${b}f virgul`);
    if (Number.isFinite(x) && x.toFixed(b) !== beklenen && Math.abs(x) < 1e21 && !/^-0/.test(x.toFixed(b))) ortada++;
  }
  assert.ok(ortada >= 20, `toFixed'in yanildigi (tam ortada) vaka sayisi az: ${ortada}`);
});

test("sayiYaz: ustel yok, binlik yok, sonlu olmayan bos, eksi sifir isaretsiz", () => {
  assert.equal(D.sayiYaz(1e22, 0), "10000000000000000000000");
  assert.equal(D.sayiYaz(1e-7, 6), "0.000000");
  assert.equal(D.sayiYaz(-1e-9, 6), "0.000000");
  assert.equal(D.sayiYaz(-0, 3), "0.000");
  assert.equal(D.sayiYaz(-0.5, 0), "0");
  assert.equal(D.sayiYaz(-1.5, 0), "-2");
  assert.equal(D.sayiYaz(1234567.5, 0, ","), "1234568");
  assert.equal(D.sayiYaz(0.9765625, 6, ","), "0,976562");
  for (const x of [NaN, Infinity, -Infinity, null, undefined, "1"]) assert.equal(D.sayiYaz(x, 6), "");
  assert.throws(() => D.sayiYaz(1, -1), RangeError);
  assert.throws(() => D.sayiYaz(1, 1.5), RangeError);
});

test("olcekliYaz: tamsayi birimden kayan noktasiz", () => {
  assert.equal(D.olcekliYaz(1790000000123, 3), "1790000000.123");
  assert.equal(D.olcekliYaz(5, 3, ","), "0,005");
  assert.equal(D.olcekliYaz(-5, 3), "-0.005");
  assert.equal(D.olcekliYaz(42, 0), "42");
  assert.equal(D.olcekliYaz(1.5, 3), "");
  assert.equal(D.olcekliYaz(NaN, 3), "");
});

// ── altin CSV ────────────────────────────────────────────────────────
const ALTIN_TR = "﻿"
  + "sira;acilis;devam;kart_ms;gecen_ms;unix_s;zaman_utc;n;v_ort_V;v_min_V;v_maks_V;i_ort_A;i_min_A;i_maks_A;"
  + "w_ort_W;w_min_W;w_maks_W;bayrak;bayraklar;not\r\n"
  + "0;0;0;6000;1000;1790000001,000;2026-09-21T14:13:21.000Z;10;1,562500;1,375000;1,750000;"
  + "0,976562;0,976562;0,976562;0,250000;0,125000;0,500000;0;;\"güç; 5 V\"\r\n"
  + "1;0;0;7000;2000;1790000002,000;2026-09-21T14:13:22.000Z;10;3,250000;3,000000;3,500000;"
  + "0,977539;0,977539;0,977539;0,500000;0,250000;1,000000;1;YUKSEK;\"'=ölçüm \"\"şarj\"\"\nĞİı, son\"\r\n"
  + "2;0;0;8000;3000;1790000003,000;2026-09-21T14:13:23.000Z;0;;;;;;;;;;6;V_HATA|I_HATA;\r\n";

const ALTIN_EN = "﻿"
  + "seq,boot,resumed,board_ms,elapsed_ms,unix_s,time_utc,n,v_avg_V,v_min_V,v_max_V,i_avg_A,i_min_A,i_max_A,"
  + "p_avg_W,p_min_W,p_max_W,flags,flag_names,note\r\n"
  + "0,0,0,6000,1000,1790000001.000,2026-09-21T14:13:21.000Z,10,1.562500,1.375000,1.750000,"
  + "0.976562,0.976562,0.976562,0.250000,0.125000,0.500000,0,,güç; 5 V\r\n"
  + "1,0,0,7000,2000,1790000002.000,2026-09-21T14:13:22.000Z,10,3.250000,3.000000,3.500000,"
  + "0.977539,0.977539,0.977539,0.500000,0.250000,1.000000,1,HIGH_RANGE,\"'=ölçüm \"\"şarj\"\"\nĞİı, son\"\r\n"
  + "2,0,0,8000,3000,1790000003.000,2026-09-21T14:13:23.000Z,0,,,,,,,,,,6,V_ERROR|I_ERROR,\r\n";

test("oturumCsv altin metin: BOM + ';' + CRLF + ondalik virgul + RFC 4180 + formul onegi + Turkce", () => {
  const [o] = oturumAl(...altinAkis());
  assert.equal(D.oturumCsv(o), ALTIN_TR);
  assert.equal(D.oturumCsv(o, D.BICIM_EXCEL_TR), ALTIN_TR);
});

test("oturumCsv altin metin: BICIM_EN (',' ayrac, '.' ondalik, Ingilizce baslik/bayrak)", () => {
  const [o] = oturumAl(...altinAkis());
  assert.equal(D.oturumCsv(o, D.BICIM_EN), ALTIN_EN);
});

test("secenekler: BOM'suz, LF, '\\t' ayrac; gecersiz secenek RangeError", () => {
  const [o] = oturumAl(...altinAkis());
  const c = D.oturumCsv(o, { bom: false, satirSonu: "\n" });
  assert.equal(c, ALTIN_TR.slice(1).replace(/\r\n/g, "\n"));
  const t = D.oturumCsv(o, { ayrac: "\t" });
  assert.equal(csvAyristir(t, "\t")[1][19], "güç; 5 V", "';' TAB ayracta tirnak gerektirmez");
  assert.ok(!t.includes('"güç; 5 V"'));
  for (const s of [{ ayrac: "," }, { ayrac: ";", ondalik: ";" }, { ondalik: "x" }, { dil: "de" },
    { satirSonu: "\r\r" }, { ayrac: '"' }, { ayrac: ";;" }]) {
    assert.throws(() => D.oturumCsv(o, s), RangeError, JSON.stringify(s));
  }
});

test("csvBayt: UTF-8, BOM = EF BB BF, Turkce karakter cok baytli", () => {
  const [o] = oturumAl(...altinAkis());
  const b = D.csvBayt(D.oturumCsv(o));
  assert.deepEqual([...b.subarray(0, 3)], [0xEF, 0xBB, 0xBF]);
  assert.equal(new TextDecoder("utf-8", { ignoreBOM: true }).decode(b), ALTIN_TR);
  const bomsuz = D.csvBayt(D.oturumCsv(o, { bom: false }));
  assert.notEqual(bomsuz[0], 0xEF);
});

test("metinHucre: RFC 4180 tirnak + formul onegi yalniz metne", () => {
  assert.equal(D.metinHucre("a;b", ";"), '"a;b"');
  assert.equal(D.metinHucre("a;b", ","), "a;b");
  assert.equal(D.metinHucre('a"b', ","), '"a""b"');
  assert.equal(D.metinHucre("a\rb", ","), '"a\rb"');
  assert.equal(D.metinHucre("a\nb", ","), '"a\nb"');
  for (const s of ["=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"]) {
    assert.equal(D.metinHucre(s, ";").replace(/^"/, "").startsWith("'"), true, s);
  }
  assert.equal(D.metinHucre("ölçüm", ";"), "ölçüm");
  assert.equal(D.metinHucre(null, ";"), "");
});

// ── sutun sayilari ───────────────────────────────────────────────────
function tumCsvler() {
  const [o] = oturumAl(...altinAkis());
  const ol = V.olcum.map((v) => oturumAl(hexten(v.veri), v.oturum)[0]);
  const [p] = oturumAl(hexten(V.pil[0].veri), V.pil[0].oturum);
  const [a] = oturumAl(hexten(V.ayrinti[0].veri), V.ayrinti[0].oturum);
  const s = skopOturumu()[0];
  const y = [...s.skoplar.values()].find((x) => x.tam);
  return [["nokta", (b) => D.oturumCsv(o, b)], ["nokta", (b) => D.oturumCsv(ol[0], b)],
    ["nokta", (b) => D.oturumCsv(ol[1], b)], ["pil", (b) => D.pilCsv(p, b)],
    ["ayrinti", (b) => D.ayrintiCsv(a, b)], ["skop", (b) => D.skopCsv(y, b)]];
}

test("her CSV: baslik + her satir KOLONLAR kadar alan, baslik sozlukten, bos satir yok (TR ve EN)", () => {
  for (const [tur, uret] of tumCsvler()) {
    for (const b of [D.BICIM_EXCEL_TR, D.BICIM_EN]) {
      const metin = uret(b);
      assert.ok(metin.startsWith("﻿"));
      const sat = csvAyristir(metin, b.ayrac);
      const kol = D.KOLONLAR[tur];
      assert.deepEqual(sat[0], kol.map((k) => ceviri(k, b.dil)), `${tur} ${b.dil} baslik`);
      assert.ok(sat.length > 1, `${tur}: veri satiri yok`);
      for (const [k, s] of sat.entries()) {
        assert.equal(s.length, kol.length, `${tur} ${b.dil} satir ${k}`);
        assert.ok(s.some((x) => x !== ""), `${tur} ${b.dil}: bos satir ${k}`);
      }
      // satir sonu YALNIZ secilen bicimde: tirnak disinda tek basina LF / CR yok
      const disari = metin.replace(/"(?:[^"]|"")*"/g, "");
      assert.equal(disari.replace(/\r\n/g, "").search(/[\r\n]/), -1, `${tur} ${b.dil}: CRLF disi satir sonu`);
    }
  }
});

// ── capraz: olcum (nokta) ────────────────────────────────────────────
const NOKTA_SUTUN = ["sira", "acilis", "kart_ms", "gecen_ms", "unix_s", "zaman_utc", "n", "v_ort_V", "v_min_V",
  "v_maks_V", "i_ort_A", "i_min_A", "i_maks_A", "w_ort_W", "w_min_W", "w_maks_W", "bayrak"];

for (const v of V.olcum) {
  test(`oturumCsv == Python hucreleri: ${v.ad} (zaman modeli, YUKSEK kanal, n=0, sarma)`, () => {
    const [o] = oturumAl(hexten(v.veri), v.oturum);
    const sat = csvAyristir(D.oturumCsv(o, { ondalik: "." }), ";");
    const indis = NOKTA_SUTUN.map((a) => sat[0].indexOf(a));
    assert.ok(indis.every((x) => x >= 0));
    assert.equal(sat.length - 1, v.nokta.length);
    v.nokta.forEach((beklenen, k) => {
      assert.deepEqual(indis.map((j) => sat[k + 1][j]), beklenen, `satir ${k}`);
    });
  });

  test(`oturumCsv V/A == kayit.js volt/amper (ayni sayinin yazimi): ${v.ad}`, () => {
    const [o] = oturumAl(hexten(v.veri), v.oturum);
    const sat = csvAyristir(D.oturumCsv(o), ";");
    const kal = o.basla.kal;
    const nk = [...o.noktalar].sort((a, b) => a[0] - b[0]);
    let yuksek = 0;
    nk.forEach(([, p], k) => {
      const r = sat[k + 1];
      if (p.n === 0) {
        assert.deepEqual(r.slice(8, 17), Array(9).fill(""), "n=0: V/A/W bos");
        return;
      }
      const kn = p.bayrak & K.KN_YUKSEK ? kal.yuksek : kal.normal;
      yuksek += p.bayrak & K.KN_YUKSEK ? 1 : 0;
      const bek = [K.volt(p.v_ort_kod, kn, false), K.volt(p.v_min_kod, kn, true), K.volt(p.v_maks_kod, kn, true),
        K.amper(p.i_ort_kod, kal, false), K.amper(p.i_min_kod, kal, true), K.amper(p.i_maks_kod, kal, true),
        p.w_ort, p.w_min, p.w_maks].map((x) => D.sayiYaz(x, 6, ","));
      assert.deepEqual(r.slice(8, 17), bek, `satir ${k}`);
    });
    assert.ok(yuksek > 0, "vektorde YUKSEK menzilli nokta yok");
  });
}

test("DEVAM: bos satir YOK, devam sutunu DEVAM'dan sonraki ILK satirda 1, acilis artar", () => {
  const v = V.olcum[0];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const sat = csvAyristir(D.oturumCsv(o), ";").slice(1);
  assert.equal(sat.length, o.noktalar.length);
  const devamSira = sat.filter((r) => r[2] === "1").map((r) => Number(r[0]));
  assert.deepEqual(devamSira, o.devamlar.map((d) => d.nokta_sira));
  assert.deepEqual([...new Set(sat.map((r) => r[1]))], ["0", "1", "2"]);
  assert.ok(sat.every((r) => r[2] === "0" || r[2] === "1"));
});

test("saatsiz akis: SAAT unix'i acilis 0'a baglar; saatsiz DEVAM'dan sonra gecen/unix BOS", () => {
  const v = V.olcum[1];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const sat = csvAyristir(D.oturumCsv(o), ";").slice(1);
  assert.ok(sat.filter((r) => r[1] === "0").every((r) => r[4] !== "" && r[5] !== ""));
  assert.ok(sat.filter((r) => r[1] !== "0").every((r) => r[4] === "" && r[5] === "" && r[6] === ""));
});

// ── capraz: pil ──────────────────────────────────────────────────────
test("pilCsv == Python: nokta + DCIR satirlari zaman sirasinda, birikimli mAh/Wh", () => {
  const v = V.pil[0];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const sat = csvAyristir(D.pilCsv(o, { ondalik: "." }), ";");
  const ad = ["kayit", "sira", "kart_ms", "yuk_mAh", "enerji_Wh", "dcir_no", "dcir_r_ani_ohm",
    "dcir_r_oturmus_ohm", "dcir_yuk_mAh"];
  const indis = ad.map((a) => sat[0].indexOf(a));
  assert.ok(indis.every((x) => x >= 0), "pil sutunu yok");
  assert.equal(sat.length - 1, v.satirlar.length);
  v.satirlar.forEach((b, k) => assert.deepEqual(indis.map((j) => sat[k + 1][j]), b, `satir ${k}`));
  // DCIR satirinda nokta sutunlari bos, nokta satirinda dcir sutunlari bos
  const dcirNo = sat[0].indexOf("dcir_no");
  const vOrt = sat[0].indexOf("v_ort_V");
  for (const r of sat.slice(1)) {
    if (r[0] === "dcir") assert.equal(r[vOrt], "");
    else assert.equal(r[dcirNo], "");
  }
  assert.equal(sat.filter((r) => r[0] === "dcir").length, 5);
});

test("pilCsv son nokta satiri == rapor enerjisi == Python enerjisi (bit bit)", () => {
  const v = V.pil[0];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const r = oturumRaporu(o);
  assert.equal(r.enerji.mah, jsden(v.enerji.mah));
  assert.equal(r.enerji.wh, jsden(v.enerji.wh));
  const sat = csvAyristir(D.pilCsv(o), ";");
  const son = sat.filter((x) => x[0] === "nokta").pop();
  assert.equal(son[sat[0].indexOf("yuk_mAh")], D.sayiYaz(r.enerji.mah, 6, ","));
  assert.equal(son[sat[0].indexOf("enerji_Wh")], D.sayiYaz(r.enerji.wh, 6, ","));
  for (const vo of V.olcum) {
    const [oo] = oturumAl(hexten(vo.veri), vo.oturum);
    const ro = oturumRaporu(oo);
    assert.equal(ro.enerji.mah, jsden(vo.enerji.mah), vo.ad);
    assert.equal(ro.enerji.wh, jsden(vo.enerji.wh), vo.ad);
  }
});

// ── capraz: ayrinti ──────────────────────────────────────────────────
test("ayrintiCsv == Python: us zamani, KA bayragi kaydin ilk orneginde, hatali ornek bos", () => {
  const v = V.ayrinti[0];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const sat = csvAyristir(D.ayrintiCsv(o, { ondalik: "." }), ";");
  const ad = ["sira", "acilis", "kart_us", "gecen_ms", "unix_s", "zaman_utc", "v_V", "i_A", "w_W",
    "ornek_bayrak", "kayit_bayrak"];
  const indis = ad.map((a) => sat[0].indexOf(a));
  assert.equal(sat.length - 1, v.satirlar.length);
  v.satirlar.forEach((b, k) => assert.deepEqual(indis.map((j) => sat[k + 1][j]), b, `satir ${k}`));
  const kb = sat.slice(1).map((r) => Number(r[indis[10]]));
  assert.ok(kb.includes(K.KA_SILME) && kb.includes(K.KA_KAYIP_ONCE));
  const devam = sat.slice(1).filter((r) => r[2] === "1");
  assert.equal(devam.length, 1);
  assert.ok(sat.slice(1).some((r) => r[sat[0].indexOf("bayraklar")].includes("SILME")));
});

// ── W1: hizali guc + yakalama boslugu ────────────────────────────────
test("W1: ayrintili W == Python bagimsiz hizali guc (bit bit) == kayit.js ayrintiGuc; ayni satirin V x A'si DEGIL", () => {
  const v = V.ayrinti[0];
  const [o] = oturumAl(hexten(v.veri), v.oturum);
  const s = D.ayrintiSerileri(o);
  const py = v.w.map(jsden);
  assert.equal(s.adet, py.length);
  for (let k = 0; k < s.adet; k++) assert.ok(Object.is(s.w[k], py[k]), `ornek ${k}: ${s.w[k]} != ${py[k]}`);
  assert.deepEqual(K.ayrintiGuc(o).map(([, w]) => w), Array.from(s.w));
  let farkli = 0;
  for (let k = 0; k < s.adet; k++) if (Number.isFinite(s.w[k]) && s.w[k] !== s.v[k] * s.i[k]) farkli++;
  assert.ok(farkli > s.adet / 2, `yalniz ${farkli}/${s.adet} ornekte hizali W farkli: test bos`);
  assert.ok(py.some((x) => Number.isNaN(x)) && py.filter(Number.isFinite).length > 20);
});

test("W1/Y7: yakalamadan sonraki ilk satirin bayraklarinda SKOP (EN: SCOPE_CAPTURE), yalniz orada; sayisal bayrak degismez", () => {
  const vakalar = [...V.olcum.map((v) => [v, D.oturumCsv]), [V.ayrinti[0], D.ayrintiCsv]];
  for (const [v, csv] of vakalar) {
    const [o] = oturumAl(hexten(v.veri), v.oturum);
    for (const [bicim, ad] of [[{}, "SKOP"], [D.BICIM_EN, "SCOPE_CAPTURE"]]) {
      const sat = csvAyristir(csv(o, bicim), bicim.ayrac || ";");
      const iB = sat[0].findIndex((x) => /^(bayraklar|flag_names)$/.test(x));
      const iS = 0;
      assert.ok(iB > 0, sat[0].join());
      const isaretli = sat.slice(1).filter((r) => r[iB].split("|").includes(ad)).map((r) => Number(r[iS]));
      assert.deepEqual(isaretli, v.skop_sonra, `${v.ad || "ayrinti"} ${ad}`);
    }
    assert.ok(v.skop_sonra.length >= 1, "vektorde yakalama yok: test bos");
  }
});

/** Ayrintili oturumun kayitlarina t0_us okuma sayaci takar. ayrintiOrnekler kayit basina t0_us'u
 *  IKI kez okur (sarma k'si + baslangic); baska hicbir ortak/ islevi okumaz. Donus: () -> o ana dek
 *  kac ayrintiOrnekler kurulumu oldu (sayac sifirlanir). */
function kurulumSayaci(o) {
  let okuma = 0;
  o.ayrinti = o.ayrinti.map((r) => {
    const { t0_us: t0, ...g } = r;
    return Object.defineProperty(g, "t0_us", { get() { okuma++; return t0; }, enumerable: true });
  });
  const n = o.ayrinti.length;
  return () => { const k = okuma / (2 * n); okuma = 0; return k; };
}

test("W1-tek-kurulum: ayrintiSerileri / ayrintiCsv / oturumRaporu ornek listesini BIRER kez kurar (guc + Y7 ayni listeyi kullanir)", () => {
  const v = V.ayrinti[0];
  const [o, kay] = oturumAl(hexten(v.veri), v.oturum);
  assert.ok(o.skoplar.size > 0 && o.ayrinti.length > 1, "vektorde yakalama/ayrinti yok: test bos");
  const kurulum = kurulumSayaci(o);
  K.ayrintiOrnekler(o);
  assert.equal(kurulum(), 1, "sayac ayrintiOrnekler'i saymiyor: test bos");
  const s = D.ayrintiSerileri(o);
  assert.equal(kurulum(), 1, "ayrintiSerileri");
  assert.deepEqual(s.yerler, K.skopYerleri(o), "seri.yerler != skopYerleri");
  kurulum();
  D.ayrintiCsv(o);
  assert.equal(kurulum(), 1, "ayrintiCsv");
  oturumRaporu(o, { kayitlar: kay });
  assert.equal(kurulum(), 1, "oturumRaporu (skopYerleri seriden gelmeli)");
});

// W1 inceleme: hizali W + Y7 eklenince ayrintiSerileri sirali ornek listesini 3-4 kez kuruyordu
// (kendisi, ayrintiGuc, skopYerleri/olcumZamanlari): dolu 11.4 MB bolum (~1.9 M ornek) 1 GB
// yiginda OOM, 600 k ornek 300 MB'ta OOM. W1 oncesi kod 600 k'yi 200 MB'ta bitiriyordu; sinir
// 250 MB. Ayri surec: yigin siniri yalniz komut satirindan verilir.
test("W1-bellek: 600 k ornekli yakalamali ayrintili oturum 250 MB yiginda ayrintiSerileri'ni bitirir", () => {
  const N = 600000;
  const disari = new URL("../src/disari.js", import.meta.url).href;
  const kod = `
    const D = await import(${JSON.stringify(disari)});
    const N = ${N};
    const kanal = { sifir_ham: 0, pga: 4.096, n: 1, kazanc: 1, tau: 0.0021 };
    const kal = { normal: kanal, yuksek: kanal, i_ofset: 0, i_pga: 0.256, sont_ohm: 0.005,
      i_duzeltme: 1, sebeke_hz: 50, faz_kal_us: [0, 0] };
    const o = { id: 1, basla: { tur: 1, hiz_ms: 0, acilis: 1, unix_s: 1.8e9, kart_ms: 1000, ad: "", kal, kal_no: 0 },
      bitir: null, noktalar: [], olaylar: [], devamlar: [], saatler: [], ad: "", etiketler: [],
      notlar: new Map(), ayrinti: [], skoplar: new Map() };
    const PER = 1300;
    let us = 1000000;
    for (let s = 0, r = 0; s < N; s += PER, r++) {
      const orn = [];
      for (let j = 0; j < PER && s + j < N; j++) orn.push([(j * 37) % 20000 - 10000, (j * 53) % 9000, j ? 500 : 0, 0]);
      o.ayrinti.push({ ilk: s, t0_ms: Math.floor(us / 1000), t0_us: us, bayrak: 0, ornekler: orn, sira: r + 10 });
      us += 2000 * PER + 20000;
    }
    o.skoplar.set(5, { no: 1, meta: { t_ms: 5000, sure_ms: 30 }, toplam: 1, t_sira: 5, acilis: 0, tam: true, kodlar: [] });
    const r = D.ayrintiSerileri(o);
    let w = 0;
    for (let k = 0; k < r.adet; k++) if (Number.isFinite(r.w[k])) w++;
    console.log(JSON.stringify({ n: r.adet, w, skop: r.skop.filter((x) => x).length }));
  `;
  const r = spawnSync(process.execPath, ["--max-old-space-size=250", "--input-type=module", "-e", kod],
    { encoding: "utf8", timeout: 300000 });
  assert.equal(r.status, 0, `cikis ${r.status}: ${(r.stderr || "").slice(-300)}`);
  const j = JSON.parse(r.stdout.trim().split("\n").pop());
  assert.equal(j.n, N);
  assert.ok(j.w > N * 0.9, `hizali W yalniz ${j.w} ornekte: test bos`);
  assert.equal(j.skop, 1, "yakalama isaretlenmedi: skop yolu kosmadi, test bos");
});

// ── skop ─────────────────────────────────────────────────────────────
function skopOturumu() {
  const a = new Akis(500);
  const id = a.ekle(K.T_BASLA, 501, BASLA(K.OTURUM_SKOP, 0, 1790000000, 1000, 4));
  const meta = { t_ms: 1500, sure_ms: 40, hz: 50000, tdiv_us: 100, adim: Math.fround(0.0119), ofset: Math.fround(63.5),
    tetik: 2, esik: 2048, histerezis: 40, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 25, onay: 2 };
  const kodlar = [0, 1000, 2048, 4095, 5336];
  a.ekle(K.T_SKOP, id, K.skopPaketle({ no: 1, ilk: 0, toplam: 5, parca: 0, meta, kodlar: kodlar.slice(0, 3) }));
  a.ekle(K.T_SKOP, id, K.skopPaketle({ no: 1, ilk: 3, toplam: 5, parca: 1, kodlar: kodlar.slice(3) }));
  a.ekle(K.T_SKOP, id, K.skopPaketle({ no: 2, ilk: 0, toplam: 5, parca: 0, meta, kodlar: kodlar.slice(0, 3) }));
  a.ekle(K.T_BITIR, id, bitirYuk(0, 1));
  const [o, kay] = oturumAl(a.bayt(), id);
  return [o, kay, kodlar, meta];
}

test("skopCsv: t_s = (i - tetik)/hz, v_V = kod*adim - ofset (META), eksik yakalama null", () => {
  const [o, , kodlar, meta] = skopOturumu();
  const [tam, eksik] = [...o.skoplar.values()];
  assert.equal(tam.tam, true);
  assert.equal(eksik.tam, false);
  assert.equal(D.skopCsv(eksik), null);
  const sat = csvAyristir(D.skopCsv(tam), ";");
  assert.deepEqual(sat[0], ["ornek", "t_s", "kod", "v_V"]);
  assert.equal(sat.length, 6);
  kodlar.forEach((kod, i) => {
    assert.deepEqual(sat[i + 1], [String(i), D.sayiYaz((i - 2) / 50000, 9, ","), String(kod),
      D.sayiYaz(kod * meta.adim - meta.ofset, 6, ",")]);
  });
  assert.equal(sat[1][1], "-0,000040000");
  assert.equal(sat[3][1], "0,000000000");
  assert.deepEqual(csvAyristir(D.skopCsv(tam, D.BICIM_EN), ",")[0], ["sample", "t_s", "code", "v_V"]);
});

// ── ham ──────────────────────────────────────────────────────────────
const anahtar = (k) => [k.tur, k.sira, k.oturum, Array.from(k.yuk).join(",")].join("|");

test("hamDisari: tek oturumlu akista baytlar AYNEN geri (yeniden cerceveleme == kartin dolgusu)", () => {
  for (const v of [...V.olcum, ...V.pil, ...V.ayrinti]) {
    const veri = hexten(v.veri);
    const kay = K.akisCoz(veri);
    assert.deepEqual(D.hamDisari(kay, v.oturum), veri);
  }
  const [veri, id] = altinAkis();
  assert.deepEqual(D.hamDisari(K.akisCoz(veri), id), veri);
});

test("hamDisari: karisik akistan yalniz o oturum + hedefi o olan NOT'lar; akisCoz geri okur, oturum ayni", () => {
  const a = new Akis(10);
  const A = a.ekle(K.T_BASLA, 11, BASLA(1, 1000, 1790000000, 5000, 3));
  const B = a.ekle(K.T_BASLA, 12, BASLA(2, 500, 1790000100, 9000, 3));
  a.ekle(K.T_NOKTA, A, birlestir(u32(0), K.noktaPaketle(P(6000, 1, 2, 3))));
  a.ekle(K.T_NOKTA, B, birlestir(u32(0), K.noktaPaketle(P(9500, 4, 5, 6))));
  a.ekle(K.T_NOT, 0, K.notPaketle(A, K.KNT_AD, 0, 0, utf8("A'nın adı")));
  a.ekle(K.T_NOT, 0, K.notPaketle(B, K.KNT_NOT, 0, 0, utf8("B notu")));
  a.ekle(K.T_SAAT, A, u32(1790000001, 6001, 3));
  a.ekle(K.T_OLAY, B, K.olayPaketle({ tur: K.KO_DCIR, kart_ms: 9600, no: 1, v_once: 3, i_once: 1, v_ani: 2.9,
    v_oturmus: 2.8, r_ani: 0.1, r_oturmus: 0.2, mah: 1, wh: 0.004 }));
  a.ekle(K.T_NOT, 0, K.notPaketle(A, K.KNT_NOT, 6000, 0, utf8("A notu")));
  a.ekle(K.T_BITIR, B, bitirYuk(1, 4));
  a.ekle(K.T_BITIR, A, bitirYuk(1, 1));
  const kay = K.akisCoz(a.bayt());
  const tum = K.oturumlariKur(kay);
  for (const id of [A, B]) {
    const ham = D.hamDisari(kay, id);
    const geri = K.akisCoz(ham);
    const bek = kay.filter((k) => k.oturum === id
      || (k.tur === K.T_NOT && new DataView(k.yuk.buffer, k.yuk.byteOffset).getUint32(0, true) === id));
    assert.deepEqual(geri.map(anahtar), bek.map(anahtar), `oturum ${id}`);
    const ot = K.oturumlariKur(geri);
    assert.deepEqual([...ot.keys()], [id]);
    const kendi = ot.get(id);
    const asil = tum.get(id);
    assert.deepEqual(kendi, asil, `oturum ${id} ayni kuruluyor`);
  }
  // ayni sira iki kez (cakisan iki indirme): bir kez yazilir; sira karisik girdi siralanir
  const ikili = [...kay, ...kay].reverse();
  assert.deepEqual(D.hamDisari(ikili, A), D.hamDisari(kay, A));
  assert.throws(() => D.hamDisari(kay, 0), RangeError);
  assert.equal(D.hamDisari(kay, 999).length, 0);
});

// ── notlar ve zaman ──────────────────────────────────────────────────
test("DEVAM'li oturumda not: tek acilisa uyan yere, belirsizde kart_ms'ye gore; genel ilk satirda", () => {
  const a = new Akis(0);
  const id = a.ekle(K.T_BASLA, 1, BASLA(1, 1000, 1790000000, 50000, 3));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), ...[51000, 52000, 53000].map((ms) => K.noktaPaketle(P(ms, 8, 8, 1)))));
  a.ekle(K.T_DEVAM, id, u32(4, 1790000100, 2000, 3));
  a.ekle(K.T_NOKTA, id, birlestir(u32(3), ...[3000, 4000, 5000].map((ms) => K.noktaPaketle(P(ms, 8, 8, 1)))));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 52500, 0, utf8("yalniz acilis 0"))); // 53000 satiri
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 3500, 0, utf8("yalniz acilis 1")));  // 4000 satiri
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 9000, 0, utf8("son acilistan sonra"))); // son satir
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 0, 0, utf8("genel")));
  const [o] = oturumAl(a.bayt(), id);
  const sat = csvAyristir(D.oturumCsv(o), ";").slice(1);
  const notu = sat.map((r) => r[19]);
  assert.deepEqual(notu, ["genel", "", "yalniz acilis 0", "", "yalniz acilis 1", "son acilistan sonra"]);
  assert.deepEqual(sat.map((r) => r[4]), ["1000", "2000", "3000", "101000", "102000", "103000"]);
});

test("zamanEkseni: kart_ms 2^32 sarmasi acilis icinde ardisik farkla acilir", () => {
  const a = new Akis(0);
  const k0 = 2 ** 32 - 1500;
  const id = a.ekle(K.T_BASLA, 1, BASLA(1, 1000, 0, k0, 3));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), ...[k0 + 1000, 500, 1500].map((ms) => K.noktaPaketle(P(ms >>> 0, 8, 8, 1)))));
  const [o] = oturumAl(a.bayt(), id);
  const s = D.noktaSerileri(o);
  assert.deepEqual([...s.gecenMs], [1000, 2000, 3000]);
  assert.deepEqual([...s.unixMs].map((x) => Number.isNaN(x)), [true, true, true], "unix 0 = bilinmiyor");
});

// ── PT (2026-10-07): OCV on evresi (KN_OCV), her ornek pil oturumu (AYRINTI) ──
test("PT2: bayrakAraliklari — KN_OCV'li kesintisiz nokta dizisi [onceki noktanin sonu (ilkse t0 - hiz), son nokta]; NaN t keser", () => {
  const t = Float64Array.of(1000, 2000, 3000, 4000, 5000, 6000, 7000);
  const b = [0x80, 0x80, 0x80, 0x80, 0x80, 0, 0x81];
  assert.deepEqual(D.bayrakAraliklari(t, b, K.KN_OCV, 1000), [[0, 5000], [6000, 7000]]);
  assert.deepEqual(D.bayrakAraliklari(t, b, K.KN_OCV), [[1000, 5000], [6000, 7000]]);
  assert.deepEqual(D.bayrakAraliklari(t, [0, 0, 0x80, 0x80, 0, 0, 0], K.KN_OCV, 1000), [[2000, 4000]]);
  assert.deepEqual(D.bayrakAraliklari(t, new Array(7).fill(0), K.KN_OCV, 1000), []);
  assert.deepEqual(D.bayrakAraliklari(Float64Array.of(1000, NaN, 3000), [0x80, 0x80, 0x80], K.KN_OCV, 1000), [[0, 1000]]);
  assert.deepEqual(D.bayrakAraliklari(Float64Array.of(1000), [0x80], K.KN_OCV), [], "tek nokta, pay yok: bos aralik");
  assert.deepEqual(D.bayrakAraliklari(null, null, K.KN_OCV), []);
});

test("PT2: pilCsv — OCV noktalari bayrak 128 + bayraklar 'OCV' (EN 'OCV'); yeni SUTUN YOK; diger bayraklarla birlikte adlandirilir", () => {
  const a = new Akis(300);
  const id = a.ekle(K.T_BASLA, 301, BASLA(K.OTURUM_PIL, 1000, 1790000000, 10000, 4));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), K.noktaPaketle(P(11000, 32, 0, 0, K.KN_OCV)),
    K.noktaPaketle(P(12000, 32, 0, 0, K.KN_OCV | K.KN_YUKSEK)), K.noktaPaketle(P(13000, 30, 1000, 2.5))));
  a.ekle(K.T_BITIR, id, bitirYuk(3, 4));
  const [o] = oturumAl(a.bayt(), id);
  for (const [bicim, dil] of [[D.BICIM_EXCEL_TR, "tr"], [D.BICIM_EN, "en"]]) {
    const s = csvAyristir(D.pilCsv(o, bicim), bicim.ayrac);
    const bas = s[0];
    assert.equal(bas.length, D.KOLONLAR.pil.length, "sutun sayisi degismedi");
    const ib = bas.indexOf(ceviri("csv.bayrak", dil));
    const ia = bas.indexOf(ceviri("csv.bayraklar", dil));
    assert.deepEqual(s.slice(1).map((r) => [r[ib], r[ia]]), [["128", "OCV"], ["129", `${ceviri("bayrak.yuksek", dil)}|OCV`], ["0", ""]]);
  }
  assert.equal(D.bayrakAdlari(K.KN_OCV | K.KN_DCIR, D.BAYRAKLAR.nokta, "en"), "DCIR|OCV");
});

test("PT4: her ornek pil oturumu (noktalar + AYRINTI) — ikisi de cozulur; pilCsv noktalardan, ayrintiCsv orneklerden", () => {
  const a = new Akis(400);
  const id = a.ekle(K.T_BASLA, 401, BASLA(K.OTURUM_PIL, 1000, 1790000000, 10000, 5));
  a.ekle(K.T_OLAY, id, K.olayPaketle({ tur: K.KO_PIL_AYAR, kart_ms: 10001, kesme_v: 3, ocv: 4.1, azami_s: 3600,
    dcir_aralik_ms: 0, dcir_ms: 200, kayit_hz: 0 }));
  a.ekle(K.T_AYRINTI, id, K.ayrintiPaketle({ ilk: 0, t0_ms: 10000, t0_us: 10000000, bayrak: 0,
    ornekler: [[32, 0, 0, 0], [32, 0, 625, 0], [31, 1024, 625, 0]] }));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), K.noktaPaketle(P(11000, 32, 0, 0, K.KN_OCV))));
  a.ekle(K.T_BITIR, id, bitirYuk(1, 1));
  const [o, kay] = oturumAl(a.bayt(), id);
  assert.equal(o.noktalar.length, 1);
  assert.equal(o.ayrinti.length, 1);
  const ay = o.olaylar.find((x) => x.tur === K.KO_PIL_AYAR);
  assert.equal(ay.dcir_aralik_ms, 0, "PT5: DCIR kapali = dcir_aralik_ms 0");
  assert.equal(ay.kayit_hz, 0, "PT3: 0 = her ornek");
  assert.equal(csvAyristir(D.pilCsv(o, { ...D.BICIM_EN, kayitlar: kay }), ",").length, 2, "pil CSV: baslik + 1 nokta");
  const ac = csvAyristir(D.ayrintiCsv(o, { ...D.BICIM_EN, kayitlar: kay }), ",");
  assert.equal(ac.length, 4, "ayrinti CSV: baslik + 3 ornek");
  assert.deepEqual(ac.slice(1).map((r) => r[3]), ["10000000", "10002500", "10005000"], "kart_us = t0_us + 4 x dt4");
});
