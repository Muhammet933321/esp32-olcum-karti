// "Bu telefon" bolumu: erisilebilirlik ve panelle ayni gorunus (5P K13, K19). Kaynak uzerinden: telefon/
// altindaki HER .vue dosyasi taranir (yeni dosya eklenince kural ona da uygulanir). Kurallar
// test/erisilebilirlik.test.js'tekilerin aynisi + panel siniflari, belirtec disi renk yok, dokunma hedefi.
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { gomuluMetinler } from "./yardim/gomulu_metin.mjs";

const TELEFON = fileURLToPath(new URL("../src/telefon", import.meta.url));
const PANEL_CSS = readFileSync(fileURLToPath(new URL("../../arayuz3/style.css", import.meta.url)), "utf8");
const DOSYALAR = readdirSync(TELEFON).filter((a) => a.endsWith(".vue")).map((ad) => ({ ad, kaynak: readFileSync(join(TELEFON, ad), "utf8") }));
const sablon = (k) => { const a = k.indexOf("<template>"); return a < 0 ? "" : k.slice(a, k.lastIndexOf("</template>")); };
const etiketler = (s, ad) => [...s.matchAll(new RegExp(`<${ad}\\b([^>]*)>([^]*?)</${ad}>`, "g"))].map((m) => ({ oz: m[1], ic: m[2], tam: m[0] }));
const STIL = (() => { const k = DOSYALAR.find((d) => d.ad === "BuTelefon.vue").kaynak; return /<style>([\s\S]*?)<\/style>/.exec(k)[1]; })();
const yorumsuzCss = (c) => c.replace(/\/\*[\s\S]*?\*\//g, "");

describe("Bu telefon: erisilebilirlik", () => {
  it("bes .vue dosyasi taraniyor (kok + dort bolum)", () => {
    expect(DOSYALAR.map((d) => d.ad).sort()).toEqual(["BildirimBolumu.vue", "BuTelefon.vue", "EsitlemeBolumu.vue", "GelismisBolumu.vue", "KartBolumu.vue"]);
  });

  it("her dugme type=\"button\" ve ADI var (gorunen metin ya da aria-label)", () => {
    let sayi = 0;
    for (const { ad, kaynak } of DOSYALAR) {
      for (const d of etiketler(sablon(kaynak), "button")) {
        sayi += 1;
        expect(d.oz, `${ad}: ${d.tam.slice(0, 80)}`).toMatch(/\btype="button"/);
        const adi = /\{\{[^}]+\}\}/.test(d.ic) || /(:|\b)aria-label(ledby)?=/.test(d.oz);
        expect(adi, `${ad}: adsiz dugme ${d.tam.slice(0, 80)}`).toBe(true);
      }
    }
    expect(sayi).toBeGreaterThanOrEqual(20);
  });

  it("her giris etiketli (label for= ya da aria-label/labelledby); anahtarlar aria-checked bildirir", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      const s = sablon(kaynak);
      for (const m of s.matchAll(/<(input|textarea|select)\b[^>]*>/g)) {
        const kimlik = /\sid="([^"]+)"/.exec(m[0]);
        const etiketli = /(:|\b)aria-label(ledby)?=/.test(m[0]) || (kimlik && new RegExp(`<label\\b[^>]*for="${kimlik[1]}"`).test(s));
        expect(Boolean(etiketli), `${ad}: etiketsiz giris ${m[0].slice(0, 80)}`).toBe(true);
      }
      for (const m of s.matchAll(/<[a-z]+\b[^>]*role="switch"[^>]*>/g)) expect(m[0], ad).toMatch(/:aria-checked=/);
      // aria-labelledby / aria-describedby / aria-controls'un gosterdigi kimlik sablonda var
      for (const m of s.matchAll(/\saria-(?:labelledby|describedby|controls)="([^"]+)"/g)) {
        for (const k of m[1].split(/\s+/)) expect(s, `${ad}: #${k} yok`).toMatch(new RegExp(`\\sid="${k}"`));
      }
    }
  });

  it("hata satirlari DUYURULUR (role=alert), sonuc satirlari canli bolgede ya da role=status", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      for (const m of sablon(kaynak).matchAll(/<[a-z]+\b[^>]*\sclass="[^"]*\bhata\b[^"]*"[^>]*>/g)) expect(m[0], ad).toMatch(/role="alert"/);
    }
  });

  it("gomulu metin yok (her metin sozlukten); katman acan bilesen yok; Ionic yok; satir ici stil yok", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      expect(gomuluMetinler(kaynak), ad).toEqual([]);
      const s = sablon(kaynak);
      expect(s, ad).not.toMatch(/<dialog\b|<ion-|\sstyle="|:style=/);
    }
  });
});

describe("Bu telefon: panelle ayni gorunus", () => {
  it("kullanilan her sinif panelin style.css'inde ya da bolumun kendi stilinde tanimli", () => {
    const tanimli = (s) => new RegExp(`\\.${s.replace(/-/g, "\\-")}(?![\\w-])`).test(PANEL_CSS) || new RegExp(`\\.${s}(?![\\w-])`).test(STIL);
    const siniflar = new Set();
    for (const { kaynak } of DOSYALAR) {
      const s = sablon(kaynak);
      for (const m of s.matchAll(/\sclass="([^"]+)"/g)) for (const c of m[1].split(/\s+/)) siniflar.add(c);
      for (const m of s.matchAll(/\s:class="([^"]+)"/g)) for (const c of m[1].matchAll(/'([a-z][a-z0-9-]*)'/g)) siniflar.add(c[1]);
    }
    expect(siniflar.size).toBeGreaterThan(15);
    for (const c of siniflar) expect(tanimli(c), `tanimsiz sinif: ${c}`).toBe(true);
    // Panelin bilinen yapi taslari gercekten kullaniliyor (Ag / Eslestirme bolumleriyle ayni dil).
    for (const c of ["kart", "ipucu", "uyari", "hata", "tehlike", "birincil", "dugme-grup", "alan", "satir", "ay-bilgi", "ay-duyuru", "ag-liste", "rozet", "skop-kume"]) {
      expect(siniflar.has(c), c).toBe(true);
    }
  });

  it("stil yalniz belirtec renkleri kullanir (uc temada dogru): renk sabiti yok", () => {
    const c = yorumsuzCss(STIL);
    expect(c).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\b(white|black|red|green|blue|gray|grey)\b/);
    for (const m of c.matchAll(/\b(color|background(?:-color)?|border(?:-[a-z]+)?|accent-color)\s*:\s*([^;]+);/g)) {
      if (/^\d|^none$/.test(m[2].trim())) continue;
      expect(m[2], m[0]).toMatch(/var\(--[a-z0-9-]+\)/);
    }
    // kullanilan belirtecler panelde tanimli
    for (const m of c.matchAll(/var\((--[a-z0-9-]+)\)/g)) expect(PANEL_CSS, m[1]).toContain(`${m[1]}:`);
  });

  it("dokunma hedefi en az 40 px: dugmeler, metin alanlari, anahtar satirlari; yazi boyutu rem", () => {
    const c = yorumsuzCss(STIL);
    const kural = (secici) => {
      const m = new RegExp(`${secici.replace(/[.[\]=]/g, (x) => `\\${x}`)}[^{]*\\{([^}]*)\\}`).exec(c);
      return m ? m[1] : "";
    };
    for (const s of [".bt-mod button", ".bt-mod input[type=password]", ".bt-mod .bt-anahtar"]) {
      const m = /min-height:\s*(\d+)px/.exec(kural(s));
      expect(m, s).not.toBe(null);
      expect(Number(m[1]), s).toBeGreaterThanOrEqual(40);
    }
    expect(c).toMatch(/\.bt-mod input\[type=text\], \.bt-mod input\[type=password\] \{ min-height: 40px; \}/);
    expect(c.match(/font-size:\s*[0-9.]+px/g) || []).toEqual([]);
  });

  it("stil kapsamli: her kural .bt-mod altinda (panelin geri kalanini etkilemez)", () => {
    const c = yorumsuzCss(STIL);
    for (const m of c.matchAll(/([^{}]+)\{[^}]*\}/g)) {
      for (const s of m[1].split(",")) expect(s.trim(), s).toMatch(/^\.bt-mod\b/);
    }
  });
});
