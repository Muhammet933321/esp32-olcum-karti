// 5D-2 — esitleme ayari: onay ayari (A21), boyut yazimi ve uygulama.js'in esitlemeyi tembel kurmasi.
// 5P (P6): eski Ionic kabugunun (kabuk_durum.js, Durum / Ayarlar ekranlari) testleri o dosyalarla birlikte
// silindi; telefonda esitleme Bu telefon > Esitleme bolumunden (src/telefon/) yonetilir.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ONAY_ANAHTARI, onayOku, onayYaz } from "../src/cekirdek/esitleme_ayar.js";
import { boyutYaz } from "../src/ekran/esitleme_ayar_gorunum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../src/${yol}`, import.meta.url)), "utf8");

describe("onay ayari (A21) ve boyut yazimi", () => {
  const depoKur = (ilk = {}) => {
    const m = new Map(Object.entries(ilk));
    return { getItem: (a) => (m.has(a) ? m.get(a) : null), setItem: (a, d) => { m.set(a, String(d)); }, removeItem: (a) => { m.delete(a); }, m };
  };

  it("VARSAYILAN KAPALI; yalniz kesin '1' acik; bozuk / atan depo KAPALI", () => {
    expect(ONAY_ANAHTARI).toBe("esitleme.onay");
    expect(onayOku(depoKur())).toBe(false);
    for (const v of ["0", "true", "evet", "", " 1", "11"]) expect(onayOku(depoKur({ [ONAY_ANAHTARI]: v })), v).toBe(false);
    expect(onayOku(depoKur({ [ONAY_ANAHTARI]: "1" }))).toBe(true);
    expect(onayOku({ getItem: () => { throw new Error("kapali"); } })).toBe(false);
    expect(onayOku(null)).toBe(false);
  });

  it("onayYaz: yalniz kesin true acar; kapatinca anahtar SILINIR; yazilamazsa eski deger doner", () => {
    const d = depoKur();
    expect(onayYaz(d, true)).toBe(true);
    expect(d.m.get(ONAY_ANAHTARI)).toBe("1");
    expect(onayYaz(d, false)).toBe(false);
    expect(d.m.has(ONAY_ANAHTARI)).toBe(false);
    for (const v of [1, "1", "true", {}, null, undefined]) expect(onayYaz(depoKur(), v), String(v)).toBe(false);
    const salt = { getItem: () => null, setItem: () => { throw new Error("dolu"); }, removeItem: () => {} };
    expect(onayYaz(salt, true)).toBe(false);
  });

  it("boyutYaz", () => {
    expect([0, 999, 1000, 12345, 999999, 1e6, 11.4e6, 2.5e9].map(boyutYaz)).toEqual(["0 B", "999 B", "1.0 kB", "12.3 kB", "1000.0 kB", "1.00 MB", "11.40 MB", "2.50 GB"]);
    expect([NaN, -1, Infinity, null, "5"].map(boyutYaz)).toEqual(["—", "—", "—", "—", "—"]);
  });
});

describe("uygulama baglantisi (kaynak)", () => {
  it("uygulama: esitleme tembel yuklenir, depo KartDepo eklentisinden, onay HER turda ayardan okunur", () => {
    const u = kaynak("cekirdek/uygulama.js");
    expect(u).toContain('Promise.all([import("./esitleme.js"), import("./depo.js")])');
    expect(u).toContain("depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),");
    expect(u).toContain("onayAcik: esitlemeOnayi,");
    expect(u).not.toMatch(/^import .*esitleme\.js/m);            // acilis paketine statik girmez
  });
});
