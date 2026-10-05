// 5F — erisilebilirlik gecisi (A44 ortak sartlar): BUTUN ekranlar icin kaynak uzerinden denetim. Tek tek
// ekranlarin kendi testleri var; bu dosya kuralin HER .vue dosyasinda tuttugunu olcer — yeni ekran eklenince
// kural kendiliginden ona da uygulanir. (Kontrast ve dokunma boyutu: test/kabuk.test.js.)
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { tercihUygula } from "../src/ekran/tercih.js";

const KOK = fileURLToPath(new URL("../src", import.meta.url));
function agac(dizin) {
  return readdirSync(dizin).flatMap((ad) => {
    const yol = join(dizin, ad);
    return statSync(yol).isDirectory() ? agac(yol) : yol.endsWith(".vue") ? [yol] : [];
  });
}
const DOSYALAR = agac(KOK).map((yol) => ({ ad: yol.slice(KOK.length + 1).replace(/\\/g, "/"), kaynak: readFileSync(yol, "utf8") }));
const sablon = (k) => { const a = k.indexOf("<template>"); return a < 0 ? "" : k.slice(a, k.lastIndexOf("</template>")); };
const CSS = readFileSync(join(KOK, "tema.css"), "utf8");
// Acilis etiketleri (cok satirli olabilir) + hemen ardindan gelen icerik.
const etiketler = (s, ad) => [...s.matchAll(new RegExp(`<${ad}\\b([^>]*)>([^]*?)</${ad}>`, "g"))].map((m) => ({ oz: m[1], ic: m[2], tam: m[0] }));

describe("erisilebilirlik: her ekranda", () => {
  it("en az 15 .vue dosyasi taraniyor", () => {
    expect(DOSYALAR.length).toBeGreaterThanOrEqual(15);
  });

  it("her dugme type=\"button\" ve ADI var (gorunen metin ya da aria-label / aria-labelledby)", () => {
    let sayi = 0;
    for (const { ad, kaynak } of DOSYALAR) {
      for (const d of etiketler(sablon(kaynak), "button")) {
        sayi += 1;
        expect(d.oz, `${ad}: ${d.tam.slice(0, 80)}`).toMatch(/\btype="button"/);
        const adi = /\{\{[^}]+\}\}/.test(d.ic) || /(:|\b)aria-label(ledby)?=/.test(d.oz);
        expect(adi, `${ad}: adsiz dugme ${d.tam.slice(0, 80)}`).toBe(true);
      }
    }
    expect(sayi).toBeGreaterThanOrEqual(25);
  });

  it("anahtar (switch) ve secenek (radio) durumunu bildirir; secenek grubu adlandirilmis", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      const s = sablon(kaynak);
      for (const m of s.matchAll(/<[a-z]+\b[^>]*role="(switch|radio)"[^>]*>/g)) expect(m[0], ad).toMatch(/:aria-checked=/);
      const radyo = (s.match(/role="radio"/g) || []).length;
      const grup = [...s.matchAll(/<[a-z]+\b[^>]*role="radiogroup"[^>]*>/g)];
      if (radyo > 0) expect(grup.length, `${ad}: radio var, radiogroup yok`).toBeGreaterThan(0);
      for (const g of grup) expect(g[0], ad).toMatch(/:aria-label=/);
    }
  });

  it("tuval (grafik) resim rolunde ve etiketli; giris alanlari etiketli", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      const s = sablon(kaynak);
      for (const m of s.matchAll(/<canvas\b[^>]*>/g)) {
        expect(m[0], ad).toMatch(/role="img"/);
        expect(m[0], ad).toMatch(/:aria-label=/);
      }
      for (const m of s.matchAll(/<(input|textarea|select)\b[^>]*>/g)) {
        const kimlik = /\bid="([^"]+)"/.exec(m[0]);
        const etiketli = /(:|\b)aria-label(ledby)?=/.test(m[0]) || (kimlik && new RegExp(`<label\\b[^>]*for="${kimlik[1]}"`).test(s));
        expect(Boolean(etiketli), `${ad}: etiketsiz giris ${m[0].slice(0, 80)}`).toBe(true);
      }
    }
  });

  it("hata satirlari ekran okuyucuya DUYURULUR (role=alert); durum satirlari role=status", () => {
    for (const { ad, kaynak } of DOSYALAR) {
      for (const m of sablon(kaynak).matchAll(/<p\b[^>]*class="bilgi hata"[^>]*>/g)) expect(m[0], ad).toMatch(/role="alert"/);
    }
  });

  it("simge tek basina anlam tasimaz: Ikon ekran okuyucudan gizli", () => {
    const ikon = DOSYALAR.find((d) => d.ad === "bilesen/Ikon.vue").kaynak;
    expect(ikon).toMatch(/<svg[^>]*aria-hidden="true"/);
  });

  it("katman acan bilesen yok (ACIL DURDUR seridi hicbir ekranda ortulmez)", () => {
    for (const { ad, kaynak } of DOSYALAR) expect(sablon(kaynak), ad).not.toMatch(/<dialog\b|ion-modal|ion-alert|ion-popover|ion-action-sheet/);
  });
});

describe("erisilebilirlik: tema", () => {
  it("yazi boyutlari rem (sistem yazi boyutuna uyar): px ile yazi boyutu YOK", () => {
    const yorumsuz = CSS.replace(/\/\*[^]*?\*\//g, "");
    expect(yorumsuz.match(/font-size:\s*[0-9.]+px/g) || []).toEqual([]);
    expect(yorumsuz.match(/font:\s*[^;]*\b[0-9.]+px\b[^;]*;/g) || []).toEqual([]);
    // En kucuk yazi 12 px esdegeri (.75rem) altina inmez.
    const boylar = [...yorumsuz.matchAll(/font(?:-size)?:\s*[^;]*?(\d*\.?\d+)rem/g)].map((m) => Number(m[1]));
    expect(boylar.length).toBeGreaterThan(10);
    expect(Math.min(...boylar)).toBeGreaterThanOrEqual(0.75);
  });

  it("klavye / anahtar erisimi: odak gorunur (:focus-visible), cerceve kaldirilmaz", () => {
    expect(CSS).toMatch(/:focus-visible\s*\{[^}]*outline:\s*[^n;][^;]*;/);
    expect(CSS.replace(/:focus-visible\s*\{[^}]*\}/g, "")).not.toMatch(/outline:\s*(none|0)\b/);
  });

  it("hareket azaltma tercihi: gecis / canlandirma varsa prefers-reduced-motion ile kapatilir", () => {
    if (/\b(transition|animation)\s*:/.test(CSS)) expect(CSS).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });

  it("belgenin dili secilen dile esit (ekran okuyucu dogru sesle okur)", () => {
    const oz = {};
    const belge = { documentElement: { setAttribute: (a, d) => { oz[a] = d; }, removeAttribute: (a) => { delete oz[a]; } } };
    tercihUygula(belge, { dil: "en", tema: "sistem" });
    expect(oz.lang).toBe("en");
    tercihUygula(belge, { dil: "tr", tema: "koyu" });
    expect(oz.lang).toBe("tr");
  });
});
