// 5C kabuk: ACIL DURDURMA mantigi (uygulama.js acilDurdur / durdurAdresleri / canliAl; A8–A11). DOM'suz.
// 5P (P6): eski Ionic kabugunun (serit bileseni, sekmeler, tema.css) testleri o dosyalarla birlikte silindi;
// telefonda serit artik panelin (arayuz3/) kendi seridi, durdurma yolu ortam uzerinden buraya gelir.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const sayim = vi.hoisted(() => ({ wifi: 0, p0: [], p0Yanit: null }));

vi.mock("../src/cekirdek/eklenti.js", () => ({
  KartAg: {
    wifiDurumu: async () => { sayim.wifi += 1; return { hataAyiklama: false }; },
    istek: async () => { throw new Error("kullanilmaz"); },
    p0: (v) => { sayim.p0.push(v.adresler); return sayim.p0Yanit ? Promise.resolve(sayim.p0Yanit) : new Promise(() => {}); },
  },
  Kesif: { ara: async () => ({ servisler: [] }) },
  Kasa: {
    liste: async () => ({ kayitlar: [] }), sayacYaz: async () => ({}), sayacOku: async () => ({ isaret: "0" }),
    anahtarYaz: async () => ({}), anahtarOku: async () => ({}), sil: async () => ({}),
  },
}));

const SRC = fileURLToPath(new URL("../src", import.meta.url));
const oku = (...yol) => readFileSync(join(SRC, ...yol), "utf8").split("\r\n").join("\n");
const yorumsuz = (metin) => metin.split("\n").filter((l) => !/^\s*(\/\/|\*)/.test(l)).join("\n");

function dosyalar(dizin) {
  const cikti = [];
  for (const ad of readdirSync(dizin)) {
    const yol = join(dizin, ad);
    if (statSync(yol).isDirectory()) cikti.push(...dosyalar(yol));
    else if (ad.endsWith(".js") || ad.endsWith(".vue")) cikti.push(yol);
  }
  return cikti;
}

describe("kabuk: durdurma mantigi (uygulama.js)", () => {
  beforeEach(() => { sayim.wifi = 0; sayim.p0 = []; sayim.p0Yanit = null; vi.resetModules(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it("acilDurdur modul yuklenir yuklenmez calisir: kart KURULMADAN, ayni gorev turunda eklentiye gider", async () => {
    vi.stubGlobal("localStorage", { getItem: () => JSON.stringify({ adres: "192.168.1.7:80", kimlik: "0123456789abcdef" }), setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    const haller = [];
    const birak = u.durdurDinle((h) => haller.push(h));
    expect(u.durdurDurumu()).toBe("bos");
    u.acilDurdur();                                  // BEKLENMIYOR
    expect(sayim.p0).toEqual([["192.168.1.7:80", "olcum.local", "192.168.4.1"]]);
    expect(sayim.wifi).toBe(0);                      // kart / kasa / kesif kurulmadi
    expect(u.durdurDurumu()).toBe("gonderiliyor");
    expect(haller).toEqual(["gonderiliyor"]);
    birak();
    u.acilDurdur();
    expect(haller).toEqual(["gonderiliyor"]);
    expect(sayim.p0.length).toBe(2);
  });

  it("onbellek yok / bozuk / localStorage atiyor: yine de kartin erisim noktasi adresine gider", async () => {
    for (const depo of [{ getItem: () => null }, { getItem: () => "{bozuk" }, { getItem: () => { throw new Error("x"); } }]) {
      sayim.p0 = [];
      vi.resetModules();
      vi.stubGlobal("localStorage", depo);
      const u = await import("../src/cekirdek/uygulama.js");
      u.acilDurdur();
      expect(sayim.p0).toEqual([["olcum.local", "192.168.4.1"]]);
    }
  });

  it("durdurAdresleri (saf): bagli adres ONCE, sonra onbellek, sonra kartin ADI; ayni adres bir kez; bozuk girdi atmaz", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null });
    const { durdurAdresleri } = await import("../src/cekirdek/uygulama.js");
    const AD = "olcum.local";                    // IP degismisse de karta giden yol (curutucu 5C, bulgu 2)
    expect(durdurAdresleri("192.168.1.7:80", { adres: "192.168.1.9:80", kimlik: "x" })).toEqual(["192.168.1.7:80", "192.168.1.9:80", AD]);
    expect(durdurAdresleri("192.168.1.7:80", { adres: "192.168.1.7:80" })).toEqual(["192.168.1.7:80", AD]);
    expect(durdurAdresleri(null, { adres: "192.168.1.9:80" })).toEqual(["192.168.1.9:80", AD]);
    expect(durdurAdresleri("192.168.1.7:80", null)).toEqual(["192.168.1.7:80", AD]);
    expect(durdurAdresleri(undefined, undefined)).toEqual([AD]);
    expect(durdurAdresleri(5, { adres: "" })).toEqual([AD]);
    expect(durdurAdresleri(AD, { adres: AD })).toEqual([AD]);
    // Erisim noktasi adresiyle birlikte en cok 4: eklentinin siniri (P0.kt AZAMI_ADRES) hicbirini kesmez.
    const { P0_AZAMI_ADRES } = await import("../src/cekirdek/ag.js");
    expect(durdurAdresleri("192.168.1.7:80", { adres: "192.168.1.9:80" }).length + 1).toBeLessThanOrEqual(P0_AZAMI_ADRES);
  });

  it("asil (bagli) adres biliniyorken yalniz BASKA adres 204 verdiyse 'baska-yanit'; asil verdiyse 'durduruldu'", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    // Kart kurulmadan (asil bilinmiyor): herhangi bir adresin 204'u "durduruldu".
    sayim.p0Yanit = { tamam: true, adres: "192.168.4.1", basarili: ["192.168.4.1"] };
    await u.acilDurdur();
    expect(u.durdurDurumu()).toBe("durduruldu");
    const kart = await u.kartAl();
    kart.durum = () => ({ durum: "bagli", adres: "192.168.1.20:80", kimlik: "0123456789abcdef" });
    await u.acilDurdur();
    expect(sayim.p0.at(-1)[0]).toBe("192.168.1.20:80");            // asil adres listenin BASINDA
    expect(u.durdurDurumu()).toBe("baska-yanit");
    sayim.p0Yanit = { tamam: true, adres: "192.168.1.20:80", basarili: ["192.168.4.1", "192.168.1.20:80"] };
    await u.acilDurdur();
    expect(u.durdurDurumu()).toBe("durduruldu");
    sayim.p0Yanit = { tamam: false, basarili: [] };
    await u.acilDurdur();
    expect(u.durdurDurumu()).toBe("ulasilamadi");
  });

  it("kart kurulduktan sonra BAGLI adres de listeye girer (es zamanli okunur)", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    const kart = await u.kartAl();
    kart.durum = () => ({ durum: "bagli", adres: "192.168.1.20:80", kimlik: "0123456789abcdef" });
    u.acilDurdur();
    expect(sayim.p0).toEqual([["192.168.1.20:80", "olcum.local", "192.168.4.1"]]);
    // Onbellek deposuna ERISILEMESE de (erisim atiyor) bagli adres kaybolmaz.
    vi.unstubAllGlobals();
    Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("depo yok"); } });
    try {
      u.acilDurdur();
      expect(sayim.p0[1]).toEqual(["192.168.1.20:80", "olcum.local", "192.168.4.1"]);
    } finally {
      delete globalThis.localStorage;
    }
  });

  it("canliAl: modul yuklenemez / kurulamazsa REDDEDER ve saklamaz (ekran 'akis hazir degil' der)", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    // Sahte eklentide akis yok: canliKur (varsa) kurulamaz; modul yoksa UygulamaHatasi.
    await expect(u.canliAl()).rejects.toBeInstanceOf(Error);
    await expect(u.canliAl()).rejects.toBeInstanceOf(Error);
    expect(oku("cekirdek", "uygulama.js")).toContain('const canliModulleri = import.meta.glob("./canli.js");');
    const disarida = dosyalar(SRC).filter((y) => !y.endsWith("uygulama.js") && /cekirdek\/canli\.js|\.\/canli\.js|canliKur\(/.test(yorumsuz(readFileSync(y, "utf8"))));
    expect(disarida.filter((y) => !y.endsWith("canli.js"))).toEqual([]);
  });
});
