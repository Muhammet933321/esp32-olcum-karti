// B73 / 2E — ortak/src/skop.js == kartin skop_olc() (kod/olcum-karti-a3/skop_olc.h) BIT BIT.
// Vektorler: uretim/ortak_vektor_skop.py C kodunu AVR emulatorunde kosturur -> test/vektor/skop.json.
// Karsilastirma Object.is: float32 cikti double'a tam cevrilmis, -0 dahil birebir.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { skopOlc, ALANLAR, AZAMI_ADET } from "../src/skop.js";

const V = JSON.parse(readFileSync(new URL("./vektor/skop.json", import.meta.url), "utf8"));
const BASLIK = new URL("../../kod/olcum-karti-a3/skop_olc.h", import.meta.url);

function ayni(gercek, beklenen, ad) {
  for (const a of ALANLAR) {
    assert.ok(Object.is(gercek[a], beklenen[a]),
      `${ad}.${a}: JS ${gercek[a]} != C ${beklenen[a]}`);
  }
}

// ── capraz vektorler: C (AVR emulatoru) ile bit bit ─────────────────────
for (const v of V.vakalar) {
  test(`C vektoru ${v.ad}: ${v.aciklama}`, () => {
    ayni(skopOlc(v.ham, v.adet, v.volt_adim, v.hz), v.beklenen, v.ad);
  });
}

test("vektorler GUNCEL skop_olc.h'den uretildi (sha256)", () => {
  const metin = readFileSync(BASLIK, "utf8").replace(/\r\n/g, "\n");
  assert.equal(createHash("sha256").update(metin, "utf8").digest("hex"), V.kaynak_sha256,
    "skop_olc.h degisti: python uretim/ortak_vektor_skop.py");
});

test("alan adlari kartin M satiriyla ayni (arayuz skopMCoz)", () => {
  assert.deepEqual([...ALANLAR], V.alanlar);
  assert.deepEqual(ALANLAR, ["f", "T", "Vpp", "Vmax", "Vmin", "Vort", "Vrms", "Vac", "duty", "tr", "tf", "n"]);
  const o = skopOlc([1, 2, 3], 3, 1, 1);
  assert.deepEqual(Object.keys(o).sort(), [...ALANLAR].sort());
});

test("vektorler C'nin her dalini kapsiyor (uretec bozulursa bos kalmasin)", () => {
  const b = V.vakalar.map((v) => v.beklenen);
  const say = (fn) => b.filter(fn).length;
  assert.ok(say((o) => o.f > 0 && o.n >= 2 && o.duty > 0) >= 15, "periyodik");
  assert.ok(say((o) => o.f === 0 && o.Vpp > 0 && (o.tr > 0 || o.tf > 0)) >= 3, "tek kenar: f yok, tr/tf var");
  assert.ok(say((o) => o.tr > 0 && o.tf === 0) >= 2 && say((o) => o.tf > 0 && o.tr === 0) >= 1, "yalniz tr / yalniz tf");
  assert.ok(say((o) => o.Vpp > 0 && o.f === 0 && o.tr === 0 && o.tf === 0) >= 2, "erken donus (hist < 1)");
  assert.ok(say((o) => ALANLAR.every((a) => o[a] === 0)) >= 3, "hepsi sifir (bos / hz <= 0)");
  assert.ok(say((o) => o.n === 1) >= 1, "tek cevrim");
  assert.ok(V.vakalar.some((v) => v.ham.length === 4000), "kartin azami adedi (4000)");
  assert.ok(V.vakalar.some((v) => v.adet < v.ham.length), "adet < dizi");
});

// ── analitik capa: A6 (test_skop_olcum.py) ile ayni bilinen dalgalar ────
test("A6 dalgalari: kare 125 Hz %50, %25, ucgen 100 Hz, sinus 156.25 Hz, duz olcumsuz", () => {
  const b = Object.fromEntries(V.vakalar.map((v) => [v.ad, v.beklenen]));
  assert.equal(b.kare50.f, 125);
  assert.equal(b.kare50.n, 3);
  assert.ok(Math.abs(b.kare50.duty - 50) < 1.5);
  assert.ok(Math.abs(b.kare25.duty - 25) < 1.5);
  assert.equal(b.ucgen.f, 100);
  assert.equal(b.sinus64.f, 156.25);
  assert.equal(b.duz.f, 0);
  assert.equal(b.duz.n, 0);
});

// ── gecersiz / kisa girdi: atmaz, C sozlesmesini dondurur ───────────────
const SIFIR = Object.fromEntries(ALANLAR.map((a) => [a, 0]));

test("bos / null / undefined / sayi olmayan girdi atmaz, hepsi 0", () => {
  for (const ham of [[], null, undefined, 42, {}, new Uint16Array(0)]) {
    assert.deepEqual(skopOlc(ham, undefined, 0.01, 1000), SIFIR);
  }
  assert.deepEqual(skopOlc(null, 10, 0.01, 1000), SIFIR);
  assert.deepEqual(skopOlc([1, 2, 3], 0, 0.01, 1000), SIFIR);
  assert.deepEqual(skopOlc([1, 2, 3], -4, 0.01, 1000), SIFIR);
  assert.deepEqual(skopOlc([1, 2, 3], NaN, 0.01, 1000), SIFIR);
});

test("hz <= 0: gerilimler DAHIL hepsi 0 (C: erken donus); hz yok/NaN: atmaz, C gibi NaN", () => {
  for (const hz of [0, -0, -1, -Infinity, undefined]) {
    // undefined -> fround NaN; NaN <= 0 yanlis: C gibi devam eder ve NaN uretir (atmaz)
    const o = skopOlc([0, 4000, 0, 4000, 0, 4000], 6, 0.01, hz);
    if (hz === undefined) {
      assert.ok(Number.isNaN(o.f) && Number.isNaN(o.tr) && o.Vpp > 0, JSON.stringify(o));
    } else {
      assert.deepEqual(o, SIFIR);
    }
  }
});

test("tek ornek: yalniz gerilimler, zaman olcumu 0", () => {
  const o = skopOlc([1000], 1, 0.5, 100);
  assert.equal(o.Vmax, 500);
  assert.equal(o.Vmin, 500);
  assert.equal(o.Vort, 500);
  assert.equal(o.Vrms, 500);
  assert.equal(o.Vac, 0);
  for (const a of ["f", "T", "duty", "tr", "tf", "n"]) assert.equal(o[a], 0);
});

test("adet varsayilani dizi boyu; adet > dizi kirpilir (C dizinin otesini okurdu)", () => {
  const ham = Array.from({ length: 300 }, (_, i) => ((i % 40) < 20 ? 3000 : 500));
  const tam = skopOlc(ham, 300, 0.01, 1000);
  assert.deepEqual(skopOlc(ham, undefined, 0.01, 1000), tam);
  assert.deepEqual(skopOlc(ham, 10_000, 0.01, 1000), tam);
  assert.deepEqual(skopOlc(ham, 300.9, 0.01, 1000), tam, "kesirli adet asagi");
  assert.deepEqual(skopOlc(ham, 150, 0.01, 1000), skopOlc(ham.slice(0, 150), undefined, 0.01, 1000));
});

test("ham kodlar C uint16_t gibi: Uint16Array/Float64Array/dizi ayni; mod 65536, NaN -> 0", () => {
  const ham = Array.from({ length: 200 }, (_, i) => 2000 + Math.round(1500 * Math.sin(i / 7)));
  const r = skopOlc(ham, 200, 0.02, 5000);
  assert.deepEqual(skopOlc(Uint16Array.from(ham), 200, 0.02, 5000), r);
  assert.deepEqual(skopOlc(Float64Array.from(ham), 200, 0.02, 5000), r);
  assert.deepEqual(skopOlc(ham.map((k) => k + 65536), 200, 0.02, 5000), r, "mod 65536");
  assert.deepEqual(skopOlc(ham.map((k) => k + 0.75), 200, 0.02, 5000), r, "kesir atilir");
  const nanli = [NaN, ...ham.slice(1)];
  assert.deepEqual(skopOlc(nanli, 200, 0.02, 5000), skopOlc([0, ...ham.slice(1)], 200, 0.02, 5000));
  assert.equal(skopOlc([-1], 1, 1, 1).Vmax, 65535, "-1 -> 65535 (uint16 atamasi)");
});

test("adet C uint16_t sinirina (65535) kirpilir", () => {
  assert.equal(AZAMI_ADET, 65535);
  const ham = Array.from({ length: 70_000 }, (_, i) => (i >= 65_535 ? 60_000 : (i % 100 < 50 ? 1000 : 3000)));
  const o = skopOlc(ham, undefined, 0.001, 1e6);
  assert.deepEqual(o, skopOlc(ham.slice(0, 65_535), undefined, 0.001, 1e6));
  assert.equal(o.Vmax, Math.fround(3000 * Math.fround(0.001)), "65535'ten sonraki 60000 gorulmedi");
});

test("float32 sonuc: her alan Math.fround'a degismez", () => {
  for (const v of V.vakalar) {
    const o = skopOlc(v.ham, v.adet, v.volt_adim, v.hz);
    for (const a of ALANLAR) assert.ok(Object.is(Math.fround(o[a]), o[a]), `${v.ad}.${a}`);
    assert.ok(Number.isInteger(o.n));
  }
});
