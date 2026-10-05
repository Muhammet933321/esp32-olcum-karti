// Curutucu 5D — Kayit.vue: "gorunen araligin istatistigi" grafikte GORUNMEYEN bir araliga ait kalabiliyor.
// Vue bileseni Node'da baglanamiyor (DOM / SFC derleyici yok); bunun yerine Kayit.vue'nun <script setup>
// METNI kaynaktan okunur, ice aktarimlari sahteleriyle degistirilir ve AYNEN calistirilir (kopya mantik yok).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { computed, nextTick, ref, shallowRef, watch } from "vue";

const kaynak = readFileSync(fileURLToPath(new URL("../../src/ekran/Kayit.vue", import.meta.url)), "utf8");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

function ekranKur() {
  const betik = /<script setup>\n([\s\S]*?)<\/script>/.exec(kaynak)[1];
  const govde = betik.split("\n").filter((l) => !/^import /.test(l)).join("\n")
    + "\nreturn { tumunuGoster, pencereDegisti, okuma, veri, tuval, hal, tablo };";
  const kancalar = { mounted: [], unmount: [] };
  const grafikler = [];
  class Grafik {
    constructor(el, secenek) { this.onDegisim = secenek.onDegisim; this.durum = null; grafikler.push(this); }
    veriAyarla() {}
    durumAyarla(d) { this.durum = d; }            // gercek Grafik: sessiz (onDegisim CAGRILMAZ)
    ciz() {}
    yokEt() {}
  }
  const okumalar = [];
  const kaynakNesne = {
    oturum: async (no) => ({ oturum: no, tur: "nokta", adet: 100, gecerli: 100, t0: 0, t1: 100000, tahmini: false, seriler: [], baslik: null, notlar: [] }),
    okuma: async (no, tA, tB) => {
      okumalar.push([tA, tB]);
      return { dt: tB - tA, sure: `${tA}-${tB}`, v: { birim: "V", adet: 1, ort: tA, min: tA, maks: tB, rms: 0 }, i: null, w: null, enerji: null };
    },
  };
  const ortam = {
    computed, ref, shallowRef, watch,
    onMounted: (fn) => kancalar.mounted.push(fn),
    onBeforeUnmount: (fn) => kancalar.unmount.push(fn),
    useRoute: () => ({ params: { oturum: "101" } }),
    useRouter: () => ({ push() {} }),
    Grafik,
    gorunurluk: (s) => s,
    Ikon: {},
    temaDinle: () => () => {},
    kayitlarAl: async () => kaynakNesne,
    SAG_EKSENLER: [],
    okumaTablosu: (ok) => (ok ? { sure: ok.sure } : null),
    satirGorunumu: (s) => s,
    c: (a) => a,
  };
  const adlar = Object.keys(ortam);
  // eslint-disable-next-line no-new-func
  const e = new Function(...adlar, govde)(...adlar.map((a) => ortam[a]));
  return { e, kancalar, grafikler, okumalar };
}

describe("curutucu 5D — Kayit.vue", () => {
  it("denetim: betik calisir; acilista istatistik TUM aralik icin istenir", async () => {
    const { e, kancalar, grafikler, okumalar } = ekranKur();
    await Promise.all(kancalar.mounted.map((fn) => fn()));
    expect(e.hal.value).toBe("hazir");
    e.tuval.value = { sahte: true };
    await nextTick(); await bekle(5);
    expect(grafikler.length).toBe(1);
    expect(okumalar).toEqual([[0, 100000]]);
    expect(e.tablo.value.sure).toBe("0-100000");
    for (const fn of kancalar.unmount) fn();
  });

  it("kaydirmadan hemen sonra 'Tumunu goster'e basilirsa tablo TUM araligin istatistigini gosterir (bekleyen eski pencere ezmez)", async () => {
    const { e, kancalar, grafikler } = ekranKur();
    await Promise.all(kancalar.mounted.map((fn) => fn()));
    e.tuval.value = { sahte: true };
    await nextTick(); await bekle(5);
    const g = grafikler[0];
    g.onDegisim({ t0: 40000, t1: 41000 }, g);        // kullanici yakinlastirdi / kaydirdi (150 ms sonra istatistik istenecek)
    await bekle(20);
    e.tumunuGoster();                                // 150 ms dolmadan: grafik [0, 100000] gosteriyor
    expect(g.durum).toEqual({ t0: 0, t1: 100000 });
    await bekle(300);
    expect(e.tablo.value.sure).toBe("0-100000");     // bugun: "40000-41000" (grafikte gorunmeyen aralik)
    for (const fn of kancalar.unmount) fn();
  });
});
