// 5D-2 — esitlemenin kabuga ve ekranlara baglanmasi: ne zaman tetiklenir (A22), ekranda ne yazar,
// onay ayari (A21), "kopyayi sifirla" (A23). Saf islevler + GERCEK kabukDurumu (kart, canli, esitleme SAHTE).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { ONAY_ANAHTARI, onayOku, onayYaz } from "../src/cekirdek/esitleme_ayar.js";
import { KDR, esitlemeGorunumu } from "../src/ekran/durum_gorunum.js";
import { boyutYaz } from "../src/ekran/esitleme_ayar_gorunum.js";
import { ESITLEME_YOK, kabukDurumu } from "../src/ekran/kabuk_durum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../src/${yol}`, import.meta.url)), "utf8");
const bosalt = () => new Promise((c) => setTimeout(c, 0));
const G = (durum, ek = {}) => ({ tur: "G", durum, oturum: 53, nokta: 0, doluluk: 380, onaysiz: 40, ...ek });
const BAGLI = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" };

function sahteler({ esitlemeVar = true, esitlemeAtar = false, baglanDurum = "bagli" } = {}) {
  const olay = [];
  let hal = "kapali", kayit = null, dinleyen = null, esitDinleyen = null;
  let esitDurum = { hal: "bos", sonMs: null, yeni: 0, sonSira: null, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false };
  const kart = {
    d: { durum: "bagli-degil", adres: null, kimlik: null },
    durum() { return this.d; },
    async baglan() { this.d = { durum: baglanDurum, adres: "192.168.1.7:80", kimlik: "0123456789abcdef" }; return { ...this.d, bilgi: {} }; },
    async istek() { return { json: async () => ({ oturumlar: [] }) }; },
  };
  const canli = {
    baslat() { hal = "baglaniyor"; },
    durdur() { hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son: null, kayit, yas_ms: 0 }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; },
    seri: () => null,
    komut: async () => true,
  };
  const esit = {
    simdi: async () => { olay.push("simdi"); return esitDurum; },
    tik: (a) => { olay.push(["tik", a.gorunur, a.bagli]); return false; },
    baglandi: () => { olay.push("baglandi"); },
    kayitBitti: () => { olay.push("kayitBitti"); },
    sifirla: async () => { olay.push("sifirla"); if (esitlemeAtar) throw Object.assign(new Error("gizli"), { tur: "depo" }); },
    durum: () => esitDurum,
    dinle(fn) { esitDinleyen = fn; return () => { esitDinleyen = null; }; },
  };
  const saat = { ms: 1000000 };
  const aralik = { fn: null };
  let kurulum = 0;
  const k = kabukDurumu({
    kartAl: async () => kart, canliAl: async () => canli,
    esitlemeAl: esitlemeVar === null ? null : async () => { kurulum += 1; if (!esitlemeVar) throw new Error("modul yok"); return esit; },
    belge: null, simdiMs: () => saat.ms,
    araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
  });
  const yay = (yeni) => { ({ hal = hal, kayit = kayit } = yeni); if (dinleyen) dinleyen(); };
  const esitYay = (d) => { esitDurum = { ...esitDurum, ...d }; if (esitDinleyen) esitDinleyen(esitDurum); };
  const tik = async () => { aralik.fn(); await bosalt(); };
  return { k, kart, olay, saat, tik, yay, esitYay, kurulum: () => kurulum };
}

describe("kabuk: esitleme ne zaman tetiklenir (A22)", () => {
  it("kart BAGLI olunca kurulur ve 'baglandi' BIR kez; sonra her tikte tik({gorunur, bagli})", async () => {
    const s = sahteler();
    expect(s.k.esitleme.value).toEqual(ESITLEME_YOK);
    await s.k.ac();
    expect(s.kurulum()).toBe(0);                       // tembel: ilk tike kadar modul yuklenmez
    await s.tik();
    expect(s.kurulum()).toBe(1);
    expect(s.k.esitleme.value).toMatchObject({ hazir: true, hal: "bos" });
    await s.tik();
    expect(s.olay).toEqual(["baglandi"]);
    await s.tik();
    await s.tik();
    expect(s.olay).toEqual(["baglandi", ["tik", true, true], ["tik", true, true]]);
    expect(s.kurulum()).toBe(1);
  });

  it("eslesmemis / bulunamayan kartta esitleme KURULMAZ ve tetiklenmez", async () => {
    for (const durum of ["eslesmemis", "bulunamadi", "kimlik-uymuyor"]) {
      const s = sahteler({ baglanDurum: durum });
      await s.k.ac();
      await s.tik();
      await s.tik();
      expect(s.kurulum(), durum).toBe(0);
      expect(s.olay, durum).toEqual([]);
    }
  });

  it("arka plana gecince tetiklenmez; one gelince 60 s kurali (tik) surer — yeniden 'baglandi' DEGIL", async () => {
    const s = sahteler();
    await s.k.ac();
    await s.tik();
    await s.tik();
    s.k.kapat();                                       // zamanlayici durur: tik yok
    expect(s.olay).toEqual(["baglandi"]);
    await s.k.ac();
    await s.tik();
    expect(s.olay).toEqual(["baglandi", ["tik", true, true]]);
  });

  it("baglanti koptu -> yeniden bagli: yeniden 'baglandi' (tik degil)", async () => {
    const s = sahteler();
    await s.k.ac();
    await s.tik();
    await s.tik();
    await s.k.baglantiDegisti({ durum: "bulunamadi" });
    s.kart.d = { durum: "bagli-degil", adres: null, kimlik: null };
    s.olay.length = 0;
    // Kopukken tik: bagli=false ile gider (esitleme.js kendi reddeder).
    await s.tik();
    expect(s.olay[0]).toEqual(["tik", true, false]);
    await s.k.baglantiDegisti(BAGLI);
    s.olay.length = 0;
    await s.tik();
    expect(s.olay).toEqual(["baglandi"]);
  });

  it("kayit BITINCE (KAYIT -> baska hal) 'kayitBitti'; kayit surerken / baslarken DEGIL", async () => {
    const s = sahteler();
    await s.k.ac();
    await s.tik();
    await s.tik();
    s.olay.length = 0;
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 60 }) });
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 60, nokta: 5 }) });
    expect(s.olay).toEqual([]);
    s.yay({ kayit: G(KDR.BOS, { oturum: 60 }) });
    expect(s.olay).toEqual(["kayitBitti"]);
    s.yay({ kayit: G(KDR.BOS, { oturum: 60 }) });
    expect(s.olay).toEqual(["kayitBitti"]);            // BOS -> BOS: yeniden tetiklemez
  });

  it("esitlemenin durumu ekrana yansir; modul yuklenemezse hazir: false; esitlemeAl yoksa dokunulmaz", async () => {
    const s = sahteler();
    await s.k.ac();
    await s.tik();
    s.esitYay({ hal: "esitleniyor" });
    expect(s.k.esitleme.value).toMatchObject({ hazir: true, hal: "esitleniyor" });
    s.esitYay({ hal: "tamam", sonMs: 5, yeni: 3, sonSira: 9 });
    expect(s.k.esitleme.value).toMatchObject({ hazir: true, hal: "tamam", yeni: 3, sonSira: 9 });
    const yok = sahteler({ esitlemeVar: false });
    await yok.k.ac();
    await yok.tik();
    expect(yok.k.esitleme.value).toMatchObject({ hazir: false });
    expect(await yok.k.simdiEsitle()).toBe(null);
    await expect(yok.k.kopyaSifirla()).rejects.toMatchObject({ tur: "esitleme-yok" });
    const hic = sahteler({ esitlemeVar: null });
    await hic.k.ac();
    await hic.tik();
    expect(hic.k.esitleme.value).toEqual(ESITLEME_YOK);
  });

  it("simdiEsitle elle tetikler (kurulmamissa kurar); kopyaSifirla hatayi TUR olarak atar, mesaji disari cikmaz", async () => {
    const s = sahteler();
    await s.k.ac();
    expect(await s.k.simdiEsitle()).toMatchObject({ hal: "bos" });
    expect(s.olay).toEqual(["simdi"]);
    await s.k.kopyaSifirla();
    expect(s.olay).toEqual(["simdi", "sifirla"]);
    const atan = sahteler({ esitlemeAtar: true });
    await atan.k.ac();
    try { await atan.k.kopyaSifirla(); expect.unreachable(); } catch (e) {
      expect(e.tur).toBe("depo");
      expect(String(e.message) + String(e.stack)).not.toContain("gizli");
    }
  });
});

describe("esitlemeGorunumu (saf)", () => {
  const E = (ek) => ({ hazir: true, hal: "bos", sonMs: null, yeni: 0, sonSira: null, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false, ...ek });

  it("hal -> metin; 'Simdi esitle' yalniz kart BAGLI ve esitleme surmuyorken", () => {
    expect(esitlemeGorunumu(null, BAGLI)).toMatchObject({ anahtar: "m.es.yok", dugme: false });
    expect(esitlemeGorunumu(E({ hazir: false }), BAGLI)).toMatchObject({ anahtar: "m.es.yok", dugme: false });
    expect(esitlemeGorunumu(E(), BAGLI)).toMatchObject({ anahtar: "m.es.bekliyor", dugme: true, sinif: "" });
    expect(esitlemeGorunumu(E(), null)).toMatchObject({ anahtar: "m.es.kart_yok", dugme: false });
    expect(esitlemeGorunumu(E(), { durum: "eslesmemis" })).toMatchObject({ anahtar: "m.es.kart_yok", dugme: false });
    expect(esitlemeGorunumu(E({ hal: "esitleniyor" }), BAGLI)).toMatchObject({ anahtar: "m.es.kopya_suruyor", suruyor: true, dugme: false });
    expect(esitlemeGorunumu(E({ hazir: null }), BAGLI)).toMatchObject({ anahtar: "m.es.bekliyor" });   // henuz kurulmadi
  });

  it("tamam: 'guncel' + gecen dakika; bekleyen / bosluk ikinci satirda", () => {
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1000 }), BAGLI, 1000 + 59999)).toMatchObject({ anahtar: "m.es.tamam_simdi", degerler: null, sinif: "iyi", ek: null, dugme: true });
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1000 }), BAGLI, 1000 + 60000)).toMatchObject({ anahtar: "m.es.kopya_tamam", degerler: { dk: 1 } });
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1000 }), BAGLI, 1000 + 7 * 60000 + 5)).toMatchObject({ degerler: { dk: 7 } });
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 5000 }), BAGLI, 1000)).toMatchObject({ anahtar: "m.es.tamam_simdi" });   // saat geri gitti: eksi dakika yok
    // Kartta telefonun alamadigi daha yeni kayit varsa ust satir "guncel" DEMEZ (curutucu 5D B10).
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1, bekleyen: 3, bosluk: 1 }), BAGLI, 1)).toMatchObject({ anahtar: "m.es.kopya_geride", sinif: "uyari", ek: "m.es.bekleyen", degerler: null });
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1, bosluk: 2 }), BAGLI, 1).ek).toBe("m.es.bosluk");
    // Kart koptuysa: kopya hala "guncel" (son esitlemedeki haliyle) ama dugme kapali.
    expect(esitlemeGorunumu(E({ hal: "tamam", sonMs: 1 }), null, 1)).toMatchObject({ anahtar: "m.es.tamam_simdi", dugme: false });
  });

  it("hata: bilinen tur kendi metniyle, bilinmeyen genel metinle (tur degeriyle); sifirla onerisi", () => {
    const beklenen = {
      "bagli-degil": "m.es.kopya_hata_bagli_degil", ag: "m.es.kopya_hata_ag", mesgul: "m.es.hata_mesgul", "kopya-uyusmuyor": "m.es.hata_kopya",
      "depo-bozuk": "m.es.hata_kopya", depo: "m.es.hata_depo", "yanit-bozuk": "m.es.hata_yanit", "cihaz-silinmis": "m.es.hata_silinmis",
    };
    for (const [tur, anahtar] of Object.entries(beklenen)) {
      expect(esitlemeGorunumu(E({ hal: "hata", hata: tur }), BAGLI), tur).toMatchObject({ anahtar, degerler: null, sinif: "uyari", dugme: true, ek: null });
    }
    expect(esitlemeGorunumu(E({ hal: "hata", hata: "http" }), BAGLI)).toMatchObject({ anahtar: "m.es.hata_genel", degerler: { tur: "http" } });
    expect(esitlemeGorunumu(E({ hal: "hata", hata: "toString" }), BAGLI)).toMatchObject({ anahtar: "m.es.hata_genel", degerler: { tur: "toString" } });
    expect(esitlemeGorunumu(E({ hal: "hata", hata: null }), BAGLI)).toMatchObject({ anahtar: "m.es.hata_genel", degerler: { tur: "?" } });
    expect(esitlemeGorunumu(E({ hal: "hata", hata: "kopya-uyusmuyor", sifirlaOner: true }), BAGLI)).toMatchObject({ sifirlaOner: true, ek: "m.es.sifirla_oner" });
    expect(esitlemeGorunumu(E({ hal: "hata", hata: "ag", sifirlaOner: 1 }), BAGLI)).toMatchObject({ sifirlaOner: false, ek: null });
  });

  it("kullanilan butun anahtarlar sozlukte ve yer tutuculari dolu", () => {
    for (const a of ["m.es.kopya_tamam", "m.es.hata_genel", "m.es.sifirla_hata"]) {
      expect(SOZLUK_MOBIL[a].tr).toMatch(/\{(dk|tur)\}/);
      expect(SOZLUK_MOBIL[a].en).toMatch(/\{(dk|tur)\}/);
    }
    // A21: aciklama PC'yi ve silinmeyi SOYLER (kullanici neyi actigini bilsin).
    expect(SOZLUK_MOBIL["m.es.onay_not"].tr).toMatch(/PC/);
    expect(SOZLUK_MOBIL["m.es.onay_not"].tr).toMatch(/sil/);
  });
});

describe("onay ayari (A21) ve boyut yazimi", () => {
  const depoKur = (ilk = {}) => {
    const m = new Map(Object.entries(ilk));
    return { getItem: (a) => (m.has(a) ? m.get(a) : null), setItem: (a, d) => { m.set(a, String(d)); }, removeItem: (a) => { m.delete(a); }, m };
  };

  it("VARSAYILAN KAPALI; yalniz kesin '1' acik; bozuk / atan depo KAPALI", () => {
    expect(ONAY_ANAHTARI).toBe("esitleme.onay");
    expect(onayOku(depoKur())).toBe(false);
    for (const v of ["0", "true", "evet", "", " 1", "11"]) expect(onayOku(depoKur({ [ONAY_ANAHTARI]: v })), v).toBe(false);
    expect(onayOku(depoKur({ [ONAY_ANAHTARI]: "1" }))).toBe(true);
    expect(onayOku({ getItem: () => { throw new Error("kapali"); } })).toBe(false);
    expect(onayOku(null)).toBe(false);
  });

  it("onayYaz: yalniz kesin true acar; kapatinca anahtar SILINIR; yazilamazsa eski deger doner", () => {
    const d = depoKur();
    expect(onayYaz(d, true)).toBe(true);
    expect(d.m.get(ONAY_ANAHTARI)).toBe("1");
    expect(onayYaz(d, false)).toBe(false);
    expect(d.m.has(ONAY_ANAHTARI)).toBe(false);
    for (const v of [1, "1", "true", {}, null, undefined]) expect(onayYaz(depoKur(), v), String(v)).toBe(false);
    const salt = { getItem: () => null, setItem: () => { throw new Error("dolu"); }, removeItem: () => {} };
    expect(onayYaz(salt, true)).toBe(false);
  });

  it("boyutYaz", () => {
    expect([0, 999, 1000, 12345, 999999, 1e6, 11.4e6, 2.5e9].map(boyutYaz)).toEqual(["0 B", "999 B", "1.0 kB", "12.3 kB", "1000.0 kB", "1.00 MB", "11.40 MB", "2.50 GB"]);
    expect([NaN, -1, Infinity, null, "5"].map(boyutYaz)).toEqual(["—", "—", "—", "—", "—"]);
  });
});

describe("ekran baglantilari (kaynak)", () => {
  it("Durum: esitleme satiri gorunumden; 'Simdi esitle' gorunumun dugme kararina bagli; yer tutucu metin kalmadi", () => {
    const d = kaynak("ekran/Durum.vue");
    expect(d).toContain("esitlemeGorunumu(kabuk.esitleme.value, kabuk.baglanti.value, kabuk.simdi.value)");
    expect(d).toMatch(/<button id="dr-esitle"[^>]*:disabled="!esit\.dugme"[^>]*@click="kabuk\.simdiEsitle\(\)"/);
    expect(d).not.toContain("esitleme_yakinda");
    expect(SOZLUK_MOBIL["m.dr.esitleme_yakinda"]).toBeUndefined();
  });

  it("Ayarlar › Esitleme: onay anahtari role=switch ve ayardan; sifirlama IKI dokunus (onayci) ve kabuktan", () => {
    const a = kaynak("ekran/EsitlemeAyar.vue");
    expect(a).toMatch(/<button id="es-onay"[^>]*role="switch"[^>]*:aria-checked="onay"/);
    expect(a).toContain("const onay = ref(esitlemeOnayi());");
    expect(a).toContain("onay.value = esitlemeOnayiYaz(!onay.value);");
    expect(a).toContain("if (suruyor.value || !onayci.bas()) return;");
    expect(a).toContain("await kabuk.kopyaSifirla();");
    expect(kaynak("ekran/Ayarlar.vue")).toContain('<section id="ay-esitleme" class="kart"><EsitlemeAyar /></section>');
  });

  it("uygulama: esitleme tembel yuklenir, depo KartDepo eklentisinden, onay HER turda ayardan okunur", () => {
    const u = kaynak("cekirdek/uygulama.js");
    expect(u).toContain('Promise.all([import("./esitleme.js"), import("./depo.js")])');
    expect(u).toContain("depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),");
    expect(u).toContain("onayAcik: esitlemeOnayi,");
    expect(u).not.toMatch(/^import .*esitleme\.js/m);            // acilis paketine statik girmez
    expect(kaynak("App.vue")).toContain("kabukDurumu({ kartAl, canliAl, esitlemeAl, bildirimIzle, pilOku, belge: document })");
  });
});
