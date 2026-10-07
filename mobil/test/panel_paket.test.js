// 5P P1 — derleme hatti: PC paneli (arayuz3/) telefon paketinde, CSP'de unsafe-eval OLMADAN.
// araclar/panel_paketle.mjs'in donusumleri + gercek bir `vite build` (gecici dizine) sinanir.
// Basliksiz tarayici acilisi ayri: test-tarayici/acilis.py.
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { readFileSync, readdirSync, statSync, mkdtempSync, rmSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join, relative } from "node:path";
import { tmpdir } from "node:os";
import vm from "node:vm";
import {
  PANEL_KOK, PANEL_HTML, VUE_SURUM, DERLEYICI_SURUM, kokSablonuAyikla, sablonDerle, jsDonustur,
  sablonOzellikleri, createAppCagrilari, acilmadiKutusu, domSablonTuzaklari, kabukDoldur,
} from "../araclar/panel_paketle.mjs";

const KOK = fileURLToPath(new URL("..", import.meta.url));
const oku = (yol) => readFileSync(join(KOK, yol), "utf8");
const PANEL_HTML_METIN = readFileSync(PANEL_HTML, "utf8");

/* arayuz3/ altindaki paketlenebilir .js dosyalari (vendor ve PC'ye ozgu servis iscisi haric). */
function panelJs(dizin = PANEL_KOK) {
  const c = [];
  for (const ad of readdirSync(dizin)) {
    const yol = join(dizin, ad);
    if (statSync(yol).isDirectory()) { if (ad !== "vendor") c.push(...panelJs(yol)); }
    else if (ad.endsWith(".js")) c.push(relative(PANEL_KOK, yol).split("\\").join("/"));
  }
  return c.sort();
}

// Toplama aninda (describe govdesi) hesaplanmaz: ayiklama/donusum atarsa TEST kirmizi olur, dosya cokmez
// (mutasyon kosucusu iddiasiz cokmeyi "SUPHELI" sayar).
const kokSablon = () => kokSablonuAyikla(PANEL_HTML_METIN).sablon;
let _sonuclar = null;
const donusumler = () => (_sonuclar ||= Object.fromEntries(panelJs().map((d) => [d,
  jsDonustur(readFileSync(join(PANEL_KOK, d), "utf8"), d, { kok: d === "app.js" })])));

describe("kok sablonu (#uyg)", () => {

  it("tek #uyg; ayiklanan sablon kabukla baslar, ayarlar/pil/kayitlar/konsol gorunumlerini icerir", () => {
    const sablon = kokSablon();
    expect(sablon.trimStart().startsWith("<!--")).toBe(true);
    expect(sablon).toContain('<div class="kabuk"');
    for (const g of ["canli", "skop", "ayar", "pil", "kayitlar", "karsilastir", "konsol"]) {
      expect(sablon, g).toContain(`v-show="gorunum === '${g}'"`);
    }
    // Kesik degil: son <main> (konsol) da icinde, #acilmadi DISARIDA.
    expect(sablon).not.toContain('id="acilmadi"');
    expect(sablon.match(/<div\b/g).length).toBe(sablon.match(/<\/div\s*>/g).length);
  });

  it("derlenir: render disari aktarilir, Vue'dan ice aktarir, bilinen panel ogeleri cizimde", () => {
    const { kod, uyarilar } = sablonDerle(kokSablon(), "#uyg");
    expect(uyarilar).toEqual([]);
    expect(kod).toMatch(/export function render\(_ctx, _cache/);
    expect(kod).toMatch(/from "vue"/);
    expect(kod).toContain('"kabuk"');
    expect(kod).toContain("cekmece-acik");
    expect(kod).toContain("_ctx.icerigeGec");
    expect(kod).toContain('_resolveComponent("kayitlar-ekran")');
    // HTML yorumlari vnode olmaz (PC'nin vendor uretim surumunun varsayilani; ilk yorumun metni).
    expect(kod).not.toContain("baglama noktasinin");
    // Derlenmis cikti kod uretmez (new Function / eval yok).
    expect(kod).not.toMatch(/new Function|\beval\s*\(/);
  });

  it("DOM sablonu tuzaklari yok: baglamada buyuk harf ve svg disinda kendinden kapanan etiket yok", () => {
    // Varsa: tarayicinin ayristirdigi (PC) ile derleyicinin ayristirdigi (telefon) ayrisir. Kesin
    // karsilastirma (tarayici innerHTML'i ile) test-tarayici/acilis.py'de.
    expect(domSablonTuzaklari(kokSablon())).toEqual([]);
  });

  it("'_' ile baslayan sablon adi yok (PC'nin with() kipi bunlari pencerede arar, telefon _ctx'te)", () => {
    const { kod } = sablonDerle(kokSablon(), "#uyg");
    expect(kod.match(/_ctx\._\w*/g) || []).toEqual([]);
  });

  it("tuzak dedektoru gercekten yakalar (bos iddia degil)", () => {
    expect(domSablonTuzaklari('<p :viewBox="v">x</p>')).toHaveLength(1);
    // svg icinde DUZ viewBox serbest (tarayici duzeltir) ama BAGLAMA :viewBox kucultulur.
    expect(domSablonTuzaklari('<svg :viewBox="v"><path :strokeWidth="w"/></svg>')).toHaveLength(2);
    expect(domSablonTuzaklari('<p @myOlay="f"></p>')).toHaveLength(1);
    expect(domSablonTuzaklari('<kayitlar-ekran :a="b" />')).toHaveLength(1);
    expect(domSablonTuzaklari('<svg viewBox="0 0 1 1"><path d="M0 0"/></svg><br/>')).toEqual([]);
  });

  it("kapanis yanlis eslesirse HATA (sessiz kesik sablon yok)", () => {
    const bozuk = PANEL_HTML_METIN.replace('<div id="uyg" v-cloak>', '<div id="uyg" v-cloak><div>');
    expect(() => kokSablonuAyikla(bozuk)).toThrow();
    const iki = PANEL_HTML_METIN + '<div id="uyg" v-cloak></div>';
    expect(() => kokSablonuAyikla(iki)).toThrow(/1 olmali/);
  });
});

describe("JS donusumu (createApp + template:)", () => {

  it("arayuz3'teki her template: derlendi; donusumden sonra HICBIRI kalmadi", () => {
    const sonuclar = donusumler();
    const sayim = Object.fromEntries(Object.entries(sonuclar).filter(([, s]) => s.sablonlar.length)
      .map(([d, s]) => [d, s.sablonlar.length]));
    // Bilinen yerler (2026-10-07): app.js'te 5 hata bileseni, 7 ekranda birer SABLON.
    expect(sayim).toMatchObject({
      "app.js": 5, "ekran/ayarlar.js": 1, "ekran/baglanti.js": 1, "ekran/eslesme_ekran.js": 1,
      "ekran/karsilastir.js": 1, "ekran/kayit_gorunum.js": 1, "ekran/kayitlar.js": 1, "ekran/pc_kopru.js": 1,
    });
    for (const [d, s] of Object.entries(sonuclar)) {
      expect(sablonOzellikleri(s.kod), d).toEqual([]);
      for (const { kimlik, sablon } of s.sablonlar) {
        const { kod, uyarilar } = sablonDerle(sablon, kimlik);
        expect(uyarilar, kimlik).toEqual([]);
        expect(kod, kimlik).toMatch(/export function render\(/);
        expect(kod.match(/_ctx\._\w*/g) || [], kimlik).toEqual([]);
      }
    }
  });

  it("app.js: kok render TEK kez enjekte, createApp TEK", () => {
    const sonuclar = donusumler();
    const s = sonuclar["app.js"];
    expect(s.kod.split("createApp({ render: __kokRender,").length).toBe(2);
    expect(s.kod.split('import { render as __kokRender } from "virtual:panel-kok";').length).toBe(2);
    expect(createAppCagrilari(s.kod)).toHaveLength(1);
    // Oteki dosyalara kok enjekte edilmez.
    for (const [d, x] of Object.entries(sonuclar)) if (d !== "app.js") expect(x.kod, d).not.toContain("__kokRender");
  });

  it("donusum ithal satirini EN BASA koyar; dosyanin geri kalani aynen (yalniz template: -> render:)", () => {
    const d = "ekran/kayitlar.js";
    const ham = readFileSync(join(PANEL_KOK, d), "utf8");
    const { kod } = donusumler()[d];
    const [ilk, ...geri] = kod.split("\n");
    expect(ilk).toBe('import { render as __panelSablon0 } from "virtual:panel-sablon/ekran/kayitlar.js/0";');
    expect(geri.join("\n")).toBe(ham.replace("template: SABLON,", "render: __panelSablon0,"));
  });

  it("derlenemeyen template: HATA verir (yeni ekran telefonda sessizce bos acilmasin)", () => {
    expect(() => jsDonustur("const A = 'x'; export const B = { template: A + '<p/>' };", "x.js")).toThrow(/derlenemeyen/);
    expect(() => jsDonustur("const n = 1; export const B = { template: `<p>${n}</p>` };", "x.js")).toThrow(/derlenemeyen/);
    expect(() => jsDonustur("let S = '<p/>'; export const B = { template: S };", "x.js")).toThrow(/derlenemeyen/);
    expect(() => jsDonustur("export const B = { template: DIS };", "x.js")).toThrow(/derlenemeyen/);
    expect(() => jsDonustur("export const B = { 'template': f() };", "x.js")).toThrow(/derlenemeyen/);
    // Yorumdaki "template:" ozellik degil, dokunulmaz.
    expect(jsDonustur("// template: 'x'\nexport const B = 1;", "x.js").sablonlar).toEqual([]);
    // Duz dizgiler: tek / cift / ters tirnak, ayni dosyada const.
    const r = jsDonustur("const S = `<b>{{ a }}</b>`; export const A = { template: '<i/>' }, B = { template: \"<u/>\" }, C = { template: S };", "x.js");
    expect(r.sablonlar.map((s) => s.sablon)).toEqual(["<i/>", "<u/>", "<b>{{ a }}</b>"]);
  });

  it("createApp sayisi 1 degilse ya da kokte zaten render varsa HATA", () => {
    expect(() => jsDonustur("export const a = 1;", "app.js", { kok: true })).toThrow(/createApp 0/);
    expect(() => jsDonustur("createApp({}); createApp({});", "app.js", { kok: true })).toThrow(/createApp 2/);
    expect(() => jsDonustur("createApp({ render() {} });", "app.js", { kok: true })).toThrow(/zaten/);
  });

  it("derleyici, uygulamanin calistirdigi vue ile ayni surum", () => {
    expect(DERLEYICI_SURUM).toBe(VUE_SURUM);
  });
});

describe("kabuk sayfasi (index.html)", () => {
  it("CSP meta'si kaynakta; yer tutucular tek; satir ici betik ve olay ozniteligi yok", () => {
    const html = oku("index.html");
    expect(html).toContain('http-equiv="Content-Security-Policy"');
    for (const ad of ["on-boya", "acilmadi", "bekci"]) expect(html.split(`<!-- panel:${ad} -->`).length, ad).toBe(2);
    expect(html.indexOf("<!-- panel:on-boya -->")).toBeLessThan(html.indexOf('rel="stylesheet"'));
    expect(html).toMatch(/<div id="uyg" v-cloak><\/div>/);
    expect(html).toContain('<script type="module" src="/src/giris.js"></script>');
  });

  it("#acilmadi kutusu arayuz3'ten: onclick -> data-yenile, baska fark yok", () => {
    const kutu = acilmadiKutusu(PANEL_HTML_METIN);
    const pc = PANEL_HTML_METIN.slice(PANEL_HTML_METIN.indexOf('<div id="acilmadi"'));
    expect(pc.startsWith(kutu.replace(" data-yenile", ' onclick="location.reload()"'))).toBe(true);
    expect(kutu).not.toMatch(/\son[a-z]+\s*=/i);
    expect(kutu).toContain('id="acilmadi-neden"');
    expect(() => acilmadiKutusu(PANEL_HTML_METIN.replace(' onclick="location.reload()"', ' onclick="x()"'))).toThrow();
    expect(() => kabukDoldur("<!-- panel:acilmadi --><!-- panel:acilmadi -->", { panelHtml: PANEL_HTML_METIN })).toThrow(/tam bir kez/);
  });
});

describe("giris.js", () => {
  const kod = oku("src/giris.js");
  const satirlar = kod.split("\n");
  it("ILK ice aktarim rtc_kapat; Vue npm runtime'i global; ortam istege bagli (glob); panel en son", () => {
    expect(satirlar.find((l) => l.startsWith("import "))).toMatch(/^import "\.\/cekirdek\/rtc_kapat\.js";/);
    expect(kod).toMatch(/^import \* as Vue from "vue";$/m);
    expect(kod).toMatch(/^const KURESEL = globalThis;\nKURESEL\.Vue = Vue;$/m);
    expect(kod).not.toMatch(/vue\.global|compiler|vue\/dist\/vue\.esm/);
    expect(kod).toContain('import.meta.glob("./ortam/index.js")');
    const i = (s) => kod.indexOf(s);
    expect(i("KURESEL.Vue = Vue")).toBeLessThan(i("await m.ortamKur({ kuresel: KURESEL })"));
    expect(i("await m.ortamKur({ kuresel: KURESEL })")).toBeLessThan(i('await import("../../arayuz3/app.js")'));
  });
});

describe("tema on boyamasi (src/on_boya.js)", () => {
  /* B7'nin karsilastirmasi (uretim/test_arayuz3.js) telefon betigi icin: on_boya.js, panelin <head>
     betigi ve ekran/tema.js temaKur HER girdide AYNI nitelikleri yazar. */
  const ortam = ({ depo = {}, acik = false, atar = "" } = {}) => {
    const nitelik = {};
    // Sorguya bakan sahte: yanlis sorgu (dark / yazim hatasi) yanlis karar verir.
    const mq = (q) => ({ matches: q === "(prefers-color-scheme: light)" ? acik : q === "(prefers-color-scheme: dark)" ? !acik : false,
      addEventListener() {}, removeEventListener() {} });
    const pencere = {
      get localStorage() {
        if (atar === "erisim") throw new Error("SecurityError");
        return {
          getItem: (k) => { if (atar === "okuma") throw new Error("okuma"); return k in depo ? depo[k] : null; },
          setItem: (k, v) => { depo[k] = String(v); },
        };
      },
      matchMedia: mq,
    };
    const belge = { documentElement: { setAttribute: (k, v) => { nitelik[k] = v; } } };
    return { pencere, belge, nitelik };
  };
  const betikKos = (kaynak, { depo, acik, mm, atar }) => {
    const o = ortam({ depo, acik, atar });
    const ctx = { document: o.belge, JSON };
    Object.defineProperty(ctx, "localStorage", { get: () => o.pencere.localStorage });
    if (mm) ctx.matchMedia = o.pencere.matchMedia;
    ctx.window = ctx;
    try { vm.createContext(ctx); vm.runInContext(kaynak, ctx); } catch (h) { o.nitelik.hata = h.message; }
    return o.nitelik;
  };

  it("on_boya.js == panelin <head> betigi == tema.js (temaOku + temaCoz) her girdide", async () => {
    const TEMA = await import(pathToFileURL(join(PANEL_KOK, "ekran", "tema.js")).href);
    const bas = (PANEL_HTML_METIN.match(/<head>([\s\S]*?)<\/head>/) || [])[1] || "";
    const pcBetik = (bas.match(/<script>([\s\S]*?)<\/script>/) || [])[1] || "";
    expect(pcBetik).toMatch(/data-tema/);
    const telefon = oku("src/on_boya.js");
    const durumlar = [];
    for (const d of [null, '"sistem"', '"koyu"', '"acik"', '"onpanel"', '"mor"', "{bozuk", "42"]) {
      for (const acik of [false, true]) for (const mm of [true, false]) durumlar.push({ d, acik, mm, atar: "" });
    }
    for (const atar of ["erisim", "okuma"]) durumlar.push({ d: '"acik"', acik: true, mm: true, atar });
    const farklar = [];
    for (const { d, acik, mm, atar } of durumlar) {
      const depo = () => (d === null ? {} : { "olcum.tema": d });
      const a = betikKos(telefon, { depo: depo(), acik, mm, atar });
      const b = betikKos(pcBetik, { depo: depo(), acik, mm, atar });
      const o = ortam({ depo: depo(), acik, atar });
      if (!mm) delete o.pencere.matchMedia;
      TEMA.temaKur({ pencere: o.pencere, belge: o.belge });
      // Karar fonksiyonu da dogrudan: temaCoz(temaOku(...)).
      const secim = TEMA.temaOku(ortam({ depo: depo(), atar }).pencere);
      const karar = { "data-tema": TEMA.temaCoz(secim, mm && acik), "data-tema-secim": secim };
      for (const [ad, x] of [["pc", b], ["tema.js", o.nitelik], ["temaCoz", karar]]) {
        if (JSON.stringify(a) !== JSON.stringify(x)) farklar.push(`${d}/${acik}/${mm}/${atar}: telefon ${JSON.stringify(a)} ${ad} ${JSON.stringify(x)}`);
      }
    }
    expect(farklar).toEqual([]);
    expect(durumlar.length).toBe(34);
  });
});

describe("acilis bekcisi (src/acilis_bekci.js)", () => {
  function sahneKur() {
    const dinleyiciler = {};
    const zamanlayicilar = [];
    const dugme = { dinle: null, addEventListener: (t, f) => { if (t === "click") dugme.dinle = f; } };
    const kutu = { hidden: true, querySelector: (s) => (s === "[data-yenile]" ? dugme : null) };
    const neden = { textContent: "" };
    const uyg = { cloak: true, hasAttribute: (a) => a === "v-cloak" && uyg.cloak };
    const yenilendi = { n: 0 };
    const belge = {
      getElementById: (id) => ({ acilmadi: kutu, "acilmadi-neden": neden, uyg })[id] || null,
      addEventListener: (t, f, yakala) => { (dinleyiciler[t] ||= []).push({ f, yakala }); },
    };
    const ctx = {
      document: belge,
      location: { reload: () => { yenilendi.n++; } },
      setTimeout: (f, ms) => zamanlayicilar.push({ f, ms }),
    };
    vm.createContext(ctx);
    vm.runInContext(oku("src/acilis_bekci.js"), ctx);
    return { ctx, belge, dinleyiciler, zamanlayicilar, dugme, kutu, neden, uyg, yenilendi };
  }

  it("Yenile dugmesi dinleyiciyle; betik hatasi (yakalama asamasi) kutuyu acar; 6 sn bekcisi", () => {
    const s = sahneKur();
    s.dugme.dinle();
    expect(s.yenilendi.n).toBe(1);
    expect(s.dinleyiciler.error).toHaveLength(1);
    expect(s.dinleyiciler.error[0].yakala).toBe(true);
    s.dinleyiciler.error[0].f({ target: { tagName: "IMG", src: "x.png" } });
    expect(s.kutu.hidden).toBe(true);
    s.dinleyiciler.error[0].f({ target: { tagName: "SCRIPT", src: "https://localhost/assets/index-abc.js" } });
    expect(s.kutu.hidden).toBe(false);
    expect(s.neden.textContent).toBe("index-abc.js yüklenemedi.");
    // Zaman asimi: Vue mount edemediyse.
    const t = sahneKur();
    expect(t.zamanlayicilar.map((z) => z.ms)).toEqual([6000]);
    t.uyg.cloak = false;
    t.zamanlayicilar[0].f();
    expect(t.kutu.hidden).toBe(true);
    t.uyg.cloak = true;
    t.zamanlayicilar[0].f();
    expect(t.kutu.hidden).toBe(false);
    expect(t.neden.textContent).toMatch(/Vue yok/);
    // giris.js'in kullandigi olay (belgede).
    expect(t.dinleyiciler["arayuz-hata"]).toHaveLength(1);
    t.dinleyiciler["arayuz-hata"][0].f({ detail: "app.js (x)" });
    expect(t.neden.textContent).toBe("app.js (x) yüklenemedi.");
  });
});

describe("vite build (gecici dizin)", () => {
  let cikti;
  let html;
  let jsDosyalar;

  beforeAll(async () => {
    cikti = mkdtempSync(join(tmpdir(), "olcum-panel-paket-"));
    const { build } = await import("vite");
    // vitest NODE_ENV=test koyar; vite onu pakete yazar ve Vue'nun gelistirme dallari kalirdi. Gercek
    // derleme (`npm run build`) gibi uretim kipinde paketle.
    const onceki = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";
    try {
      await build({
        configFile: join(KOK, "vite.config.js"), root: KOK, logLevel: "silent", mode: "production",
        build: { outDir: cikti, emptyOutDir: true },
      });
    } finally {
      process.env.NODE_ENV = onceki;
    }
    html = readFileSync(join(cikti, "index.html"), "utf8");
    const topla = (d) => readdirSync(d).flatMap((a) => (statSync(join(d, a)).isDirectory() ? topla(join(d, a)) : [join(d, a)]));
    jsDosyalar = topla(cikti).filter((y) => y.endsWith(".js"));
  }, 120000);

  afterAll(() => { if (cikti) rmSync(cikti, { recursive: true, force: true }); });

  it("paketin hicbir JS'inde new Function / Function( / eval( / runtime derleyici yok", () => {
    expect(jsDosyalar.length).toBeGreaterThan(5);
    const bulgular = [];
    for (const y of jsDosyalar) {
      const k = readFileSync(y, "utf8");
      for (const [ad, d] of [["Function(", /(?<![\w$])Function\s*\(/], ["eval(", /(?<![\w$])eval\s*\(/],
        ["compileToFunction", /compileToFunction/], ["runtime-derleme uyarisi", /Runtime compilation is not supported/]]) {
        if (d.test(k)) bulgular.push(`${relative(cikti, y)}: ${ad}`);
      }
    }
    expect(bulgular).toEqual([]);
  });

  it("pakette derlenmemis template: kalmadi; kok render ve ekran render'lari var", () => {
    const hepsi = jsDosyalar.map((y) => readFileSync(y, "utf8")).join("\n");
    expect(hepsi).not.toMatch(/\btemplate\s*:/);
    // Kok sablondan bir parca (sozluk anahtari degil, sablonun kendi sinifi) pakette.
    expect(hepsi).toContain("cekmece-acik");
    expect(hepsi).toContain("kayitlar-ekran");
  });

  it("index.html: CSP AYNEN, tema betigi stilden ONCE, satir ici betik / olay ozniteligi yok", () => {
    const csp = (m) => /http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(m)[1];
    expect(csp(html)).toBe(csp(oku("index.html")));
    expect(html.indexOf('<script src="./on_boya.js"></script>')).toBeGreaterThan(html.indexOf("Content-Security-Policy"));
    expect(html.indexOf('<script src="./on_boya.js"></script>')).toBeLessThan(html.indexOf('rel="stylesheet"'));
    expect(html).toContain('<script src="./acilis_bekci.js"></script>');
    expect(html).not.toMatch(/<!-- panel:/);
    for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
      expect(m[1], m[0]).toMatch(/\bsrc=/);
      expect(m[2].trim(), m[0]).toBe("");
    }
    expect(html).not.toMatch(/\son[a-z]+\s*=/i);
    expect(html.indexOf('<div id="uyg" v-cloak></div>')).toBeLessThan(html.indexOf('<div id="acilmadi"'));
    expect(html.indexOf('<div id="acilmadi"')).toBeLessThan(html.indexOf('<script src="./acilis_bekci.js">'));
    expect(html).toContain(acilmadiKutusu(PANEL_HTML_METIN));
  });

  it("klasik betikler pakette kaynaklariyla AYNI", () => {
    for (const ad of ["on_boya.js", "acilis_bekci.js"]) {
      expect(readFileSync(join(cikti, ad), "utf8"), ad).toBe(oku(`src/${ad}`));
    }
  });
});
