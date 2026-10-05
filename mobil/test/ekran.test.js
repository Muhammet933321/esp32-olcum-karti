// 5C ekranlari: durum -> gorunum eslemesi saf islevlerde (Durum A39, Canli A40) + kabugun ortak
// durumu (kart baglantisi, canli akis, one / arkaya gecis A6). canli'nin SAHTESI kullanilir.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { SOZLUK } from "@ortak/sozluk.js";
import { seriHazirla } from "@ortak/grafik.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import {
  BIRIM, DURDUR_KOMUTU, HIZLAR, PENCERELER, VARSAYILAN_HIZ_MS, canliHali, hizKomutu, kayitDugmesi, pencereSerileri,
} from "../src/ekran/canli_gorunum.js";
import {
  KDR, OLCUM_EN_AZ_MS, YOK, amperYaz, baglantiGorunumu, gAlan, gecenYaz, hizYaz, kayitGorunumu, kayitIzle, kayitSuresi,
  olcumYazilari, sureYaz, voltYaz, wattYaz,
} from "../src/ekran/durum_gorunum.js";
import { YENIDEN_ARA_MS, YENIDEN_DENE_MS, kabukDurumu } from "../src/ekran/kabuk_durum.js";
import { OZET_HANE, pbkdf2Gorunumu } from "../src/ekran/olcum_gorunum.js";

const vue = (ad) => readFileSync(fileURLToPath(new URL(`../src/ekran/${ad}`, import.meta.url)), "utf8");
const varMi = (anahtar) => Object.hasOwn(SOZLUK_MOBIL, anahtar) || Object.hasOwn(SOZLUK, anahtar);
const G = (durum, ek = {}) => ({ tur: "G", durum, oturum: 53, nokta: 0, sonraki: 54, onay: 0, doluluk: 380, onaysiz: 40, dusen: 0, ...ek });

describe("sayi ve sure yazilari", () => {
  it("V 3 hane, A 3 hane, W 2 hane; sonlu olmayan -> cizgi", () => {
    expect(voltYaz(12.4824)).toBe("12.482");
    expect(amperYaz(1.936049)).toBe("1.936");
    expect(wattYaz(24.1663)).toBe("24.17");
    expect(voltYaz(230.456)).toBe("230.46");
    expect(wattYaz(1234.56)).toBe("1234.6");
    expect(amperYaz(-0.0004)).toBe("-0.000");
    for (const x of [NaN, Infinity, null, undefined, "12"]) expect(voltYaz(x)).toBe(YOK);
  });

  it("olcumYazilari: D satirindan; ADC hatasinda o kanal ve guc YOK; olcum yoksa hepsi YOK", () => {
    expect(olcumYazilari({ tur: "D", v: 12.4824, a: 1.936, w: 24.1663, adcHata: 0 })).toEqual({ v: "12.482", a: "1.936", w: "24.17" });
    expect(olcumYazilari({ v: 1.7157, a: 1.936, w: 3.3, adcHata: 1 })).toEqual({ v: YOK, a: "1.936", w: YOK });
    expect(olcumYazilari({ v: 12, a: 0, w: 0, adcHata: 2 })).toEqual({ v: "12.000", a: YOK, w: YOK });
    expect(olcumYazilari(null)).toEqual({ v: YOK, a: YOK, w: YOK });
  });

  it("sureYaz, hizYaz, gecenYaz", () => {
    expect(sureYaz(5050000)).toBe("01:24:10");
    expect(sureYaz(0)).toBe("00:00:00");
    expect(sureYaz(100 * 3600000)).toBe("100:00:00");
    expect(sureYaz(null)).toBe(YOK);
    expect(hizYaz(200)).toEqual({ yazi: "5/s", yaklasik: false });
    expect(hizYaz(1000)).toEqual({ yazi: "1/s", yaklasik: false });
    expect(hizYaz(20)).toEqual({ yazi: "50/s", yaklasik: false });
    expect(hizYaz(10000, true)).toEqual({ anahtar: "cn.hiz_s", degerler: { s: 10 }, yaklasik: true });
    expect(hizYaz(60000)).toEqual({ anahtar: "cn.hiz_dk", degerler: { dk: 1 }, yaklasik: false });
    expect(hizYaz(0)).toBe(null);
    expect(hizYaz(null)).toBe(null);
    expect(gecenYaz(2400)).toEqual({ anahtar: "m.dr.once_sn", degerler: { n: 2 } });
    expect(gecenYaz(125000)).toEqual({ anahtar: "m.dr.once_dk", degerler: { n: 2 } });
    expect(gecenYaz(7200000)).toEqual({ anahtar: "m.dr.once_sa", degerler: { n: 2 } });
    expect(gecenYaz(-1)).toBe(null);
  });
});

describe("Durum: aktif kayit karti (G satirindan)", () => {
  it("G satiri yok -> 'kayit durumu bilinmiyor'; kayit yok (BOS) -> 'kayit yok'", () => {
    expect(kayitGorunumu(null, null, 0)).toMatchObject({ var: false, suruyor: false, rozet: "m.dr.kayit_bilinmiyor", doluluk: null });
    expect(kayitGorunumu(G(KDR.BOS), null, 0)).toMatchObject({ var: true, suruyor: false, rozet: "m.dr.kayit_yok", doluluk: 38, onaysiz: 4 });
  });

  it("kayit suruyor: sure / hiz / doluluk / esitlenmemis bicimi (bu telefonun Gb'siyle)", () => {
    let iz = kayitIzle(null, G(KDR.BOS), 1000);
    iz = kayitIzle(iz, G(KDR.KAYIT, { nokta: 0 }), 2000, 200);
    iz = kayitIzle(iz, G(KDR.KAYIT, { nokta: 25250 }), 5052000, null);
    const g = kayitGorunumu(G(KDR.KAYIT, { nokta: 25250 }), iz, 5052000);
    expect(g).toMatchObject({ suruyor: true, rozet: "cn.kayit_suruyor", sure: "01:24:10", doluluk: 38, onaysiz: 4, oturum: 53 });
    expect(g.hiz).toEqual({ yazi: "5/s", yaklasik: false });
  });

  it("ilk G'de kayit zaten suruyorsa sure UYDURULMAZ; hiz nokta artisindan olculur (yaklasik)", () => {
    let iz = kayitIzle(null, G(KDR.KAYIT, { nokta: 1000 }), 0);
    expect(kayitSuresi(iz, 5000)).toBe(null);
    expect(kayitGorunumu(G(KDR.KAYIT, { nokta: 1000 }), iz, 5000)).toMatchObject({ suruyor: true, sure: YOK, hiz: null });
    iz = kayitIzle(iz, G(KDR.KAYIT, { nokta: 1025 }), OLCUM_EN_AZ_MS - 5000);
    expect(iz.hizMs).toBe(null);                                   // gozlem henuz kisa
    iz = kayitIzle(iz, G(KDR.KAYIT, { nokta: 1050 }), OLCUM_EN_AZ_MS);
    expect(iz).toMatchObject({ hizMs: 200, olculen: true });
    const g = kayitGorunumu(G(KDR.KAYIT, { nokta: 1050 }), iz, OLCUM_EN_AZ_MS);
    expect(g.hiz).toEqual({ yazi: "5/s", yaklasik: true });
    expect(g.sure).toBe("00:03:30");                               // 1050 nokta x 200 ms
  });

  it("kayit basladigini GORDUYSEK ve hiz bilinmiyorsa sure gorulen baslangictan; oturum degisince sifirlanir", () => {
    let iz = kayitIzle(null, G(KDR.BOS), 0);
    iz = kayitIzle(iz, G(KDR.KAYIT, { nokta: 0 }), 10000);
    expect(kayitSuresi(iz, 75000)).toBe(65000);
    const yeni = kayitIzle(iz, G(KDR.KAYIT, { oturum: 54, nokta: 0 }), 80000, 1000);
    expect(yeni).toMatchObject({ oturum: 54, basMs: 80000, hizMs: 1000 });
    // Baska oturumun izlemesi bu G'ye UYGULANMAZ.
    expect(kayitGorunumu(G(KDR.KAYIT, { oturum: 99 }), iz, 75000)).toMatchObject({ sure: YOK, hiz: null });
    expect(kayitIzle(yeni, G(KDR.BOS), 90000)).toMatchObject({ durum: KDR.BOS, oturum: null });
  });

  it("dolu / hata / bilinmeyen durum: ortak sozlukteki metin, uyari sinifi; doluluk 0..100'e kirpilir", () => {
    expect(kayitGorunumu(G(KDR.DOLU, { doluluk: 1000 }), null, 0)).toMatchObject({ rozet: "kayit.durum.3", sinif: "uyari", doluluk: 100 });
    expect(kayitGorunumu(G(KDR.HATA), null, 0).rozet).toBe("kayit.durum.5");
    expect(kayitGorunumu(G(9), null, 0)).toMatchObject({ rozet: "kayit.durum.bilinmeyen", rozetDeger: { kod: 9 } });
    for (const d of [0, 3, 4, 5]) expect(varMi(`kayit.durum.${d}`), d).toBe(true);
    expect(varMi("kayit.durum.bilinmeyen") && varMi("cn.kayit_suruyor") && varMi("cn.hiz_s") && varMi("cn.hiz_dk")).toBe(true);
    // Firmware'in uzun alan adlari da okunur.
    expect(gAlan({ doluluk_binde: 120 }, "doluluk", "doluluk_binde")).toBe(120);
    expect(gAlan(null, "durum")).toBe(null);
  });
});

describe("Durum: baglanti satiri", () => {
  const bagli = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" };

  it("bu agda / ulasilamiyor + son gorulme / araniyor", () => {
    // Veri AKARKEN "son gorulme" yazilmaz (saniyede bir "0 sn once" gorunup kayboluyordu — kullanici, 2026-10-05).
    for (const [son, simdi] of [[8000, 10000], [10000, 10000], [10400, 10000], [null, 10000]]) {
      expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal: "acik" }, sonGorulmeMs: son, simdiMs: simdi }))
        .toMatchObject({ anahtar: "m.dr.bu_agda", sinif: "iyi", gecen: null, esles: false, yeniden: false });
    }
    expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: false, hal: "kapali" }, sonGorulmeMs: 8000, simdiMs: 10000 }).gecen).toBe(null);
    // Veri gelmiyorken yazilir; saat tikten GERIDEYSE (veri tikler arasinda geldi) satir kaybolmaz: 0 sn.
    for (const hal of ["eski", "hata", "baglaniyor", "dolu"]) {
      expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal }, sonGorulmeMs: 8000, simdiMs: 10000 }).gecen, hal).toEqual({ anahtar: "m.dr.once_sn", degerler: { n: 2 } });
      expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal }, sonGorulmeMs: 10400, simdiMs: 10000 }).gecen, hal).toEqual({ anahtar: "m.dr.once_sn", degerler: { n: 0 } });
    }
    expect(baglantiGorunumu({ baglanti: null, sonGorulmeMs: 8000, simdiMs: 10000 }).gecen).toEqual({ anahtar: "m.dr.once_sn", degerler: { n: 2 } });
    expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal: "eski" }, sonGorulmeMs: null, simdiMs: 10000 }).gecen).toBe(null);
    // Kayit kartindaki "son veri" de ayni: saat gerideyken kaybolmaz.
    expect(kayitGorunumu({ tur: "G", durum: 1, oturum: 0, doluluk: 1, onaysiz: 1 }, null, 10000, { taze: false, sonGorulmeMs: 10400 }).sonVeri)
      .toEqual({ anahtar: "m.dr.once_sn", degerler: { n: 0 } });
    expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal: "hata" } })).toMatchObject({ anahtar: "m.dr.ulasilamiyor", yeniden: true });
    expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal: "dolu" } }).anahtar).toBe("m.cn.dolu");
    expect(baglantiGorunumu({ baglanti: bagli, akis: { hazir: true, hal: "baglaniyor" } }).anahtar).toBe("m.cn.baglaniyor");
    expect(baglantiGorunumu({ baglanti: null, araniyor: true })).toMatchObject({ anahtar: "m.dr.araniyor", yeniden: false });
    expect(baglantiGorunumu({ baglanti: null })).toMatchObject({ anahtar: "m.dr.ulasilamiyor", yeniden: true, gecen: null });
    expect(baglantiGorunumu({ baglanti: { durum: "bulunamadi" } })).toMatchObject({ anahtar: "m.dr.ulasilamiyor", yeniden: true });
  });

  it("eslesmemis / kimlik uymuyor / kasa bozuk -> 'Esles' (Ayarlar'a goturur)", () => {
    expect(baglantiGorunumu({ baglanti: { durum: "eslesmemis" } })).toMatchObject({ anahtar: "m.dr.eslesmemis", esles: true });
    expect(baglantiGorunumu({ baglanti: { durum: "kimlik-uymuyor" } })).toMatchObject({ anahtar: "m.bg.durum_kimlik", esles: true });
    expect(baglantiGorunumu({ baglanti: { durum: "kasa-bozuk" } })).toMatchObject({ anahtar: "m.dr.kasa_bozuk", esles: true });
    expect(vue("Durum.vue")).toContain('<button v-if="bag.esles" id="dr-esles" type="button" class="dugme ana" @click="ayarlaraGit">');
    expect(vue("Durum.vue")).toContain('const ayarlaraGit = () => yonlendirici.push(sekmeBul("ayarlar").yol);');
  });
});

describe("Canli", () => {
  const bagli = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" };

  it("hiz secici -> dogru Gb<ms> komutu; listede olmayan hiz komut OLMAZ", () => {
    expect(HIZLAR.map((h) => [h.yazi, hizKomutu(h.ms)])).toEqual([["1/s", "Gb1000"], ["5/s", "Gb200"], ["10/s", "Gb100"], ["50/s", "Gb20"]]);
    for (const h of HIZLAR) expect(h.yazi).toBe(`${1000 / h.ms}/s`);
    for (const x of [0, 50, 250, 60000, null, "200", NaN]) expect(hizKomutu(x), String(x)).toBe(null);
    expect(HIZLAR.some((h) => h.ms === VARSAYILAN_HIZ_MS)).toBe(true);
    expect(DURDUR_KOMUTU).toBe("Gd");
    expect(PENCERELER.map((p) => p.s)).toEqual([60, 300]);
  });

  it("kart yok -> 'kart bu agda degil'; yuva dolu -> '4 izleyici'; akis modulu yok -> 'akis hazir degil'", () => {
    expect(canliHali({ baglanti: null })).toMatchObject({ anahtar: "m.cn.kart_yok", akiyor: false, komut: false });
    expect(canliHali({ baglanti: { durum: "bulunamadi" } })).toMatchObject({ anahtar: "m.cn.kart_yok", komut: false });
    expect(canliHali({ baglanti: null, araniyor: true }).anahtar).toBe("m.dr.araniyor");
    expect(canliHali({ baglanti: bagli, akis: { hazir: true, hal: "hata" } })).toMatchObject({ anahtar: "m.cn.kart_yok", akiyor: false, komut: false });
    expect(canliHali({ baglanti: bagli, akis: { hazir: true, hal: "dolu" } })).toMatchObject({ anahtar: "m.cn.dolu", akiyor: false });
    expect(canliHali({ baglanti: bagli, akis: { hazir: false, hal: "kapali" } })).toMatchObject({ anahtar: "m.cn.akis_yok", komut: false });
    expect(canliHali({ baglanti: bagli, akis: { hazir: true, hal: "baglaniyor" } }).anahtar).toBe("m.cn.baglaniyor");
    expect(canliHali({ baglanti: bagli, akis: { hazir: true, hal: "acik" } })).toMatchObject({ anahtar: "m.dr.bu_agda", akiyor: true, komut: true });
    expect(canliHali({ baglanti: { durum: "eslesmemis" } })).toMatchObject({ anahtar: "m.dr.eslesmemis", esles: true, komut: false });
    expect(SOZLUK_MOBIL["m.cn.kart_yok"].tr).toBe("Kart bu ağda değil");
    expect(SOZLUK_MOBIL["m.cn.dolu"].tr).toBe("Karta 4 izleyici bağlı");
    // Akis akmiyorken ekrandaki rakamlar ESKI olcumu gostermez.
    expect(vue("Canli.vue")).toContain("olcumYazilari(hal.value.akiyor ? kabuk.akis.value.son : null)");
  });

  it("kayit dugmesi: kayit suruyor -> durdur; hazir -> baslat; dolu / hata -> kapali + neden", () => {
    expect(kayitDugmesi(G(KDR.KAYIT))).toEqual({ is: "durdur", neden: null });
    expect(kayitDugmesi(G(KDR.BOS))).toEqual({ is: "baslat", neden: null });
    expect(kayitDugmesi(null).is).toBe("baslat");
    expect(kayitDugmesi(G(KDR.DOLU))).toMatchObject({ is: "kapali", neden: "kayit.durum.3" });
    expect(kayitDugmesi(G(KDR.TARIYOR))).toMatchObject({ is: "kapali", neden: "kayit.durum.0" });
  });

  it("pencereSerileri: son 60 s / 5 dk; uc kanal ayni t; sag eksen TEK birim; bos veri atmaz", () => {
    const n = 400;
    const seri = { t: new Float64Array(n + 8), v: new Float64Array(n + 8), a: new Float64Array(n + 8), w: new Float64Array(n + 8), n };
    for (let i = 0; i < n; i++) { seri.t[i] = 1000000 + i * 1000; seri.v[i] = 12 + i / 1000; seri.a[i] = 1; seri.w[i] = 12; }
    const p = pencereSerileri(seri, 60000, "a");
    expect(p.sonT).toBe(1399000);
    expect(p.n).toBe(61);
    expect(p.seriler.map((s) => [s.ad, s.eksen, s.gizli, s.renk])).toEqual([["V", "sol", false, "volt"], ["A", "sag", false, "amper"], ["W", "sag", true, "watt"]]);
    expect(p.seriler[0].t[0]).toBe(1339000);
    expect(p.seriler[1].t).toBe(p.seriler[0].t);
    expect(p.seriler[0].y.length).toBe(61);
    expect(pencereSerileri(seri, 300000, "w").n).toBe(301);
    expect(pencereSerileri(seri, 300000, "w").seriler.map((s) => s.gizli)).toEqual([false, true, false]);
    for (const s of p.seriler) expect(() => seriHazirla(s)).not.toThrow();      // ortak/grafik.js'in bekledigi bicim
    for (const bos of [null, undefined, { t: new Float64Array(0), v: new Float64Array(0), a: new Float64Array(0), w: new Float64Array(0), n: 0 }]) {
      expect(pencereSerileri(bos, 60000)).toMatchObject({ seriler: [], n: 0 });
    }
    expect(BIRIM).toEqual({ v: "V", a: "A", w: "W" });
  });
});

// ── kabugun ortak durumu, canli'nin SAHTESIYLE ───────────────────────────
function sahteler({ baglan = "bagli", canliYok = false, canliBekle = null } = {}) {
  const olay = [];
  let hal = "kapali", son = null, kayit = null, dinleyen = null;
  const kart = {
    d: { durum: "bagli-degil", adres: null, kimlik: null },
    baglanSonucu: baglan,
    durum() { return this.d; },
    async baglan(s) {
      olay.push(["baglan", s.elle]);
      if (this.baglanSonucu === "kasa") throw Object.assign(new Error("kasa"), { tur: "kasa" });
      const var_ = this.baglanSonucu === "bagli" || this.baglanSonucu === "eslesmemis";
      this.d = var_ ? { durum: this.baglanSonucu, adres: "192.168.1.7:80", kimlik: "0123456789abcdef" } : { durum: "bagli-degil", adres: null, kimlik: null };
      return { durum: this.baglanSonucu, adres: this.d.adres, kimlik: this.d.kimlik, bilgi: {} };
    },
  };
  const canli = {
    baslat() { olay.push("baslat"); hal = "baglaniyor"; },
    durdur() { olay.push("durdur"); hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son, kayit, yas_ms: 0 }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; },
    seri: () => ({ t: new Float64Array(0), v: new Float64Array(0), a: new Float64Array(0), w: new Float64Array(0), n: 0 }),
    async komut(metin) { olay.push(["komut", metin]); if (metin === "Gd" && hal !== "acik") throw Object.assign(new Error("x"), { tur: "ag" }); return true; },
  };
  const belge = {
    visibilityState: "visible", dinleyen: null,
    addEventListener(ad, fn) { olay.push(["dinle", ad]); this.dinleyen = fn; },
    removeEventListener() { this.dinleyen = null; },
  };
  const saat = { ms: 1000000 };
  const aralik = { fn: null };
  const k = kabukDurumu({
    kartAl: async () => kart,
    canliAl: async () => { if (canliYok) throw new Error("canli-yok"); if (canliBekle) await canliBekle; return canli; },
    belge, simdiMs: () => saat.ms,
    araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
  });
  const yay = (yeni) => { ({ hal = hal, son = son, kayit = kayit } = yeni); if (dinleyen) dinleyen(); };
  return { k, kart, canli, belge, olay, saat, aralik, yay, dinliyor: () => dinleyen !== null };
}

describe("kabuk durumu (canli sahtesiyle)", () => {
  it("ac: kart bulunur, esliyse akis acilir; D ve G satirlari duruma yansir", async () => {
    const s = sahteler();
    await s.k.ac();
    expect(s.olay).toEqual([["dinle", "visibilitychange"], ["baglan", null], "baslat"]);
    expect(s.k.baglanti.value).toEqual({ durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" });
    expect(s.k.akis.value).toMatchObject({ hazir: true, hal: "baglaniyor" });
    const cizim = s.k.cizim.value;
    s.yay({ hal: "acik", son: { tur: "D", v: 12.482, a: 1.936, w: 24.17, adcHata: 0 }, kayit: G(KDR.BOS) });
    expect(s.k.akis.value).toMatchObject({ hal: "acik", bagli: true, son: { v: 12.482 }, kayit: { durum: KDR.BOS } });
    expect(s.k.sonGorulme.value).toBe(1000000);
    expect(s.k.cizim.value).toBe(cizim + 1);
    expect(s.k.izleme.value).toMatchObject({ durum: KDR.BOS });
  });

  it("arka plana gecince akis HEMEN kapanir, one gelince yeniden acilir (A6)", async () => {
    const s = sahteler();
    await s.k.ac();
    s.belge.visibilityState = "hidden";
    s.belge.dinleyen();
    expect(s.olay.at(-1)).toBe("durdur");
    expect(s.k.akis.value.hal).toBe("kapali");
    expect(s.aralik.fn).toBe(null);
    s.belge.visibilityState = "visible";
    s.belge.dinleyen();
    await new Promise((c) => setTimeout(c, 0));
    expect(s.olay.at(-1)).toBe("baslat");
    expect(s.olay.filter((o) => o[0] === "baglan").length).toBe(1);        // kart yeniden ARANMADI
  });

  it("canli beklenirken arka plana gecildiyse akis ACILMAZ", async () => {
    let birak = null;
    const s = sahteler({ canliBekle: new Promise((c) => { birak = c; }) });
    const soz = s.k.ac();
    await new Promise((c) => setTimeout(c, 0));          // kart bulundu; canli modulu hala yukleniyor
    expect(s.k.baglanti.value.durum).toBe("bagli");
    s.k.kapat();
    birak();
    await soz;
    expect(s.olay).not.toContain("baslat");
    // One gelince acilir.
    await s.k.ac();
    expect(s.olay.at(-1)).toBe("baslat");
  });

  it("eslesmemis / bulunamadi: akis acilmaz; kart yok durumu atlanmaz", async () => {
    for (const durum of ["eslesmemis", "bulunamadi"]) {
      const s = sahteler({ baglan: durum });
      await s.k.ac();
      expect(s.k.baglanti.value.durum).toBe(durum);
      expect(s.olay).not.toContain("baslat");
      expect(canliHali({ baglanti: s.k.baglanti.value, akis: s.k.akis.value }).akiyor).toBe(false);
    }
    const kasa = sahteler({ baglan: "kasa" });
    await kasa.k.ac();
    expect(kasa.k.baglanti.value.durum).toBe("kasa-bozuk");
  });

  it("canli modulu yoksa: baglanti durur, akis 'hazir degil', komut reddedilir", async () => {
    const s = sahteler({ canliYok: true });
    await s.k.ac();
    expect(s.k.akis.value).toMatchObject({ hazir: false, hal: "kapali" });
    expect(canliHali({ baglanti: s.k.baglanti.value, akis: s.k.akis.value }).anahtar).toBe("m.cn.akis_yok");
    await expect(s.k.kayitBaslat(200)).rejects.toMatchObject({ tur: "akis-yok" });
    expect(s.k.seri()).toBe(null);
  });

  it("kayitBaslat secilen hizin komutunu yollar ve o hizi yeni oturuma yazar; gecersiz hiz aga CIKMAZ", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    await s.k.kayitBaslat(1000);
    expect(s.olay.at(-1)).toEqual(["komut", "Gb1000"]);
    s.yay({ kayit: G(KDR.KAYIT, { nokta: 0 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 53, hizMs: 1000, olculen: false });
    await expect(s.k.kayitBaslat(250)).rejects.toMatchObject({ tur: "hiz-gecersiz" });
    expect(s.olay.filter((o) => o[0] === "komut").length).toBe(1);
    await s.k.kayitDurdur();
    expect(s.olay.at(-1)).toEqual(["komut", "Gd"]);
    s.yay({ hal: "hata" });
    await expect(s.k.kayitDurdur()).rejects.toMatchObject({ tur: "ag" });
  });

  it("kart bulunamadiysa aralikla yeniden dener; akis uzun sure hatadaysa karti yeniden arar", async () => {
    const s = sahteler({ baglan: "bulunamadi" });
    await s.k.ac();
    s.saat.ms += YENIDEN_DENE_MS - 1000;
    s.aralik.fn();
    expect(s.olay.filter((o) => o[0] === "baglan").length).toBe(1);
    s.kart.baglanSonucu = "bagli";
    s.saat.ms += 1000;
    s.aralik.fn();
    await new Promise((c) => setTimeout(c, 0));
    expect(s.k.baglanti.value.durum).toBe("bagli");
    expect(s.olay.at(-1)).toBe("baslat");
    expect(s.k.simdi.value).toBe(s.saat.ms);
    s.yay({ hal: "hata" });
    s.saat.ms += YENIDEN_ARA_MS;
    s.kart.d = { durum: "bagli-degil", adres: null, kimlik: null };
    s.aralik.fn();
    await new Promise((c) => setTimeout(c, 0));
    expect(s.olay.filter((o) => o[0] === "baglan").length).toBe(3);
  });

  it("baglantiDegisti (Ayarlar'dan): akis kapanir, yeni duruma gore kurulur; birak dinlemeyi kaldirir", async () => {
    const s = sahteler();
    await s.k.ac();
    await s.k.baglantiDegisti(null);
    expect(s.olay.at(-1)).toBe("durdur");
    expect(s.k.baglanti.value).toBe(null);
    await s.k.baglantiDegisti({ durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef", bilgi: { tur: 20000 } });
    expect(s.olay.at(-1)).toBe("baslat");
    expect(s.k.baglanti.value).toEqual({ durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" });
    s.k.birak();
    expect(s.dinliyor()).toBe(false);
    expect(s.belge.dinleyen).toBe(null);
  });
});

describe("Ayarlar > Gelismis: PBKDF2 olcumu gorunumu", () => {
  const o = { tur: 20000, sureler: [30, 29, 44], enAz: 29, ortanca: 30, enCok: 44, ozet: "3f042897317e112506e74084a8529f73c13d0720f75925a0d42d209d464cc676" };

  it("dogru / YANLIS / basvuru yok ayri metin; ozetin ilk 16 hanesi; sure yer tutuculari", () => {
    expect(pbkdf2Gorunumu({ ...o, dogru: true })).toEqual({ sure: { tur: 20000, enaz: 29, ortanca: 30, encok: 44 }, dogrulama: "m.ol.dogru", sinif: "", ozet: "3f042897317e1125" });
    expect(pbkdf2Gorunumu({ ...o, dogru: false })).toMatchObject({ dogrulama: "m.ol.yanlis", sinif: "hata" });
    expect(pbkdf2Gorunumu({ ...o, tur: 50000, dogru: null }).dogrulama).toBe("m.ol.basvuru_yok");
    expect(OZET_HANE).toBe(16);
    expect(new Set(["m.ol.dogru", "m.ol.yanlis", "m.ol.basvuru_yok"].map((a) => SOZLUK_MOBIL[a].tr)).size).toBe(3);
    expect(SOZLUK_MOBIL["m.ol.uygulama"].tr).toBe("Uygulama: saf JS (WebView)");
  });

  it("KartBul.vue: cikti id='pbkdf2-sonuc' altinda; kart bulunmadan da calisir (varsayilan 20 000 tur)", () => {
    const v = vue("KartBul.vue");
    expect(v).toContain('<div v-if="pbkdf2Suruyor || pbkdf2Sonuc" id="pbkdf2-sonuc" role="status">');
    expect(v).toContain("const PBKDF2_VARSAYILAN_TUR = 20000;");
    expect(v).toContain("Number.isInteger(sonuc.value?.bilgi?.tur) ? sonuc.value.bilgi.tur : PBKDF2_VARSAYILAN_TUR");
    expect(v).toContain("pbkdf2Sonuc.value = pbkdf2Gorunumu(pbkdf2Olc(tur));");
    for (const a of ['c("m.ol.pbkdf2_sonuc", pbkdf2Sonuc.sure)', "c(pbkdf2Sonuc.dogrulama)", 'c("m.ol.ozet", { ozet: pbkdf2Sonuc.ozet })', 'c("m.ol.uygulama")']) expect(v).toContain(a);
    expect(v).not.toMatch(/<ion-button id="pbkdf2"[^>]*disabled/);
  });
});
