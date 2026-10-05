// Curutucu 5D — Ö6 (A27) olcumu kayit gorunumunun GERCEK cizim yolunu olcmuyor.
// GrafikOlcum.vue Grafik'e HAM diziler verir. Kayit.vue ise Worker'dan gelen veriyi `ref(...)` icinde tutar:
// Vue `ref` DERIN tepkilidir — seri nesneleri ve piramit (`oz`, `oz.duzeyler[...]`) Proxy olur; Grafik.ciz()
// her karede piramide bu Proxy'lerin tuzaklarindan erisir. Olculen yol (ham) ile kullanicinin gordugu yol
// (tepkili) ayni degil; bu makinede tepkili yol ~6-7 kat yavas (asagidaki olcum yazdirilir).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as Vue from "vue";
import { Grafik, seriHazirla } from "../../../ortak/src/grafik.js";
import { ozetKur } from "../../../ortak/src/ozet.js";
import { gorunurluk } from "../../../arayuz3/ekran/kayit_gorunum.js";
import { grafikSerileri, kareBetigi, seriUret } from "../../src/cekirdek/grafik_olcum.js";

const kayitVue = readFileSync(fileURLToPath(new URL("../../src/ekran/Kayit.vue", import.meta.url)), "utf8");

// Kayit.vue'nun veriyi tuttugu kap (kaynaktan okunur: `const veri = ref(null);` / shallowRef / ...).
function kayitEkraniKabi() {
  const m = /^const veri = (\w+)\(null\);$/m.exec(kayitVue);
  expect(m, "Kayit.vue'da `const veri = <kap>(null);` bulunamadi").not.toBe(null);
  expect(typeof Vue[m[1]]).toBe("function");
  return Vue[m[1]](null);
}

// Worker'dan gelen gorunum verisinin bicimi (kayit_veri.js oturumGorunumu): seriler piramitleriyle.
function iscidenGelen(n) {
  const seri = seriUret(n);
  return { seri, seriler: grafikSerileri(seri).map((s) => ({ ...s, oz: ozetKur(s.t, s.y) })) };
}

// Kayit.vue: grafik.veriAyarla(gorunurluk(veri.value.seriler, { v: true, sag, zarf: true }))
const ekraninVerdigi = (kap) => gorunurluk(kap.value.seriler, { v: true, sag: "akim", zarf: true });

function tuvalKur(w, h) {
  const ctx = new Proxy({}, {
    get(hedef, ad) { if (ad in hedef) return hedef[ad]; if (ad === "measureText") return () => ({ width: 10 }); return () => undefined; },
    set(hedef, ad, v) { hedef[ad] = v; return true; },
  });
  return { clientWidth: w, clientHeight: h, width: 0, height: 0, style: {}, tabIndex: 0, getContext: () => ctx, addEventListener() {}, removeEventListener() {} };
}

function p95(seriler, kareler) {
  const g = new Grafik(tuvalKur(360, 240), { zamanKokeni: 0, pencere: { devicePixelRatio: 1 }, renk: () => "#888888" });
  g.veriAyarla(seriler);
  const s = [];
  for (const [t0, t1] of kareler) { g.durumAyarla({ t0, t1 }); const a = performance.now(); g.ciz(); s.push(performance.now() - a); }
  s.sort((a, b) => a - b);
  return s[Math.floor(s.length * 0.95)];
}

describe("curutucu 5D — Ö6 olcumu ile kayit gorunumu ayni yolu cizer", () => {
  it("Kayit.vue'nun Grafik'e verdigi seriler ve piramitleri Vue Proxy'si DEGIL (olcum araci ham dizilerle olcuyor)", () => {
    const kap = kayitEkraniKabi();
    kap.value = { seriler: iscidenGelen(2000).seriler, t0: 0, t1: 1 };
    const verilen = ekraninVerdigi(kap).map(seriHazirla);
    expect(verilen.length).toBeGreaterThan(0);
    for (const s of verilen) {
      expect(s.oz, "piramit yeniden kurulmamali").toBeTruthy();
      expect(Vue.isReactive(s.oz), `seri ${s.ad}: piramit (oz) tepkili Proxy`).toBe(false);
      expect(Vue.isReactive(s.oz.duzeyler), `seri ${s.ad}: oz.duzeyler tepkili Proxy`).toBe(false);
    }
  });

  it("800 bin noktada kayit ekraninin yolu, olcum aracinin yolundan en cok 2 kat yavas (bugun ~6-7 kat)", () => {
    const N = 800000;
    const { seri, seriler } = iscidenGelen(N);
    const kareler = kareBetigi(seri.t[0], seri.t[N - 1], 200);
    p95(seriler, kareler);                                   // isinma
    const ham = Math.min(p95(seriler, kareler), p95(seriler, kareler));
    const kap = kayitEkraniKabi();
    kap.value = { seriler: seriler.map((s) => ({ ...s })), t0: 0, t1: 1 };
    const ekran = Math.min(p95(ekraninVerdigi(kap), kareler), p95(ekraninVerdigi(kap), kareler));
    console.log(`cizim p95: olcum araci yolu ${ham.toFixed(2)} ms, kayit ekrani yolu ${ekran.toFixed(2)} ms, oran ${(ekran / ham).toFixed(1)}x`);
    expect(ekran / ham).toBeLessThan(2);
  });
});
