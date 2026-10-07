// 5P (P3) — telefon ortaminin ARKA PLANI (K17): eski App.vue / kabuk_durum.js'in kurdugu isler panelden
// bagimsiz. Elle saat + elle tik; kart / canli / esitleme / bildirim / pil sahte nesnelerle gozlenir.
import { describe, it, expect } from "vitest";
import { PIL_YOKLAMA_MS } from "../src/cekirdek/pil_durum.js";
import { TIK_MS, YENIDEN_ARA_MS, YENIDEN_DENE_MS, arkaPlanKur, oturumTuruBul } from "../src/ortam/arka_plan.js";

const KIM = "0123456789abcdef";
const bosalt = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };
const G = (durum, oturum) => ({ tur: "G", durum, oturum });

function dunya({ bulunur = true, eslesmis = true, liste = { oturumlar: [{ id: 41, tur: 1 }, { id: 42, tur: 2 }] } } = {}) {
  let t = 1_000_000;
  const d = {
    kartDurumu: "bagli-degil", baglanSayisi: 0, istekler: [], canliBaslat: 0, canliDurdur: 0,
    esit: [], bildirim: [], pilOkuma: 0, pilCevap: "BEKLEMEDE", soru: [], dil: [], mesgul: false, lang: "tr",
    tik: null, aralikSilindi: 0,
  };
  const kart = {
    durum: () => ({ durum: d.kartDurumu, adres: d.kartDurumu === "bagli-degil" ? null : "192.168.1.7", kimlik: d.kartDurumu === "bagli-degil" ? null : KIM }),
    baglan: async () => {
      d.baglanSayisi += 1;
      if (!bulunur) return { durum: "bulunamadi", adres: null, kimlik: null };
      d.kartDurumu = eslesmis ? "bagli" : "eslesmemis";
      return { durum: d.kartDurumu, adres: "192.168.1.7", kimlik: KIM };
    },
    istek: async (yontem, yol) => { d.istekler.push(yol); return { json: async () => liste }; },
  };
  let canliD = { hal: "kapali", sebep: null, kod: null, son: null, kayit: null };
  const canliDinle = new Set();
  const canli = {
    durum: () => canliD,
    dinle: (fn) => { canliDinle.add(fn); return () => canliDinle.delete(fn); },
    hamDinle: () => () => {},
    baslat: () => { d.canliBaslat += 1; canliD = { ...canliD, hal: "baglaniyor" }; },
    durdur: () => { d.canliDurdur += 1; canliD = { ...canliD, hal: "kapali" }; },
  };
  const yay = (parca) => { canliD = { ...canliD, ...parca }; for (const fn of canliDinle) fn(canliD); };
  const esit = {
    baglandi: () => d.esit.push("baglandi"), tik: (x) => d.esit.push(`tik:${x.gorunur}:${x.bagli}`),
    kayitBitti: () => d.esit.push("kayitBitti"), gorunurluk: (v) => d.esit.push(`gorunurluk:${v}`),
  };
  const belge = {
    visibilityState: "visible", documentElement: {}, l: null,
    addEventListener: (a, fn) => { belge.l = fn; }, removeEventListener: () => { belge.l = null; },
  };
  const arka = arkaPlanKur({
    kartAl: async () => kart, canliAl: async () => canli, esitlemeAl: async () => esit,
    bildirimIzle: { tik: (x) => d.bildirim.push(x) },
    pilOku: async () => { d.pilOkuma += 1; return d.pilCevap; },
    izlemeSorusu: { kayitBitti: () => d.soru.push("bitti") },
    bildirimDil: async (dil) => { d.dil.push(dil); },
    dilOku: () => d.lang,
    mesgulMu: () => d.mesgul,
    belge, simdiMs: () => t,
    araliKur: (fn, ms) => { expect(ms).toBe(TIK_MS); d.tik = fn; return 7; },
    araliSil: (no) => { expect(no).toBe(7); d.aralikSilindi += 1; d.tik = null; },
  });
  async function ilerle(ms) {
    const hedef = t + ms;
    while (t + TIK_MS <= hedef) { t += TIK_MS; if (d.tik) d.tik(); await bosalt(); }
    t = hedef;
    await bosalt();
  }
  return { d, arka, kart, belge, yay, ilerle, saat: () => t, saatAyarla: (x) => { t = x; } };
}

describe("arka plan (K17): eski kabugun isleri", () => {
  it("acilis: kart aranir, eşitleme kurulur ve yeni baglantida HEMEN bir tur, sonra her tikte (60 s kurali eşitleyicide)", async () => {
    const w = dunya();
    w.arka.baslat();
    await bosalt();
    expect(w.d.baglanSayisi).toBe(1);
    expect(w.arka.durum().baglanti).toEqual({ durum: "bagli", adres: "192.168.1.7", kimlik: KIM });
    expect(w.d.canliBaslat).toBe(0);                     // panel istemedikce akis ACILMAZ
    await w.ilerle(3000);
    expect(w.d.esit).toEqual(["gorunurluk:true", "baglandi", "tik:true:true"]);
  });

  it("akis: yalniz panel isterken + ondeyken + bagliyken; arka plana gecince HEMEN kapanir, eşitleme / tik durur; one donunce yeniden", async () => {
    const w = dunya();
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await bosalt();
    expect(w.d.canliBaslat).toBe(1);
    await w.ilerle(2000);                                // eşitleme ilk tikte kurulur
    w.belge.visibilityState = "hidden";
    w.belge.l();
    expect(w.d.canliDurdur).toBe(1);
    expect(w.d.aralikSilindi).toBe(1);
    expect(w.d.esit.at(-1)).toBe("gorunurluk:false");
    w.belge.visibilityState = "visible";
    w.belge.l();
    await bosalt();
    expect(w.d.canliBaslat).toBe(2);
    expect(w.d.esit).toContain("gorunurluk:true");
    w.arka.akisIste(false);
    expect(w.d.canliDurdur).toBe(2);
  });

  it("kayit bitti (G: KAYIT -> BOS): eşitleme turu + izleme sorusu kapanir; KAYIT -> BEKLIYOR soruyu KAPATMAZ ama eşitler", async () => {
    const w = dunya();
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await w.ilerle(2000);
    w.yay({ hal: "acik", kayit: G(2, 41) });
    w.yay({ kayit: G(1, 41) });
    expect(w.d.esit.filter((x) => x === "kayitBitti").length).toBe(1);
    expect(w.d.soru).toEqual(["bitti"]);
    w.yay({ kayit: G(2, 41) });
    w.yay({ kayit: G(4, 41) });
    expect(w.d.esit.filter((x) => x === "kayitBitti").length).toBe(2);
    expect(w.d.soru).toEqual(["bitti"]);
  });

  it("bildirim izleyicisi her tikte: gorunur, bagli, kimlik, adres, son G satiri", async () => {
    const w = dunya();
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await bosalt();
    w.yay({ hal: "acik", kayit: G(2, 41) });
    await w.ilerle(1000);
    expect(w.d.bildirim.at(-1)).toEqual({ gorunur: true, bagli: true, kimlik: KIM, adres: "192.168.1.7", kayit: G(2, 41) });
  });

  it("bildirim dili = panelin dili (belge lang): acilista ve degisince BIR kez", async () => {
    const w = dunya();
    w.arka.baslat();
    await w.ilerle(3000);
    expect(w.d.dil).toEqual(["tr"]);
    w.d.lang = "en";
    await w.ilerle(3000);
    expect(w.d.dil).toEqual(["tr", "en"]);
  });

  it("ACIL DURDUR seridi (K9): yalniz akis acik + veri taze + /pil 'BEKLEMEDE' taze + pil oturumu yokken GIZLI; pil 30 s'de bir", async () => {
    const w = dunya();
    expect(w.arka.seritGorunur()).toBe(true);           // hicbir sey bilinmiyor
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await bosalt();
    w.yay({ hal: "acik", son: { tur: "D", v: 1 } });
    await w.ilerle(1000);
    expect(w.d.pilOkuma).toBe(1);
    w.yay({ son: { tur: "D", v: 2 } });
    expect(w.arka.seritGorunur()).toBe(false);
    await w.ilerle(PIL_YOKLAMA_MS);
    expect(w.d.pilOkuma).toBe(2);
    // veri eskidi -> gorunur
    expect(w.arka.seritGorunur()).toBe(true);
    w.yay({ son: { tur: "D", v: 3 } });
    expect(w.arka.seritGorunur()).toBe(false);
    // pil oturumu basladi (tur 2): G degisince pil BILINMIYOR + tur sorulur -> gorunur
    w.yay({ kayit: G(2, 42) });
    await bosalt();
    expect(w.d.istekler).toContain("/kayit/liste");
    expect(w.arka.durum().oturumTuru).toBe(2);
    expect(w.arka.seritGorunur()).toBe(true);
    // pil test sururken
    w.d.pilCevap = "CALISIYOR";
    await w.ilerle(1000);
    expect(w.arka.seritGorunur()).toBe(true);
  });

  it("kart bulunamadi: 15 s'de bir yeniden aranir; 'Bu telefon'da eslestirme SURERKEN (mesgulMu) ARANMAZ — baglan() da", async () => {
    const w = dunya({ bulunur: false });
    w.arka.baslat();
    await bosalt();
    expect(w.d.baglanSayisi).toBe(1);
    await w.ilerle(YENIDEN_DENE_MS - 2000);
    expect(w.d.baglanSayisi).toBe(1);
    await w.ilerle(3000);
    expect(w.d.baglanSayisi).toBe(2);
    w.d.mesgul = true;
    await w.ilerle(YENIDEN_DENE_MS * 3);
    expect(w.d.baglanSayisi).toBe(2);
    expect(await w.arka.baglan()).toMatchObject({ durum: "bulunamadi" });
    expect(w.d.baglanSayisi).toBe(2);
    w.d.mesgul = false;
    await w.ilerle(TIK_MS);
    expect(w.d.baglanSayisi).toBe(3);
  });

  it("akis 30 s hatada: kart ZORLA yeniden aranir (adres degismis olabilir)", async () => {
    const w = dunya();
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await bosalt();
    w.yay({ hal: "hata", sebep: "baglanti" });
    await w.ilerle(YENIDEN_ARA_MS - 2000);
    expect(w.d.baglanSayisi).toBe(1);
    await w.ilerle(3000);
    expect(w.d.baglanSayisi).toBe(2);
  });

  it("baglantiDegisti (Bu telefon -> Kart bitti): akis yeni duruma gore yeniden; dinleyiciye haber", async () => {
    const w = dunya({ eslesmis: false });
    const gorulen = [];
    w.arka.dinle((s) => gorulen.push(s.baglanti && s.baglanti.durum));
    w.arka.baslat();
    await bosalt();
    w.arka.akisIste(true);
    await bosalt();
    expect(w.d.canliBaslat).toBe(0);                    // eslesmemis: akis yok
    await w.arka.baglantiDegisti({ durum: "bagli", adres: "192.168.1.7", kimlik: KIM, anahtar: "SIZMAZ" });
    expect(w.d.canliBaslat).toBe(1);
    expect(gorulen).toContain("bagli");
    expect(JSON.stringify(w.arka.durum())).not.toContain("SIZMAZ");
  });

  it("oturumTuruBul (saf)", () => {
    expect(oturumTuruBul({ oturumlar: [{ id: 3, tur: 2 }] }, 3)).toBe(2);
    expect(oturumTuruBul({ oturumlar: [{ id: 3, tur: "2" }] }, 3)).toBeNull();
    expect(oturumTuruBul(null, 3)).toBeNull();
  });
});
