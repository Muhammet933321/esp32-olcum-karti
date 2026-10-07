// Curutucu 5D — B1: 5D'nin esitleme metinleri, eslestirme ekraninin AYNI adli anahtarlarini EZDI.
// sozluk_mobil.js tek nesne degismezidir; ayni anahtar iki kez yazilirsa JS SONUNCUYU tutar, hata vermez.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ceviriMobil } from "../../src/cekirdek/sozluk_mobil.js";

const oku = (yol) => readFileSync(fileURLToPath(new URL(`../../src/${yol}`, import.meta.url)), "utf8");

describe("curutucu 5D — sozluk", () => {
  it("sozluk_mobil.js'te hicbir anahtar IKI kez tanimlanmaz (sonraki tanim oncekini sessizce ezer)", () => {
    const adlar = [...oku("cekirdek/sozluk_mobil.js").matchAll(/^ {2}"(m\.[A-Za-z0-9_.]+)":/gm)].map((m) => m[1]);
    expect(adlar.length).toBeGreaterThan(100);
    const sayim = new Map();
    for (const a of adlar) sayim.set(a, (sayim.get(a) || 0) + 1);
    expect([...sayim].filter(([, n]) => n > 1).map(([a]) => a)).toEqual([]);
  });

  it("eslestirme (Bu telefon › Kart, KartBolumu.vue) kendi metnini gosterir: 'Eslestirildi', esitleme cumlesi DEGIL", () => {
    // KartBolumu.vue bu iki anahtari kullaniyor (kaynakta dogrulanir; 5P P6'dan once Esles.vue), beklenen metinler eslestirmeye aittir.
    const e = oku("telefon/KartBolumu.vue");
    expect(e).toContain("t('m.es.tamam')");
    expect(e).toContain("t('m.es.suruyor')");
    const tamam = ceviriMobil("m.es.tamam", "tr");
    const suruyor = ceviriMobil("m.es.suruyor", "tr");
    expect(tamam).not.toContain("{dk}");                  // bolum deger vermez: ham yer tutucu ekrana cikar
    expect(tamam).not.toMatch(/kopya/i);
    expect(suruyor).not.toMatch(/Kayıtlar|telefona alınıyor/);
  });
});
