// CURUTUCU 5C — ekranin "yanlis ama emin" gosterdigi degerler. 5P (P6): eski Ionic ekranlarinin (Durum / Canli,
// kabukDurumu) bulgulari o dosyalarla birlikte silindi; burada canli.js'in grafik tamponu kaldi (GERCEK canliKur).
import { describe, it, expect } from "vitest";
import { canliKur } from "../../src/cekirdek/canli.js";

describe("curutucu 5C: grafik tamponu okunamayan olcumu de ciziyor", () => {
  function canliDuzenegi() {
    const dinleyen = {};
    const kart = { durum: () => ({ durum: "bagli" }), istek: async () => ({}), akisUrl: async () => "http://192.168.1.7:80/akis?_c=1&_s=1&_i=00" };
    const ag = { akisAc: async () => ({ kimlik: "a1" }), akisKapat: async () => {} };
    const canli = canliKur({ kart, ag, eklenti: { addListener: (ad, fn) => { dinleyen[ad] = fn; } } });
    return { canli, yay: (ad, veri) => dinleyen[ad](veri) };
  }

  it("adc_hata = 3 (iki ADC de okunamadi) ve 'nan' satirlari seri()'ye GIRMEMELI", async () => {
    const s = canliDuzenegi();
    s.canli.baslat();
    await new Promise((c) => setTimeout(c, 0));
    await new Promise((c) => setTimeout(c, 0));
    s.yay("akisDurum", { kimlik: "a1", hal: "acik" });
    s.yay("akis", { kimlik: "a1", satirlar: [
      "D 0.0000 0.000000 0.00000 10.0000 0.0027778 123456 500 0 3",      // okunamadi: sayilar anlamsiz
      "D nan nan nan 10.0000 0.0027778 123457 501 0 0",
    ] });
    const seri = s.canli.seri();
    s.canli.durdur();
    console.log(`[grafik] seri.n=${seri.n} v=[${Array.from(seri.v).join(",")}]`);
    expect(seri.n).toBe(0);                                    // KIRMIZI: grafik 0 V ve NaN noktasi ciziyor
  });
});
