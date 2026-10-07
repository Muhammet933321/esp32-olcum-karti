// "Bu telefon" bolumu (5P K13, K14): mantik + gercek Vue sunucu cizimi (DOM'suz).
//
// Bilesenler SFC: sablon burada vue/compiler-sfc ile derlenir, secenekler telefon/*_bolum.js'ten gelir ve
// vue/server-renderer ile HTML'e cizilir (vitest'te vue eklentisi yok; derleme vite'tekiyle ayni derleyici).
// Mantik testleri bilesen orneginin taklidiyle (props + data + computed + methods) kosar; ayni durum sonra
// cizilip sablonun onu dogru gosterdigi olculur.
import { describe, it, expect, vi, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import * as Vue from "vue";
import { renderToString } from "vue/server-renderer";
import { compileTemplate, parse } from "vue/compiler-sfc";
import { KartHatasi } from "../src/cekirdek/kart.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { KART_BOLUMU, adDenetle, baglantiOzeti, cihazListesiCoz, eslesHataMetni, parolaKisa } from "../src/telefon/kart_bolum.js";
import { ESITLEME_BOLUMU } from "../src/telefon/esitleme_bolum.js";
import { BILDIRIM_BOLUMU } from "../src/telefon/bildirim_bolum.js";
import { GELISMIS_BOLUMU, kunyeCoz } from "../src/telefon/gelismis_bolum.js";
import { BU_TELEFON } from "../src/telefon/bu_telefon.js";
import { dilCoz, ikinciAdim, zamanYaz } from "../src/telefon/ortak.js";
import { baglantiBildir, baglantiDinle, mesgulMu, mesgulYap } from "../src/telefon/olay.js";
import { kesifTanisi } from "../src/telefon/tani.js";

const TELEFON = fileURLToPath(new URL("../src/telefon", import.meta.url));
const KIMLIK = "0123456789abcdef";
const PAROLA = "gizli-web-parolasi-77";

// ── sablon derleme + cizim ─────────────────────────────────────────────
const renderler = new Map();
function render(dosya) {
  if (!renderler.has(dosya)) {
    const { descriptor, errors } = parse(readFileSync(join(TELEFON, dosya), "utf8"), { filename: dosya });
    expect(errors, dosya).toEqual([]);
    const s = compileTemplate({ source: descriptor.template.content, filename: dosya, id: dosya, compilerOptions: { mode: "function" } });
    expect(s.errors, dosya).toEqual([]);
    renderler.set(dosya, new Function("Vue", s.code)(Vue));
  }
  return renderler.get(dosya);
}

const DOSYA = new Map([
  [KART_BOLUMU, "KartBolumu.vue"], [ESITLEME_BOLUMU, "EsitlemeBolumu.vue"], [BILDIRIM_BOLUMU, "BildirimBolumu.vue"],
  [GELISMIS_BOLUMU, "GelismisBolumu.vue"],
]);
const bilesen = (secenek) => ({ ...secenek, render: render(DOSYA.get(secenek)) });

// Bir bolumu verilen durumla ciz (data uzerine `durum` yazilir).
async function ciz(secenek, props, durum = {}) {
  const b = bilesen(secenek);
  const kok = { ...b, data() { return { ...secenek.data.call(this), ...durum }; } };
  return renderToString(Vue.createSSRApp(kok, props));
}

// Kok bilesen: BuTelefon.vue'nun yaptigi gibi alt bolumlerle kurulur.
function kokBilesen() {
  return {
    ...BU_TELEFON,
    render: render("BuTelefon.vue"),
    components: {
      KartBolumu: bilesen(KART_BOLUMU), EsitlemeBolumu: bilesen(ESITLEME_BOLUMU),
      BildirimBolumu: bilesen(BILDIRIM_BOLUMU), GelismisBolumu: bilesen(GELISMIS_BOLUMU),
    },
  };
}

// Bilesen orneginin taklidi (mantik testleri): props + data + computed + methods; created kosar.
function ornek(secenek, props) {
  const vm = { ...props, $refs: {}, $emit: vi.fn() };
  for (const k of [...(secenek.mixins || []), secenek]) {
    for (const [ad, p] of Object.entries(k.props || {})) if (!(ad in vm)) vm[ad] = typeof p.default === "function" ? p.default() : p.default;
  }
  if (secenek.data) Object.assign(vm, secenek.data.call(vm));
  for (const k of [...(secenek.mixins || []), secenek]) {
    for (const [ad, fn] of Object.entries(k.methods || {})) vm[ad] = fn.bind(vm);
    for (const [ad, fn] of Object.entries(k.computed || {})) Object.defineProperty(vm, ad, { get: () => fn.call(vm), configurable: true });
  }
  if (secenek.created) secenek.created.call(vm);
  return vm;
}
const durumu = (secenek, vm) => Object.fromEntries(Object.keys(secenek.data.call({ ...vm })).map((a) => [a, vm[a]]));
// SSR cikisindaki kacisli metin (Vue " ve ' karakterlerini kacirir).
const kac = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ── sahteler ───────────────────────────────────────────────────────────
const yanit = (j, status = 200) => new Response(j === null ? null : JSON.stringify(j), { status });

function sahteKart({ durum = { durum: "bagli", adres: "192.168.1.20", kimlik: KIMLIK }, cihazlar = null, hatalar = {} } = {}) {
  const liste = cihazlar || [
    { n: 2, ad: "Xiaomi", eklenme: 1790000000, son: 1790000100 },
    { n: 1, ad: "Desktop", eklenme: 1789000000, son: 0 },
    { n: 3, ad: "Tablet", eklenme: 1790500000, son: 1790500500 },
  ];
  const k = {
    istekler: [],
    esles: vi.fn(async () => ({ kimlik: KIMLIK, n: 2 })),
    eslesmeyiKaldir: vi.fn(async () => ({ kartta: true })),
    saatVer: vi.fn(async () => true),
    baglan: vi.fn(async () => ({ ...durum, bilgi: { saat: 0, tur: 20000 } })),
    durum: () => durum,
    async istek(yontem, yol, arg = []) {
      k.istekler.push([yontem, yol, arg]);
      if (hatalar[yol]) throw hatalar[yol];
      if (yol === "/cihaz/liste") return yanit({ cihazlar: liste });
      if (yol === "/cihaz/sil") return yanit(null, 204);
      if (yol === "/kunye.json") return yanit({ surum: "0123456789ab", dosya: 14, icerik_bayt: 90000 });
      if (yol === "/kayit/liste") return yanit({ oturumlar: [{ id: 1 }, { id: 2 }] });
      throw new KartHatasi("http", { durum: 404 });
    },
  };
  return k;
}

function sahteBildirim(d = {}) {
  const durum = { zarf: true, izin: true, izinGerekli: true, pilMuaf: false, calisiyor: false, izleme: "durduruldu", anlik: true, kapali: ["esik"], uretici: "xiaomi", ...d };
  return {
    durum: vi.fn(async () => durum), yenile: vi.fn(async () => "yazildi"), izinIste: vi.fn(async () => true),
    pilMuafiyetiIste: vi.fn(async () => true), ayarYaz: vi.fn(async () => {}), uygulamaAyarlariAc: vi.fn(async () => {}),
    deneme: vi.fn(async () => true), _durum: durum,
  };
}

function sahteBaglam(kart = sahteKart(), ek = {}) {
  const olay = { bildir: [], mesgul: [] };
  const bl = sahteBildirim();
  return {
    olay, bl, kart,
    kartAl: async () => kart,
    kareBekle: async () => {},
    baglantiBildir: (b) => { olay.bildir.push(b); return b; },
    mesgulYap: (v) => { olay.mesgul.push(v); },
    kendiN: vi.fn(async (k) => (k === KIMLIK ? 2 : null)),
    kesifTanisi: vi.fn(async () => ({
      sonuc: { adres: "192.168.1.20", kimlik: KIMLIK, kaynak: "nsd", sureMs: 140, txtKimlik: KIMLIK, tur: 50000 },
      denenenler: [{ adres: "192.168.1.20", kaynak: "nsd", sonuc: "tamam" }, { adres: "olcum.local", kaynak: "ad", sonuc: "ad-cozulmedi" }],
      duyurular: [{ adres: "192.168.1.20:80", uyuyor: true }], hata: null,
    })),
    esitlemeOnayi: vi.fn(() => false),
    esitlemeOnayiYaz: vi.fn((v) => v),
    kopyaBoyutu: vi.fn(async () => ({ toplam: 4560000 })),
    kopyaSifirla: vi.fn(async () => {}),
    bildirim: () => bl,
    bildirimKimligi: vi.fn(async () => KIMLIK),
    bildirimSon: () => null,
    durdurOlc: vi.fn(async () => ({ tekrar: 20, basari: 20, enAz: 31, ortanca: 44, enCok: 90 })),
    pbkdf2Olc: vi.fn((tur) => ({ tur, enAz: 700, ortanca: 760, enCok: 800, ozet: "3f042897317e112506e7", dogru: tur === 20000 ? true : null })),
    webSinama: vi.fn(async () => [{ yol: "fetch", adres: "http://example.com/", sonuc: "engellendi" }]),
    uygulamaSurumu: vi.fn(async () => "0.1.0"),
    ...ek,
  };
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

// ── saf yardimcilar ────────────────────────────────────────────────────
describe("ortak yardimcilar", () => {
  it("dilCoz: tr / en aynen; sistem ve bilinmeyen telefonun diline gore", () => {
    expect(dilCoz("tr", "en-US")).toBe("tr");
    expect(dilCoz("en", "tr-TR")).toBe("en");
    expect(dilCoz("sistem", "en-GB")).toBe("en");
    expect(dilCoz("sistem", "tr-TR")).toBe("tr");
    expect(dilCoz(undefined, "")).toBe("tr");
    expect(dilCoz("de", "de-DE")).toBe("tr");
  });

  it("ikinciAdim yalniz SILAHLI anahtarda true", () => {
    expect(ikinciAdim(null, "sil3")).toBe(false);
    expect(ikinciAdim("sil2", "sil3")).toBe(false);
    expect(ikinciAdim("sil3", "sil3")).toBe(true);
  });

  it("zamanYaz: unix s -> YYYY-AA-GG SS:DD; 0 / bozuk -> —", () => {
    expect(zamanYaz(0)).toBe("—");
    expect(zamanYaz(NaN)).toBe("—");
    expect(zamanYaz(1790000000)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });

  it("olay: baglanti dinleyicisi ozet alir (sir yok), hatali dinleyici digerini bozmaz; mesgul sayaci", () => {
    const gelen = [];
    const birak1 = baglantiDinle(() => { throw new Error("x"); });
    const birak2 = baglantiDinle((o) => gelen.push(o));
    baglantiBildir({ durum: "bagli", adres: "1.2.3.4", kimlik: KIMLIK, K: new Uint8Array(32), bilgi: { x: 1 } });
    baglantiBildir(null);
    birak1(); birak2();
    baglantiBildir({ durum: "bagli" });
    expect(gelen).toEqual([{ durum: "bagli", adres: "1.2.3.4", kimlik: KIMLIK }, null]);
    expect(mesgulMu()).toBe(false);
    mesgulYap(true); expect(mesgulMu()).toBe(true);
    mesgulYap(false); mesgulYap(false); expect(mesgulMu()).toBe(false);
    mesgulYap(true); expect(mesgulMu()).toBe(true);
    mesgulYap(false);
  });
});

describe("Kart: ad / parola / liste denetimleri", () => {
  it("cihaz adi 1–24 BAYT (UTF-8), denetim karakteri yok", () => {
    expect(adDenetle("Telefon")).toBe(null);
    expect(adDenetle("a".repeat(24))).toBe(null);
    expect(adDenetle("a".repeat(25))).toBe("m.es.hata_ad");
    expect(adDenetle("ğ".repeat(12))).toBe(null);             // 24 bayt
    expect(adDenetle("ğ".repeat(13))).toBe("m.es.hata_ad");   // 13 karakter ama 26 bayt
    expect(adDenetle("")).toBe("m.es.hata_ad");
    expect(adDenetle("a\u0001b")).toBe("m.es.hata_ad");
    expect(adDenetle(null)).toBe("m.es.hata_ad");
  });

  it("parola en az 12 BAYT", () => {
    expect(parolaKisa("a".repeat(11))).toBe(true);
    expect(parolaKisa("a".repeat(12))).toBe(false);
    expect(parolaKisa("ğ".repeat(6))).toBe(false);
    expect(parolaKisa(undefined)).toBe(true);
  });

  it("cihazListesiCoz: kartin bicimi ({n, ad, eklenme, son}), numara sirasi; bozuk kayit atlanir, bozuk yanit ATAR", () => {
    expect(cihazListesiCoz({ cihazlar: [{ n: 3, ad: "B", eklenme: 5, son: 6 }, { n: 1, ad: "A", eklenme: 1, son: 0 }, { n: "x", ad: "C" }, null, { n: 2 }] }))
      .toEqual([{ n: 1, ad: "A", eklenme: 1, son: 0 }, { n: 3, ad: "B", eklenme: 5, son: 6 }]);
    expect(cihazListesiCoz({ cihazlar: [] })).toEqual([]);
    expect(() => cihazListesiCoz({})).toThrow();
    expect(() => cihazListesiCoz(null)).toThrow();
  });

  it("eslestirme hatasi -> sozluk anahtari; bekle saniyeyi tasir; bilinmeyen genel", () => {
    expect(eslesHataMetni(new KartHatasi("parola-yanlis"))).toEqual({ anahtar: "m.es.hata_parola_yanlis", degerler: null });
    expect(eslesHataMetni(new KartHatasi("bekle", { saniye: 30 }))).toEqual({ anahtar: "m.es.hata_bekle_saniye", degerler: { saniye: 30 } });
    expect(eslesHataMetni(new Error("ic mesaj"))).toEqual({ anahtar: "m.es.hata_bilinmeyen", degerler: null });
  });

  it("baglantiOzeti: bagli-degil -> null; bilgiden yalniz saat kaynagi", () => {
    expect(baglantiOzeti({ durum: "bagli-degil" })).toBe(null);
    expect(baglantiOzeti({ durum: "eslesmemis", adres: "a", kimlik: KIMLIK, bilgi: { saat: 1, tur: 2 } })).toEqual({ durum: "eslesmemis", adres: "a", kimlik: KIMLIK, saat: 1 });
  });
});

// ── Kart bolumu ────────────────────────────────────────────────────────
describe("Kart bolumu", () => {
  it("acilista bilinen baglanti + eslesmis cihaz listesi; bu telefonun satiri isaretli, kendisi buradan SILINEMEZ", async () => {
    const b = sahteBaglam();
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    expect(vm.bagli).toBe(true);
    expect(vm.liste.map((c) => c.n)).toEqual([1, 2, 3]);
    expect(vm.kendiN).toBe(2);
    expect(b.kart.istekler).toEqual([["GET", "/cihaz/liste", []]]);
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toContain("192.168.1.20");
    expect(html).toContain(KIMLIK);
    const satir = (n) => html.slice(html.indexOf(`data-bt-cihaz="${n}"`), html.indexOf("</li>", html.indexOf(`data-bt-cihaz="${n}"`)));
    expect(satir(2)).toContain("data-bt-kendi");
    expect(satir(2)).toContain(SOZLUK_MOBIL["m.bt.bu_telefon"].tr);
    expect(satir(2)).not.toContain("data-bt-sil=");
    expect(satir(2)).toContain("data-bt-kendi-kaldir");
    expect(satir(1)).not.toContain("data-bt-kendi=");
    expect(satir(1)).toContain('data-bt-sil="1"');
    expect(satir(3)).toContain("Tablet");
  });

  it("cihaz silme IKI adim: onaysiz / baska satirin onayiyla hicbir istek gitmez; onaylinca TEK imzali POST /cihaz/sil?n=", async () => {
    const b = sahteBaglam();
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    b.kart.istekler.length = 0;
    await vm.cihazSil(3);
    expect(b.kart.istekler).toEqual([]);
    vm.onayIste("sil3");
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toContain('data-bt-sil-eminim="3"');
    expect(html).not.toContain('data-bt-sil-eminim="1"');
    expect(html).toContain(SOZLUK_MOBIL["m.bt.sil_uyari"].tr);
    await vm.cihazSil(1);
    expect(b.kart.istekler).toEqual([]);
    expect(vm.onay).toBe("sil3");
    await vm.cihazSil(3);
    expect(b.kart.istekler[0]).toEqual(["POST", "/cihaz/sil", [["n", "3"]]]);
    expect(b.kart.istekler.filter((i) => i[1] === "/cihaz/sil").length).toBe(1);
    expect(b.kart.istekler[1]).toEqual(["GET", "/cihaz/liste", []]);      // liste yenilendi
    expect(vm.onay).toBe(null);
    expect(vm.mesaj).toEqual({ anahtar: "m.bt.silindi", degerler: { n: 3 } });
    // Bu telefonun satiri onay silahli olsa da cihazSil'den silinmez (o "Eslesmeyi kaldir").
    vm.onayIste("sil2");
    await vm.cihazSil(2);
    expect(b.kart.istekler.filter((i) => i[1] === "/cihaz/sil").length).toBe(1);
  });

  it("silme hatasi TUR adiyla yazilir; vazgec onayi kaldirir", async () => {
    const b = sahteBaglam(sahteKart({ hatalar: { "/cihaz/sil": new KartHatasi("http", { durum: 404 }) } }));
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    vm.onayIste("sil1");
    vm.onayVazgec();
    await vm.cihazSil(1);
    expect(b.kart.istekler.some((i) => i[1] === "/cihaz/sil")).toBe(false);
    vm.onayIste("sil1");
    await vm.cihazSil(1);
    expect(vm.mesaj).toEqual({ anahtar: "m.bt.sil_hata", degerler: { n: 1, tur: "http" } });
    expect(vm.mesajHata).toBe(true);
  });

  it("liste okunamazsa hata gorunur (bos liste sanilmaz)", async () => {
    const b = sahteBaglam(sahteKart({ hatalar: { "/cihaz/liste": new KartHatasi("ag") } }));
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    expect(vm.listeHata).toEqual({ anahtar: "m.bt.liste_hata", degerler: { tur: "ag" } });
    expect(vm.listeBos).toBe(false);
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toMatch(/class="hata" role="alert" data-bt-liste-hata/);
    expect(html).not.toContain("data-bt-liste-bos");
  });

  it("eslesmeyi kaldir IKI adim; kaldirinca baglanti haberi (null) gider", async () => {
    const b = sahteBaglam();
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    await vm.kaldir();
    expect(b.kart.eslesmeyiKaldir).not.toHaveBeenCalled();
    vm.onayIste("kaldir");
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toContain("data-bt-kaldir-eminim");
    expect(html).toContain(SOZLUK_MOBIL["m.bt.kaldir_uyari"].tr);
    await vm.kaldir();
    expect(b.kart.eslesmeyiKaldir).toHaveBeenCalledTimes(1);
    expect(vm.baglanti).toBe(null);
    expect(vm.liste).toEqual([]);
    expect(vm.mesaj).toEqual({ anahtar: "m.bg.kaldirildi", degerler: null });
    expect(b.olay.bildir.at(-1)).toBe(null);
    expect(vm.$emit).toHaveBeenCalledWith("baglanti-degisti", null);
  });

  it("Baglan: elle adres kart.baglan'a gider; sonuc + haber; bulunamazsa tani ipucu", async () => {
    const k = sahteKart({ durum: { durum: "bulunamadi", adres: null, kimlik: null } });
    const b = sahteBaglam(k);
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    vm.elle = " 192.168.1.20 ";
    await vm.baglan();
    expect(k.baglan).toHaveBeenCalledWith({ elle: "192.168.1.20" });
    expect(vm.bulunamadi).toBe(true);
    expect(b.olay.bildir).toEqual([{ durum: "bulunamadi", adres: null, kimlik: null, saat: 0 }]);
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toContain("data-bt-tani-ipucu");
  });

  it("islem hatasi tur adiyla; kasa bozuksa kaldir yine sunulur", async () => {
    const k = sahteKart();
    k.baglan.mockRejectedValueOnce(new KartHatasi("kasa"));
    const vm = ornek(KART_BOLUMU, { b: sahteBaglam(k), dil: "tr" });
    await vm.baglan();
    expect(vm.kasaBozuk).toBe(true);
    expect(vm.kaldirAcik).toBe(true);
    expect(vm.mesaj.anahtar).toBe("m.bg.kasa_bozuk");
  });

  it("imzali deneme ve kart saati", async () => {
    const b = sahteBaglam();
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    await vm.dene();
    expect(vm.mesaj).toEqual({ anahtar: "m.bg.imzali_tamam", degerler: { oturum: 2 } });
    await vm.saatVer();
    expect(b.kart.saatVer).toHaveBeenCalledTimes(1);
    expect(vm.mesaj.anahtar).toBe("m.bt.saat_verildi");
    expect(vm.baglanti.saat).toBe(2);
    b.kart.saatVer.mockResolvedValueOnce(false);
    await vm.saatVer();
    expect(vm.mesaj.anahtar).toBe("m.bt.saat_gerekmedi");
  });
});

describe("Kart: eslestirme ve WEB parolasi", () => {
  function izle() {
    const kayit = [];
    for (const ad of ["log", "info", "warn", "error", "debug", "trace"]) vi.spyOn(console, ad).mockImplementation((...a) => { kayit.push(a); });
    const depo = (ad) => ({ getItem: vi.fn(() => null), setItem: vi.fn((...a) => kayit.push([ad, ...a])), removeItem: vi.fn(), clear: vi.fn(), key: () => null, length: 0 });
    vi.stubGlobal("localStorage", depo("localStorage"));
    vi.stubGlobal("sessionStorage", depo("sessionStorage"));
    return kayit;
  }

  async function eslesmemis() {
    const k = sahteKart({ durum: { durum: "eslesmemis", adres: "192.168.1.20", kimlik: KIMLIK } });
    const b = sahteBaglam(k);
    const vm = ornek(KART_BOLUMU, { b, dil: "tr" });
    await vm.durumOku();
    return { k, b, vm };
  }

  it("parola alandan okunur, cagridan ONCE silinir; kart.esles (ad, parola); hicbir yere yazilmaz / gunluge gitmez", async () => {
    const kayit = izle();
    const { k, b, vm } = await eslesmemis();
    expect(vm.eslesmeAcik).toBe(true);
    const alan = { value: PAROLA };
    vm.$refs.parola = alan;
    let cagriAnindaAlan = null;
    k.esles.mockImplementation(async () => { cagriAnindaAlan = alan.value; return { kimlik: KIMLIK, n: 2 }; });
    await vm.eslestir();
    expect(k.esles).toHaveBeenCalledWith(SOZLUK_MOBIL["m.es.ad_varsayilan"].tr, PAROLA);
    expect(cagriAnindaAlan).toBe("");
    expect(alan.value).toBe("");
    expect(vm.eslesTamam).toBe(true);
    expect(vm.baglanti.durum).toBe("bagli");
    expect(b.olay.mesgul).toEqual([true, false]);
    expect(JSON.stringify(durumu(KART_BOLUMU, vm))).not.toContain(PAROLA);
    expect(JSON.stringify(kayit)).not.toContain(PAROLA);
    expect(JSON.stringify(b.olay)).not.toContain(PAROLA);
    expect(localStorage.setItem).not.toHaveBeenCalled();
    expect(sessionStorage.setItem).not.toHaveBeenCalled();
    // eslesince liste okunur ve form kalkar
    expect(k.istekler.some((i) => i[1] === "/cihaz/liste")).toBe(true);
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).not.toContain("data-bt-esles=");
    expect(html).toContain("data-bt-esles-tamam");
    expect(html).not.toContain(PAROLA);
  });

  it("yanlis parola: alan yine bosalir, hata yalniz sozluk anahtari; mesgul birakilir", async () => {
    const kayit = izle();
    const { k, b, vm } = await eslesmemis();
    const alan = { value: PAROLA };
    vm.$refs.parola = alan;
    k.esles.mockRejectedValueOnce(new KartHatasi("parola-yanlis"));
    await vm.eslestir();
    expect(alan.value).toBe("");
    expect(vm.eslesHata).toEqual({ anahtar: "m.es.hata_parola_yanlis", degerler: null });
    expect(vm.eslesTamam).toBe(false);
    expect(b.olay.mesgul).toEqual([true, false]);
    expect(JSON.stringify(durumu(KART_BOLUMU, vm)) + JSON.stringify(kayit)).not.toContain(PAROLA);
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toMatch(/class="hata" role="alert" data-bt-esles-hata/);
  });

  it("kisa parola ya da gecersiz ad karta HIC gitmez; alan yine bosalir", async () => {
    izle();
    const { k, vm } = await eslesmemis();
    vm.$refs.parola = { value: "kisa-parola" };
    await vm.eslestir();
    expect(k.esles).not.toHaveBeenCalled();
    expect(vm.$refs.parola.value).toBe("");
    expect(vm.eslesHata.anahtar).toBe("m.es.hata_parola_kisa");
    vm.ad = "a".repeat(25);
    vm.$refs.parola = { value: PAROLA };
    await vm.eslestir();
    expect(k.esles).not.toHaveBeenCalled();
    expect(vm.$refs.parola.value).toBe("");
    expect(vm.eslesHata.anahtar).toBe("m.es.hata_ad");
    expect(vm.adHatasi).toBe(true);
  });

  it("parola alani Vue durumuna baglanmaz (v-model YOK), WEB parolasi oldugu yazar", async () => {
    const vue = readFileSync(join(TELEFON, "KartBolumu.vue"), "utf8");
    const alan = /<input\b[^>]*id="bt-parola"[^>]*>/.exec(vue)[0];
    expect(alan).toContain('type="password"');
    expect(alan).toContain('ref="parola"');
    expect(alan).not.toMatch(/v-model|:value/);
    expect(alan).toContain('autocomplete="off"');
    const kod = readFileSync(join(TELEFON, "kart_bolum.js"), "utf8");
    expect(kod).not.toMatch(/console\.|localStorage|sessionStorage|this\.parola\b/);
    expect(SOZLUK_MOBIL["m.es.parola"].tr).toContain("WEB parolası");
    expect(SOZLUK_MOBIL["m.es.parola"].tr).toContain("Wi-Fi parolası DEĞİL");
    expect(SOZLUK_MOBIL["m.es.parola"].en).toContain("NOT the Wi-Fi password");
    const { b, vm } = await eslesmemis();
    const html = await ciz(KART_BOLUMU, { b, dil: "tr" }, durumu(KART_BOLUMU, vm));
    expect(html).toContain('id="bt-parola"');
    expect(html).toContain("Wi-Fi parolası DEĞİL");
  });
});

// ── dil ────────────────────────────────────────────────────────────────
describe("dil secimi", () => {
  it("bolumler dilSecim'e uyar (tr / en); kok lang ozelligini ayarlar", async () => {
    const kok = kokBilesen();
    const b = sahteBaglam();
    const tr = await renderToString(Vue.createSSRApp(kok, { dilSecim: "tr", baglam: b }));
    const en = await renderToString(Vue.createSSRApp(kok, { dilSecim: "en", baglam: b }));
    expect(tr).toContain('lang="tr"');
    expect(en).toContain('lang="en"');
    for (const a of ["m.bt.baslik", "m.ay.kart", "m.ay.esitleme", "m.ay.bildirim", "m.ay.gelismis", "m.bg.baglan", "m.es.sifirla"]) {
      expect(tr, a).toContain(SOZLUK_MOBIL[a].tr);
      expect(en, a).toContain(SOZLUK_MOBIL[a].en);
    }
    expect(en).not.toContain(SOZLUK_MOBIL["m.bg.baglan"].tr);
  });

  it("kok: dort bolum de var; baglam prop'u alt bolumlere gecer", async () => {
    const html = await renderToString(Vue.createSSRApp(kokBilesen(), { dilSecim: "tr", baglam: sahteBaglam() }));
    for (const ad of ["kart", "esitleme", "bildirim", "gelismis"]) expect(html, ad).toContain(`data-bt-bolum="${ad}"`);
    expect(html).toContain("data-bu-telefon");
  });

  it("kok baglamsiz cizilmez (gercek baglami yalniz BuTelefon.vue verir)", () => {
    const vm = ornek(BU_TELEFON, { dilSecim: "en" });
    expect(vm.dil).toBe("en");
    expect(() => vm.b).toThrow(TypeError);
    vm.baglantiDegisti({ durum: "bagli" });
    expect(vm.$emit).toHaveBeenCalledWith("baglanti-degisti", { durum: "bagli" });
  });
});

// ── Esitleme ───────────────────────────────────────────────────────────
describe("Esitleme bolumu", () => {
  it("onay VARSAYILAN kapali; anahtar saklanan degeri gosterir; boyut", async () => {
    const b = sahteBaglam();
    const vm = ornek(ESITLEME_BOLUMU, { b, dil: "tr" });
    expect(vm.onay).toBe(false);
    await vm.boyutOku();
    expect(vm.boyut).toBe("4.56 MB");
    let html = await ciz(ESITLEME_BOLUMU, { b, dil: "tr" }, durumu(ESITLEME_BOLUMU, vm));
    expect(html).toMatch(/id="bt-es-onay"[^>]*aria-checked="false"/);
    expect(html).toContain("4.56 MB");
    vm.onayDegistir(true);
    expect(b.esitlemeOnayiYaz).toHaveBeenCalledWith(true);
    expect(vm.onay).toBe(true);
    b.esitlemeOnayiYaz.mockReturnValueOnce(false);         // yazilamadi: eski hal
    vm.onayDegistir(false);
    expect(vm.onay).toBe(false);
    b.esitlemeOnayi.mockReturnValue(true);                 // created saklanan degeri okur
    html = await ciz(ESITLEME_BOLUMU, { b, dil: "tr" }, durumu(ESITLEME_BOLUMU, vm));
    expect(html).toMatch(/id="bt-es-onay"[^>]*aria-checked="true"/);
  });

  it("kopyayi sifirla IKI adim; hata tur adiyla", async () => {
    const b = sahteBaglam();
    const vm = ornek(ESITLEME_BOLUMU, { b, dil: "tr" });
    await vm.sifirla();
    expect(b.kopyaSifirla).not.toHaveBeenCalled();
    vm.sifirlaBasla();
    const html = await ciz(ESITLEME_BOLUMU, { b, dil: "tr" }, durumu(ESITLEME_BOLUMU, vm));
    expect(html).toContain("data-bt-es-sifirla-eminim");
    expect(html).toContain("data-bt-es-sifirla-vazgec");
    await vm.sifirla();
    expect(b.kopyaSifirla).toHaveBeenCalledTimes(1);
    expect(vm.sonuc.anahtar).toBe("m.es.sifirlandi");
    vm.sifirlaBasla();
    b.kopyaSifirla.mockRejectedValueOnce(Object.assign(new Error("x"), { tur: "mesgul" }));
    await vm.sifirla();
    expect(vm.hata).toEqual({ anahtar: "m.es.sifirla_hata", degerler: { tur: "mesgul" } });
  });
});

// ── Bildirimler ────────────────────────────────────────────────────────
describe("Bildirim bolumu", () => {
  it("durum, 7 olay sinifi anahtari (aria-checked), pil yoneticisi adimlari ureticiye gore", async () => {
    const b = sahteBaglam();
    const vm = ornek(BILDIRIM_BOLUMU, { b, dil: "tr", yoklamaMs: 0 });
    await vm.oku();
    expect(vm.g.siniflar.length).toBe(7);
    const html = await ciz(BILDIRIM_BOLUMU, { b, dil: "tr", yoklamaMs: 0 }, { ...durumu(BILDIRIM_BOLUMU, vm), yonergeAcik: true });
    expect((html.match(/data-bt-bl-sinif=/g) || []).length).toBe(7);
    expect(html).toMatch(/aria-checked="false"[^>]*data-bt-bl-sinif="esik"/);
    expect(html).toMatch(/aria-checked="true"[^>]*data-bt-bl-sinif="dolu"/);
    expect(html).toContain(kac(SOZLUK_MOBIL["m.bl.yn_xiaomi_1"].tr));
    expect(html).toContain("data-bt-bl-pil-iste");          // anlik acik + pil kisitli
  });

  it("islemler bildirim modulune gider; hata tur adiyla", async () => {
    const b = sahteBaglam();
    const vm = ornek(BILDIRIM_BOLUMU, { b, dil: "tr", yoklamaMs: 0 });
    await vm.oku();
    await vm.sinifDegistir("dolu");
    expect(b.bl.ayarYaz).toHaveBeenLastCalledWith({ kapali: ["dolu", "esik"] });
    await vm.anlikCevir();
    expect(b.bl.ayarYaz).toHaveBeenLastCalledWith({ anlik: false });
    await vm.yenile();
    expect(vm.sonuc).toEqual({ anahtar: "m.bl.yenile_tamam" });
    await vm.deneme();
    expect(vm.sonuc).toEqual({ anahtar: "m.bl.deneme_tamam" });
    b.bl.pilMuafiyetiIste.mockRejectedValueOnce(Object.assign(new Error("x"), { tur: "ag" }));
    await vm.pilIste();
    expect(vm.hata).toEqual({ anahtar: "m.bl.hata_ag", degerler: null });
  });
});

// ── Gelismis ───────────────────────────────────────────────────────────
describe("Gelismis bolumu", () => {
  it("surumler: uygulama + kartin paneli (/kunye.json, imzali); kart bagli degilse sebep", async () => {
    const b = sahteBaglam();
    const vm = ornek(GELISMIS_BOLUMU, { b, dil: "tr" });
    await vm.surumOku();
    expect(vm.uygulama).toBe("0.1.0");
    expect(vm.panel).toEqual({ surum: "0123456789ab", dosya: 14 });
    expect(b.kart.istekler).toEqual([["GET", "/kunye.json", []]]);
    const html = await ciz(GELISMIS_BOLUMU, { b, dil: "en" }, durumu(GELISMIS_BOLUMU, vm));
    expect(html).toContain("0123456789ab · 14 files");
    const b2 = sahteBaglam(sahteKart({ durum: { durum: "eslesmemis", adres: "x", kimlik: KIMLIK } }));
    const vm2 = ornek(GELISMIS_BOLUMU, { b: b2, dil: "tr" });
    await vm2.panelOku();
    expect(vm2.panel).toBe(null);
    expect(vm2.panelYazi).toBe(SOZLUK_MOBIL["m.bt.panel_bagli_degil"].tr);
    expect(b2.kart.istekler).toEqual([]);
  });

  it("kunyeCoz bicimi denetler", () => {
    expect(kunyeCoz({ surum: "0123456789ab", dosya: 3, icerik_bayt: 9 })).toEqual({ surum: "0123456789ab", dosya: 3 });
    expect(kunyeCoz({ surum: "XYZ", dosya: 3 })).toBe(null);
    expect(kunyeCoz(null)).toBe(null);
  });

  it("kesif tanisi gorunur; PBKDF2 kartin bildirdigi turla; DURDUR olcumu", async () => {
    const b = sahteBaglam();
    const vm = ornek(GELISMIS_BOLUMU, { b, dil: "tr" });
    vm.elle = "192.168.1.20";
    await vm.kesifAra();
    expect(b.kesifTanisi).toHaveBeenCalledWith({ elle: "192.168.1.20" });
    await vm.pbkdf2Sina();
    expect(b.pbkdf2Olc).toHaveBeenCalledWith(50000);
    await vm.durdurSina();
    await vm.webSina();
    const html = await ciz(GELISMIS_BOLUMU, { b, dil: "tr" }, durumu(GELISMIS_BOLUMU, vm));
    expect(html).toContain("olcum.local");
    expect(html).toContain(SOZLUK_MOBIL["m.sonuc.ad_cozulmedi"].tr);
    expect(html).toContain(SOZLUK_MOBIL["m.kb.kaynak_nsd"].tr);
    expect(html).toContain("192.168.1.20:80");
    expect(html).toContain("data-bt-durdur-sonuc");
    expect(html).toContain("data-bt-pbkdf2-sonuc");
    expect(html).toContain(SOZLUK_MOBIL["m.ws.engellendi"].tr);
    // tani olmadan varsayilan tur
    const vm2 = ornek(GELISMIS_BOLUMU, { b, dil: "tr" });
    await vm2.pbkdf2Sina();
    expect(b.pbkdf2Olc).toHaveBeenLastCalledWith(20000);
  });
});

// ── kesif tanisi (tani.js) ─────────────────────────────────────────────
describe("kesifTanisi", () => {
  class KesifHatasi extends Error { constructor(tur, denenenler) { super(tur); this.tur = tur; this.denenenler = denenenler; } }
  class HedefHatasi extends Error { constructor(tur) { super(tur); this.tur = tur; } }
  const bag = (wifi, bul, nsd = async () => ({ servisler: [] })) => ({
    KartAg: { wifiDurumu: async () => wifi }, Kesif: { nsdTara: nsd },
    agKur: () => ({ kartFetch: async () => {} }), kesifKur: () => ({ bul }), onbellek: null, KesifHatasi, HedefHatasi,
  });

  it("Wi-Fi yoksa (hotspot da yoksa) hemen soyler; hotspot sahibiyken arar", async () => {
    const bul = vi.fn(async () => { throw new KesifHatasi("bulunamadi", []); });
    expect((await kesifTanisi(bag({ wifi: false }, bul))).hata).toBe("m.kb.hata_wifi_yok");
    expect(bul).not.toHaveBeenCalled();
    expect((await kesifTanisi(bag({ wifi: false, paylasim: true }, bul))).hata).toBe("m.kb.hata_bulunamadi");
    expect(bul).toHaveBeenCalledTimes(1);
  });

  it("basari: sonuc + denenenler + duyurular (TXT kimligi karsilastirilir)", async () => {
    const s = await kesifTanisi(bag({ wifi: true }, async ({ elle }) => ({
      adres: "10.0.0.5", kimlik: KIMLIK, kaynak: elle ? "elle" : "nsd", sureMs: 99, txtKimlik: KIMLIK, bilgi: { tur: 30000 },
      denenenler: [{ adres: "10.0.0.5", kaynak: "nsd", sonuc: "tamam" }],
    }), async () => ({ servisler: [{ ip: "10.0.0.5", port: 80, kimlik: KIMLIK }, { ip: "10.0.0.9", port: 80, kimlik: "ffffffffffffffff" }] })), { elle: " 10.0.0.5 " });
    expect(s.hata).toBe(null);
    expect(s.sonuc).toMatchObject({ adres: "10.0.0.5", kaynak: "elle", tur: 30000 });
    expect(s.duyurular).toEqual([{ adres: "10.0.0.5:80", uyuyor: true }, { adres: "10.0.0.9:80", uyuyor: false }]);
  });

  it("hata: kesif hatasinin denenenleri korunur; hedef hatasi kendi metni; bilinmeyen hata genel; ATMAZ", async () => {
    const d = [{ adres: "1.2.3.4", kaynak: "elle", sonuc: "zaman-asimi" }];
    let s = await kesifTanisi(bag({ wifi: true }, async () => { throw new KesifHatasi("kimlik-uymuyor", d); }));
    expect(s).toMatchObject({ hata: "m.kb.hata_kimlik", denenenler: d });
    s = await kesifTanisi(bag({ wifi: true }, async () => { throw new HedefHatasi("ozel-degil"); }));
    expect(s.hata).toBe("m.kb.hata_ozel_degil");
    s = await kesifTanisi(bag({ wifi: true }, async () => { throw new TypeError("gizli ic mesaj"); }));
    expect(s.hata).toBe("m.kb.hata_bilinmeyen");
    expect(JSON.stringify(s)).not.toContain("gizli");
  });
});
