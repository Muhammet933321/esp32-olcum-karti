// B73 / 2E — ortak/src/skop.js == kartin skop_olc() (kod/olcum-karti-a3/skop_olc.h) BIT BIT.
// Vektorler: uretim/ortak_vektor_skop.py C kodunu AVR emulatorunde kosturur -> test/vektor/skop.json.
// Karsilastirma Object.is: float32 cikti double'a tam cevrilmis, -0 dahil birebir.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { skopOlc, u64f, ALANLAR, AZAMI_ADET } from "../src/skop.js";

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

// ── 1F (2026-10-02): dort kusurun TAM degerli capalari (C vektorlerinin kendisinde) ──
test("1F S3: ideal karede duty TAM %50 / %25 / %90 (eskiden bir ornek fazla: %49.79)", () => {
  const b = Object.fromEntries(V.vakalar.map((v) => [v.ad, v.beklenen]));
  assert.equal(b.kare50.duty, 50);
  assert.equal(b.kare25.duty, 25);
  assert.equal(b.kare90.duty, 90);
  assert.equal(b.kare50_tam_4000.duty, 50);
  assert.equal(b.tam_olcek_65535.duty, 50);
});

test("1F S1: duz cizgide Vac TAM 0 (eskiden 2048 kodda 0.196 V, 65535'te 0.559 V)", () => {
  const b = Object.fromEntries(V.vakalar.map((v) => [v.ad, v.beklenen]));
  for (const ad of ["duz", "sabit_65535", "duz_4095_4000"]) {
    assert.ok(Object.is(b[ad].Vac, 0), `${ad}.Vac = ${b[ad].Vac}`);
    assert.equal(b[ad].Vrms, b[ad].Vort, `${ad}: duz cizgide Vrms == Vort`);
  }
});

test("1F S1: kucuk AC Vac double basvuruya 1e-6 bagil icinde (eskiden ±3 kodda 0)", () => {
  for (const ad of ["dc_ustu_kucuk_ac", "hist_7", "hist_8", "sinus_gurultu", "gurultulu_kare",
    "tavan_tek_fark_4000"]) {
    const v = V.vakalar.find((x) => x.ad === ad);
    const h = v.ham.slice(0, v.adet);
    const ort = h.reduce((a, k) => a + k, 0) / h.length;
    const std = Math.sqrt(h.reduce((a, k) => a + (k - ort) ** 2, 0) / h.length);
    const beklenen = std * Math.abs(v.volt_adim);
    assert.ok(beklenen > 0 && Math.abs(v.beklenen.Vac - beklenen) <= 1e-6 * beklenen,
      `${ad}: C ${v.beklenen.Vac} ~ double ${beklenen}`);
  }
});

test("1F S4: %90'a varmayan cuce darbe tr/tf'ye girmez — yalniz TAM kenar", () => {
  const b = Object.fromEntries(V.vakalar.map((v) => [v.ad, v.beklenen]));
  const sekiz = Math.fround(8 / Math.fround(10000)); // 8 ornek @ 10 kHz, C: (t90 - t10) / hz
  assert.equal(b.cuce_iki_yon.tr, sekiz, "yukari cuce + tam yukselen: 8 ornek");
  assert.equal(b.cuce_iki_yon.tf, sekiz, "asagi cuce + tam dusen: 8 ornek");
  // cuce_darbe: tam kenar 200+400j, alt 560 / ust 3440 -> (8 + 0.1) - 0.9 = 7.2 ornek
  assert.ok(Math.abs(b.cuce_darbe.tr - 7.2e-4) < 1e-8, `cuce_darbe.tr ${b.cuce_darbe.tr} (eskiden 4.89 ms)`);
  // geri seken: %10'u gecip geri inen ilk tepe sayilmaz; rampa 500+350j: 635 -> 3315
  const sek = (8 + 15 / 350) - (135 / 350);
  assert.ok(Math.abs(b.geri_seken_kenar.tr - sek / 1e4) < 1e-8, `geri_seken_kenar.tr ${b.geri_seken_kenar.tr}`);
});

test("u64f: BigInt -> float32 DOGRU yuvarlar (Math.fround(Number(b)) 2^53 ustunde iki kez yuvarlar)", () => {
  const f32a = new Float32Array(1);
  const u32a = new Uint32Array(f32a.buffer);
  const komsu = (f, d) => { f32a[0] = f; u32a[0] += d; return f32a[0]; };
  // bagimsiz kahin: iki float32 adaydan tam (BigInt) uzakligi kucuk olan, esitlikte cift mantis
  const kahin = (b) => {
    const f = Math.fround(Number(b));
    let en = null;
    for (const c of [komsu(f, -1), f, komsu(f, 1)]) {
      if (!(Number.isInteger(c) && c >= 0)) continue; // b tamsayi: aday da tamsayi olmali
      const cb = BigInt(c);
      const u = cb > b ? cb - b : b - cb;
      f32a[0] = c;
      const cift = (u32a[0] & 1) === 0;
      if (en === null || u < en.u || (u === en.u && cift)) en = { c, u };
    }
    return en.c;
  };
  const ornekler = [0n, 1n, 16777215n, 16777216n, 16777217n, 16777219n, 33554435n,
    (1n << 60n) + (1n << 36n) + 1n, // yari + 1: yukari; iki kez yuvarlama asagi verirdi
    (1n << 60n) + (1n << 36n), (1n << 60n) + (3n << 36n), (1n << 64n) - 1n,
    65535n ** 4n, 18445618199572250625n - 1n];
  let x = 0x9e3779b97f4a7c15n;
  for (let i = 0; i < 2000; i++) {
    x = (x * 6364136223846793005n + 1442695040888963407n) & ((1n << 64n) - 1n);
    ornekler.push(x >> BigInt(i % 40));
  }
  for (const b of ornekler) {
    assert.ok(Object.is(u64f(b), kahin(b)), `${b}: u64f ${u64f(b)} != ${kahin(b)}`);
  }
  assert.notEqual(Math.fround(Number((1n << 60n) + (1n << 36n) + 1n)), u64f((1n << 60n) + (1n << 36n) + 1n),
    "kahinin yakaladigi iki kez yuvarlama durumu gercekten farkli olmali");
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
