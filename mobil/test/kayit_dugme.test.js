// 5C duzeltmeleri (curutucu 5C) + pil testi surerken salt okuma (A40): kayit dugmesinin mantigi,
// etkin oturumun turu, eski olcumun gosterilmemesi, grafikte "veri yok", kabugun yeniden aramasi.
// Saf islevler + GERCEK kabukDurumu (canli ve kart SAHTE); Vue bilesenleri kaynak olarak denetlenir.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { seriHazirla } from "@ortak/grafik.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { pencereSerileri, verisizleriAt } from "../src/ekran/canli_gorunum.js";
import { KDR, OTURUM_TURU, gorunenOlcum, kayitGorunumu, oturumKilidi, oturumTuruBul } from "../src/ekran/durum_gorunum.js";
import { HIZ_OMRU_MS, YENIDEN_ARA_MS, kabukDurumu } from "../src/ekran/kabuk_durum.js";
import { ONAY_MS, dokunus, dugmeHali, durdurOnayi } from "../src/ekran/kayit_dugme.js";

const vue = (ad) => readFileSync(fileURLToPath(new URL(`../src/ekran/${ad}`, import.meta.url)), "utf8");
const G = (durum, ek = {}) => ({ tur: "G", durum, oturum: 53, nokta: 0, doluluk: 380, onaysiz: 40, ...ek });
const BAGLI = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" };
const akis = (hal, kayit = G(KDR.BOS)) => ({ hazir: true, hal, bagli: hal === "acik", son: null, kayit });
const bosalt = () => new Promise((c) => setTimeout(c, 0));

describe("kayit dugmesi (saf)", () => {
  it("kapalilik kartin BAGLI olmasina bakar, akisin acik olmasina DEGIL: akis hatadayken de basilabilir", () => {
    for (const hal of ["acik", "hata", "baglaniyor", "dolu", "kapali"]) {
      expect(dugmeHali({ baglanti: BAGLI, akis: akis(hal) }), hal).toMatchObject({ is: "baslat", kapali: false });
      expect(dugmeHali({ baglanti: BAGLI, akis: akis(hal, G(KDR.KAYIT)) }), hal).toMatchObject({ is: "durdur", kapali: false });
    }
    for (const baglanti of [null, { durum: "eslesmemis" }, { durum: "bulunamadi" }, { durum: "kimlik-uymuyor" }, { durum: "kasa-bozuk" }]) {
      expect(dugmeHali({ baglanti, akis: akis("acik") }).kapali).toBe(true);
    }
    // Akis modulu yok / henuz kurulmadi: komut yolu da yok.
    expect(dugmeHali({ baglanti: BAGLI, akis: { hazir: false, hal: "kapali", kayit: null } }).kapali).toBe(true);
    expect(dugmeHali({ baglanti: BAGLI, akis: { hazir: null, hal: "kapali", kayit: null } }).kapali).toBe(true);
    expect(dugmeHali({ baglanti: BAGLI, akis: null }).kapali).toBe(true);
    expect(dugmeHali().kapali).toBe(true);
  });

  it("komut surerken ve kart kayit baslatamazken (dolu / hata / tariyor) KAPALI + neden", () => {
    expect(dugmeHali({ baglanti: BAGLI, akis: akis("acik"), suruyor: true }).kapali).toBe(true);
    expect(dugmeHali({ baglanti: BAGLI, akis: akis("acik", G(KDR.DOLU)) })).toEqual({ is: "baslat", kapali: true, neden: "kayit.durum.3", nedenDeger: null, aciklama: null });
    expect(dugmeHali({ baglanti: BAGLI, akis: akis("acik", G(KDR.TARIYOR)) })).toMatchObject({ kapali: true, neden: "kayit.durum.0" });
    expect(dugmeHali({ baglanti: BAGLI, akis: akis("acik", G(9)) })).toMatchObject({ kapali: true, neden: "kayit.durum.bilinmeyen", nedenDeger: { kod: 9 } });
    expect(dugmeHali({ baglanti: BAGLI, akis: akis("acik", null) })).toMatchObject({ is: "baslat", kapali: false, neden: null });
  });

  it("pil testi suruyorsa SALT OKUMA: dugme kapali + aciklama; tur bilinmiyorsa / olcumse / skopsa ACIK", () => {
    const kayitta = akis("acik", G(KDR.KAYIT));
    expect(dugmeHali({ baglanti: BAGLI, akis: kayitta, oturumTuru: OTURUM_TURU.PIL })).toEqual({ is: "durdur", kapali: true, neden: null, nedenDeger: null, aciklama: "m.dr.pil_salt_okuma" });
    for (const tur of [null, OTURUM_TURU.OLCUM, OTURUM_TURU.SKOP, 7]) {
      expect(dugmeHali({ baglanti: BAGLI, akis: kayitta, oturumTuru: tur }), String(tur)).toMatchObject({ is: "durdur", kapali: false, aciklama: null });
    }
  });

  it("'durdur' IKI dokunus ister; onay ONAY_MS sonra kendiliginden duser; 'baslat' tek dokunus", () => {
    expect(ONAY_MS).toBe(4000);
    const isler = [];
    const onaylar = [];
    const onayci = durdurOnayi({
      degisti: (v) => onaylar.push(v),
      zamanla: (fn, ms) => { const k = { fn, ms }; isler.push(k); return k; },
      zamaniBirak: (k) => { const i = isler.indexOf(k); if (i >= 0) isler.splice(i, 1); },
    });
    const durdur = { is: "durdur", kapali: false };
    expect(dokunus(durdur, onayci)).toBe(null);                  // 1. dokunus: yalniz onay istenir
    expect(onaylar).toEqual([true]);
    expect(isler.map((k) => k.ms)).toEqual([ONAY_MS]);
    expect(dokunus(durdur, onayci)).toBe("durdur");              // 2. dokunus: komut
    expect(onaylar).toEqual([true, false]);
    expect(isler).toEqual([]);
    // Onay suresi dolarsa bastan: yine iki dokunus.
    expect(dokunus(durdur, onayci)).toBe(null);
    isler.shift().fn();
    expect(onaylar.at(-1)).toBe(false);
    expect(dokunus(durdur, onayci)).toBe(null);
    onayci.birak();
    expect(isler).toEqual([]);
    expect(dokunus({ is: "baslat", kapali: false }, onayci)).toBe("baslat");
    expect(() => durdurOnayi({})).toThrow(TypeError);
  });

  it("KAPALI dugme hicbir sey yapmaz: ne komut ne onay adimi", () => {
    let basildi = 0;
    const onayci = { bas: () => { basildi += 1; return true; } };
    expect(dokunus({ is: "baslat", kapali: true }, onayci)).toBe(null);
    expect(dokunus({ is: "durdur", kapali: true }, onayci)).toBe(null);
    expect(dokunus(null, onayci)).toBe(null);
    expect(basildi).toBe(0);
  });

  it("KayitDugmesi.vue mantigi saf modulden alir: iki dugme de dugme.kapali ile kapanir, dokunus tek isleyicide", () => {
    const k = vue("KayitDugmesi.vue");
    expect(k).toContain('<button v-if="dugme.is === \'durdur\'" id="kayit-durdur" type="button" class="dugme" :disabled="dugme.kapali" @click="bas">');
    expect(k).toContain('<button v-else id="kayit-baslat" type="button" class="dugme ana" :disabled="dugme.kapali" @click="bas">');
    expect(k).toContain("const is = dokunus(dugme.value, onayci);");
    expect(k).toContain("baglanti: kabuk.baglanti.value, akis: kabuk.akis.value, suruyor: suruyor.value, oturumTuru: kabuk.oturumTuru.value,");
    expect(k).toContain('<p v-if="dugme.aciklama" id="kayit-salt-okuma" class="bilgi uyari">{{ c(dugme.aciklama) }}</p>');
    expect(k).not.toMatch(/setTimeout|canliHali|hal\.komut/);
  });
});

describe("etkin oturumun turu (A40)", () => {
  const liste = { surum: 2, oturumlar: [{ id: 52, tur: 1 }, { id: 53, tur: 2 }, { id: 54, tur: 3 }, { id: 55 }, null, "x"] };

  it("oturumTuruBul: /kayit/liste'den id = oturum olan kaydin turu; bulunamazsa / bozuksa null", () => {
    expect(oturumTuruBul(liste, 52)).toBe(1);
    expect(oturumTuruBul(liste, 53)).toBe(2);
    expect(oturumTuruBul(liste, 54)).toBe(3);
    expect(oturumTuruBul(liste, 55)).toBe(null);                 // tur alani yok
    expect(oturumTuruBul(liste, 99)).toBe(null);
    for (const bozuk of [null, undefined, "x", {}, { oturumlar: "x" }, []]) expect(oturumTuruBul(bozuk, 53)).toBe(null);
    expect(oturumTuruBul(liste, null)).toBe(null);
    expect(oturumTuruBul({ oturumlar: [{ id: 53, tur: "2" }] }, 53)).toBe(null);
  });

  it("oturumKilidi: pil -> salt okuma + rozet + aciklama; skop -> yalniz rozet; olcum / bilinmiyor -> hicbiri", () => {
    expect(OTURUM_TURU).toEqual({ OLCUM: 1, PIL: 2, SKOP: 3 });
    expect(oturumKilidi(2)).toEqual({ saltOkuma: true, rozet: "m.dr.pil_testi", aciklama: "m.dr.pil_salt_okuma" });
    expect(oturumKilidi(3)).toEqual({ saltOkuma: false, rozet: "m.dr.skop_gunlugu", aciklama: null });
    for (const tur of [1, null, undefined, 0, 9]) expect(oturumKilidi(tur)).toEqual({ saltOkuma: false, rozet: null, aciklama: null });
    expect(SOZLUK_MOBIL["m.dr.pil_testi"].tr).toBe("Pil testi sürüyor");
    expect(SOZLUK_MOBIL["m.dr.skop_gunlugu"].tr).toBe("Osiloskop günlüğü");
    expect(SOZLUK_MOBIL["m.dr.pil_salt_okuma"].tr).toBe("Pil testi karttan ya da panelden yönetilir. Acil durumda DURDUR.");
  });

  it("Canli ve Durum rozeti gosterir; Canli'da hiz secici salt okumada KAPALI", () => {
    const c = vue("Canli.vue"), d = vue("Durum.vue");
    for (const k of [c, d]) expect(k).toContain("const kilit = computed(() => oturumKilidi(kabuk.oturumTuru.value));");
    expect(c).toContain('<p v-if="kilit.rozet" id="cn-oturum-turu"><span class="rozet uyari">{{ c(kilit.rozet) }}</span></p>');
    expect(d).toContain('<span v-if="kilit.rozet" id="dr-oturum-turu" class="rozet uyari">{{ c(kilit.rozet) }}</span>');
    expect(c).toContain(':disabled="kayitSuruyor || kilit.saltOkuma" @click="hiz = h.ms"');
  });
});

describe("eski olcum gosterilmez; grafikte okunamayan kanal 'veri yok'", () => {
  it("gorunenOlcum: yalniz akis ACIKKEN; hata / baglaniyor / dolu / kapali -> null", () => {
    const son = { tur: "D", v: 12, a: 1, w: 12, adcHata: 0 };
    expect(gorunenOlcum("acik", son)).toBe(son);
    for (const hal of ["hata", "baglaniyor", "dolu", "kapali", undefined]) expect(gorunenOlcum(hal, son), String(hal)).toBe(null);
    expect(gorunenOlcum("acik", null)).toBe(null);
  });

  it("Durum.vue olcumu Canli.vue ile AYNI kosula baglar", () => {
    const satir = "olcumYazilari(hal.value.akiyor ? kabuk.akis.value.son : null)";
    expect(vue("Durum.vue")).toContain(satir);
    expect(vue("Canli.vue")).toContain(satir);
    expect(vue("Durum.vue")).not.toContain("olcumYazilari(kabuk.akis.value.son)");
  });

  it("verisizleriAt / pencereSerileri: NaN noktalar kanalin KENDI dizisinden cikar; otekiler etkilenmez", () => {
    const t = Float64Array.from([1000, 2000, 3000, 4000]);
    const tam = Float64Array.from([1, 2, 3, 4]);
    expect(verisizleriAt(t, tam).t).toBe(t);                      // hepsi sonlu: kopya yok
    const d = verisizleriAt(t, Float64Array.from([1, NaN, Infinity, 4]));
    expect([Array.from(d.t), Array.from(d.y)]).toEqual([[1000, 4000], [1, 4]]);
    const seri = { t, v: Float64Array.from([12, NaN, 12, 12]), a: Float64Array.from([1, 2, NaN, 1]), w: Float64Array.from([12, NaN, NaN, 12]), n: 4 };
    const p = pencereSerileri(seri, 60000, "a");
    expect(p.n).toBe(4);
    expect(p.seriler.map((s) => [Array.from(s.t), Array.from(s.y)])).toEqual([
      [[1000, 3000, 4000], [12, 12, 12]],
      [[1000, 2000, 4000], [1, 2, 1]],
      [[1000, 4000], [12, 12]],
    ]);
    for (const s of p.seriler) expect(() => seriHazirla(s)).not.toThrow();
    for (const s of p.seriler) expect(Array.from(s.y).every(Number.isFinite)).toBe(true);
  });
});

// ── kabuk: GERCEK kabukDurumu, canli ve kart sahte ────────────────────────
function sahteler({ liste = null, listeHata = false, komutHata = { v: false } } = {}) {
  const olay = [];
  let hal = "kapali", son = null, kayit = null, dinleyen = null;
  const kart = {
    d: { durum: "bagli-degil", adres: null, kimlik: null },
    adres: "192.168.1.7:80",
    durum() { return this.d; },
    async baglan() {
      olay.push("baglan");
      this.d = { durum: "bagli", adres: this.adres, kimlik: "0123456789abcdef" };
      return { ...this.d, bilgi: {} };
    },
    async istek(yontem, yol) {
      olay.push(["istek", yontem, yol]);
      if (listeHata) throw Object.assign(new Error("x"), { tur: "ag" });
      return { json: async () => liste };
    },
  };
  const canli = {
    baslat(s) { olay.push(["baslat", s && s.koru === true]); hal = "baglaniyor"; },
    durdur() { olay.push("durdur"); hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son, kayit, yas_ms: 0 }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; },
    seri: () => null,
    komut: async () => { if (komutHata.v) throw Object.assign(new Error("x"), { tur: "komut-ret" }); return true; },
  };
  const saat = { ms: 1000000 };
  const aralik = { fn: null };
  const k = kabukDurumu({
    kartAl: async () => kart, canliAl: async () => canli, belge: null, simdiMs: () => saat.ms,
    araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
  });
  const yay = (yeni) => { ({ hal = hal, son = son, kayit = kayit } = yeni); if (dinleyen) dinleyen(); };
  return { k, kart, olay, saat, aralik, yay, istekler: () => olay.filter((o) => Array.isArray(o) && o[0] === "istek") };
}

describe("kabuk: etkin oturumun turu BIR kez okunur", () => {
  it("kayit surerken oturum degisince imzali GET /kayit/liste; pil -> 2; ayni oturumda yeniden SORULMAZ", async () => {
    const s = sahteler({ liste: { oturumlar: [{ id: 53, tur: 2 }, { id: 54, tur: 1 }] } });
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    expect(s.istekler()).toEqual([]);                            // kayit yokken sorulmaz
    expect(s.k.oturumTuru.value).toBe(null);
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 53, nokta: 1 }) });
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 53, nokta: 2 }) });
    await bosalt();
    expect(s.istekler()).toEqual([["istek", "GET", "/kayit/liste"]]);
    expect(s.k.oturumTuru.value).toBe(2);
    expect(dugmeHali({ baglanti: s.k.baglanti.value, akis: s.k.akis.value, oturumTuru: s.k.oturumTuru.value })).toMatchObject({ is: "durdur", kapali: true });
    // Yeni oturum: yeniden sorulur; o arada tur BILINMIYOR.
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 54, nokta: 0 }) });
    expect(s.k.oturumTuru.value).toBe(null);
    await bosalt();
    expect(s.istekler().length).toBe(2);
    expect(s.k.oturumTuru.value).toBe(1);
    // Kayit bitti: tur silinir.
    s.yay({ kayit: G(KDR.BOS) });
    expect(s.k.oturumTuru.value).toBe(null);
  });

  it("tur OKUNAMAZSA (ag hatasi / listede yok) bilinmiyor kalir ve dugmeler ACIK; yeniden denenmez", async () => {
    for (const secenek of [{ listeHata: true }, { liste: { oturumlar: [] } }, { liste: null }]) {
      const s = sahteler(secenek);
      await s.k.ac();
      s.yay({ hal: "acik", kayit: G(KDR.KAYIT, { oturum: 53 }) });
      await bosalt();
      s.yay({ kayit: G(KDR.KAYIT, { oturum: 53, nokta: 5 }) });
      await bosalt();
      expect(s.istekler().length).toBe(1);
      expect(s.k.oturumTuru.value).toBe(null);
      expect(dugmeHali({ baglanti: s.k.baglanti.value, akis: s.k.akis.value, oturumTuru: s.k.oturumTuru.value }).kapali).toBe(false);
    }
  });

  it("gec gelen yanit BASKA oturuma yazilmaz", async () => {
    const s = sahteler({ liste: { oturumlar: [{ id: 53, tur: 2 }] } });
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.KAYIT, { oturum: 53 }) });
    s.yay({ kayit: G(KDR.BOS) });                                // yanit gelmeden kayit bitti
    await bosalt();
    expect(s.k.oturumTuru.value).toBe(null);
  });
});

describe("kabuk: yeniden arama (curutucu 5C, bulgu 2 ve 5)", () => {
  it("akis YENIDEN_ARA_MS'dir hatada: kart 'bagli' gorunse de KOSULSUZ aranir; adres ayniysa akisa DOKUNULMAZ", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik" });
    s.yay({ hal: "hata" });
    s.saat.ms += YENIDEN_ARA_MS - 1000;
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(1);
    s.saat.ms += 1000;
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(2);
    expect(s.olay.filter((o) => o === "durdur")).toEqual([]);      // canli'nin kendi dongusu (geri cekilme) surer
    // Hata surdukce her YENIDEN_ARA_MS'de bir.
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(2);
    s.saat.ms += YENIDEN_ARA_MS;
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(3);
  });

  it("adres DEGISTIYSE akis yeni adresle, geri cekilme sayaci KORUNARAK yeniden acilir", async () => {
    const s = sahteler();
    await s.k.ac();
    expect(s.olay.at(-1)).toEqual(["baslat", false]);              // ilk acilis: sayac sifirdan
    s.yay({ hal: "hata" });
    s.kart.adres = "192.168.1.23:80";
    s.saat.ms += YENIDEN_ARA_MS;
    s.aralik.fn();
    await bosalt();
    expect(s.k.baglanti.value.adres).toBe("192.168.1.23:80");
    expect(s.olay.slice(-3)).toEqual(["baglan", "durdur", ["baslat", true]]);
  });

  it("eslestirme surerken (mesgulYap) kart yeniden ARANMAZ; bitince aranir", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "hata" });
    s.k.mesgulYap(true);
    s.saat.ms += YENIDEN_ARA_MS;
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(1);
    s.k.mesgulYap(false);
    s.aralik.fn();
    await bosalt();
    expect(s.olay.filter((o) => o === "baglan").length).toBe(2);
    expect(vue("Baglanti.vue")).toContain("watch(eslesiyor, (v) => mesgulYap(v));");
  });
});

describe("kabuk: bu telefonun Gb hizi yalniz TAZE ve GORULEN baslangica yazilir", () => {
  it("HIZ_OMRU_MS icinde gorulen BOS -> KAYIT: hiz yazilir; sure dolduysa yazilmaz (olculur)", async () => {
    expect(HIZ_OMRU_MS).toBe(10000);
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    await s.k.kayitBaslat(100);
    s.saat.ms += HIZ_OMRU_MS;
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 60 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 60, hizMs: 100, olculen: false });
    s.yay({ kayit: G(KDR.BOS) });
    await s.k.kayitBaslat(100);
    s.saat.ms += HIZ_OMRU_MS + 1;
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 61 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 61, hizMs: null });
    expect(kayitGorunumu(s.k.akis.value.kayit, s.k.izleme.value, s.saat.ms).hiz).toBe(null);
  });

  it("REDDEDILEN Gb'nin hizi unutulur: hemen ardindan baskasinin baslattigi kayda yazilmaz", async () => {
    const komutHata = { v: true };
    const s = sahteler({ komutHata });
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    await expect(s.k.kayitBaslat(1000)).rejects.toMatchObject({ tur: "komut-ret" });
    s.saat.ms += 500;                                  // omur DOLMADAN: baskasi (PC / panel) kayit baslatti
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 80 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 80, hizMs: null });
    // Kabul edilen Gb'de ayni akis hizi YAZAR (test gercekten ret yolunu olcuyor).
    s.yay({ kayit: G(KDR.BOS) });
    komutHata.v = false;
    await s.k.kayitBaslat(1000);
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 81 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 81, hizMs: 1000 });
  });

  it("baslangici GORULMEYEN kayda (ilk G zaten KAYIT) bekleyen hiz yazilmaz", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik" });
    await s.k.kayitBaslat(100);
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 70, nokta: 500 }) });
    expect(s.k.izleme.value).toMatchObject({ oturum: 70, hizMs: null });
  });
});
