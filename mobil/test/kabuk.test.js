// 5C kabuk: ACIL DURDUR seridi her rotada, sekmelerin ustunde, tek dokunus, hicbir seyi beklemeden
// (A8–A11); dort sekme; tema degiskenleri ve dokunma boyutlari (A44). DOM'suz: kaynak + mantik.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { DURDURULDU_SURE_MS, seritGorunumu, seritSuresi } from "../src/bilesen/durdur_gorunum.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { ILK_YOL, SEKMELER, sekmeBul } from "../src/ekran/sekmeler.js";

const sayim = vi.hoisted(() => ({ wifi: 0, p0: [] }));

vi.mock("../src/cekirdek/eklenti.js", () => ({
  KartAg: {
    wifiDurumu: async () => { sayim.wifi += 1; return { hataAyiklama: false }; },
    istek: async () => { throw new Error("kullanilmaz"); },
    p0: (v) => { sayim.p0.push(v.adresler); return new Promise(() => {}); },
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

const sablon = (vue) => /<template>([\s\S]*)<\/template>/.exec(vue)[1];

describe("kabuk: ACIL DURDUR seridi", () => {
  const APP = oku("App.vue");
  const SERIT = oku("bilesen", "DurdurSeridi.vue");

  it("serit kabukta, yonlendirici cikisinin DISINDA ve sekmelerin HEMEN ustunde (kaynak sirasi)", () => {
    const s = sablon(APP);
    expect(s).toMatch(/<main id="icerik" class="icerik"><router-view \/><\/main>\s*<DurdurSeridi \/>\s*<nav id="sekmeler" class="sekme"/);
    expect(s.match(/<DurdurSeridi\b/g).length).toBe(1);
    expect(s.match(/<router-view\b/g).length).toBe(1);
    // Kosula bagli degil: hicbir v-if / v-show seridi gizleyemez.
    expect(s).not.toMatch(/<DurdurSeridi[^>]*v-(if|show)/);
    expect(sablon(SERIT)).not.toMatch(/v-show|<div id="durdur-seridi"[^>]*v-if|<button id="durdur"[^>]*(v-if|:disabled|disabled)/);
  });

  it("serit TEK yerde: ekranlar ve rotalar onu kendileri koymaz; her sekme ayri ekran", () => {
    const kullananlar = dosyalar(SRC).filter((y) => /<DurdurSeridi\b|DurdurSeridi\.vue/.test(yorumsuz(readFileSync(y, "utf8"))))
      .map((y) => y.slice(SRC.length + 1).split("\\").join("/"));
    expect(kullananlar).toEqual(["App.vue"]);
    const y = oku("yonlendirme.js");
    for (const s of SEKMELER) {
      const ad = s.ad[0].toUpperCase() + s.ad.slice(1);
      expect(y, s.ad).toContain(`import ${ad} from "./ekran/${ad}.vue";`);
    }
    expect(y).toContain("...SEKMELER.map((s) => ({ path: s.yol, name: s.ad, component: EKRANLAR[s.ad] }))");
    expect(SEKMELER.map((s) => s.ad)).toEqual(["durum", "canli", "kayitlar", "ayarlar"]);
    expect(ILK_YOL).toBe("/durum");
    expect(sekmeBul("canli").yol).toBe("/canli");
    expect(sekmeBul(undefined).ad).toBe("durum");
    for (const s of SEKMELER) expect(Object.hasOwn(SOZLUK_MOBIL, s.baslik), s.baslik).toBe(true);
  });

  it("seridi ortebilecek katman bileseni (iletisim kutusu, kayan pencere, tam sayfa) src/ agacinda YOK", () => {
    const YASAK = /ion-modal|ion-alert|ion-popover|ion-action-sheet|ion-loading|ion-toast|ion-page|ion-content|IonModal|IonPage|IonContent|alertController|modalController|\bconfirm\(|\balert\(|\bprompt\(/;
    for (const y of dosyalar(SRC)) expect(yorumsuz(readFileSync(y, "utf8")), y).not.toMatch(YASAK);
  });

  it("dokunus isleyicisi DOGRUDAN acilDurdur: araya bekleme, onay, yonlendirme girmez", () => {
    expect(sablon(SERIT)).toContain('<button id="durdur" type="button" class="durdur" :aria-label="c(\'m.dd.etiket\')" @click="acilDurdur">');
    expect(SERIT).toContain('import { acilDurdur, durdurDinle, durdurDurumu } from "../cekirdek/uygulama.js";');
    expect(yorumsuz(SERIT)).not.toMatch(/\bawait\b|\basync\b|vue-router|useRouter|kartAl|canliAl/);
    const u = yorumsuz(oku("cekirdek", "uygulama.js"));
    const govde = /export function acilDurdur\(\) \{\n([\s\S]*?)\n\}/.exec(u)[1];
    expect(govde.trim()).toBe("return durdurNesnesi.durdur();");
    // durdur nesnesi MODUL duzeyinde kurulur (girintisiz), bir islevin icinde degil.
    expect(u).toMatch(/\nconst durdurNesnesi = durdurKur\(\{\n {2}p0: agKur\(KartAg\)\.p0,\n {2}adresler,\n/);
  });

  it("'Kaydi durdur' kirmizi DEGIL ve seritten ayri: cerceveli dugme, DURDUR sinifini / rengini kullanmaz", () => {
    const k = oku("ekran", "KayitDugmesi.vue");
    expect(sablon(k)).toContain('<button v-if="dugme.is === \'durdur\'" id="kayit-durdur" type="button" class="dugme"');
    expect(k).not.toMatch(/class="[^"]*\bdurdur\b|acilDurdur|--durdur/);
    const css = oku("tema.css");
    const dugme = /\n\.dugme \{([^}]*)\}/.exec(css)[1];
    expect(dugme).toContain("border: 1px solid var(--kenar-koyu)");
    expect(dugme).not.toContain("--durdur");
  });
});

describe("kabuk: durdurma mantigi (uygulama.js)", () => {
  beforeEach(() => { sayim.wifi = 0; sayim.p0 = []; vi.resetModules(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it("acilDurdur modul yuklenir yuklenmez calisir: kart KURULMADAN, ayni gorev turunda eklentiye gider", async () => {
    vi.stubGlobal("localStorage", { getItem: () => JSON.stringify({ adres: "192.168.1.7:80", kimlik: "0123456789abcdef" }), setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    const haller = [];
    const birak = u.durdurDinle((h) => haller.push(h));
    expect(u.durdurDurumu()).toBe("bos");
    u.acilDurdur();                                  // BEKLENMIYOR
    expect(sayim.p0).toEqual([["192.168.1.7:80", "192.168.4.1"]]);
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
      expect(sayim.p0).toEqual([["192.168.4.1"]]);
    }
  });

  it("durdurAdresleri (saf): bagli adres ONCE, sonra onbellek; ayni adres bir kez; bozuk girdi atmaz", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null });
    const { durdurAdresleri } = await import("../src/cekirdek/uygulama.js");
    expect(durdurAdresleri("192.168.1.7:80", { adres: "192.168.1.9:80", kimlik: "x" })).toEqual(["192.168.1.7:80", "192.168.1.9:80"]);
    expect(durdurAdresleri("192.168.1.7:80", { adres: "192.168.1.7:80" })).toEqual(["192.168.1.7:80"]);
    expect(durdurAdresleri(null, { adres: "192.168.1.9:80" })).toEqual(["192.168.1.9:80"]);
    expect(durdurAdresleri("192.168.1.7:80", null)).toEqual(["192.168.1.7:80"]);
    expect(durdurAdresleri(undefined, undefined)).toEqual([]);
    expect(durdurAdresleri(5, { adres: "" })).toEqual([]);
  });

  it("kart kurulduktan sonra BAGLI adres de listeye girer (es zamanli okunur)", async () => {
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
    const u = await import("../src/cekirdek/uygulama.js");
    const kart = await u.kartAl();
    kart.durum = () => ({ durum: "bagli", adres: "192.168.1.20:80", kimlik: "0123456789abcdef" });
    u.acilDurdur();
    expect(sayim.p0).toEqual([["192.168.1.20:80", "192.168.4.1"]]);
    // Onbellek deposuna ERISILEMESE de (erisim atiyor) bagli adres kaybolmaz.
    vi.unstubAllGlobals();
    Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("depo yok"); } });
    try {
      u.acilDurdur();
      expect(sayim.p0[1]).toEqual(["192.168.1.20:80", "192.168.4.1"]);
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

describe("serit gorunumu (A10)", () => {
  it("bos: yalniz dugme; gonderiliyor; durduruldu GECICI; ulasilamadi KALICI ve uyari rolunde", () => {
    expect(seritGorunumu("bos").anahtar).toBe(null);
    expect(seritGorunumu("gonderiliyor").anahtar).toBe("m.dd.gonderiliyor");
    expect(seritGorunumu("durduruldu")).toMatchObject({ anahtar: "m.dd.durduruldu", kalici: false });
    expect(seritGorunumu("ulasilamadi")).toMatchObject({ anahtar: "m.dd.ulasilamadi", sinif: "ulasilamadi", kalici: true, rol: "alert" });
    expect(seritGorunumu("bilinmeyen").anahtar).toBe(null);
    expect(seritSuresi("durduruldu")).toBe(DURDURULDU_SURE_MS);
    expect(DURDURULDU_SURE_MS).toBeGreaterThanOrEqual(2000);
    expect(seritSuresi("ulasilamadi")).toBe(0);            // kendiliginden SILINMEZ
    expect(seritSuresi("gonderiliyor")).toBe(0);
    expect(SOZLUK_MOBIL["m.dd.ulasilamadi"].tr).toMatch(/^ULAŞILAMADI/);
    expect(SOZLUK_MOBIL["m.dd.ulasilamadi"].en).toMatch(/^UNREACHABLE/);
  });
});

describe("tema.css (A44)", () => {
  const CSS = oku("tema.css");
  const blok = (bas, son) => CSS.slice(CSS.indexOf(`/* tema:${bas} */`), CSS.indexOf(`/* tema:${son} */`));
  const degiskenler = (b) => Object.fromEntries([...b.matchAll(/(--[a-z0-9-]+):\s*(#[0-9a-f]{6})\b/g)].map((m) => [m[1], m[2]]));
  const px = (deger) => {                        // "max(3.5rem, 56px)" -> kok yazi boyutu ne olursa olsun en az kac px
    const m = /^max\(([\d.]+)rem, (\d+)px\)$/.exec(deger);
    return m ? Number(m[2]) : NaN;
  };
  const kok = (ad) => new RegExp(`${ad}:\\s*([^;]+);`).exec(CSS)[1].trim();

  it("uc renk blogu (koyu, sistem-acik, acik) AYNI degisken kumesini tanimlar; acik ikisi birebir ayni", () => {
    const koyu = degiskenler(blok("koyu", "acik-sistem"));
    const sistem = degiskenler(blok("acik-sistem", "acik"));
    const acik = degiskenler(blok("acik", "son"));
    expect(Object.keys(koyu).length).toBeGreaterThanOrEqual(19);
    expect(Object.keys(sistem).sort()).toEqual(Object.keys(koyu).sort());
    expect(acik).toEqual(sistem);
    expect(blok("acik-sistem", "acik")).toContain("@media (prefers-color-scheme: light)");
    expect(koyu["--zemin"]).not.toBe(acik["--zemin"]);
    // CSS'te kullanilan her renk degiskeni tanimli.
    const tanimli = new Set([...CSS.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));
    for (const m of CSS.matchAll(/var\((--[a-z0-9-]+)\)/g)) expect(tanimli.has(m[1]), m[1]).toBe(true);
  });

  it("kontrast >= 4.5:1 (WCAG): iki temada metin / zemin ciftleri", () => {
    const parlaklik = (hex) => {
      const k = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
      return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2];
    };
    const oran = (a, b) => { const [x, y] = [parlaklik(a), parlaklik(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
    const CIFTLER = [
      ["--yazi", "--zemin"], ["--yazi", "--kart"], ["--yazi", "--zemin-2"], ["--soluk", "--zemin"], ["--soluk", "--kart"], ["--soluk", "--zemin-2"],
      ["--vurgu", "--zemin-2"], ["--vurgu", "--vurgu-zemin"], ["--dolgu-yazi", "--dolgu"], ["--durdur-yazi", "--durdur"],
      ["--iyi", "--iyi-zemin"], ["--iyi", "--zemin-2"], ["--uyari", "--uyari-zemin"], ["--uyari", "--zemin"],
      ["--volt", "--kart"], ["--amper", "--kart"], ["--watt", "--kart"],
    ];
    for (const [ad, d] of [["koyu", degiskenler(blok("koyu", "acik-sistem"))], ["acik", degiskenler(blok("acik", "son"))]]) {
      for (const [metin, zemin] of CIFTLER) expect(oran(d[metin], d[zemin]), `${ad} ${metin} / ${zemin}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("DURDUR >= 56 px, sekme ve her dugme >= 48 px (kok yazi boyutu kuculse de)", () => {
    expect(px(kok("--durdur-yukseklik"))).toBeGreaterThanOrEqual(56);
    expect(px(kok("--sekme-yukseklik"))).toBeGreaterThanOrEqual(48);
    expect(px(kok("--dokunma"))).toBeGreaterThanOrEqual(48);
    expect(/\n\.durdur \{([^}]*)\}/.exec(CSS)[1]).toContain("min-height: var(--durdur-yukseklik)");
    expect(/\n\.durdur \{([^}]*)\}/.exec(CSS)[1]).toContain("width: 100%");
    expect(/\n\.sekme a \{([^}]*)\}/.exec(CSS)[1]).toContain("min-height: var(--sekme-yukseklik)");
    expect(/\n\.dugme \{([^}]*)\}/.exec(CSS)[1]).toContain("min-height: var(--dokunma)");
    expect(/\n\.secim button \{([^}]*)\}/.exec(CSS)[1]).toContain("min-height: var(--dokunma)");
    // Serit her seyin ustunde.
    expect(Number(/\n\.serit \{[^}]*z-index: (\d+)/.exec(CSS)[1])).toBeGreaterThanOrEqual(1000);
    // Etkin sekme / secili secenek yalniz renkle ayrilmaz.
    expect(/\.sekme a\[aria-current="page"\] \{([^}]*)\}/.exec(CSS)[1]).toMatch(/font-weight: 700; border-top-color/);
    expect(/\.secim button\[aria-checked="true"\] \{([^}]*)\}/.exec(CSS)[1]).toContain("box-shadow: inset");
  });

  it("main.js tema.css'i ve yonlendiriciyi kurar; ilk ice aktarim degismedi", () => {
    const m = oku("main.js");
    expect(m).toContain('import "./tema.css";');
    expect(m).toContain(".use(yonlendiriciKur())");
    expect(m.split("\n")[0]).toMatch(/^import "\.\/cekirdek\/rtc_kapat\.js";/);
  });
});
