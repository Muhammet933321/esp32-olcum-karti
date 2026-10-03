// 5A-2 duman: `@ortak` takma adi paketlenecek kodun AYNISINI gosteriyor ve 1D vektorlerini geciyor.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { hex, hexten, utf8Kodla } from "@ortak/kripto.js";
import { imzala, kanonik, cihazAnahtari, kanitIstemci } from "@ortak/imza.js";

const V = JSON.parse(readFileSync(new URL("../../uretim/vektor_guvenlik.json", import.meta.url), "utf8"));

describe("ortak/ ice aktarma", () => {
  it("imza vektorleri (kanonik metin + imza)", () => {
    expect(V.imza.length).toBeGreaterThan(0);
    for (const v of V.imza) {
      const govde = hexten(v.govde);
      expect(hex(kanonik(v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde))).toBe(v.kanonik);
      expect(imzala(hexten(v.K), v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde)).toBe(v.imza);
    }
  });

  it("eslestirme vektoru (istemci kaniti + K)", () => {
    const p = V.protokol;
    const P = hexten(p.P);
    expect(hex(kanitIstemci(P, p.kimlik, hexten(p.nk), hexten(p.nc), p.ad))).toBe(p.kanit_istemci);
    expect(hex(cihazAnahtari(P, p.kimlik, hexten(p.nk), hexten(p.nc), p.n))).toBe(p.K);
  });
});
