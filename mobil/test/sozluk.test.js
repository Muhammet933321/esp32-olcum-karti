// Sozluk kurallari (A43) + "ekrana gomulu metin yok" (tasarim §4 Ekranlar).
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { SOZLUK } from "@ortak/sozluk.js";
import { SOZLUK_MOBIL, ceviriMobil } from "../src/cekirdek/sozluk_mobil.js";
import { gomuluMetinler } from "./yardim/gomulu_metin.mjs";

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
    expect(ceviriMobil("m.bt.baslik", "tr")).toBe("Bu telefon");
    expect(ceviriMobil("m.bt.baslik", "en")).toBe("This phone");
    expect(() => ceviriMobil("m.yok.boyle.anahtar", "tr")).not.toThrow();
  });
});

describe("ekrana gomulu metin yok", () => {
  it("ayiklayici gomulu metni ve duz ozelligi yakalar (kendi sinamasi)", () => {
    expect(gomuluMetinler("<template><p>Merhaba</p></template>")).toEqual(["Merhaba"]);
    expect(gomuluMetinler('<template><b aria-label="Dur"/></template>')).toEqual(['aria-label="Dur"']);
    expect(gomuluMetinler('<template><p :title="c(\'m.x.y\')">{{ c("m.x.y") }} · 12</p></template>')).toEqual([]);
    expect(gomuluMetinler("<template><b title='Dur'/></template>")).toEqual(['title="Dur"']);
    // Curutucu 5A-7 (S1–S5): bagli ozellik, v-text, {{ }} icindeki sabit ve betikteki cumle de yakalanir.
    expect(gomuluMetinler(`<template><b :helper-text="'Adres gir'"/></template>`).length).toBe(1);
    expect(gomuluMetinler(`<template><b v-text="'Bulundu!'"/></template>`).length).toBe(1);
    expect(gomuluMetinler('<template><p>{{ x + " (deneme sürümü)" }}</p></template>').length).toBe(1);
    expect(gomuluMetinler('<script setup>\nhata.value = c("m.x.y") + " — tekrar deneyin";\n</script>').length).toBe(1);
    // Karsilastirma belirteci, sozluk anahtari, boyut adi ve import yolu metin DEGILDIR.
    expect(gomuluMetinler(`<template><b v-if="s.kaynak === 'nsd'" :size="'large'" :key="a + b"/></template>`)).toEqual([]);
    expect(gomuluMetinler('<script setup>\nimport { x } from "../cekirdek/ag.js";\nconst T = { "kimlik-uymuyor": "m.kb.hata_kimlik" };\n</script>')).toEqual([]);
  });

  it("src/**/*.vue sablonlarinda harf iceren duz metin yok", () => {
    const vueler = dosyalar(SRC, [".vue"]);
    expect(vueler.length).toBeGreaterThan(0);
    for (const y of vueler) expect(gomuluMetinler(readFileSync(y, "utf8")), y).toEqual([]);
  });
});
