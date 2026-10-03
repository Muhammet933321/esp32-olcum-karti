// Kosucunun KENDI sinamasi: yalanci "OLDU" vermiyor, yasayan mutasyonu ve olmayan deseni soyluyor.
import { describe, it, expect } from "vitest";
import { biriniKos, uygula } from "../mutasyon/kos.mjs";

describe("mutasyon kosucusu", () => {
  it("uygula: tam bir kez gecen deseni degistirir; yoksa / cogulsa hata", () => {
    expect(uygula("a b c", "b", "X")).toEqual({ metin: "a X c" });
    expect(uygula("a b c", "z", "X")).toEqual({ hata: "desen yok" });
    expect(uygula("a b b", "b", "X")).toEqual({ hata: "desen birden cok" });
  });

  it("iddiayi bozan mutasyon OLDU", () => {
    const r = biriniKos({ ad: "x", dosya: "src/cekirdek/sozluk_mobil.js", bul: '"Measurement Board"', koy: '""', test: "test/sozluk.test.js" });
    expect(r.sonuc).toBe("OLDU");
  }, 120000);

  it("davranisi degistirmeyen mutasyon YASIYOR", () => {
    const r = biriniKos({ ad: "x", dosya: "src/cekirdek/sozluk_mobil.js", bul: "HICBIR ZAMAN ATMAZ", koy: "hic atmaz", test: "test/sozluk.test.js" });
    expect(r.sonuc).toBe("YASIYOR");
  }, 120000);

  it("sozdizimini bozan mutasyon OLDU sayilmaz (SUPHELI)", () => {
    const r = biriniKos({ ad: "x", dosya: "src/cekirdek/sozluk_mobil.js", bul: "export const SOZLUK_MOBIL", koy: "export const const SOZLUK_MOBIL", test: "test/sozluk.test.js" });
    expect(r.sonuc).toBe("SUPHELI");
  }, 120000);

  it("deseni olmayan mutasyon UYGULANAMADI", () => {
    const r = biriniKos({ ad: "x", dosya: "src/cekirdek/sozluk_mobil.js", bul: "boyle bir dizgi yok", koy: "", test: "test/sozluk.test.js" });
    expect(r.sonuc).toBe("UYGULANAMADI");
  });
});
