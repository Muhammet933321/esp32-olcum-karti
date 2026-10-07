// Olcum gorunumu (Bu telefon > Gelismis: PBKDF2 olcumu; src/ekran/olcum_gorunum.js — telefon/gelismis_bolum.js kullanir).
// 5P (P6): eski Ionic ekranlarinin (Durum / Canli / kabuk) testleri ekranlarla birlikte silindi.
import { describe, it, expect } from "vitest";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { OZET_HANE, pbkdf2Gorunumu } from "../src/ekran/olcum_gorunum.js";

describe("Ayarlar > Gelismis: PBKDF2 olcumu gorunumu", () => {
  const o = { tur: 20000, sureler: [30, 29, 44], enAz: 29, ortanca: 30, enCok: 44, ozet: "3f042897317e112506e74084a8529f73c13d0720f75925a0d42d209d464cc676" };

  it("dogru / YANLIS / basvuru yok ayri metin; ozetin ilk 16 hanesi; sure yer tutuculari", () => {
    expect(pbkdf2Gorunumu({ ...o, dogru: true })).toEqual({ sure: { tur: 20000, enaz: 29, ortanca: 30, encok: 44 }, dogrulama: "m.ol.dogru", sinif: "", ozet: "3f042897317e1125" });
    expect(pbkdf2Gorunumu({ ...o, dogru: false })).toMatchObject({ dogrulama: "m.ol.yanlis", sinif: "hata" });
    expect(pbkdf2Gorunumu({ ...o, tur: 50000, dogru: null }).dogrulama).toBe("m.ol.basvuru_yok");
    expect(OZET_HANE).toBe(16);
    expect(new Set(["m.ol.dogru", "m.ol.yanlis", "m.ol.basvuru_yok"].map((a) => SOZLUK_MOBIL[a].tr)).size).toBe(3);
    expect(SOZLUK_MOBIL["m.ol.uygulama"].tr).toBe("Uygulama: saf JS (WebView)");
  });
});
