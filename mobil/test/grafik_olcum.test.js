// 5D-4 — Ö6 grafik olcumu (A27): seri ve betik BELIRLENIMCI; olcum dongusu sahte saatle sinanir.
// Gercek sure telefonda olculur (DURUM.md); burada olcumun NEYI olctugu ve ozetin dogrulugu sabitlenir.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { cizimPlani, durumKur, seriHazirla } from "@ortak/grafik.js";
import { KARE, NOKTA, OLCUT_MS, grafikOlc, grafikSerileri, kareBetigi, ozetle, seriUret } from "../src/cekirdek/grafik_olcum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../src/${yol}`, import.meta.url)), "utf8");

describe("Ö6 sabitleri ve seri", () => {
  it("800 bin nokta, 200 kare, olcut 33 ms (A27)", () => {
    expect([NOKTA, KARE, OLCUT_MS]).toEqual([800000, 200, 33]);
  });

  it("seriUret belirlenimci: iki cagri AYNI; t artan (100 ms), degerler sonlu, tek orneklik sicramalar var", () => {
    const a = seriUret(100000), b = seriUret(100000);
    expect(a.t.length).toBe(100000);
    expect(Buffer.from(a.v.buffer).equals(Buffer.from(b.v.buffer))).toBe(true);
    expect(Buffer.from(a.i.buffer).equals(Buffer.from(b.i.buffer))).toBe(true);
    expect([a.t[0], a.t[1], a.t[99999]]).toEqual([0, 100, 9999900]);
    let sonlu = true, sicrama = 0;
    for (let k = 0; k < a.v.length; k++) {
      if (!Number.isFinite(a.v[k]) || !Number.isFinite(a.i[k])) sonlu = false;
      if (k > 0 && a.v[k] - a.v[k - 1] > 1) sicrama += 1;
    }
    expect(sonlu).toBe(true);
    expect(sicrama).toBe(1);                               // k = 50021
    for (const n of [0, 1, 1.5, -5, "8"]) expect(() => seriUret(n)).toThrow(RangeError);
    const s = grafikSerileri(a);
    expect(s.map((x) => [x.ad, x.eksen, x.renk])).toEqual([["V", "sol", "volt"], ["I", "sag", "amper"]]);
    expect(s[0].t).toBe(s[1].t);
  });
});

describe("kareBetigi", () => {
  const bas = 0, son = 79999900;
  const k = kareBetigi(bas, son, 200);

  it("200 pencere, hepsi aralik icinde ve pozitif genislikte; belirlenimci", () => {
    expect(k.length).toBe(200);
    for (const [t0, t1] of k) {
      expect(t0).toBeGreaterThanOrEqual(bas);
      expect(t1).toBeLessThanOrEqual(son + 1e-6);
      expect(t1 - t0).toBeGreaterThan(0);
    }
    expect(kareBetigi(bas, son, 200)).toEqual(k);
  });

  it("dort bolum: yakinlas (tam -> 1/2000), dar pencereyle saga kaydir, orta genislikte sola kaydir, tama uzaklas", () => {
    const gen = k.map(([a, b]) => b - a), tam = son - bas;
    expect(gen[0]).toBeCloseTo(tam, 3);
    expect(gen[49]).toBeCloseTo(tam / 2000, 3);
    for (let i = 1; i < 50; i++) expect(gen[i]).toBeLessThan(gen[i - 1]);                       // yakinlasma
    for (let i = 51; i < 100; i++) { expect(gen[i]).toBeCloseTo(tam / 2000, 3); expect(k[i][0]).toBeGreaterThan(k[i - 1][0]); }   // saga
    for (let i = 101; i < 150; i++) { expect(gen[i]).toBeCloseTo(tam / 40, 3); expect(k[i][0]).toBeLessThan(k[i - 1][0]); }       // sola
    for (let i = 151; i < 200; i++) expect(gen[i]).toBeGreaterThan(gen[i - 1]);                 // uzaklasma
    expect(gen[199]).toBeCloseTo(tam, 3);
    // Betik hem HAM veriyi (dar pencere: ~400 nokta) hem piramidin ust duzeylerini (tam: 800 bin) cizdirir.
    expect(gen[49] / 100).toBeLessThan(1000);
    expect(gen[0] / 100).toBeGreaterThan(700000);
  });

  it("gecersiz girdi: RangeError", () => {
    for (const [a, b, n] of [[5, 5, 200], [9, 1, 200], [0, 10, 3], [0, 10, 1.5]]) expect(() => kareBetigi(a, b, n)).toThrow(RangeError);
    expect(kareBetigi(0, 1000, 7).length).toBe(7);
  });
});

describe("ozetle", () => {
  it("ortanca / p95 / en uzun (en yakin sira yontemi), 0.1 ms'ye yuvarli; sonlu olmayan atilir; bos -> null", () => {
    const yuz = Array.from({ length: 100 }, (_, i) => i + 1);          // 1 … 100
    expect(ozetle(yuz)).toEqual({ ortanca: 50, p95: 95, enUzun: 100 });
    expect(ozetle([...yuz].reverse())).toEqual({ ortanca: 50, p95: 95, enUzun: 100 });
    expect(ozetle([5])).toEqual({ ortanca: 5, p95: 5, enUzun: 5 });
    expect(ozetle([1.04, 1.06, NaN, Infinity, -3, 2.449])).toEqual({ ortanca: 1.1, p95: 2.4, enUzun: 2.4 });
    // Tek uzun kare p95'i degil EN UZUN'u etkiler (200 karede 10'a kadar aykiri p95'e girmez).
    const kareler = Array.from({ length: 200 }, () => 10);
    kareler[77] = 400;
    expect(ozetle(kareler)).toEqual({ ortanca: 10, p95: 10, enUzun: 400 });
    for (let i = 0; i < 11; i++) kareler[i] = 50;
    expect(ozetle(kareler).p95).toBe(50);
    expect(ozetle([])).toBe(null);
    expect(ozetle([NaN])).toBe(null);
  });
});

describe("grafikOlc (sahte saat ve sahte grafik)", () => {
  function duzenek({ cizimMs = () => 4, kareMs = () => 16, hazirlikMs = 120 } = {}) {
    const saat = { ms: 1000 };
    const olay = [];
    let kare = -1;
    const grafik = {
      veriAyarla(s) { olay.push(["veri", s.length]); saat.ms += hazirlikMs; },
      durumAyarla(d) { kare += 1; olay.push(["durum", d.t0, d.t1]); },
      ciz() { olay.push("ciz"); if (kare >= 0) saat.ms += cizimMs(kare); },
    };
    const kareBekle = async () => { olay.push("bekle"); if (kare >= 0) saat.ms += kareMs(kare); };
    return { saat, olay, grafik, kareBekle, simdi: () => saat.ms };
  }
  const seriler = grafikSerileri(seriUret(1000));
  const kareler = kareBetigi(0, 99900, 20);

  it("her karede: pencere ayarlanir, cizilir, bir animasyon karesi beklenir; sureler dogru toplanir", async () => {
    const d = duzenek({ cizimMs: (k) => (k === 7 ? 30 : 4), kareMs: (k) => (k === 7 ? 40 : 16) });
    const s = await grafikOlc({ grafik: d.grafik, seriler, kareler, simdi: d.simdi, kareBekle: d.kareBekle });
    expect(s).toEqual({
      nokta: 1000, kare: 20, hazirlikMs: 120,
      cizim: { ortanca: 4, p95: 4, enUzun: 30 },
      aralik: { ortanca: 20, p95: 20, enUzun: 70 },          // aralik = cizim + bekleme (16 + 4; 7. karede 40 + 30)
      gecti: true,
    });
    expect(d.olay.slice(0, 3)).toEqual([["veri", 2], "ciz", "bekle"]);
    expect(d.olay.filter((o) => Array.isArray(o) && o[0] === "durum").map((o) => [o[1], o[2]])).toEqual(kareler);
    expect(d.olay.slice(3, 9)).toEqual([["durum", kareler[0][0], kareler[0][1]], "ciz", "bekle", ["durum", kareler[1][0], kareler[1][1]], "ciz", "bekle"]);
  });

  it("olcut KARE ARALIGININ p95'ine uygulanir: 33 ms ve ustu KALIR; cizim hizli olsa da", async () => {
    const yavas = duzenek({ cizimMs: () => 2, kareMs: () => 31 });       // aralik 33.0
    expect((await grafikOlc({ grafik: yavas.grafik, seriler, kareler, simdi: yavas.simdi, kareBekle: yavas.kareBekle })).gecti).toBe(false);
    const sinir = duzenek({ cizimMs: () => 2, kareMs: () => 30.9 });     // aralik 32.9
    expect((await grafikOlc({ grafik: sinir.grafik, seriler, kareler, simdi: sinir.simdi, kareBekle: sinir.kareBekle })).gecti).toBe(true);
    // Yalniz 1 kare cok uzun (20'de 1 = %5): p95'e girmez ama EN UZUN'da gorunur.
    const tek = duzenek({ kareMs: (k) => (k === 3 ? 500 : 16) });
    const s = await grafikOlc({ grafik: tek.grafik, seriler, kareler, simdi: tek.simdi, kareBekle: tek.kareBekle });
    expect(s.gecti).toBe(true);
    expect(s.aralik.enUzun).toBe(504);
  });

  it("iptal edilirse null doner (yarim olcum sonuc diye YAZILMAZ)", async () => {
    const d = duzenek();
    let n = 0;
    expect(await grafikOlc({ grafik: d.grafik, seriler, kareler, simdi: d.simdi, kareBekle: d.kareBekle, iptal: () => ++n > 5 })).toBe(null);
  });

  it("betik GERCEK cizim planini uretir: her pencerede plan kurulur, dar pencerede ham nokta, tamda ozet", () => {
    const seri = seriUret(200000);
    const s = grafikSerileri(seri).map(seriHazirla);
    const durum = durumKur(s);
    for (const [t0, t1] of kareBetigi(seri.t[0], seri.t[199999], 12)) {
      const plan = cizimPlani(s, { ...durum, t0, t1 }, { w: 360, h: 240 }, { zamanKokeni: 0 });
      expect(plan).toBeTruthy();
    }
  });
});

describe("ekran baglantisi (kaynak)", () => {
  it("GrafikOlcum: ortak Grafik + gercek animasyon karesi + performance.now; Ayarlar > Gelismis'te", () => {
    const g = kaynak("ekran/GrafikOlcum.vue");
    expect(g).toContain("const kareBekle = () => new Promise((coz) => { requestAnimationFrame(() => coz()); });");
    expect(g).toContain("simdi: () => performance.now(), kareBekle, iptal: () => birakildi,");
    expect(g).toContain("grafik = new Grafik(tuval.value, { zamanKokeni: 0 });");
    expect(g).toContain("kareler: kareBetigi(seri.t[0], seri.t[NOKTA - 1], KARE),");
    expect(g).toContain("if (grafik) grafik.yokEt();");
    expect(kaynak("ekran/Ayarlar.vue")).toContain('<section v-if="gelismis" id="ay-grafik-olcum" class="kart"><GrafikOlcum /></section>');
  });

  it("canli grafik: veri yokken tuval gizlenir (anlamsiz eksen yazisi cizilmez)", () => {
    const c = kaynak("bilesen/CanliGrafik.vue");
    expect(c).toContain("bos.value = p.n === 0;");
    expect(c).toContain(':class="{ kucuk, bos }"');
    expect(kaynak("tema.css")).toContain(".grafik.bos { visibility: hidden; }");
  });
});
