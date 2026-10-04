// CURUTUCU (5A-7): ag.js'e karsi kanit testleri. Su an KIRMIZI. Ag YOK (eklenti sahte).
import { describe, it, expect } from "vitest";
import { agKur, KartAgHatasi, urlDenetle } from "../../src/cekirdek/ag.js";

describe("curutucu / ag", () => {
  it("A1: urlDenetle, ad cevresinde BOSLUK olan URL'yi kabul ediyor (Kotlin ayni URL'yi 'bicim' ile reddeder)", () => {
    // JS kapisi "istegi hic kurmadan dogru hatayi soylemek icin" — burada soylemiyor; karar Kotlin'e kaliyor.
    expect(() => urlDenetle("http:// 192.168.1.5 /x")).toThrow(KartAgHatasi);
  });

  it("A2: eklenti bozuk base64 govde donerse kartFetch KartAgHatasi DEGIL ham DOMException atar (hata sozlesmesi delinir)", async () => {
    const ag = agKur({ istek: async () => ({ kod: 200, basliklar: {}, govde: "***bozuk***" }) });
    const h = await ag.kartFetch("http://192.168.1.5/x").catch((e) => e);
    expect(h, `atilan: ${h?.name}`).toBeInstanceOf(KartAgHatasi);
  });

  it("A3: eklenti hic donmezse kartFetch de hic donmez — zamanAsimiMs yalniz eklentiye EMANET", async () => {
    const ag = agKur({ istek: () => new Promise(() => {}) }, { zamanAsimiMs: 100 });
    const s = await Promise.race([
      ag.kartFetch("http://192.168.1.5/x").then(() => "dondu", (e) => `hata:${e.tur}`),
      new Promise((c) => setTimeout(() => c("ASILI KALDI"), 1500)),
    ]);
    expect(s).toBe("hata:zaman-asimi");
  });
});
