// Curutucu 5D — Durum ekraninin esitleme satiri: "Telefondaki kopya guncel" YANLIS soylenebiliyor.
import { describe, it, expect } from "vitest";
import { esitlemeGorunumu } from "../../src/ekran/durum_gorunum.js";
import { ceviriMobil } from "../../src/cekirdek/sozluk_mobil.js";

const BAGLI = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" };
const TAMAM = { hazir: true, hal: "tamam", sonMs: 1000, yeni: 0, sonSira: 500, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false };

describe("curutucu 5D — esitleme satiri", () => {
  it("denetim: bekleyen yokken 'guncel' ve yesil", () => {
    const g = esitlemeGorunumu(TAMAM, BAGLI, 1500);
    expect(g.sinif).toBe("iyi");
    expect(ceviriMobil(g.anahtar, "tr", g.degerler)).toMatch(/güncel/);
  });

  it("kartta telefonun ALAMADIGI daha yeni kayit varken (bekleyen > 0) satir 'kopya guncel' DEMEZ ve yesil olmaz", () => {
    // Esitleyici: bos yanit + X-Sonraki-Sira ileride -> { bekleyen: N }. Kopya kartin N sira GERISINDE.
    const g = esitlemeGorunumu({ ...TAMAM, bekleyen: 37 }, BAGLI, 1500);
    const yazi = ceviriMobil(g.anahtar, "tr", g.degerler);
    expect(g.ek).toBe("m.es.bekleyen");                  // alt satir zaten "kartta daha yeni kayit var" diyor
    expect(yazi).not.toMatch(/güncel/);                   // ust satir ayni anda tersini soyluyor
    expect(g.sinif).not.toBe("iyi");
  });
});
