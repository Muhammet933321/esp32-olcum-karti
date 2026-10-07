// 5P (P3) — ortamKur (index.js): kuresel nesneye `__olcumOrtam`, arka plan baslar, "Bu telefon" olay.js'i
// baglanir; anlik izleme kutusu (soru_cizim.js) Vue render islevi ile belge govdesine. Vue runtime-dom'u
// belgeyi YUKLENIRKEN yakaladigi icin kucuk bir sahte DOM her ice aktarmadan ONCE kurulur (vi.hoisted).
import { describe, it, expect, vi, afterAll } from "vitest";

const DOM = vi.hoisted(() => {
  class Dugum {
    constructor(tur, ad = null) {
      this.nodeType = tur;
      this.tagName = ad ? ad.toUpperCase() : undefined;
      this.childNodes = [];
      this.parentNode = null;
      this.nodeValue = null;
      this.oz = new Map();
      this.dinleyici = {};
      this.style = { cssText: "" };
      this.className = "";
      if (tur === 1) this.disabled = false;
    }
    get nextSibling() { const p = this.parentNode; if (!p) return null; return p.childNodes[p.childNodes.indexOf(this) + 1] || null; }
    get firstChild() { return this.childNodes[0] || null; }
    insertBefore(c, ref) {
      if (c.parentNode) c.parentNode.removeChild(c);
      const i = ref ? this.childNodes.indexOf(ref) : -1;
      if (i < 0) this.childNodes.push(c); else this.childNodes.splice(i, 0, c);
      c.parentNode = this;
      return c;
    }
    appendChild(c) { return this.insertBefore(c, null); }
    removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) this.childNodes.splice(i, 1); c.parentNode = null; return c; }
    set textContent(s) {
      for (const c of [...this.childNodes]) this.removeChild(c);
      if (s) { const t = new Dugum(3); t.nodeValue = String(s); this.appendChild(t); }
    }
    get textContent() { return this.nodeType === 3 ? this.nodeValue : this.childNodes.map((c) => (c.nodeType === 8 ? "" : c.textContent)).join(""); }
    setAttribute(a, v) { this.oz.set(a, String(v)); }
    getAttribute(a) { return this.oz.has(a) ? this.oz.get(a) : null; }
    removeAttribute(a) { this.oz.delete(a); }
    hasAttribute(a) { return this.oz.has(a); }
    addEventListener(t, fn) { (this.dinleyici[t] ||= []).push(fn); }
    removeEventListener(t, fn) { this.dinleyici[t] = (this.dinleyici[t] || []).filter((x) => x !== fn); }
    tikla() { for (const fn of this.dinleyici.click || []) fn({ type: "click" }); }
    bul(kosul) {
      if (kosul(this)) return this;
      for (const c of this.childNodes) { const b = c.bul(kosul); if (b) return b; }
      return null;
    }
  }
  const belgeDinleyici = new Set();
  const body = new Dugum(1, "body");
  const uyg = new Dugum(1, "div");
  uyg.setAttribute("id", "uyg");
  body.appendChild(uyg);
  const belge = {
    body, title: "Ölçüm Kartı", visibilityState: "visible", documentElement: { lang: "tr" },
    createElement: (ad) => new Dugum(1, ad),
    createElementNS: (_ns, ad) => new Dugum(1, ad),
    createTextNode: (s) => { const t = new Dugum(3); t.nodeValue = s; return t; },
    createComment: (s) => { const t = new Dugum(8); t.nodeValue = s; return t; },
    querySelector: () => null,
    addEventListener: (a, fn) => { if (a === "visibilitychange") belgeDinleyici.add(fn); },
    removeEventListener: (a, fn) => { belgeDinleyici.delete(fn); },
  };
  const onceki = globalThis.document;
  globalThis.document = belge;
  return { belge, body, uyg, onceki };
});

const G = vi.hoisted(() => ({ baglan: 0, ayarYaz: [], kartDurum: "bagli-degil" }));

vi.mock("../src/cekirdek/uygulama.js", () => {
  const kart = {
    durum: () => ({ durum: G.kartDurum, adres: null, kimlik: null }),
    baglan: async () => { G.baglan += 1; return { durum: "bulunamadi", adres: null, kimlik: null }; },
    istek: async () => { throw Object.assign(new Error("ag"), { tur: "ag" }); },
  };
  return {
    kartAl: async () => kart,
    canliAl: async () => { throw new Error("canli yok"); },
    esitlemeAl: async () => ({ dinle: () => () => {}, gorunurluk: () => {}, tik: () => {}, baglandi: () => {} }),
    bildirimAl: () => ({ ayarYaz: async (x) => { G.ayarYaz.push(x); } }),
    bildirimIzle: { tik: () => {} },
    izlemeSorusu: { dinle: () => () => {}, kayitBasladi: async () => {}, kayitBitti: () => {} },
    pilOku: async () => null,
    acilDurdur: async () => ({ tamam: true }),
  };
});
vi.mock("../src/cekirdek/eklenti.js", () => ({
  KartDepo: {}, Paylas: { baslat: async () => ({}), yaz: async () => ({}), gonder: async () => ({}) },
  Yazdir: { yazdir: async () => ({}) },
}));

afterAll(() => { globalThis.document = DOM.onceki; });

describe("soru_cizim: Vue render islevi, belge govdesine (panelin #uyg'sine dokunmadan)", () => {
  it("soru kutusu: metin + iki dugme (type=button), tikla -> evet/hayir; mesgulken dugmeler kapali; null -> yalniz kendi kutusu kalkar", async () => {
    const { vueCizici, soruDugumu } = await import("../src/ortam/soru_cizim.js");
    const { ceviriMobil } = await import("../src/cekirdek/sozluk_mobil.js");
    const ciz = vueCizici({ belge: DOM.belge, dilAl: () => "tr" });
    const tik = [];
    ciz({ hal: "soruluyor", soru: true, mesgul: false, evet: () => tik.push("evet"), hayir: () => tik.push("hayir") });
    expect(DOM.body.childNodes[0]).toBe(DOM.uyg);
    const kutu = DOM.body.bul((d) => d.getAttribute && d.getAttribute("id") === "ortam-izleme-soru");
    expect(kutu).not.toBeNull();
    expect(kutu.getAttribute("role")).toBe("alertdialog");
    expect(kutu.className).toBe("uyari");
    expect(kutu.style.cssText).toContain("position:fixed");
    expect(kutu.textContent).toContain(ceviriMobil("m.bl.soru", "tr"));
    const evet = kutu.bul((d) => d.getAttribute && d.getAttribute("data-ortam-soru") === "evet");
    const hayir = kutu.bul((d) => d.getAttribute && d.getAttribute("data-ortam-soru") === "hayir");
    expect(evet.textContent).toBe(ceviriMobil("m.bl.soru_evet", "tr"));
    expect(evet.getAttribute("type")).toBe("button");
    expect(evet.disabled).toBe(false);
    evet.tikla();
    hayir.tikla();
    expect(tik).toEqual(["evet", "hayir"]);
    ciz({ hal: "aciliyor", soru: true, mesgul: true, evet: () => {}, hayir: () => {} });
    expect(DOM.body.bul((d) => d.getAttribute && d.getAttribute("data-ortam-soru") === "evet").disabled).toBe(true);
    ciz({ hal: "acildi", soru: false });
    const sonuc = DOM.body.bul((d) => d.getAttribute && d.getAttribute("id") === "ortam-izleme-soru");
    expect(sonuc.getAttribute("role")).toBe("status");
    expect(sonuc.textContent).toBe(ceviriMobil("m.bl.soru_acildi", "tr"));
    ciz(null);
    expect(DOM.body.childNodes.filter((d) => d.nodeType === 1)).toEqual([DOM.uyg]);
    expect(soruDugumu({ hal: "garip", soru: false })).toBeNull();
    expect(soruDugumu(null)).toBeNull();
    // ingilizce
    const en = vueCizici({ belge: DOM.belge, dilAl: () => "en" });
    en({ hal: "acilamadi", soru: false });
    expect(DOM.body.textContent).toContain(ceviriMobil("m.bl.soru_acilamadi", "en"));
    en(null);
    // govdesiz belge: hicbir sey yapmaz
    expect(() => vueCizici({ belge: {} })({ hal: "acildi", soru: false })).not.toThrow();
  });
});

describe("ortamKur (index.js)", () => {
  it("kuresel nesne verilmezse REDDEDER (panel ortamsiz acilmasin); verilince __olcumOrtam kurulur, arka plan baslar, ikinci cagri AYNI", async () => {
    const m = await import("../src/ortam/index.js");
    await expect(m.ortamKur()).rejects.toMatchObject({ name: "OrtamHatasi", tur: "kuresel-yok" });
    const kuresel = {};
    const o = await m.ortamKur({ kuresel, belge: DOM.belge });
    expect(kuresel[m.KURESEL_AD]).toBe(o);
    expect(m.KURESEL_AD).toBe("__olcumOrtam");
    expect(Object.keys(kuresel)).toEqual([]);                     // sayilmaz
    expect(() => { "use strict"; kuresel.__olcumOrtam = null; }).toThrow(TypeError);
    expect(o.ad).toBe("telefon");
    await new Promise((r) => setTimeout(r, 20));
    expect(G.baglan).toBe(1);                                     // acilista kart arandi (arka plan)
    expect(G.ayarYaz).toEqual([{ dil: "tr" }]);                   // bildirim dili = panelin dili
    expect(await m.ortamKur({ kuresel: {}, belge: DOM.belge })).toBe(o);
    expect(await o.p0()).toBe(true);
    expect(o.serit(null)).toBe(true);
    m.arkaPlanAl().birak();
  });

  it("'Bu telefon' olay.js: baglantiBildir -> arka plan yeni baglantiyi alir; mesgulYap surerken kart ARANMAZ", async () => {
    const m = await import("../src/ortam/index.js");
    const olay = await import("../src/telefon/olay.js");
    const arka = m.arkaPlanAl();
    olay.baglantiBildir({ durum: "bagli", adres: "192.168.1.7", kimlik: "0123456789abcdef" });
    await new Promise((r) => setTimeout(r, 10));
    expect(arka.durum().baglanti).toEqual({ durum: "bagli", adres: "192.168.1.7", kimlik: "0123456789abcdef" });
    olay.mesgulYap(true);
    const n = G.baglan;
    expect(await arka.ara({ zorla: true })).toMatchObject({ durum: "bagli" });
    expect(G.baglan).toBe(n);
    olay.mesgulYap(false);
    await arka.ara({ zorla: true });
    expect(G.baglan).toBe(n + 1);
    arka.birak();
  });
});
