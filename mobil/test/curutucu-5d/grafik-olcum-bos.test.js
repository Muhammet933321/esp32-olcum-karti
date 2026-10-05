// Curutucu 5D — Ö6 olcumu (A27): "p95 < 33 ms GECTI" HICBIR SEY cizilmeden de cikabiliyor.
// GERCEK ortak Grafik + GERCEK grafikOlc; tuval sahte (2B baglam her cagriyi sayar), saat sahte.
// Grafik.ciz() tuvalin gorunen boyu 0 ise (duzen henuz kurulmadi, bolum kapali, ekran dondu) temizleyip
// `null` doner — cizim YOK. grafikOlc bunu denetlemiyor: kare araligi ekranin 16.7 ms'si olur ve "GECTI" yazilir.
import { describe, it, expect } from "vitest";
import { Grafik } from "../../../ortak/src/grafik.js";
import { grafikOlc, grafikSerileri, kareBetigi, seriUret } from "../../src/cekirdek/grafik_olcum.js";

function tuvalKur(w, h) {
  const sayac = { cizgi: 0 };
  const ctx = new Proxy({}, {
    get(hedef, ad) {
      if (ad in hedef) return hedef[ad];
      if (ad === "measureText") return () => ({ width: 10 });
      return (...a) => { if (ad === "lineTo" || ad === "fillRect" || ad === "stroke") sayac.cizgi += 1; return undefined; };
    },
    set(hedef, ad, v) { hedef[ad] = v; return true; },
  });
  const tuval = {
    clientWidth: w, clientHeight: h, width: 0, height: 0, style: {}, tabIndex: 0,
    getContext: () => ctx, addEventListener() {}, removeEventListener() {},
  };
  return { tuval, sayac };
}

async function olc(w, h) {
  const { tuval, sayac } = tuvalKur(w, h);
  const saat = { ms: 0 };
  // pencere: rAF yok (istek() hemen cizer), dpr 1; renkler yedekten.
  const grafik = new Grafik(tuval, { zamanKokeni: 0, pencere: { devicePixelRatio: 1 }, renk: () => "#888888" });
  const seri = seriUret(20000);
  const sonuc = await grafikOlc({
    grafik, seriler: grafikSerileri(seri), kareler: kareBetigi(seri.t[0], seri.t[19999], 40),
    simdi: () => saat.ms, kareBekle: async () => { saat.ms += 16.7; },      // 60 Hz ekran
  }).then((s) => s, () => "atti");
  return { sonuc, sayac };
}

describe("curutucu 5D — Ö6 grafik olcumu", () => {
  it("denetim: gorunen tuvalde olcum gercekten cizer", async () => {
    const { sonuc, sayac } = await olc(360, 240);
    expect(sayac.cizgi).toBeGreaterThan(1000);
    expect(sonuc.gecti).toBe(true);
  });

  it("tuval gorunmuyorken (0 x 0: hicbir sey cizilmez) olcum 'GECTI' DEMEZ", async () => {
    const { sonuc, sayac } = await olc(0, 0);
    expect(sayac.cizgi).toBe(0);                       // kanit: tek bir cizgi bile cizilmedi
    // Dogru davranis: null (olcum yapilamadi) / hata / gecti: false — ama ASLA gecti: true.
    expect(sonuc && sonuc !== "atti" ? sonuc.gecti : false).toBe(false);
  });
});
