// Dil / tema tercihi (A42, A43): saklama, gecersiz degerin reddi, belgeye uygulama, tepkisel ceviri.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { DEPO_ANAHTARI, DILLER, TEMALAR, TEMA_OLAYI, VARSAYILAN, tercihOku, tercihUygula, tercihYaz } from "../src/ekran/tercih.js";
import { temaDinle } from "../src/bilesen/tema_dinle.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";

function depoKur(ilk = {}) {
  const m = new Map(Object.entries(ilk));
  return { getItem: (a) => (m.has(a) ? m.get(a) : null), setItem: (a, d) => { m.set(a, String(d)); }, m };
}

function belgeKur() {
  const oz = new Map();
  const dinleyici = new Map();
  return {
    oz,
    documentElement: {
      setAttribute: (a, d) => oz.set(a, d),
      removeAttribute: (a) => oz.delete(a),
    },
    addEventListener: (olay, fn) => { dinleyici.set(fn, olay); },
    removeEventListener: (olay, fn) => { dinleyici.delete(fn); },
    dispatchEvent: (e) => { for (const [fn, olay] of [...dinleyici]) if (olay === e.type) fn(e); return true; },
    dinleyiciSayisi: () => dinleyici.size,
  };
}

describe("tercih", () => {
  it("varsayilan: Turkce + sistem temasi; bozuk / eksik / gecersiz kayit varsayilana duser", () => {
    expect(VARSAYILAN).toEqual({ dil: "tr", tema: "sistem" });
    expect(tercihOku(depoKur())).toEqual(VARSAYILAN);
    for (const ham of ["{bozuk", "null", "5", '"tr"', "[]", '{"dil":"de","tema":"mor"}', '{"dil":5,"tema":null}']) {
      expect(tercihOku(depoKur({ [DEPO_ANAHTARI]: ham })), ham).toEqual(VARSAYILAN);
    }
    expect(tercihOku({ getItem: () => { throw new Error("x"); } })).toEqual(VARSAYILAN);
  });

  it("yaz / oku: her gecerli dil ve tema saklanir; gecersiz deger YAZILMAZ, oteki alan korunur", () => {
    const depo = depoKur();
    for (const dil of DILLER) for (const tema of TEMALAR) {
      expect(tercihYaz(depo, { dil, tema })).toEqual({ dil, tema });
      expect(tercihOku(depo)).toEqual({ dil, tema });
    }
    tercihYaz(depo, { dil: "en", tema: "koyu" });
    expect(tercihYaz(depo, { dil: "xx" })).toEqual({ dil: "en", tema: "koyu" });
    expect(tercihYaz(depo, { tema: "acik" })).toEqual({ dil: "en", tema: "acik" });
    expect(tercihYaz(depo, { dil: "tr" })).toEqual({ dil: "tr", tema: "acik" });
    expect(tercihYaz(depo, null)).toEqual({ dil: "tr", tema: "acik" });
    // Depo yazilamiyorsa atmaz; secim yine doner.
    expect(tercihYaz({ getItem: () => null, setItem: () => { throw new Error("dolu"); } }, { dil: "en" })).toEqual({ dil: "en", tema: "sistem" });
  });

  it("belgeye uygulama: sistem -> data-tema YOK; koyu / acik -> data-tema; lang; tema olayi gonderilir", () => {
    const b = belgeKur();
    let olay = 0;
    b.addEventListener(TEMA_OLAYI, () => { olay++; });
    tercihUygula(b, { dil: "en", tema: "koyu" });
    expect(b.oz.get("data-tema")).toBe("koyu");
    expect(b.oz.get("lang")).toBe("en");
    tercihUygula(b, { dil: "tr", tema: "acik" });
    expect(b.oz.get("data-tema")).toBe("acik");
    tercihUygula(b, { dil: "tr", tema: "sistem" });
    expect(b.oz.has("data-tema")).toBe(false);
    expect(b.oz.get("lang")).toBe("tr");
    expect(olay).toBe(3);
  });

  it("tema.css: data-tema koyu ve acik bloklari var; sistem acik temasi data-tema=koyu iken UYGULANMAZ", () => {
    const css = readFileSync(new URL("../src/tema.css", import.meta.url), "utf8");
    expect(css).toMatch(/:root\[data-tema="koyu"\]/);
    expect(css).toMatch(/:root\[data-tema="acik"\]/);
    expect(css).toMatch(/@media \(prefers-color-scheme: light\) \{\s*:root:not\(\[data-tema="koyu"\]\)/);
  });

  it("temaDinle: Ayarlar'dan tema secilince de (tema olayi) haber verir; birakinca dinlemez", () => {
    const b = belgeKur();
    let n = 0;
    const birak = temaDinle(() => { n++; }, null, b);
    tercihUygula(b, { dil: "tr", tema: "koyu" });
    expect(n).toBe(1);
    birak();
    tercihUygula(b, { dil: "tr", tema: "acik" });
    expect(n).toBe(1);
    expect(b.dinleyiciSayisi()).toBe(0);
  });

  it("metin.js: c() secilen dile gore cevirir; tercihSec dili ve temayi degistirir (tepkisel ref)", async () => {
    const m = await import("../src/ekran/metin.js");
    expect(m.dil.value).toBe("tr");
    expect(m.c("m.ay.tema_koyu")).toBe(SOZLUK_MOBIL["m.ay.tema_koyu"].tr);
    m.tercihSec({ dil: "en" });
    expect(m.dil.value).toBe("en");
    expect(m.c("m.ay.tema_koyu")).toBe(SOZLUK_MOBIL["m.ay.tema_koyu"].en);
    m.tercihSec({ tema: "acik", dil: "tr" });
    expect([m.dil.value, m.tema.value]).toEqual(["tr", "acik"]);
    m.tercihSec({ dil: "zz", tema: "zz" });
    expect([m.dil.value, m.tema.value]).toEqual(["tr", "acik"]);
  });

  it("hicbir ekran dili sabit yazmiyor: src/ekran ve src/bilesen'de ceviriMobil(…, \"tr\") yok", () => {
    for (const yol of ["Baglanti.vue", "Esles.vue", "KartBul.vue", "Ayarlar.vue", "Durum.vue", "Canli.vue"]) {
      const k = readFileSync(new URL(`../src/ekran/${yol}`, import.meta.url), "utf8");
      expect(k, yol).not.toMatch(/const dil = "tr"|ceviriMobil\(/);
    }
  });
});
