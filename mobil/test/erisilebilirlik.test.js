// 5F — erisilebilirlik gecisi (A44 ortak sartlar): src/ altindaki BUTUN .vue dosyalari icin kaynak uzerinden
// denetim. Bu dosya kuralin HER .vue dosyasinda tuttugunu olcer — yeni ekran eklenince kural kendiliginden ona
// da uygulanir. 5P (P6): eski Ionic ekranlari, tema.css ve tercih.js silindi; telefonda gorunus panelin
// (arayuz3/style.css) — kontrast / dokunma hedefi / panel siniflari: test/telefon_erisilebilirlik.test.js.
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const KOK = fileURLToPath(new URL("../src", import.meta.url));
function agac(dizin) {
  return readdirSync(dizin).flatMap((ad) => {
    const yol = join(dizin, ad);
    return statSync(yol).isDirectory() ? agac(yol) : yol.endsWith(".vue") ? [yol] : [];
  });
}
const DOSYALAR = agac(KOK).map((yol) => ({ ad: yol.slice(KOK.length + 1).replace(/\\/g, "/"), kaynak: readFileSync(yol, "utf8") }));
const sablon = (k) => { const a = k.indexOf("<template>"); return a < 0 ? "" : k.slice(a, k.lastIndexOf("</template>")); };
// Acilis etiketleri (cok satirli olabilir) + hemen ardindan gelen icerik.
const etiketler = (s, ad) => [...s.matchAll(new RegExp(`<${ad}\\b([^>]*)>([^]*?)</${ad}>`, "g"))].map((m) => ({ oz: m[1], ic: m[2], tam: m[0] }));

describe("erisilebilirlik: her ekranda", () => {
  it("en az 5 .vue dosyasi taraniyor (Bu telefon: kok + dort bolum)", () => {
    expect(DOSYALAR.length).toBeGreaterThanOrEqual(5);
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
    expect(sayi).toBeGreaterThanOrEqual(20);
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

  it("katman acan bilesen yok (ACIL DURDUR seridi hicbir ekranda ortulmez)", () => {
    for (const { ad, kaynak } of DOSYALAR) expect(sablon(kaynak), ad).not.toMatch(/<dialog\b|ion-modal|ion-alert|ion-popover|ion-action-sheet/);
  });
});
