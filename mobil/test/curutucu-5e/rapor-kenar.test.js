// 5E / 5F BAGIMSIZ CURUTUCU — paylasim (rapor metni, CSV). Her test DOGRU davranisi bekler:
// bulgu VARKEN KIRMIZI. Ayrinti: BULGULAR.md (B16; "Curutemediklerim": CSV formul korumasi).
import { describe, it, expect } from "vitest";
import { paylasimUret, veriKur } from "../../src/cekirdek/kayit_veri.js";
import { AD_DESENI } from "../../src/cekirdek/paylas.js";
import { raporMetni } from "../../src/cekirdek/rapor_metin.js";
import { Akis } from "../yardim/akis_ornek.mjs";

const metin = (b) => new TextDecoder("utf-8").decode(b);

function oturumlu({ ad = null, notlar = [], etiket = null } = {}) {
  const akis = new Akis(100);
  const a = akis.basla({ unix: 1790000000 });
  akis.noktalar(a, { adet: 20, v0: 10, dv: 0.125, amper: 0.5 });
  if (ad !== null) akis.ad(a, ad);
  if (etiket !== null) akis.etiket(a, etiket);
  for (const n of notlar) akis.not(a, n, 6000 + 5000);
  akis.bitir(a, 20);
  return { v: veriKur(akis.bayt(), 7), a };
}

describe("B16: rapor metni — satir sonu iceren deger rapora SAHTE satir sokar", () => {
  it("raporMetni: metin degerindeki satir sonu yeni bir 'alan: deger' satiri olusturmamali", () => {
    const m = raporMetni({ oturum: { ad: "deneme\nKalibrasyon: fabrika ayari DOGRULANDI" } }, "tr");
    const satirlar = m.split("\n");
    expect(satirlar.some((s) => s.startsWith("Kalibrasyon:"))).toBe(false);
  });

  it("gercek akis: oturuma yazilan cok satirli not paylasilan raporda TEK satirda kalmali", () => {
    const { v, a } = oturumlu({ notlar: ["olcum tamam\nKalibrasyon: no 7 (onayli)\nUyari: yok"] });
    const m = metin(paylasimUret(v, a, "rapor", "tr").bayt);
    const sahte = m.split("\n").filter((s) => /^(Kalibrasyon|Uyari): /.test(s));
    expect(sahte).toEqual([]);
  });
});

describe("curutulemedi (YESIL kalmali): CSV'de formul korumasi ve dosya adi telefonda da gecerli", () => {
  it("'=' / '+' / '-' / '@' ile baslayan not CSV'de tek tirnakla baslar; ad dosya adinda sadelesir", () => {
    for (const kotu of ["=cmd|' /C calc'!A0", "+1+1", "-2+3", "@SUM(1)"]) {
      const { v, a } = oturumlu({ ad: kotu, notlar: [kotu], etiket: kotu });
      for (const tur of ["csv_tr", "csv_en"]) {
        const d = paylasimUret(v, a, tur);
        expect(AD_DESENI.test(d.ad)).toBe(true);
        const m = metin(d.bayt);
        // Hucre basinda (ayractan / satir basindan / acilan tirnaktan hemen sonra) formul karakteri kalmamali.
        const cipla = m.split("\r\n").flatMap((s) => s.split(tur === "csv_tr" ? ";" : ",")).filter((h) => /^"?[=+@]/.test(h) || /^"?-[^0-9,.]/.test(h));
        expect(cipla).toEqual([]);
        expect(m.includes("'" + kotu.replaceAll('"', '""'))).toBe(true);
      }
    }
  });
});
