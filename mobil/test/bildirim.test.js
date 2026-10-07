// 5E-4 — bildirimin WebView yarisi: zarfin karttan alinip ACILMADAN eklentiye verilmesi (A31), eklenti
// durumunun suzulmesi, kabugun tikinden beslenen izleyici (A29, A35) ve Ayarlar › Bildirimler gorunumu.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  BILGI_YOLU, BildirimHatasi, DILLER, URETICILER, KAYITTA, SINIFLAR, ZARF_AZAMI, ZARF_EN_AZ, bildirimIzleyici, bildirimKur, izlemeSorusuKur,
} from "../src/cekirdek/bildirim.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { KDR } from "../src/cekirdek/akis_ayir.js";
import { bildirimGorunumu, hataMetni, pilYonergesi, sinifCevir } from "../src/ekran/bildirim_gorunum.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../${yol}`, import.meta.url)), "utf8");
const KIMLIK = "0123456789abcdef";
const zarfBayt = (boy = 120) => Uint8Array.from({ length: boy }, (_, i) => (i < 4 ? [0x4f, 0x4b, 0x42, 0x31][i] : (i * 7) & 0xff));
const turu = async (soz) => { try { await soz; return null; } catch (e) { return e instanceof BildirimHatasi ? e.tur : `baska:${e && e.message}`; } };
class Red extends Error { constructor(tur) { super(`gizli ${tur}`); this.code = tur; } }

function duzen({ kartDurum = { durum: "bagli", adres: "192.168.1.7:80", kimlik: KIMLIK }, istek = null, eklentiRed = {}, durum = {} } = {}) {
  const cagrilar = [];
  const istekler = [];
  const kart = {
    durum: () => kartDurum,
    async istek(...a) {
      istekler.push(a);
      if (istek) return istek(...a);
      return { arrayBuffer: async () => zarfBayt().buffer };
    },
  };
  const eklenti = {};
  for (const ad of ["uygulamaAyarlariAc", "adresYaz", "zarfYaz", "zarfSil", "durum", "ayarYaz", "izinIste", "pilMuafiyetiIste", "deneme", "izlemeBaslat", "izlemeDurdur", "yerel"]) {
    eklenti[ad] = async (veri) => {
      cagrilar.push([ad, veri]);
      if (eklentiRed[ad]) throw eklentiRed[ad];
      if (ad === "durum") return durum;
      if (ad === "izlemeBaslat") return { basladi: true, neden: "" };
      if (ad === "yerel") return { iletildi: true };
      if (ad === "izinIste" || ad === "deneme") return { izin: true };
      if (ad === "pilMuafiyetiIste") return { pilMuaf: false };
      return {};
    };
  }
  return { b: bildirimKur({ kartAl: async () => kart, eklenti }), cagrilar, istekler, kart };
}

describe("bildirim.yenile: zarf karttan imzali istekle alinir, ACILMADAN saklanir (A31)", () => {
  it("bagli kartta GET /bildirim/bilgi -> zarfYaz({ kimlik, zarf: base64 }); govde bayt bayt ayni", async () => {
    const d = duzen();
    expect(await d.b.yenile()).toBe("yazildi");
    expect(d.istekler).toEqual([["GET", "/bildirim/bilgi"]]);
    expect(BILGI_YOLU).toBe("/bildirim/bilgi");
    expect(d.cagrilar.length).toBe(1);
    const [ad, veri] = d.cagrilar[0];
    expect(ad).toBe("zarfYaz");
    expect(Object.keys(veri).sort()).toEqual(["kimlik", "zarf"]);
    expect(veri.kimlik).toBe(KIMLIK);
    expect(Buffer.from(veri.zarf, "base64")).toEqual(Buffer.from(zarfBayt()));
  });

  it("kart bagli / eslesmis degilse ISTEK GITMEZ: bagli-degil", async () => {
    for (const kartDurum of [{ durum: "bagli-degil", adres: null, kimlik: null }, { durum: "eslesmemis", adres: "x", kimlik: KIMLIK }, { durum: "bagli", adres: "x", kimlik: "KOTU" }, null]) {
      const d = duzen({ kartDurum });
      expect(await turu(d.b.yenile())).toBe("bagli-degil");
      expect(d.istekler).toEqual([]);
      expect(d.cagrilar).toEqual([]);
    }
    const b = bildirimKur({ kartAl: async () => { throw new Error("kurulamadi"); }, eklenti: {} });
    expect(await turu(b.yenile())).toBe("bagli-degil");
  });

  it("404: kartta ayarli degil -> 'kartta-ayarsiz', eldeki zarfa DOKUNULMAZ (K-10); baska HTTP hatasinda da", async () => {
    const d = duzen({ istek: async () => { throw Object.assign(new Error("x"), { tur: "http", durum: 404 }); } });
    expect(await d.b.yenile()).toBe("kartta-ayarsiz");
    expect(d.cagrilar).toEqual([]);                                          // ne silme ne yazma
    // Zarfi JS tarafindan silen HICBIR yol yok: yalniz basarili yenileme yazar, eslesme kalkinca yerel taraf siler.
    for (const f of ["src/cekirdek/bildirim.js", "src/cekirdek/uygulama.js", "src/telefon/BildirimBolumu.vue", "src/telefon/bildirim_bolum.js", "src/ortam/arka_plan.js"]) {
      expect(readFileSync(new URL("../" + f, import.meta.url), "utf8"), f).not.toMatch(/zarfSil/);
    }
    // 404 govdesi zarf gibi gorunse de YAZILMAZ.
    const sahte = duzen({ istek: async () => { throw Object.assign(new Error("x"), { tur: "http", durum: 404, govde: new Uint8Array(233) }); } });
    expect(await sahte.b.yenile()).toBe("kartta-ayarsiz");
    expect(sahte.cagrilar).toEqual([]);
    for (const [hata, beklenen] of [
      [{ tur: "http", durum: 500 }, "kart"], [{ tur: "http", durum: 403 }, "kart"], [{ tur: "ag", ag: "zaman-asimi" }, "ag"],
      [{ tur: "cihaz-silinmis" }, "cihaz-silinmis"], [{ tur: "kasa" }, "kart"], [{}, "kart"],
    ]) {
      const e = duzen({ istek: async () => { throw Object.assign(new Error("gizli-ayrinti"), hata); } });
      expect(await turu(e.b.yenile())).toBe(beklenen);
      expect(e.cagrilar).toEqual([]);
    }
  });

  it("boyu tutmayan govde eklentiye VERILMEZ (bicim); sinirlar kabul", async () => {
    for (const boy of [0, ZARF_EN_AZ - 1, ZARF_AZAMI + 1]) {
      const d = duzen({ istek: async () => ({ arrayBuffer: async () => zarfBayt(boy).buffer }) });
      expect(await turu(d.b.yenile())).toBe("bicim");
      expect(d.cagrilar).toEqual([]);
    }
    for (const boy of [ZARF_EN_AZ, ZARF_AZAMI]) {
      const d = duzen({ istek: async () => ({ arrayBuffer: async () => zarfBayt(boy).buffer }) });
      expect(await d.b.yenile()).toBe("yazildi");
      expect(Buffer.from(d.cagrilar[0][1].zarf, "base64").length).toBe(boy);
    }
    expect([ZARF_EN_AZ, ZARF_AZAMI]).toEqual([32, 2048]);
  });

  it("eklenti reddederse TUR adi cikar (zarf bu telefonun anahtariyla acilmadi = etiket); mesaj disari cikmaz", async () => {
    for (const [kod, beklenen] of [["etiket", "etiket"], ["adres", "adres"], ["anahtar-yok", "anahtar-yok"], ["Gizli Mesaj!", "ic-hata"], [undefined, "ic-hata"]]) {
      const d = duzen({ eklentiRed: { zarfYaz: new Red(kod) } });
      let hata = null;
      try { await d.b.yenile(); } catch (e) { hata = e; }
      expect(hata).toBeInstanceOf(BildirimHatasi);
      expect(hata.tur).toBe(beklenen);
      expect(hata.message).toBe(beklenen);
    }
  });

  it("modul zarfi ACMAZ: kaynakta kripto / zarf cozucu ice aktarimi ve ag cagrisi yok", () => {
    const k = kaynak("src/cekirdek/bildirim.js").replace(/\/\/[^\n]*/g, "");
    expect(k).not.toMatch(/\bimport\b/);
    expect(k).not.toMatch(/zarfAc|bilgiCoz|chacha|fetch\s*\(|XMLHttpRequest|WebSocket/i);
  });
});

describe("bildirim.durum / ayarYaz: eklenti verisi alan alan suzulur", () => {
  it("durum: yalniz bilinen alanlar, dogru turde; bilinmeyen izleme / dil / sinif ayiklanir", async () => {
    const d = duzen({ durum: {
      zarf: true, izin: "evet", izinGerekli: true, pilMuaf: 1, calisiyor: true, izleme: "izleniyor", anlik: true,
      kapali: ["deneme", "yok-boyle", "bitti", 7], dil: "en", uri: "mqtts://gizli.example", kullanici: "gizli",
    } });
    expect(await d.b.durum(KIMLIK)).toEqual({
      zarf: true, izin: false, izinGerekli: true, pilMuaf: false, calisiyor: true, izleme: "izleniyor", anlik: true,
      kapali: ["bitti", "deneme"], dil: "en", uretici: "diger",
    });
    expect(d.cagrilar).toEqual([["durum", { kimlik: KIMLIK }]]);
    const bos = duzen({ durum: { izleme: "<script>", dil: "de", kapali: "bitti" } });
    expect(await bos.b.durum("KOTU")).toEqual({
      zarf: false, izin: false, izinGerekli: false, pilMuaf: false, calisiyor: false, izleme: "durduruldu", anlik: false, kapali: [], dil: "tr", uretici: "diger",
    });
    expect(bos.cagrilar).toEqual([["durum", {}]]);
  });

  it("ayarYaz: yalniz verilen ve gecerli alanlar gider; siniflar SINIFLAR sirasinda", async () => {
    const d = duzen();
    await d.b.ayarYaz({ anlik: true });
    await d.b.ayarYaz({ kapali: ["deneme", "x", "kopuk"], dil: "en" });
    await d.b.ayarYaz({ anlik: "evet", dil: "de", kapali: "bitti" });
    await d.b.ayarYaz();
    expect(d.cagrilar).toEqual([
      ["ayarYaz", { anlik: true }], ["ayarYaz", { kapali: ["kopuk", "deneme"], dil: "en" }], ["ayarYaz", {}], ["ayarYaz", {}],
    ]);
    expect(SINIFLAR).toEqual(["kopuk", "bitti", "dolu", "esik", "yeniden_basladi", "kacirilan", "deneme"]);
    expect(DILLER).toEqual(["tr", "en"]);
  });

  it("izlemeBaslat / yerel: gecersiz kimlik ve sayi eklentiye GITMEZ; donusler suzulur", async () => {
    const d = duzen();
    expect(await d.b.izlemeBaslat(KIMLIK)).toEqual({ basladi: true, neden: "" });
    expect(await d.b.yerel(KIMLIK, 2, 53)).toBe(true);
    expect(await turu(d.b.izlemeBaslat("../x"))).toBe("bicim");
    for (const [kod, oturum] of [[-1, 5], [2, -1], [2.5, 5], ["2", 5], [2, null]]) expect(await turu(d.b.yerel(KIMLIK, kod, oturum))).toBe("bicim");
    expect(await turu(d.b.yerel("KOTU", 2, 5))).toBe("bicim");
    expect(d.cagrilar).toEqual([["izlemeBaslat", { kimlik: KIMLIK }], ["yerel", { kimlik: KIMLIK, durum: 2, oturum: 53 }]]);
    expect(await d.b.izinIste()).toBe(true);
    expect(await d.b.pilMuafiyetiIste()).toBe(false);
    expect(await d.b.deneme()).toBe(true);
  });

  it("Kotlin tarafiyla AYNI sabitler: siniflar, zarf sinirlari, kayitta sayilan durumlar", () => {
    const kt = kaynak("android/app/src/main/java/tr/olcumkarti/mobil/bildirim/BildirimDeposu.kt");
    expect(kt).toContain(`val SINIFLAR = listOf(${SINIFLAR.map((s) => `"${s}"`).join(", ")})`);
    expect(kt).toContain(`const val ZARF_AZAMI = ${ZARF_AZAMI}`);
    expect(kaynak("android/app/src/main/java/tr/olcumkarti/mobil/bildirim/Zarf.kt")).toContain("const val EN_AZ = 4 + NONCE + ETIKET");
    expect(KAYITTA).toEqual([KDR.KAYIT, KDR.BEKLIYOR]);
    // Eklentinin yontem adlari: WebView'in cagirdigi her ad Kotlin'de @PluginMethod olarak var.
    const eklenti = kaynak("android/app/src/main/java/tr/olcumkarti/mobil/bildirim/BildirimPlugin.kt");
    const js = kaynak("src/cekirdek/bildirim.js");
    const cagrilan = [...js.matchAll(/cagir\("([A-Za-z]+)"/g)].map((m) => m[1]);
    expect(new Set(cagrilan).size).toBe(11);                 // zarfSil artik JS'ten CAGRILMAZ (K-10)
    for (const ad of cagrilan) expect(eklenti, ad).toMatch(new RegExp(`@PluginMethod\\s+fun ${ad}\\(`));
  });
});

describe("bildirimIzleyici: kabugun tikinden (A29, A31, A35)", () => {
  function izleyici({ yenileAtar = null, baslatAtar = false } = {}) {
    const olay = [];
    const bildirim = {
      yenile: async () => { olay.push("yenile"); await new Promise((c) => setTimeout(c, 5)); if (yenileAtar) throw Object.assign(new Error("x"), { tur: yenileAtar }); olay.push("yenile-bitti"); return "yazildi"; },
      izlemeBaslat: async (k) => { olay.push(["baslat", k]); if (baslatAtar) throw new Error("x"); return { basladi: true, neden: "" }; },
      yerel: async (k, d, o) => { olay.push(["yerel", k, d, o]); return true; },
    };
    return { i: bildirimIzleyici({ bildirim }), olay };
  }
  const G = (durum, oturum = 53) => ({ tur: "G", durum, oturum });
  const on = { gorunur: true, bagli: true, kimlik: KIMLIK };

  it("yeni baglantida zarf BIR kez yenilenir; baglanti kopup gelince yeniden", async () => {
    const { i, olay } = izleyici();
    i.tik({ ...on, kayit: null }); i.tik({ ...on, kayit: null }); i.tik({ ...on, kayit: null });
    await i.bosalt();
    expect(olay).toEqual(["yenile", "yenile-bitti"]);
    expect(i.son()).toBe("yazildi");
    i.tik({ ...on, bagli: false, kayit: null });
    i.tik({ ...on, kayit: null });
    await i.bosalt();
    expect(olay.filter((o) => o === "yenile").length).toBe(2);
  });

  it("gorunur degil / bagli degil / kimlik gecersiz: HICBIR sey yapilmaz", async () => {
    const { i, olay } = izleyici();
    i.tik({ gorunur: false, bagli: true, kimlik: KIMLIK, kayit: G(KDR.KAYIT) });
    i.tik({ gorunur: true, bagli: false, kimlik: KIMLIK, kayit: G(KDR.KAYIT) });
    i.tik({ gorunur: true, bagli: true, kimlik: null, kayit: G(KDR.KAYIT) });
    i.tik({ gorunur: true, bagli: true, kimlik: "KOTU", kayit: G(KDR.KAYIT) });
    await i.bosalt();
    expect(olay).toEqual([]);
    expect(i.son()).toBe(null);
  });

  it("kayit suruyor: ZARF YAZILDIKTAN SONRA izleme baslatilir, sonra yerel durum iletilir; ayni durum yinelenmez", async () => {
    const { i, olay } = izleyici();
    i.tik({ ...on, kayit: G(KDR.KAYIT) });
    i.tik({ ...on, kayit: G(KDR.KAYIT) });
    await i.bosalt();
    expect(olay).toEqual(["yenile", "yenile-bitti", ["baslat", KIMLIK], ["yerel", KIMLIK, 2, 53]]);
    i.tik({ ...on, kayit: G(KDR.BOS) });                 // kayit bitti: izleme BASLATILMAZ, durum iletilir
    await i.bosalt();
    expect(olay.slice(4)).toEqual([["yerel", KIMLIK, 1, 53]]);
    i.tik({ ...on, kayit: G(KDR.BEKLIYOR, 54) });        // bekliyor da kayit sayilir
    await i.bosalt();
    expect(olay.slice(5)).toEqual([["baslat", KIMLIK], ["yerel", KIMLIK, 4, 54]]);
    i.tik({ ...on, kayit: G(KDR.DOLU, 54) });
    await i.bosalt();
    expect(olay.slice(7)).toEqual([["yerel", KIMLIK, 3, 54]]);
  });

  it("baglanti kopup gelince AYNI kayit durumu yeniden iletilir (servis o arada kapanmis olabilir)", async () => {
    const { i, olay } = izleyici();
    i.tik({ ...on, kayit: G(KDR.KAYIT) });
    await i.bosalt();
    i.tik({ ...on, gorunur: false, kayit: G(KDR.KAYIT) });
    i.tik({ ...on, kayit: G(KDR.KAYIT) });
    await i.bosalt();
    expect(olay.filter((o) => Array.isArray(o) && o[0] === "baslat").length).toBe(2);
  });

  it("bicimsiz G satiri iletilmez; hatalar yukari CIKMAZ ve sonraki isi durdurmaz", async () => {
    const bozuk = izleyici();
    for (const kayit of [{ durum: "2", oturum: 5 }, { durum: 2 }, { durum: -1, oturum: 5 }, { durum: 2, oturum: 1.5 }, {}]) bozuk.i.tik({ ...on, kayit });
    await bozuk.i.bosalt();
    expect(bozuk.olay).toEqual(["yenile", "yenile-bitti"]);

    const { i, olay } = izleyici({ yenileAtar: "ag", baslatAtar: true });
    expect(() => i.tik({ ...on, kayit: G(KDR.KAYIT) })).not.toThrow();
    await i.bosalt();
    expect(i.son()).toBe("ag");
    expect(olay).toEqual(["yenile", ["baslat", KIMLIK], ["yerel", KIMLIK, 2, 53]]);
  });
});

describe("Ayarlar › Bildirimler gorunumu (saf)", () => {
  const D = { zarf: true, izin: true, izinGerekli: true, pilMuaf: true, calisiyor: false, izleme: "durduruldu", anlik: false, kapali: [], dil: "tr" };

  it("durum okunamadiysa null; kart bilinmiyorsa 'kart yok'", () => {
    expect(bildirimGorunumu(null)).toBe(null);
    expect(bildirimGorunumu(D, { kimlik: null }).ayar).toBe("m.bl.kart_yok");
  });

  it("zarf var / yok / kartta ayarsiz; uyari yalniz zarf yokken", () => {
    expect(bildirimGorunumu(D, { kimlik: KIMLIK })).toMatchObject({ ayar: "m.bl.zarf_var", ayarUyari: false });
    expect(bildirimGorunumu({ ...D, zarf: false }, { kimlik: KIMLIK })).toMatchObject({ ayar: "m.bl.zarf_yok", ayarUyari: true });
    expect(bildirimGorunumu({ ...D, zarf: false }, { kimlik: KIMLIK, son: "kartta-ayarsiz" }).ayar).toBe("m.bl.kartta_ayarsiz");
    // Zarf DURURKEN kart "ayarli degil" dediyse (zarf silinmez — K-10) bu ayrica soylenir ve uyaridir.
    expect(bildirimGorunumu(D, { kimlik: KIMLIK, son: "kartta-ayarsiz" })).toMatchObject({ ayar: "m.bl.kartta_ayarsiz_zarf", ayarUyari: true });
    expect(bildirimGorunumu(D, { kimlik: KIMLIK, son: "yazildi" })).toMatchObject({ ayar: "m.bl.zarf_var", ayarUyari: false });
    expect(bildirimGorunumu(D, { kimlik: KIMLIK, son: "ag" })).toMatchObject({ ayar: "m.bl.zarf_var", ayarUyari: false });
    expect(bildirimGorunumu(D, { kimlik: null, son: "kartta-ayarsiz" }).ayar).toBe("m.bl.kart_yok");
    expect(SOZLUK_MOBIL["m.bl.kartta_ayarsiz_zarf"].tr).toMatch(/silinmedi/);
  });

  it("izin dugmesi yalniz izin YOK ve istenebilirken; pil yalniz anlik izleme ACIKKEN konu edilir (A37)", () => {
    expect(bildirimGorunumu(D, { kimlik: KIMLIK })).toMatchObject({ izin: "m.bl.izin_var", izinIste: false, pilGoster: false, pilIste: false });
    expect(bildirimGorunumu({ ...D, izin: false }, { kimlik: KIMLIK })).toMatchObject({ izin: "m.bl.izin_yok", izinIste: true });
    expect(bildirimGorunumu({ ...D, izin: false, izinGerekli: false }, { kimlik: KIMLIK }).izinIste).toBe(false);
    expect(bildirimGorunumu({ ...D, pilMuaf: false }, { kimlik: KIMLIK })).toMatchObject({ pilGoster: false, pilIste: false });
    expect(bildirimGorunumu({ ...D, anlik: true, pilMuaf: false }, { kimlik: KIMLIK })).toMatchObject({ pilGoster: true, pil: "m.bl.pil_kisitli", pilIste: true });
    expect(bildirimGorunumu({ ...D, anlik: true }, { kimlik: KIMLIK })).toMatchObject({ pilGoster: true, pil: "m.bl.pil_muaf", pilIste: false });
  });

  it("izleme durumu: her adin kendi metni, sorunlu olanlar uyari; bilinmeyen 'calismiyor'", () => {
    const adlar = ["durduruldu", "baglaniyor", "izleniyor", "internet", "guven", "araci", "kayit-bitti", "ayar", "ic-hata"];
    const g = adlar.map((izleme) => bildirimGorunumu({ ...D, izleme }, { kimlik: KIMLIK }));
    expect(new Set(g.map((x) => x.izleme)).size).toBe(adlar.length);
    expect(adlar.filter((_, n) => g[n].izlemeUyari)).toEqual(["internet", "guven", "araci", "ayar", "ic-hata"]);
    expect(bildirimGorunumu({ ...D, izleme: "yok-boyle" }, { kimlik: KIMLIK }).izleme).toBe("m.bl.izleme_durduruldu");
  });

  it("siniflar: yedisi de, sirayla; sinifCevir tek sinifi cevirir, bilinmeyeni yok sayar", () => {
    const g = bildirimGorunumu({ ...D, kapali: ["bitti"] }, { kimlik: KIMLIK });
    expect(g.siniflar.map((s) => s.sinif)).toEqual(SINIFLAR);
    expect(g.siniflar.filter((s) => !s.acik).map((s) => s.sinif)).toEqual(["bitti"]);
    expect(sinifCevir(["bitti"], "kopuk")).toEqual(["kopuk", "bitti"]);
    expect(sinifCevir(["kopuk", "bitti"], "bitti")).toEqual(["kopuk"]);
    expect(sinifCevir(["bitti", "x"], "yok-boyle")).toEqual(["bitti"]);
  });

  it("hata metinleri: bilinen tur kendi metniyle, bilinmeyen genel metinle (turun adiyla)", () => {
    expect(hataMetni("ag")).toEqual({ anahtar: "m.bl.hata_ag", degerler: null });
    expect(hataMetni("etiket").anahtar).toBe("m.bl.hata_zarf");
    expect(hataMetni("adres").anahtar).toBe("m.bl.hata_adres");
    expect(hataMetni("bagli-degil").anahtar).toBe("m.bl.hata_bagli_degil");
    expect(hataMetni("kart")).toEqual({ anahtar: "m.bl.hata_genel", degerler: { tur: "kart" } });
    expect(hataMetni(undefined)).toEqual({ anahtar: "m.bl.hata_genel", degerler: { tur: "?" } });
  });

  it("gorunumun ve ekranin kullandigi HER anahtar sozlukte (tr + en); A37 metinleri nedenini soyluyor", () => {
    const D2 = [true, false].flatMap((zarf) => [true, false].flatMap((izin) => [true, false].flatMap((anlik) => [true, false].map((pilMuaf) => ({ ...D, zarf, izin, anlik, pilMuaf })))));
    const anahtarlar = new Set();
    for (const d of D2) for (const son of [null, "kartta-ayarsiz"]) for (const kimlik of [KIMLIK, null]) {
      const g = bildirimGorunumu(d, { kimlik, son });
      for (const a of [g.ayar, g.izin, g.pil, g.izleme, ...g.siniflar.map((s) => s.anahtar)]) anahtarlar.add(a);
    }
    for (const izleme of ["baglaniyor", "izleniyor", "internet", "guven", "araci", "kayit-bitti", "ayar", "ic-hata"]) anahtarlar.add(bildirimGorunumu({ ...D, izleme }, { kimlik: KIMLIK }).izleme);
    for (const t of ["bagli-degil", "ag", "cihaz-silinmis", "etiket", "adres", "x"]) anahtarlar.add(hataMetni(t).anahtar);
    for (const f of ["src/telefon/BildirimBolumu.vue", "src/telefon/bildirim_bolum.js"]) {
      for (const m of kaynak(f).matchAll(/["'](m\.bl\.[a-z_]+)["']/g)) anahtarlar.add(m[1]);
    }
    anahtarlar.add("m.ay.bildirim");
    expect(anahtarlar.size).toBeGreaterThan(40);
    for (const a of anahtarlar) {
      expect(Object.hasOwn(SOZLUK_MOBIL, a), a).toBe(true);
      expect(SOZLUK_MOBIL[a].tr.length, a).toBeGreaterThan(1);
      expect(SOZLUK_MOBIL[a].en.length, a).toBeGreaterThan(1);
    }
    expect(SOZLUK_MOBIL["m.bl.pil_not"].tr).toMatch(/ekran kapalıyken/);
    expect(SOZLUK_MOBIL["m.bl.izin_not"].tr).toMatch(/çalışır ama bildirim göstermez/);
    expect(SOZLUK_MOBIL["m.bl.anlik_not"].tr).toMatch(/Kapalıyken bildirimler 15 dakikaya kadar gecikebilir/);
  });

  it("ekran (Bu telefon › Bildirimler): izin ve pil dugmeleri ACIKLAMASIYLA birlikte; araci bilgisi gosteren alan yok", () => {
    const v = kaynak("src/telefon/BildirimBolumu.vue");
    expect(v).toMatch(/data-bt-bl-izin-iste[^]*m\.bl\.izin_not/);
    expect(v).toMatch(/m\.bl\.pil_not[^]*data-bt-bl-pil-iste/);
    const sablon = v.slice(v.indexOf("<template>"));
    expect(sablon).not.toMatch(/uri|kullanici|parola|onek|mqtt|adres/i);
    expect(sablon.match(/role="switch"/g).length).toBe(2);                 // anlik izleme + olay anahtarlari (v-for)
  });
});

describe("izleme sorusu: kayit BU telefondan baslatilinca bir kez (kullanici karari 2026-10-05)", () => {
  const D = { zarf: true, izin: true, izinGerekli: true, pilMuaf: false, calisiyor: false, izleme: "durduruldu", anlik: false, kapali: [], dil: "tr" };
  function soru({ durum = D, basladi = true, kimlik = KIMLIK, atar = null } = {}) {
    const olay = [];
    const haller = [];
    const bildirim = {
      durum: async (k) => { olay.push(["durum", k]); if (atar === "durum") throw new Error("x"); return typeof durum === "function" ? durum() : durum; },
      izinIste: async () => { olay.push("izinIste"); return false; },
      izlemeBaslat: async (k, s) => { olay.push(["baslat", k, s]); if (atar === "baslat") throw new Error("x"); return { basladi, neden: basladi ? "" : "zarf-yok" }; },
    };
    const s = izlemeSorusuKur({ bildirim, kimlikAl: async () => kimlik });
    s.dinle((h) => haller.push(h));
    return { s, olay, haller };
  }

  it("anlik izleme KAPALI + zarf var: sorulur; 'ac' -> yalniz bu kayit icin baslatilir (ayar DEGISMEZ)", async () => {
    const { s, olay, haller } = soru();
    expect(s.hal()).toBe("yok");
    await s.kayitBasladi();
    expect(s.hal()).toBe("soruluyor");
    await s.evet();
    expect(s.hal()).toBe("acildi");
    expect(haller).toEqual(["soruluyor", "aciliyor", "acildi"]);
    expect(olay).toEqual([["durum", KIMLIK], ["durum", KIMLIK], ["baslat", KIMLIK, { buKayit: true }]]);
  });

  it("'hayir' -> soru kapanir, hicbir sey baslatilmaz; soru sorulmamisken evet / hayir etkisiz", async () => {
    const { s, olay } = soru();
    await s.evet(); s.hayir();
    expect(olay).toEqual([]);
    await s.kayitBasladi();
    s.hayir();
    expect(s.hal()).toBe("yok");
    await s.evet();
    expect(olay.filter((o) => Array.isArray(o) && o[0] === "baslat")).toEqual([]);
  });

  it("SORULMAZ: anlik izleme zaten acik / servis calisiyor / bildirim ayari (zarf) yok / kart bilinmiyor / durum okunamadi", async () => {
    for (const secenek of [{ durum: { ...D, anlik: true } }, { durum: { ...D, calisiyor: true } }, { durum: { ...D, zarf: false } }, { kimlik: null }, { kimlik: "KOTU" }, { atar: "durum" }]) {
      const { s } = soru(secenek);
      await s.kayitBasladi();
      expect(s.hal(), JSON.stringify(secenek)).toBe("yok");
    }
  });

  it("izin yoksa once izin istenir; reddedilse de izleme baslatilir", async () => {
    const { s, olay } = soru({ durum: { ...D, izin: false } });
    await s.kayitBasladi();
    await s.evet();
    expect(olay.slice(2)).toEqual(["izinIste", ["baslat", KIMLIK, { buKayit: true }]]);
    expect(s.hal()).toBe("acildi");
    const eski = soru({ durum: { ...D, izin: false, izinGerekli: false } });      // Android 12 ve oncesi: izin penceresi yok
    await eski.s.kayitBasladi(); await eski.s.evet();
    expect(eski.olay).not.toContain("izinIste");
  });

  it("baslatilamazsa 'acilamadi' (hata yukari cikmaz); kayit bitince soru da sonuc da kalkar", async () => {
    for (const secenek of [{ basladi: false }, { atar: "baslat" }]) {
      const { s } = soru(secenek);
      await s.kayitBasladi();
      await s.evet();
      expect(s.hal()).toBe("acilamadi");
      s.kayitBitti();
      expect(s.hal()).toBe("yok");
    }
    const { s } = soru();
    await s.kayitBasladi();
    s.kayitBitti();
    expect(s.hal()).toBe("yok");
  });

  it("kayit bittikten sonra biten 'ac' islemi sonucu YAZMAZ; yeni kayit yeniden sorar", async () => {
    let coz;
    const bekle = new Promise((c) => { coz = c; });
    const olay = [];
    const s = izlemeSorusuKur({
      bildirim: { durum: async () => D, izinIste: async () => true, izlemeBaslat: async () => { olay.push("baslat"); await bekle; return { basladi: true, neden: "" }; } },
      kimlikAl: async () => KIMLIK,
    });
    await s.kayitBasladi();
    const e = s.evet();
    await new Promise((c) => setTimeout(c, 0));
    s.kayitBitti();
    coz();
    await e;
    expect(s.hal()).toBe("yok");
    await s.kayitBasladi();
    expect(s.hal()).toBe("soruluyor");
  });

  it("ekran (telefon ortami, soru_cizim.js): soru metinleri sozlukte; eklenti buKayit'i yalniz acikca true ise kullanir", () => {
    const v = kaynak("src/ortam/soru_cizim.js");
    for (const a of ["m.bl.soru", "m.bl.soru_evet", "m.bl.soru_hayir", "m.bl.soru_acildi", "m.bl.soru_acilamadi"]) {
      expect(v).toContain(`"${a}"`);
      expect(SOZLUK_MOBIL[a].tr.length).toBeGreaterThan(1);
      expect(SOZLUK_MOBIL[a].en.length).toBeGreaterThan(1);
    }
    expect(SOZLUK_MOBIL["m.bl.soru"].tr).toMatch(/Bu kayıt için anlık izleme açılsın mı\?/);
    // Eklenti: buKayit yalniz ACIKCA true ise ayari asar; ayar yazimi "bu kayit icin" izlemeyi kesmez.
    const kt = kaynak("android/app/src/main/java/tr/olcumkarti/mobil/bildirim/BildirimPlugin.kt");
    expect(kt).toContain('!ayar().anlik && call.getBoolean("buKayit") != true -> "kapali"');
    expect(kt).toContain("if (eski.anlik && !yeni.anlik && IzlemeServisi.calisanKimlik != null) IzlemeServisi.durdur(context)");
  });

  it("izlemeBaslat: buKayit yalniz istenince gider", async () => {
    const d = duzen();
    await d.b.izlemeBaslat(KIMLIK, { buKayit: true });
    await d.b.izlemeBaslat(KIMLIK, { buKayit: "evet" });
    expect(d.cagrilar).toEqual([["izlemeBaslat", { kimlik: KIMLIK, buKayit: true }], ["izlemeBaslat", { kimlik: KIMLIK }]]);
  });
});

describe("A36: kartin yerel adresi servise verilir (servis araci 'cevrimdisi' derken imzasiz yoklar)", () => {
  it("yeni baglantida adres ZARFTAN ONCE yazilir; adres yoksa yazilmaz; hata sonraki isi durdurmaz", async () => {
    const olay = [];
    const bildirim = {
      adresYaz: async (k, a) => { olay.push(["adres", k, a]); throw new Error("x"); },
      yenile: async () => { olay.push("yenile"); return "yazildi"; },
      izlemeBaslat: async () => ({ basladi: false, neden: "kapali" }), yerel: async () => true,
    };
    const i = bildirimIzleyici({ bildirim });
    i.tik({ gorunur: true, bagli: true, kimlik: KIMLIK, adres: "192.168.1.7:80", kayit: null });
    i.tik({ gorunur: true, bagli: true, kimlik: KIMLIK, adres: "192.168.1.7:80", kayit: null });
    await i.bosalt();
    expect(olay).toEqual([["adres", KIMLIK, "192.168.1.7:80"], "yenile"]);
    const adressiz = [];
    const j = bildirimIzleyici({ bildirim: { ...bildirim, adresYaz: async () => { adressiz.push("adres"); }, yenile: async () => { adressiz.push("yenile"); return "yazildi"; } } });
    j.tik({ gorunur: true, bagli: true, kimlik: KIMLIK, adres: null, kayit: null });
    await j.bosalt();
    expect(adressiz).toEqual(["yenile"]);
  });

  it("adresYaz: bos / uzun / metin olmayan adres ve gecersiz kimlik eklentiye GITMEZ", async () => {
    const d = duzen();
    await d.b.adresYaz(KIMLIK, "192.168.1.7:80");
    for (const a of ["", "x".repeat(22), null, 5]) expect(await turu(d.b.adresYaz(KIMLIK, a))).toBe("bicim");
    expect(await turu(d.b.adresYaz("KOTU", "192.168.1.7"))).toBe("bicim");
    expect(d.cagrilar).toEqual([["adresYaz", { kimlik: KIMLIK, adres: "192.168.1.7:80" }]]);
  });
});

describe("A37: pil yoneticisi yonergesi (Honor ve digerleri)", () => {
  it("uretici sinifi eklentiden suzulerek gelir; bilinmeyen 'diger'", async () => {
    for (const [gelen, beklenen] of [["honor", "honor"], ["xiaomi", "xiaomi"], ["HONOR", "diger"], ["<b>", "diger"], [undefined, "diger"], [5, "diger"]]) {
      const d = duzen({ durum: { uretici: gelen } });
      expect((await d.b.durum(KIMLIK)).uretici).toBe(beklenen);
    }
    expect(URETICILER).toEqual(["honor", "huawei", "xiaomi", "samsung", "diger"]);
    const d = duzen();
    await d.b.uygulamaAyarlariAc();
    expect(d.cagrilar).toEqual([["uygulamaAyarlariAc", {}]]);
  });

  it("her uretici sinifinin adimlari var, hepsi sozlukte (tr + en); Honor: otomatik yonet KAPALI + uc izin ACIK", () => {
    for (const u of URETICILER) {
      const y = pilYonergesi(u);
      expect(y.uretici).toBe(u);
      expect(y.adimlar.length).toBeGreaterThanOrEqual(2);
      expect(y.ozel).toBe(u !== "diger");
      for (const a of y.adimlar) {
        expect(SOZLUK_MOBIL[a].tr.length, a).toBeGreaterThan(10);
        expect(SOZLUK_MOBIL[a].en.length, a).toBeGreaterThan(10);
      }
    }
    expect(pilYonergesi("yok-boyle")).toEqual(pilYonergesi("diger"));
    expect(pilYonergesi(undefined).ozel).toBe(false);
    const honor = pilYonergesi("honor").adimlar.map((a) => SOZLUK_MOBIL[a].tr).join(" ");
    expect(honor).toMatch(/Uygulama başlatma/);
    expect(honor).toMatch(/"Otomatik yönet"i KAPAT/);
    expect(honor).toMatch(/Otomatik başlatma, İkincil başlatma, Arka planda çalıştır/);
    expect(pilYonergesi("huawei").adimlar).toEqual(pilYonergesi("honor").adimlar);
    expect(pilYonergesi("xiaomi").adimlar).not.toEqual(pilYonergesi("honor").adimlar);
    // Adim listesi disaridan degistirilemez (kopya doner).
    pilYonergesi("honor").adimlar.push("x");
    expect(pilYonergesi("honor").adimlar.length).toBe(4);
  });

  it("gorunum yonergeyi tasir; ekran: yalniz anlik izleme acikken, nedeniyle; ayar sayfasini KULLANICI degistirir", () => {
    const D = { zarf: true, izin: true, izinGerekli: true, pilMuaf: true, calisiyor: false, izleme: "durduruldu", anlik: true, kapali: [], dil: "tr", uretici: "honor" };
    expect(bildirimGorunumu(D, { kimlik: KIMLIK }).yonerge.uretici).toBe("honor");
    expect(bildirimGorunumu({ ...D, uretici: undefined }, { kimlik: KIMLIK }).yonerge.uretici).toBe("diger");
    const v = kaynak("src/telefon/BildirimBolumu.vue");
    const pil = v.slice(v.indexOf('<template v-if="g.pilGoster">'));
    expect(pil).toMatch(/data-bt-bl-yonerge[^>]*:aria-expanded="yonergeAcik \? 'true' : 'false'"[^>]*aria-controls="bt-bl-yonerge"/);
    expect(pil).toMatch(/m\.bl\.yn_neden[^]*<ol class="bt-adimlar">[^]*m\.bl\.yn_not[^]*data-bt-bl-ayarlari-ac/);
    expect(SOZLUK_MOBIL["m.bl.yn_not"].tr).toMatch(/uygulama değiştiremez/);
    const kt = kaynak("android/app/src/main/java/tr/olcumkarti/mobil/bildirim/BildirimPlugin.kt");
    expect(kt).toContain("Settings.ACTION_APPLICATION_DETAILS_SETTINGS");
    expect(kt).toContain('.put("uretici", Uretici.sinifi(Build.MANUFACTURER, Build.BRAND))');
    // Model / surum WebView'e gitmez.
    expect(kt).not.toMatch(/Build\.(MODEL|DEVICE|PRODUCT|SERIAL|FINGERPRINT|DISPLAY)|VERSION\.RELEASE/);
  });
});
