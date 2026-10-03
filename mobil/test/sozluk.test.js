// Sozluk kurallari (A43) + "ekrana gomulu metin yok" (tasarim §4 Ekranlar).
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { SOZLUK } from "@ortak/sozluk.js";
import { SOZLUK_MOBIL, ceviriMobil } from "../src/cekirdek/sozluk_mobil.js";

const SRC = fileURLToPath(new URL("../src", import.meta.url));

function dosyalar(dizin, son) {
  const cikti = [];
  for (const ad of readdirSync(dizin)) {
    const yol = join(dizin, ad);
    if (statSync(yol).isDirectory()) cikti.push(...dosyalar(yol, son));
    else if (son.some((s) => ad.endsWith(s))) cikti.push(yol);
  }
  return cikti;
}

const yerTutucular = (s) => [...s.matchAll(/\{([a-z_]+)\}/g)].map((m) => m[1]).sort().join(",");

// <template> blogundaki duz metin dugumleri ve cevrilmesi gereken duz ozellikler.
export function gomuluMetinler(vue) {
  const m = /<template>([\s\S]*)<\/template>/.exec(vue);
  if (!m) return [];
  const sablon = m[1].replace(/<!--[\s\S]*?-->/g, "");
  const bulunan = [];
  for (const d of sablon.matchAll(/>([^<]+)</g)) {
    const metin = d[1].replace(/\{\{[\s\S]*?\}\}/g, "").trim();
    if (/\p{L}/u.test(metin)) bulunan.push(metin);
  }
  for (const o of sablon.matchAll(/\s(aria-label|title|placeholder|label|alt)="([^"]*)"/g)) {
    if (/\p{L}/u.test(o[2])) bulunan.push(`${o[1]}="${o[2]}"`);
  }
  return bulunan;
}

describe("sozluk_mobil", () => {
  const anahtarlar = Object.keys(SOZLUK_MOBIL);

  it("her anahtar m. ile baslar, tr ve en dolu, yer tutucular ayni", () => {
    expect(anahtarlar.length).toBeGreaterThan(0);
    for (const a of anahtarlar) {
      const { tr, en } = SOZLUK_MOBIL[a];
      expect(a.startsWith("m."), a).toBe(true);
      expect(typeof tr === "string" && tr.trim().length > 0, `${a} tr`).toBe(true);
      expect(typeof en === "string" && en.trim().length > 0, `${a} en`).toBe(true);
      expect(yerTutucular(en), a).toBe(yerTutucular(tr));
    }
  });

  it("ortak sozlukle cakisma yok", () => {
    for (const a of anahtarlar) expect(Object.hasOwn(SOZLUK, a), a).toBe(false);
  });

  it("kaynakta kullanilan her m. anahtari sozlukte; sozlukteki her anahtar kullaniliyor", () => {
    const kaynak = dosyalar(SRC, [".vue", ".js"])
      .filter((y) => !y.endsWith("sozluk_mobil.js"))
      .map((y) => readFileSync(y, "utf8")).join("\n");
    const kullanilan = new Set([...kaynak.matchAll(/["'`](m\.[a-z0-9_.]+)["'`]/g)].map((m) => m[1]));
    for (const a of kullanilan) expect(Object.hasOwn(SOZLUK_MOBIL, a), `sozlukte yok: ${a}`).toBe(true);
    for (const a of anahtarlar) expect(kullanilan.has(a), `kullanilmiyor: ${a}`).toBe(true);
  });

  it("ceviriMobil atmaz; dil secer; ortak sozluge duser", () => {
    expect(ceviriMobil("m.uygulama", "tr")).toBe("Ölçüm Kartı");
    expect(ceviriMobil("m.uygulama", "en")).toBe("Measurement Board");
    expect(() => ceviriMobil("m.yok.boyle.anahtar", "tr")).not.toThrow();
  });
});

describe("ekrana gomulu metin yok", () => {
  it("ayiklayici gomulu metni ve duz ozelligi yakalar (kendi sinamasi)", () => {
    expect(gomuluMetinler("<template><p>Merhaba</p></template>")).toEqual(["Merhaba"]);
    expect(gomuluMetinler('<template><b aria-label="Dur"/></template>')).toEqual(['aria-label="Dur"']);
    expect(gomuluMetinler('<template><p :title="c(\'m.x\')">{{ c("m.x") }} · 12</p></template>')).toEqual([]);
  });

  it("src/**/*.vue sablonlarinda harf iceren duz metin yok", () => {
    const vueler = dosyalar(SRC, [".vue"]);
    expect(vueler.length).toBeGreaterThan(0);
    for (const y of vueler) expect(gomuluMetinler(readFileSync(y, "utf8")), y).toEqual([]);
  });
});
