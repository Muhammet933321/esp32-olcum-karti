// "Bu telefon" giris noktasi (telefon/index.js): ortamin ayarBolumu() sozlesmesi (5P K13) — bolum() bir Vue
// bileseni doner; BuTelefon.vue dort alt bolumu ve GERCEK baglami baglar; calisma aninda sablon derlenmez.
import { describe, it, expect, vi } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

// vitest'te vue eklentisi yok: SFC'nin kendisi burada taklit edilir (sablonu telefon_bolum.test.js derler).
vi.mock("../src/telefon/BuTelefon.vue", () => ({ default: { name: "BuTelefonBolumu", props: { dilSecim: String } } }));

const TELEFON = fileURLToPath(new URL("../src/telefon", import.meta.url));
const oku = (ad) => readFileSync(join(TELEFON, ad), "utf8");

describe("telefon/index.js", () => {
  it("bolum() BuTelefon.vue'nun varsayilan bilesenini doner (tembel ice aktarma)", async () => {
    const { bolum, baglantiDinle, mesgulMu } = await import("../src/telefon/index.js");
    const b = await bolum();
    expect(b).toMatchObject({ name: "BuTelefonBolumu" });
    expect(typeof b.props.dilSecim).toBe("function");
    expect(await bolum()).toBe(b);
    expect(typeof baglantiDinle).toBe("function");
    expect(mesgulMu()).toBe(false);
    expect(oku("index.js")).toMatch(/export async function bolum\(\) \{\n\s+const m = await import\("\.\/BuTelefon\.vue"\);\n\s+return m\.default;/);
  });

  it("BuTelefon.vue: kok secenekleri + dort alt bolum + gercek baglam; prop dilSecim", async () => {
    const vue = oku("BuTelefon.vue");
    for (const ad of ["KartBolumu", "EsitlemeBolumu", "BildirimBolumu", "GelismisBolumu"]) {
      expect(vue).toContain(`import ${ad} from "./${ad}.vue";`);
      expect(vue).toContain(`<${ad.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase()} :dil="dil" :b="b"`);
    }
    expect(vue).toContain("components: { KartBolumu, EsitlemeBolumu, BildirimBolumu, GelismisBolumu }");
    expect(vue).toContain("methods: { ...BU_TELEFON.methods, varsayilanBaglam: gercekBaglam }");
    const { BU_TELEFON } = await import("../src/telefon/bu_telefon.js");
    expect(Object.keys(BU_TELEFON.props)).toEqual(["dilSecim", "baglam"]);
  });

  it("calisma aninda sablon derlenmez: telefon/ JS'inde `template:` yok; her .vue'nun <template>'i var", () => {
    for (const ad of readdirSync(TELEFON)) {
      const k = oku(ad);
      if (ad.endsWith(".js")) expect(k, ad).not.toMatch(/\btemplate\s*:/);
      if (ad.endsWith(".vue")) {
        expect(k, ad).toMatch(/<template>[\s\S]+<\/template>/);
        expect(k, ad).toMatch(/<script>[\s\S]*export default/);
      }
    }
  });

  it("kart / kasa KURULMAZ: cekirdek uygulama.js'in tekil nesnesi (S1); Ionic yok", () => {
    for (const ad of readdirSync(TELEFON)) {
      const k = oku(ad);
      expect(k, ad).not.toMatch(/\bkartKur\(|\bkasaKur\(|@ionic|<ion-/);
    }
    expect(oku("baglam.js")).toContain('from "../cekirdek/uygulama.js";');
  });
});
