// ACIL DURDUR seridinin gorunurlugu ve verinin tazeligi (kullanici karari, 2026-10-05):
//   * pil testinin SURMEDIGI kesin biliniyorsa serit gizli; suphede (ulasilamiyor, veri eski, okunamadi, yeni
//     acildi) HER ZAMAN gorunur
//   * baglanti durumu akisin TCP zaman asimina degil SON VERININ YASINA bagli
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  PIL_BILINMIYOR, PIL_DURUMLARI, PIL_SIRA, PIL_TAZE_MS, PIL_YOKLAMA_MS, PIL_YOLU, VERI_ESKI_MS,
  akisHali, durdurGorunur, pilDurumuCoz, pilSurmuyorKesin,
} from "../src/cekirdek/pil_durum.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { canliHali } from "../src/ekran/canli_gorunum.js";
import { baglantiGorunumu } from "../src/ekran/durum_gorunum.js";
import { kabukDurumu } from "../src/ekran/kabuk_durum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../${yol}`, import.meta.url)), "utf8");
const bosalt = () => new Promise((c) => setTimeout(c, 0));
const KIMLIK = "0123456789abcdef";
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

  it("gorunumler: 'eski' -> 'Veri gelmiyor' (uyari, son gorulme yazilir, yeniden dene); 'Bu agda' DENMEZ", () => {
    const b = { durum: "bagli", adres: "192.168.1.7:80", kimlik: KIMLIK };
    const g = baglantiGorunumu({ baglanti: b, akis: { hazir: true, hal: "eski" }, sonGorulmeMs: T - 8000, simdiMs: T });
    expect(g).toMatchObject({ anahtar: "m.dr.veri_yok", sinif: "uyari", yeniden: true });
    expect(g.gecen).not.toBe(null);
    expect(baglantiGorunumu({ baglanti: b, akis: { hazir: true, hal: "acik" } }).anahtar).toBe("m.dr.bu_agda");
    const c = canliHali({ baglanti: b, akis: { hazir: true, hal: "eski" } });
    expect(c).toMatchObject({ anahtar: "m.dr.veri_yok", sinif: "uyari", akiyor: false });
    expect(SOZLUK_MOBIL["m.dr.veri_yok"]).toEqual({ tr: "Veri gelmiyor", en: "No data" });
  });
});

// ── kabuk: gercek kabukDurumu, sahte kart / akis / saat ──
function kabuk({ pilYanit = () => "BEKLEMEDE", baglanDurum = "bagli", pilVar = true, oturumlar = [] } = {}) {
  const saat = { ms: T };
  let hal = "kapali", kayit = null, son = null, dinleyen = null;
  const pilCagri = [];
  const kart = {
    d: { durum: "bagli-degil", adres: null, kimlik: null },
    durum() { return this.d; },
    async baglan() { this.d = { durum: baglanDurum, adres: "192.168.1.7:80", kimlik: KIMLIK }; return { ...this.d, bilgi: {} }; },
    async istek() { return { json: async () => ({ oturumlar }) }; },
  };
  const canli = {
    baslat() { hal = "baglaniyor"; }, durdur() { hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son, kayit, yas_ms: 0 }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; }, seri: () => null, komut: async () => true,
  };
  const aralik = { fn: null };
  const k = kabukDurumu({
    kartAl: async () => kart, canliAl: async () => canli,
    pilOku: pilVar ? async () => { pilCagri.push(saat.ms); return pilYanit(); } : null,
    belge: null, simdiMs: () => saat.ms,
    araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
  });
  let olcumNo = 0;
  // Akistan yeni bir olcum satiri geldi (hal acik).
  const veri = (yeniKayit = kayit) => { hal = "acik"; kayit = yeniKayit; son = { tur: "D", volt: 11, no: ++olcumNo }; if (dinleyen) dinleyen(); };
  const tik = async (ilerlet = 1000) => { saat.ms += ilerlet; aralik.fn(); await bosalt(); await bosalt(); };
  return { k, kart, saat, veri, tik, pilCagri, yay: (h) => { hal = h; if (dinleyen) dinleyen(); } };
}
const G = (durum, oturum = 0) => ({ tur: "G", durum, oturum });

describe("kabuk: serit gorunurlugu uctan uca", () => {
  it("uygulama yeni acildi / kart yok: GORUNUR; baglanip veri ve /pil gelince GIZLENIR", async () => {
    const s = kabuk();
    expect(s.k.seritGorunur()).toBe(true);                                   // hicbir sey bilinmiyor
    await s.k.ac();
    expect(s.k.seritGorunur()).toBe(true);                                   // bagli ama veri de /pil de yok
    s.veri(G(1));
    expect(s.k.seritGorunur()).toBe(true);                                   // veri var, /pil henuz okunmadi
    await s.tik();
    expect(s.pilCagri.length).toBe(1);
    expect(s.k.pil.value).toMatchObject({ durum: "BEKLEMEDE" });
    s.veri();
    expect(s.k.seritGorunur()).toBe(false);                                  // pil testinin surmedigi KESIN
    s.k.kapat();
  });

  it("pil testi suruyorsa (CALISIYOR) gorunur kalir", async () => {
    const s = kabuk({ pilYanit: () => "CALISIYOR" });
    await s.k.ac(); s.veri(G(2, 77)); await s.tik(); s.veri();
    expect(s.k.pil.value.durum).toBe("CALISIYOR");
    expect(s.k.seritGorunur()).toBe(true);
    s.k.kapat();
  });

  it("/pil okunamazsa (hata ya da taninmayan yanit) BILINMIYOR: gorunur; sonraki yoklamada yeniden denenir", async () => {
    let n = 0;
    const s = kabuk({ pilYanit: () => { n += 1; if (n === 1) throw new Error("ag"); if (n === 2) return null; return "BEKLEMEDE"; } });
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);
    expect(s.k.seritGorunur()).toBe(true);
    for (let i = 0; i < 30; i++) { await s.tik(); s.veri(); }                // 30 s sonra ikinci okuma: null
    expect(s.pilCagri.length).toBe(2);
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);                              // taninmayan yanit durum diye SAKLANMAZ
    expect(s.k.seritGorunur()).toBe(true);
    for (let i = 0; i < 30; i++) { await s.tik(); s.veri(); }
    expect(s.pilCagri.length).toBe(3);
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();
  });

  it("once okunmus, SONRAKI okuma hata verirse eski durum KORUNMAZ: gorunur", async () => {
    let n = 0;
    const s = kabuk({ pilYanit: () => { n += 1; if (n === 2) throw new Error("ag"); return "BEKLEMEDE"; } });
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    for (let i = 0; i < 30; i++) { await s.tik(); s.veri(); }                // ikinci okuma: hata
    expect(s.pilCagri.length).toBe(2);
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);
    expect(s.k.seritGorunur()).toBe(true);
    s.k.kapat();
  });

  it("etkin kayit PIL OTURUMUYSA (/kayit/liste: tur 2) kartin /pil'i ne derse desin gorunur", async () => {
    const s = kabuk({ pilYanit: () => "BEKLEMEDE", oturumlar: [{ id: 81, tur: 2 }] });
    await s.k.ac(); s.veri(G(2, 81)); await s.tik(); s.veri(); await s.tik(); s.veri();
    expect(s.k.oturumTuru.value).toBe(2);
    expect(s.k.pil.value).toMatchObject({ durum: "BEKLEMEDE" });
    expect(s.k.seritGorunur()).toBe(true);
    const olcum = kabuk({ oturumlar: [{ id: 81, tur: 1 }] });                 // olcum kaydi: gizlenebilir
    await olcum.k.ac(); olcum.veri(G(2, 81)); await olcum.tik(); olcum.veri(); await olcum.tik(); olcum.veri();
    expect(olcum.k.oturumTuru.value).toBe(1);
    expect(olcum.k.seritGorunur()).toBe(false);
    s.k.kapat(); olcum.k.kapat();
  });

  it("arka plana gecip donunce pil durumu UNUTULMUSTUR: yeni okuma gelene dek gorunur", async () => {
    const s = kabuk();
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();
    await s.k.ac(); s.veri();
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);
    expect(s.k.seritGorunur()).toBe(true);
    await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();
  });

  it("/pil 30 s'de bir okunur (daha sik DEGIL: kartin olcum dongusu mesgul edilmez)", async () => {
    const s = kabuk();
    await s.k.ac(); s.veri(G(1));
    for (let i = 0; i < 95; i++) { await s.tik(); s.veri(); }
    expect(s.pilCagri.length).toBe(4);                                       // t+1, +31, +61, +91 s
    expect(s.pilCagri[1] - s.pilCagri[0]).toBe(PIL_YOKLAMA_MS);
    expect(s.k.seritGorunur()).toBe(false);                                  // arada hic gorunmedi (taze kaldi)
    s.k.kapat();
  });

  it("kayit durumu DEGISINCE (G satiri) hemen BILINMIYOR ve yeniden okunur — pil testi baslamis olabilir", async () => {
    let durum = "BEKLEMEDE";
    const s = kabuk({ pilYanit: () => durum });
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    durum = "CALISIYOR";
    s.veri(G(2, 81));                                                        // kayit basladi (pil oturumu olabilir)
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);
    expect(s.k.seritGorunur()).toBe(true);                                   // okuma gelmeden ONCE gorunur
    await s.tik(); s.veri();
    expect(s.pilCagri.length).toBe(2);                                       // 30 s beklemeden
    expect(s.k.seritGorunur()).toBe(true);
    durum = "BITTI";
    s.veri(G(1, 0));
    expect(s.k.seritGorunur()).toBe(true);
    await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();
  });

  it("veri 5 s'dir gelmiyorsa: durum 'eski' (Veri gelmiyor), rakamlar silinir ve serit GORUNUR; veri donunce duzelir", async () => {
    const s = kabuk();
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.akis.value.hal).toBe("acik");
    expect(s.k.seritGorunur()).toBe(false);
    for (let i = 0; i < 5; i++) await s.tik();                               // 5 s veri yok: henuz taze sayilir
    expect(s.k.akis.value.hal).toBe("acik");
    await s.tik();                                                           // 6. saniye
    expect(s.k.akis.value).toMatchObject({ hal: "eski", bagli: false, son: null });
    expect(s.k.seritGorunur()).toBe(true);
    expect(baglantiGorunumu({ baglanti: s.k.baglanti.value, akis: s.k.akis.value, sonGorulmeMs: s.k.sonGorulme.value, simdiMs: s.k.simdi.value }).anahtar).toBe("m.dr.veri_yok");
    s.veri();                                                                // kart geri geldi
    expect(s.k.akis.value.hal).toBe("acik");
    await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();
  });

  it("akis hataya dusunce / arka plana gecince / eslesmemis kartta: gorunur ve pil durumu unutulur", async () => {
    const s = kabuk();
    await s.k.ac(); s.veri(G(1)); await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.yay("hata");
    expect(s.k.seritGorunur()).toBe(true);
    s.veri(); await s.tik(); s.veri();
    expect(s.k.seritGorunur()).toBe(false);
    s.k.kapat();                                                             // arka plan
    expect(s.k.seritGorunur()).toBe(true);
    const e = kabuk({ baglanDurum: "eslesmemis" });
    await e.k.ac(); e.veri(G(1)); await e.tik(); e.veri();
    expect(e.pilCagri).toEqual([]);                                          // imzali istek atilamaz: okunmaz
    expect(e.k.seritGorunur()).toBe(true);
    e.k.kapat();
  });

  it("pilOku verilmezse (okuma yolu yok) serit HEP gorunur; bildirim / esitleme etkilenmez", async () => {
    const s = kabuk({ pilVar: false });
    await s.k.ac(); s.veri(G(1));
    for (let i = 0; i < 40; i++) { await s.tik(); s.veri(); }
    expect(s.k.seritGorunur()).toBe(true);
    s.k.kapat();
  });

  it("gec donen ESKI okuma (kayit durumu o arada degisti) sonucu YAZMAZ", async () => {
    let coz;
    let n = 0;
    const s = kabuk({ pilYanit: () => { n += 1; return n === 1 ? new Promise((c) => { coz = c; }) : "CALISIYOR"; } });
    await s.k.ac(); s.veri(G(1)); await s.tik();                             // 1. okuma asili
    s.veri(G(2, 81));                                                        // kayit durumu degisti
    coz("BEKLEMEDE");                                                        // eski okuma simdi dondu
    await bosalt(); await bosalt();
    expect(s.k.pil.value).toBe(PIL_BILINMIYOR);
    await s.tik(); s.veri();
    expect(s.k.pil.value.durum).toBe("CALISIYOR");
    expect(s.k.seritGorunur()).toBe(true);
    s.k.kapat();
  });
});
