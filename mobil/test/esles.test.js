// Eslestirme ekrani (A12, A13): durum mantigi (esles_durum.js) + sablonun parola alani kurallari.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { KartHatasi } from "../src/cekirdek/kart.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { ESLES_HATA, baglantiHatasi, eslesDurumu, kaldirGorunur, kaldirMesaji } from "../src/ekran/esles_durum.js";

const VUE = readFileSync(fileURLToPath(new URL("../src/ekran/Esles.vue", import.meta.url)), "utf8");
const PAROLA = "sinama-parolasi-1";
const kareYok = async () => {};

function sahteKart(davranis) {
  const cagrilar = [];
  return { cagrilar, esles: async (ad, parola) => { cagrilar.push({ ad, parola }); return davranis(ad, parola); } };
}

describe("eslesDurumu", () => {
  it("basari: kart.esles ad ve parolayla cagrilir; alan TEMIZLENIR; tamam", async () => {
    let cagriAnindaAlan = null;
    const d = { parola: null };
    const kart = sahteKart(() => { cagriAnindaAlan = d.parola.value; return { kimlik: "0123456789abcdef", n: 2 }; });
    const s = eslesDurumu(kart, { kareBekle: kareYok, varsayilanAd: "Telefon" });
    d.parola = s.parola;
    expect(s.ad.value).toBe("Telefon");
    s.parola.value = PAROLA;
    await s.gonder();
    expect(kart.cagrilar).toEqual([{ ad: "Telefon", parola: PAROLA }]);
    expect(cagriAnindaAlan).toBe("");                   // PBKDF2 surerken de alanda parola yok
    expect(s.parola.value).toBe("");
    expect(s.tamam.value).toBe(true);
    expect(s.hata.value).toBe(null);
    expect(s.suruyor.value).toBe(false);
  });

  it("basarisizlik: alan yine TEMIZLENIR; hata sozluk anahtari olarak; durum nesnesinde parola kalmaz", async () => {
    const kart = sahteKart(() => { throw new KartHatasi("parola-yanlis"); });
    const s = eslesDurumu(kart, { kareBekle: kareYok, varsayilanAd: "Telefon" });
    s.parola.value = PAROLA;
    await s.gonder();
    expect(s.parola.value).toBe("");
    expect(s.tamam.value).toBe(false);
    expect(s.hata.value).toEqual({ anahtar: "m.es.hata_parola_yanlis", degerler: null });
    expect(JSON.stringify({ ad: s.ad.value, parola: s.parola.value, hata: s.hata.value })).not.toContain(PAROLA);
  });

  it("her hata turunun AYRI metni var; bekle saniyeyi tasir; bilinmeyen tur genel metne duser", async () => {
    const turler = ["parola-kisa", "parola-yanlis", "parola-yok", "bekle", "liste-dolu", "sure-doldu", "kart-sahte",
      "tur-sinir-disi", "kart-gecersiz", "kimlik-uymuyor", "ag", "kasa", "ad-gecersiz", "bagli-degil", "zaten-esli"];
    const metinler = new Set();
    for (const tur of turler) {
      const kart = sahteKart(() => { throw new KartHatasi(tur); });
      const s = eslesDurumu(kart, { kareBekle: kareYok, varsayilanAd: "Telefon" });
      s.parola.value = PAROLA;
      await s.gonder();
      expect(s.hata.value.anahtar, tur).toBe(ESLES_HATA[tur]);
      expect(Object.hasOwn(SOZLUK_MOBIL, s.hata.value.anahtar), tur).toBe(true);
      metinler.add(SOZLUK_MOBIL[s.hata.value.anahtar].tr);
    }
    expect(metinler.size).toBe(turler.length);

    const bekle = eslesDurumu(sahteKart(() => { throw new KartHatasi("bekle", { saniye: 16 }); }), { kareBekle: kareYok, varsayilanAd: "T" });
    bekle.parola.value = PAROLA;
    await bekle.gonder();
    expect(bekle.hata.value).toEqual({ anahtar: "m.es.hata_bekle_saniye", degerler: { saniye: 16 } });

    for (const atilan of [new KartHatasi("boyle-bir-tur-yok"), new Error("gizli-sinama ayrinti"), "dizgi"]) {
      const s = eslesDurumu(sahteKart(() => { throw atilan; }), { kareBekle: kareYok, varsayilanAd: "T" });
      s.parola.value = PAROLA;
      await s.gonder();
      expect(s.hata.value).toEqual({ anahtar: "m.es.hata_bilinmeyen", degerler: null });
      expect(s.parola.value).toBe("");
    }
  });

  it("ilerleme gostergesi cizilsin diye kart.esles'ten ONCE bir kare beklenir; surerken ikinci gonderim yok", async () => {
    const sira = [];
    let birak;
    const kart = sahteKart(() => { sira.push("esles"); return {}; });
    const s = eslesDurumu(kart, {
      kareBekle: () => { sira.push(`kare:${s.suruyor.value}`); return new Promise((r) => { birak = r; }); },
      varsayilanAd: "T",
    });
    s.parola.value = PAROLA;
    const soz = s.gonder();
    expect(s.suruyor.value).toBe(true);
    await s.gonder();                                    // surerken: yok sayilir
    birak();
    await soz;
    expect(sira).toEqual(["kare:true", "esles"]);
    expect(kart.cagrilar.length).toBe(1);
  });
});

describe("Esles.vue sablonu", () => {
  const parolaAlani = /<ion-input\b[^>]*id="es-parola"[^>]*>/.exec(VUE)?.[0] ?? "";

  it("parola alani: gizli, otomatik doldurma / duzeltme / buyuk harf / yazim denetimi kapali", () => {
    expect(parolaAlani).not.toBe("");
    for (const oz of ['type="password"', 'autocomplete="off"', 'autocapitalize="off"', 'autocorrect="off"', ':spellcheck="false"',
      'v-model="parola"', ":label=\"c('m.es.parola')\"", ':disabled="suruyor"']) {
      expect(parolaAlani, oz).toContain(oz);
    }
  });

  it("etiket acikca WEB parolasi der — Wi-Fi parolasi DEGIL (TR ve EN)", () => {
    const { tr, en } = SOZLUK_MOBIL["m.es.parola"];
    expect(tr).toMatch(/WEB parolası/);
    expect(tr).toMatch(/Wi-Fi parolası DEĞİL/);
    expect(en).toMatch(/WEB password/);
    expect(en).toMatch(/NOT the Wi-Fi password/);
  });

  it("kartin kimligi ve adresi gorunur; ilerleme gostergesi ve hata bolgesi var; durum mantigi esles_durum.js'ten", () => {
    expect(VUE).toMatch(/\{\{ kimlik \}\}/);
    expect(VUE).toMatch(/\{\{ adres \}\}/);
    expect(VUE).toMatch(/<ion-spinner\b/);
    expect(VUE).toMatch(/id="es-hata" role="alert"/);
    expect(VUE).toContain("eslesDurumu(props.kart");
    expect(VUE).toMatch(/requestAnimationFrame/);
    // Dokunma alanlari >= 48 px
    expect(VUE).toMatch(/min-height: 48px/);
  });
});

// ── Baglanti ekrani kararlari (curutucu 5B: Y3 + okuyarak verilenler) ────────
describe("Baglanti ekrani kararlari", () => {
  const BG = readFileSync(fileURLToPath(new URL("../src/ekran/Baglanti.vue", import.meta.url)), "utf8");

  it("kaldirMesaji: 'kartta kaldirildi' YALNIZ kart sildiyse; 401 (null) icin AYRI metin; ulasilamadiysa yerel", () => {
    expect(kaldirMesaji(true)).toBe("m.bg.kaldirildi");
    expect(kaldirMesaji(null)).toBe("m.bg.kaldirildi_belirsiz");
    expect(kaldirMesaji(false)).toBe("m.bg.kaldirildi_yerel");
    expect(kaldirMesaji(undefined)).toBe("m.bg.kaldirildi_yerel");
    const { tr, en } = SOZLUK_MOBIL["m.bg.kaldirildi_belirsiz"];
    expect(tr).toMatch(/kartta kalmış olabilir/);
    expect(tr).toMatch(/panelinden ya da USB/);
    expect(en).toMatch(/may still be on the board/);
    expect(new Set([true, null, false].map((k) => SOZLUK_MOBIL[kaldirMesaji(k)].tr)).size).toBe(3);
  });

  it("kaldirGorunur: esliyken, kimlik uymazken ve kasa bozukken GORUNUR; eslesmemis / bulunamadi / bos iken degil", () => {
    expect(kaldirGorunur({ durum: "bagli" }, false)).toBe(true);
    expect(kaldirGorunur({ durum: "kimlik-uymuyor" }, false)).toBe(true);
    expect(kaldirGorunur(null, true)).toBe(true);
    expect(kaldirGorunur({ durum: "eslesmemis" }, true)).toBe(true);
    expect(kaldirGorunur({ durum: "eslesmemis" }, false)).toBe(false);
    expect(kaldirGorunur({ durum: "bulunamadi" }, false)).toBe(false);
    expect(kaldirGorunur(null, false)).toBe(false);
  });

  it("baglantiHatasi: 'kasa' -> 'kayit bozuk, kaldirip yeniden esles' metni + dugme; otekiler genel metin (yalniz TUR)", () => {
    expect(baglantiHatasi(new KartHatasi("kasa"))).toEqual({ anahtar: "m.bg.kasa_bozuk", degerler: null, kasaBozuk: true });
    expect(baglantiHatasi(new KartHatasi("ag", { ag: "baglanti" }))).toEqual({ anahtar: "m.bg.hata", degerler: { tur: "ag" }, kasaBozuk: false });
    expect(baglantiHatasi(new Error("ic ayrinti"))).toEqual({ anahtar: "m.bg.hata", degerler: { tur: "?" }, kasaBozuk: false });
    expect(baglantiHatasi(null)).toEqual({ anahtar: "m.bg.hata", degerler: { tur: "?" }, kasaBozuk: false });
    expect(SOZLUK_MOBIL["m.bg.kasa_bozuk"].tr).toMatch(/Eşleşmeyi kaldırıp yeniden eşleş/);
  });

  it("Baglanti.vue bu kararlari kullanir (dugme kosulu, mesaj secimi, kasa hatasi)", () => {
    expect(BG).toContain('<ion-button v-if="kaldirGorunur(baglanti, kasaBozuk)" id="bg-kaldir"');
    expect(BG).toContain("mesaj.value = c(kaldirMesaji(s.kartta));");
    expect(BG).toContain("const h = baglantiHatasi(e);");
    expect(BG).toContain("if (h.kasaBozuk) { kasaBozuk.value = true; baglanti.value = null; }");
  });
});
