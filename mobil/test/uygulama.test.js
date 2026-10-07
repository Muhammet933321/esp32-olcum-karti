// uygulama.js (S1, curutucu 5B S4): uygulamada TEK kart / kasa nesnesi. Ekranlar kartKur / kasaKur cagirmaz.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const sayim = vi.hoisted(() => ({ wifi: 0, liste: 0, boz: false }));

vi.mock("../src/cekirdek/eklenti.js", () => ({
  KartAg: {
    wifiDurumu: async () => {
      sayim.wifi += 1;
      if (sayim.boz) throw new Error("eklenti yok");
      return { hataAyiklama: false };
    },
    istek: async () => { throw new Error("kullanilmaz"); },
  },
  Kesif: { ara: async () => ({ servisler: [] }) },
  Kasa: {
    liste: async () => { sayim.liste += 1; return { kayitlar: [] }; },
    sayacYaz: async () => ({}), sayacOku: async () => ({ isaret: "0" }),
    anahtarYaz: async () => ({}), anahtarOku: async () => ({}), sil: async () => ({}),
  },
}));

const SRC = fileURLToPath(new URL("../src", import.meta.url));

function dosyalar(dizin) {
  const cikti = [];
  for (const ad of readdirSync(dizin)) {
    const yol = join(dizin, ad);
    if (statSync(yol).isDirectory()) cikti.push(...dosyalar(yol));
    else if (ad.endsWith(".js") || ad.endsWith(".vue")) cikti.push(yol);
  }
  return cikti;
}

describe("uygulama: tek kart nesnesi", () => {
  beforeEach(() => {
    sayim.wifi = 0; sayim.liste = 0; sayim.boz = false;
    vi.resetModules();
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it("kartAl her cagrida (art arda ve ES ZAMANLI) AYNI nesneyi doner; kurulum bir kez", async () => {
    const { kartAl } = await import("../src/cekirdek/uygulama.js");
    const [a, b] = await Promise.all([kartAl(), kartAl()]);
    const c = await kartAl();
    expect(typeof a.baglan).toBe("function");
    expect(b).toBe(a);
    expect(c).toBe(a);
    expect(sayim.wifi).toBe(1);
  });

  it("kurulum basarisiz olursa hata cagirana gider ve SAKLANMAZ: sonraki cagri yeniden kurar", async () => {
    const { kartAl } = await import("../src/cekirdek/uygulama.js");
    sayim.boz = true;
    await expect(kartAl()).rejects.toThrow();
    sayim.boz = false;
    const a = await kartAl();
    expect(a).toBe(await kartAl());
    expect(sayim.wifi).toBe(2);
  });

  it("src/ agacinda kartKur( ve kasaKur( CAGRISI yalniz uygulama.js'te (ekranlar kendi kasasini kuramaz)", () => {
    const cagiranlar = { kartKur: [], kasaKur: [] };
    for (const yol of dosyalar(SRC)) {
      const kod = readFileSync(yol, "utf8").split("\n").filter((l) => !/^\s*(\/\/|\*)/.test(l)).join("\n");
      const ad = yol.slice(SRC.length + 1).split("\\").join("/");
      if (/(?<!function )\bkartKur\(/.test(kod)) cagiranlar.kartKur.push(ad);
      if (/(?<!function )\bkasaKur\(/.test(kod)) cagiranlar.kasaKur.push(ad);
    }
    expect(cagiranlar).toEqual({ kartKur: ["cekirdek/uygulama.js"], kasaKur: ["cekirdek/uygulama.js"] });
  });

  it("Bu telefon (telefon/baglam.js) ve telefon ortami kart nesnesini kartAl'dan alir", () => {
    // 5P (P6): eski Baglanti.vue silindi; kartla konusan canli yollar bunlar.
    const baglam = readFileSync(join(SRC, "telefon", "baglam.js"), "utf8");
    expect(baglam).toMatch(/import \{[^}]*\bkartAl\b[^}]*\} from "\.\.\/cekirdek\/uygulama\.js";/);
    expect(baglam).toMatch(/^ {4}kartAl,$/m);
    const ortam = readFileSync(join(SRC, "ortam", "index.js"), "utf8");
    expect(ortam).toMatch(/import \{[^}]*\bkartAl\b[^}]*\} from "\.\.\/cekirdek\/uygulama\.js";/);
  });
});
