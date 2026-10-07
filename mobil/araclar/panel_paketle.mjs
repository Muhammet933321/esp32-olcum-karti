// panel_paketle.mjs — 5P P1: PC panelini (arayuz3/) TELEFON paketine sokan vite eklentisi.
//
// NEDEN (spec 2026-10-07-5p K1/K2): uygulamanin CSP'si `script-src 'self'` — `unsafe-eval` YOK. Panel
// ise Vue'nun TAM surumuyle calisiyor: kok sablonu (#uyg) sayfanin DOM'unda, ekranlarin sablonlari
// `template:` dizgileri; ikisi de calisma aninda `new Function` ile derleniyor ve CSP bunu engeller.
// Bu eklenti derlemeyi DERLEME ANINA alir:
//   1. arayuz3/index.html'den #uyg'nin ICI (Vue'nun mount'ta okudugu innerHTML) ayiklanir,
//      @vue/compiler-dom ile render islevine derlenir -> sanal modul `virtual:panel-kok`.
//   2. arayuz3/app.js'teki TEK `createApp({ ... })` -> `createApp({ render: __kokRender, ... })`.
//   3. arayuz3/**/*.js icindeki her `template:` ozelligi (duz dizgi ya da ayni dosyadaki duz dizgili
//      `const`) -> `render: __panelSablonN` (her biri kendi sanal modulu). Donusumden sonra bir
//      `template:` KALIRSA derleme HATA verir: runtime Vue'da derlenmemis sablon uretim kipinde
//      SESSIZCE bos cizilir — yeni bir ekran telefonda bos acilmasin.
//   4. index.html'in yer tutuculari doldurulur: #acilmadi kutusu arayuz3'ten (onclick'siz), tema on
//      boyamasi (src/on_boya.js) ve acilis bekcisi (src/acilis_bekci.js) DIS klasik betik olarak.
// arayuz3/ DEGISMEZ (PC'de kartin sundugu tek dosya, B27 A2); donusum yalniz paketteki kopyadadir.
import { readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, resolve, sep } from "node:path";
import MagicString from "magic-string";
import { parseAst } from "vite";

const BURASI = dirname(fileURLToPath(import.meta.url));
export const MOBIL_KOK = resolve(BURASI, "..");
export const PANEL_KOK = resolve(MOBIL_KOK, "..", "arayuz3");
export const PANEL_HTML = join(PANEL_KOK, "index.html");

// Derleyici, uygulamanin calistirdigi `vue` ile AYNI surumden (vue'nun kendi bagimliligi) alinir.
const vueIste = createRequire(createRequire(import.meta.url).resolve("vue/package.json"));
const derleyici = vueIste("@vue/compiler-dom");
export const VUE_SURUM = vueIste("./package.json").version;
export const DERLEYICI_SURUM = vueIste("@vue/compiler-dom/package.json").version;

export const KOK_MODUL = "virtual:panel-kok";
const SABLON_ONEK = "virtual:panel-sablon/";
const IC_ONEK = "\0";

/* Derleme secenekleri. `comments: false` panelin vendor surumunun uretim varsayilani (yorumlar vnode
   olmaz); oteki varsayilanlar (whitespace 'condense', delimiters) her iki tarafta ayni. */
export const DERLEME_SECENEK = Object.freeze({
  mode: "module", prefixIdentifiers: true, hoistStatic: true, cacheHandlers: true, comments: false,
});

/** Sablonu ES modulune derler (`export function render`). Derleme hatasi -> istisna (yerli). */
export function sablonDerle(sablon, ad = "sablon") {
  const uyarilar = [];
  const { code } = derleyici.compile(sablon, {
    ...DERLEME_SECENEK,
    onError(h) {
      const yer = h.loc ? ` (satir ${h.loc.start.line}, sutun ${h.loc.start.column})` : "";
      throw new Error(`panel_paketle: ${ad} sablonu derlenemedi: ${h.message}${yer}`);
    },
    onWarn(u) { uyarilar.push(u.message); },
  });
  return { kod: code, uyarilar };
}

// ─── 1. kok sablonu ─────────────────────────────────────────────────────────────────────────────

const KOK_ACILIS = /<div\s+id="uyg"(\s+v-cloak)?\s*>/g;

/** `<div id="uyg" v-cloak>` ... eslesen `</div>` arasini (tarayicinin innerHTML'i) verir.
    Div derinligi sayilir, yorumlar atlanir; sonuc ayrica #acilmadi kutusuna kadar yalniz bosluk/yorum
    kalmasiyla dogrulanir (yanlis kapanis = hata, sessiz kesik sablon yok). */
export function kokSablonuAyikla(html) {
  const acilislar = [...html.matchAll(KOK_ACILIS)];
  if (acilislar.length !== 1) throw new Error(`panel_paketle: #uyg acilisi ${acilislar.length} kez bulundu (1 olmali)`);
  const bas = acilislar[0].index + acilislar[0][0].length;
  const ETIKET = /<!--[\s\S]*?-->|<div\b[^>]*>|<\/div\s*>/gi;
  ETIKET.lastIndex = bas;
  let derinlik = 1;
  let m;
  while ((m = ETIKET.exec(html))) {
    if (m[0].startsWith("<!--")) continue;
    if (m[0].startsWith("</")) derinlik--;
    else derinlik++;
    if (derinlik === 0) break;
  }
  if (!m || derinlik !== 0) throw new Error("panel_paketle: #uyg'nin kapanisi bulunamadi");
  const son = m.index;
  const kalan = html.slice(son + m[0].length);
  const kutu = kalan.indexOf('<div id="acilmadi"');
  if (kutu < 0 || kalan.slice(0, kutu).replace(/<!--[\s\S]*?-->/g, "").trim() !== "") {
    throw new Error("panel_paketle: #uyg kapanisindan sonra #acilmadi'dan once beklenmeyen icerik (kapanis yanlis eslesti?)");
  }
  return { sablon: html.slice(bas, son), bas, son };
}

// ─── 4. #acilmadi kutusu ────────────────────────────────────────────────────────────────────────

const YENILE_ONCLICK = ' onclick="location.reload()"';

/** arayuz3'un #acilmadi kutusu; satir ici `onclick` CSP'de calismaz -> `data-yenile` (bekci dinler).
    Baska bir `on…=` ozniteligi kalirsa HATA (sessizce olu dugme olmasin). */
export function acilmadiKutusu(html) {
  const bas = html.indexOf('<div id="acilmadi"');
  if (bas < 0 || html.indexOf('<div id="acilmadi"', bas + 1) >= 0) throw new Error("panel_paketle: #acilmadi kutusu tek degil");
  const ETIKET = /<div\b[^>]*>|<\/div\s*>/gi;
  ETIKET.lastIndex = bas;
  let derinlik = 0;
  let m;
  while ((m = ETIKET.exec(html))) {
    derinlik += m[0].startsWith("</") ? -1 : 1;
    if (derinlik === 0) break;
  }
  if (!m) throw new Error("panel_paketle: #acilmadi kapanisi yok");
  let kutu = html.slice(bas, m.index + m[0].length);
  if (kutu.split(YENILE_ONCLICK).length !== 2) throw new Error("panel_paketle: #acilmadi'da beklenen onclick yok");
  kutu = kutu.replace(YENILE_ONCLICK, " data-yenile");
  if (/\son[a-z]+\s*=/i.test(kutu)) throw new Error("panel_paketle: #acilmadi'da satir ici olay ozniteligi kaldi");
  return kutu;
}

// ─── 2 + 3. JS donusumu ─────────────────────────────────────────────────────────────────────────

function dizgiDegeri(dugum) {
  if (!dugum) return null;
  if (dugum.type === "Literal" && typeof dugum.value === "string") return dugum.value;
  if (dugum.type === "TemplateLiteral" && dugum.expressions.length === 0) return dugum.quasis[0].value.cooked;
  return null;
}

function ozellikAdi(o) {
  if (o.type !== "Property" || o.computed) return null;
  if (o.key.type === "Identifier") return o.key.name;
  if (o.key.type === "Literal") return String(o.key.value);
  return null;
}

/* Bagimsiz kucuk yuruyucu (estree): her dugumu ziyaret eder. */
function yuru(dugum, ziyaret) {
  if (!dugum || typeof dugum.type !== "string") return;
  ziyaret(dugum);
  for (const anahtar of Object.keys(dugum)) {
    if (anahtar === "parent") continue;
    const d = dugum[anahtar];
    if (Array.isArray(d)) { for (const c of d) if (c && typeof c.type === "string") yuru(c, ziyaret); }
    else if (d && typeof d.type === "string") yuru(d, ziyaret);
  }
}

/** Dosyanin `template:` ozelliklerini bulur (donusturmeden). Donus: [{dugum, sablon|null, neden}] */
export function sablonOzellikleri(kod, ast = parseAst(kod)) {
  const sabitler = new Map();     // ad -> [init dugumu]
  for (const d of ast.body) {
    const bildirim = d.type === "ExportNamedDeclaration" ? d.declaration : d;
    if (bildirim?.type !== "VariableDeclaration") continue;
    for (const b of bildirim.declarations) {
      if (b.id.type !== "Identifier") continue;
      if (!sabitler.has(b.id.name)) sabitler.set(b.id.name, []);
      sabitler.get(b.id.name).push({ tur: bildirim.kind, init: b.init });
    }
  }
  const bulunan = [];
  yuru(ast, (d) => {
    if (d.type !== "Property" || ozellikAdi(d) !== "template") return;
    let sablon = dizgiDegeri(d.value);
    let neden = sablon === null ? "deger duz dizgi degil" : null;
    if (sablon === null && d.value.type === "Identifier") {
      const tanim = sabitler.get(d.value.name) || [];
      if (tanim.length === 1 && tanim[0].tur === "const") {
        sablon = dizgiDegeri(tanim[0].init);
        neden = sablon === null ? `${d.value.name} duz dizgili bir const degil` : null;
      } else neden = `${d.value.name} dosyada tek bir const olarak tanimli degil`;
    }
    bulunan.push({ dugum: d, sablon, neden });
  });
  return bulunan;
}

/** `createApp({` cagrilarini bulur (ilk argumani nesne olanlar). */
export function createAppCagrilari(kod, ast = parseAst(kod)) {
  const c = [];
  yuru(ast, (d) => {
    if (d.type === "CallExpression" && d.callee.type === "Identifier" && d.callee.name === "createApp") c.push(d);
  });
  return c;
}

/**
 * Bir panel modulunu donusturur. `kok`: app.js mi (render enjekte edilir).
 * Donus: { kod, harita, sablonlar: [{kimlik, sablon}] } — kimlik sanal modulun adi.
 * Derlenemeyen `template:` ya da createApp sayisi 1 degil -> istisna.
 */
export function jsDonustur(kod, dosyaAdi, { kok = false } = {}) {
  const ast = parseAst(kod);
  const s = new MagicString(kod);
  const sablonlar = [];
  const ithal = [];
  const ozellikler = sablonOzellikleri(kod, ast);
  const derlenemeyen = ozellikler.filter((o) => o.sablon === null);
  if (derlenemeyen.length) {
    const satir = (i) => kod.slice(0, i).split("\n").length;
    throw new Error(`panel_paketle: ${dosyaAdi}: derlenemeyen template: ` +
      derlenemeyen.map((o) => `satir ${satir(o.dugum.start)} (${o.neden})`).join(", ") +
      " — telefon paketinde runtime derleyici YOK; sablonu duz dizgi yap");
  }
  ozellikler.forEach((o, i) => {
    const yerel = `__panelSablon${i}`;
    const kimlik = `${SABLON_ONEK}${dosyaAdi}/${i}`;
    s.overwrite(o.dugum.start, o.dugum.end, `render: ${yerel}`);
    ithal.push(`import { render as ${yerel} } from ${JSON.stringify(kimlik)};`);
    sablonlar.push({ kimlik, sablon: o.sablon });
  });
  if (kok) {
    const cagri = createAppCagrilari(kod, ast);
    if (cagri.length !== 1) throw new Error(`panel_paketle: ${dosyaAdi}: createApp ${cagri.length} kez (1 olmali)`);
    const arg = cagri[0].arguments[0];
    if (!arg || arg.type !== "ObjectExpression") throw new Error(`panel_paketle: ${dosyaAdi}: createApp'in argumani nesne degil`);
    if (arg.properties.some((p) => ["render", "template"].includes(ozellikAdi(p)))) {
      throw new Error(`panel_paketle: ${dosyaAdi}: kok bilesende zaten render/template var`);
    }
    s.appendLeft(arg.start + 1, " render: __kokRender,");
    ithal.push(`import { render as __kokRender } from ${JSON.stringify(KOK_MODUL)};`);
  }
  // Ithal satirlari en basa (ES ithalleri zaten yukari tasinir; satir numaralari harita ile korunur).
  if (ithal.length) s.prepend(ithal.join(" ") + "\n");
  const yeni = s.toString();
  // Guvence: donusmus kodda HIC template ozelligi kalmadi.
  const kalan = sablonOzellikleri(yeni);
  if (kalan.length) throw new Error(`panel_paketle: ${dosyaAdi}: donusumden sonra ${kalan.length} template: kaldi`);
  return { kod: yeni, harita: s.generateMap({ hires: true, source: dosyaAdi, includeContent: true }), sablonlar };
}

// ─── DOM sablonu tuzaklari (bilgi) ──────────────────────────────────────────────────────────────

const BOS_ETIKETLER = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);

/** Tarayicinin ayristirmasiyla derleyicinin ayristirmasinin AYRILABILECEGI yerler (in-DOM sablon):
    (a) baglama/yonerge ozniteliginde buyuk harf (tarayici kucultur: `:viewBox` -> `:viewbox`),
    (b) svg/math disinda kendinden kapanan bos-olmayan etiket (tarayici acik sayar).
    Bos liste = iki ayristirma bu acilardan ayni. Kesin karsilastirma basliksiz tarayici testinde. */
export function domSablonTuzaklari(sablon) {
  const bulgular = [];
  const temiz = sablon.replace(/<!--[\s\S]*?-->/g, (y) => y.replace(/[^\n]/g, " "));
  const ETIKET = /<(\/?)([a-zA-Z][\w-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?)*)\s*(\/?)>/g;
  const yabanci = [];
  let m;
  while ((m = ETIKET.exec(temiz))) {
    const [, kapanis, ad, oz, kendinden] = m;
    const kucuk = ad.toLowerCase();
    const satir = temiz.slice(0, m.index).split("\n").length;
    if (kapanis) {
      if (yabanci.length && yabanci[yabanci.length - 1] === kucuk) yabanci.pop();
      continue;
    }
    // svg/math'in kendisi ve ici yabanci icerik: tarayici duz SVG adlarini (viewBox) duzeltir.
    const icYabanci = yabanci.length > 0 || kucuk === "svg" || kucuk === "math";
    for (const o of oz.matchAll(/\s+([^\s"'>\/=]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?/g)) {
      const n = o[1];
      if (/^(?::|@|#|v-)/.test(n) && /[A-Z]/.test(n)) bulgular.push({ tur: "buyuk-harf", satir, ad, oznitelik: n });
      else if (/[A-Z]/.test(n) && !icYabanci) bulgular.push({ tur: "buyuk-harf", satir, ad, oznitelik: n });
    }
    if (kendinden) {
      if (!yabanci.length && !BOS_ETIKETLER.has(kucuk)) bulgular.push({ tur: "kendinden-kapanan", satir, ad });
    } else if (kucuk === "svg" || kucuk === "math" || yabanci.length) {
      yabanci.push(kucuk);
    }
  }
  return bulgular;
}

// ─── vite eklentisi ─────────────────────────────────────────────────────────────────────────────

/* Panel kokunun iki yazimi: verilen yol ve gercek yol. Mutasyon kosucusunun kopyasinda arayuz3/ bir
   BAGLANTI (junction); vite modul kimligini gercek yola cozer. */
function panelKokleri() {
  const k = [PANEL_KOK];
  try { const g = realpathSync(PANEL_KOK); if (g !== PANEL_KOK) k.push(g); } catch { /* yok */ }
  return k;
}

/** Panel dosyasiysa arayuz3/'e gore goreli adi ('app.js', 'ekran/x.js'), degilse null. */
export function panelGoreliAd(id, kokler = panelKokleri()) {
  const yol = id.split("?")[0];
  if (!yol.endsWith(".js")) return null;
  for (const kok of kokler) {
    const r = relative(kok, yol);
    if (r && !r.startsWith("..") && !r.includes(":")) return r.split(sep).join("/");
  }
  return null;
}

const BETIKLER = Object.freeze({ "on_boya.js": "src/on_boya.js", "acilis_bekci.js": "src/acilis_bekci.js" });

const tut = (ad) => `<!-- panel:${ad} -->`;

function tekYerTutucu(html, ad) {
  if (html.split(tut(ad)).length !== 2) throw new Error(`panel_paketle: index.html'de ${tut(ad)} tam bir kez olmali`);
}

/** index.html yer tutuculari: `<!-- panel:acilmadi -->` (kutu), `<!-- panel:on-boya -->` ve
    `<!-- panel:bekci -->` (klasik betikler). `betikYolu` null ise betik yer tutuculari kalir. */
export function kabukDoldur(html, { panelHtml, betikYolu = null }) {
  tekYerTutucu(html, "acilmadi");
  let sonuc = html.replace(tut("acilmadi"), acilmadiKutusu(panelHtml));
  if (betikYolu) sonuc = betikleriYerlestir(sonuc, betikYolu);
  return sonuc;
}

export function betikleriYerlestir(html, betikYolu) {
  tekYerTutucu(html, "on-boya");
  tekYerTutucu(html, "bekci");
  return html
    .replace(tut("on-boya"), `<script src="${betikYolu("on_boya.js")}"></script>`)
    .replace(tut("bekci"), `<script src="${betikYolu("acilis_bekci.js")}"></script>`);
}

/* Klasik betik etiketleri derlemede vite'in HTML isleminden SONRA konur ("post"): vite modul olmayan
   `<script src>`'yi paketleyemez (uyari verir); dosyalar generateBundle'da oldugu gibi kopyalanir. */
function betikEklentisi(durum) {
  return {
    name: "panel-paketle:betikler",
    transformIndexHtml: {
      order: "post",
      handler(html) {
        return betikleriYerlestir(html, (ad) => (durum.derleme ? `./${ad}` : `/${BETIKLER[ad]}`));
      },
    },
    generateBundle() {
      for (const [ad, kaynak] of Object.entries(BETIKLER)) {
        this.emitFile({ type: "asset", fileName: ad, source: readFileSync(join(MOBIL_KOK, kaynak), "utf8") });
      }
    },
  };
}

export default function panelPaketle() {
  const durum = { derleme: false };
  return [anaEklenti(durum), betikEklentisi(durum)];
}

function anaEklenti(durum) {
  const sablonKodlari = new Map();     // sanal kimlik -> sablon metni
  const kokler = panelKokleri();
  return {
    name: "panel-paketle",
    enforce: "pre",
    configResolved(c) { durum.derleme = c.command === "build"; },
    resolveId(id) {
      if (id === KOK_MODUL || id.startsWith(SABLON_ONEK)) return IC_ONEK + id;
      return null;
    },
    load(id) {
      if (!id.startsWith(IC_ONEK)) return null;
      const kimlik = id.slice(IC_ONEK.length);
      if (kimlik === KOK_MODUL) {
        this.addWatchFile(PANEL_HTML);
        const { sablon } = kokSablonuAyikla(readFileSync(PANEL_HTML, "utf8"));
        const { kod, uyarilar } = sablonDerle(sablon, "#uyg (arayuz3/index.html)");
        for (const u of uyarilar) this.warn(`#uyg: ${u}`);
        return kod;
      }
      if (kimlik.startsWith(SABLON_ONEK)) {
        if (!sablonKodlari.has(kimlik)) throw new Error(`panel_paketle: bilinmeyen sablon ${kimlik}`);
        const { kod, uyarilar } = sablonDerle(sablonKodlari.get(kimlik), kimlik);
        for (const u of uyarilar) this.warn(`${kimlik}: ${u}`);
        return kod;
      }
      return null;
    },
    transform(kod, id) {
      const ad = panelGoreliAd(id, kokler);
      if (!ad) return null;
      const sonuc = jsDonustur(kod, ad, { kok: ad === "app.js" });
      for (const { kimlik, sablon } of sonuc.sablonlar) sablonKodlari.set(kimlik, sablon);
      return { code: sonuc.kod, map: sonuc.harita };
    },
    transformIndexHtml: {
      order: "pre",
      handler(html) {
        return kabukDoldur(html, { panelHtml: readFileSync(PANEL_HTML, "utf8") });
      },
    },
  };
}
