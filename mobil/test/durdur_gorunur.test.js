// ACIL DURDUR seridinin gorunurlugu ve verinin tazeligi (kullanici karari, 2026-10-05):
//   * pil testinin SURMEDIGI kesin biliniyorsa serit gizli; suphede (ulasilamiyor, veri eski, okunamadi, yeni
//     acildi) HER ZAMAN gorunur
//   * baglanti durumu akisin TCP zaman asimina degil SON VERININ YASINA bagli
// 5P (P6): eski Ionic arayuzu (kabuk_durum / durum_gorunum / canli_gorunum) silindi; burada yalniz saf
// cekirdek modulu (pil_durum.js) kaldi.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  PIL_BILINMIYOR, PIL_DURUMLARI, PIL_SIRA, PIL_TAZE_MS, PIL_YOKLAMA_MS, PIL_YOLU, VERI_ESKI_MS,
  akisHali, durdurGorunur, pilDurumuCoz, pilSurmuyorKesin,
} from "../src/cekirdek/pil_durum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../${yol}`, import.meta.url)), "utf8");
const T = 1_000_000;
// Pil testinin surmedigi KESIN olan durum: bagli, akis acik, veri taze, /pil taze ve "BEKLEMEDE".
const KESIN = { bagli: true, akisHal: "acik", veriYasMs: 200, pil: { durum: "BEKLEMEDE", okunduMs: T - 1000 }, oturumTuru: null, simdiMs: T };

describe("pil durumunun okunmasi (/pil)", () => {
  const yanit = (durum) => `durum=${durum}\nhata=YOK\nmah=0.0000\nwh=0.000000\nsira=0\nilk_sira=0\nkalan=0\ncoulomb=0.000\n--\n`;

  it("kartin bes durumu tanınır; yalniz baslik bolumune bakilir", () => {
    for (const d of ["BEKLEMEDE", "CALISIYOR", "BITTI", "DURDURULDU", "HATA"]) expect(pilDurumuCoz(yanit(d))).toBe(d);
    expect(PIL_DURUMLARI).toEqual(["BEKLEMEDE", "CALISIYOR", "BITTI", "DURDURULDU", "HATA"]);
    // Nokta bolumundeki "durum=" basliga karismaz.
    expect(pilDurumuCoz(`${yanit("CALISIYOR")}durum=BEKLEMEDE\n1,2,3\n`)).toBe("CALISIYOR");
    expect(pilDurumuCoz("durum=BITTI \nhata=YOK\n--\n")).toBe("BITTI");
  });

  it("taninmayan / eksik / bicimsiz / celiskili yanit: null (BILINMIYOR)", () => {
    for (const m of ["", "hata=YOK\n--\n", "durum=\n--\n", "durum=calisiyor\n--\n", "durum=KAPALI\n--\n", "<html>durum=BEKLEMEDE</html>",
      " durum=BEKLEMEDE\n--\n", "durum=BEKLEMEDE\ndurum=CALISIYOR\n--\n", null, undefined, 5, {}]) {
      expect(pilDurumuCoz(m), JSON.stringify(m)).toBe(null);
    }
  });

  it("istek: imzali GET /pil, nokta istemeden (sira en buyuk); kartin durum adlari firmware ile ayni", () => {
    expect([PIL_YOLU, PIL_SIRA]).toEqual(["/pil", "2147483647"]);
    const u = kaynak("src/cekirdek/uygulama.js");
    expect(u).toContain('istek("GET", PIL_YOLU, [["sira", PIL_SIRA]])');
    expect(u).toContain("return pilDurumuCoz(await yanit.text());");
    const fw = readFileSync(fileURLToPath(new URL("../../kod/olcum-karti-a3/olcum-karti-a3.ino", import.meta.url)), "utf8");
    for (const d of PIL_DURUMLARI) expect(fw, d).toContain(`return "${d}";`);
    expect(fw).toContain('g += F("durum=");     g += pil_durum_metni(pil.durum);');
  });
});

describe("serit kurali: pil testinin surmedigi KESIN ise gizli, suphede GORUNUR", () => {
  it("kesin surmuyor: gizli (BEKLEMEDE / BITTI / DURDURULDU / HATA)", () => {
    for (const durum of ["BEKLEMEDE", "BITTI", "DURDURULDU", "HATA"]) {
      const g = { ...KESIN, pil: { durum, okunduMs: T - 1000 } };
      expect(pilSurmuyorKesin(g), durum).toBe(true);
      expect(durdurGorunur(g), durum).toBe(false);
    }
  });

  it("pil testi SURUYOR: gorunur (kartin durumu CALISIYOR ya da etkin oturum pil oturumu)", () => {
    expect(durdurGorunur({ ...KESIN, pil: { durum: "CALISIYOR", okunduMs: T - 1000 } })).toBe(true);
    expect(durdurGorunur({ ...KESIN, oturumTuru: 2 })).toBe(true);
    expect(durdurGorunur({ ...KESIN, oturumTuru: 1 })).toBe(false);          // olcum kaydi: p0 hicbir seyi kesmez
    expect(durdurGorunur({ ...KESIN, oturumTuru: 3 })).toBe(false);
  });

  it("BILINMIYOR: gorunur — her tek kosul icin (suphede HER ZAMAN goster)", () => {
    const supheli = {
      "hic girdi yok (uygulama yeni acildi)": undefined,
      "bos nesne": {},
      "kart bagli degil": { ...KESIN, bagli: false },
      "bagli alani dogru degil": { ...KESIN, bagli: "evet" },
      "akis hatada (ulasilamiyor)": { ...KESIN, akisHal: "hata" },
      "akis baglaniyor": { ...KESIN, akisHal: "baglaniyor" },
      "akis dolu (izleyemiyoruz)": { ...KESIN, akisHal: "dolu" },
      "akis kapali": { ...KESIN, akisHal: "kapali" },
      "veri eski (hal)": { ...KESIN, akisHal: "eski" },
      "veri eski (yas)": { ...KESIN, veriYasMs: VERI_ESKI_MS + 1 },
      "veri hic gelmedi": { ...KESIN, veriYasMs: null },
      "veri yasi eksi (saat geri gitti)": { ...KESIN, veriYasMs: -1 },
      "veri yasi sayi degil": { ...KESIN, veriYasMs: NaN },
      "pil hic okunmadi": { ...KESIN, pil: PIL_BILINMIYOR },
      "pil null": { ...KESIN, pil: null },
      "pil durumu taninmiyor": { ...KESIN, pil: { durum: "KAPALI", okunduMs: T - 1000 } },
      "pil durumu metin degil": { ...KESIN, pil: { durum: 0, okunduMs: T - 1000 } },
      "pil okumasi eski": { ...KESIN, pil: { durum: "BEKLEMEDE", okunduMs: T - PIL_TAZE_MS - 1 } },
      "pil okuma ani yok": { ...KESIN, pil: { durum: "BEKLEMEDE", okunduMs: null } },
      "pil okumasi gelecekte (saat geri gitti)": { ...KESIN, pil: { durum: "BEKLEMEDE", okunduMs: T + 1 } },
    };
    for (const [ad, g] of Object.entries(supheli)) expect(durdurGorunur(g), ad).toBe(true);
    expect(Object.keys(supheli).length).toBe(20);
    // Okuma ani olmayan pil durumu, saat kucukken de (yas hesabi tutsa bile) gecerli SAYILMAZ.
    expect(durdurGorunur({ ...KESIN, simdiMs: 1000, pil: { durum: "BEKLEMEDE", okunduMs: null } })).toBe(true);
    expect(durdurGorunur({ ...KESIN, simdiMs: 1000, pil: { durum: "BEKLEMEDE", okunduMs: 500 } })).toBe(false);
  });

  it("sinirlar: veri tam 5 s / pil okumasi tam 45 s tazedir; bir ms fazlasi degil", () => {
    expect(durdurGorunur({ ...KESIN, veriYasMs: VERI_ESKI_MS })).toBe(false);
    expect(durdurGorunur({ ...KESIN, pil: { durum: "BEKLEMEDE", okunduMs: T - PIL_TAZE_MS } })).toBe(false);
    expect([VERI_ESKI_MS, PIL_YOKLAMA_MS, PIL_TAZE_MS]).toEqual([5000, 30000, 45000]);
    expect(PIL_TAZE_MS).toBeGreaterThan(PIL_YOKLAMA_MS);                     // bir yoklama gecikse de serit titremez
  });
});

describe("baglanti durumu SON VERININ YASINA bagli (TCP zaman asimina degil)", () => {
  it("akisHali: acik + veri 5 s'den eski -> 'eski'; baska haller degismez", () => {
    expect(akisHali("acik", T - 5000, T)).toBe("acik");
    expect(akisHali("acik", T - 5001, T)).toBe("eski");
    expect(akisHali("acik", null, T)).toBe("acik");                          // henuz veri gelmedi: baglanti yeni
    for (const h of ["hata", "baglaniyor", "dolu", "kapali"]) expect(akisHali(h, T - 60000, T)).toBe(h);
  });
});
