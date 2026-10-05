// 5D-3 — Kayitlar ve kayit gorunumu: veri kaynagi (cekirdek/kayitlar.js), gorunum yardimcilari, ekran
// baglantilari. Istemci GERCEK (yedek yolu: islemci ana is parcaciginda), depo: depo.js + eklenti sahtesi
// (gercek dosyalar), kart SAHTE nesne.
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as Kayit from "../../ortak/src/kayit.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { depoKur } from "../src/cekirdek/depo.js";
import { depoAdresi, kayitIstemciKur } from "../src/cekirdek/kayit_istemci.js";
import { islemciKur, oturumGorunumu, veriKur } from "../src/cekirdek/kayit_veri.js";
import { KayitlarHatasi, kayitlarKur } from "../src/cekirdek/kayitlar.js";
import { SAG_EKSENLER, TUR_SECENEKLERI, kartNotu, okumaTablosu, satirGorunumu, sayiYaz } from "../src/ekran/kayitlar_gorunum.js";
import { ALT_ROTALAR, SEKMELER, sekmeBul } from "../src/ekran/sekmeler.js";
import { Akis, ikiOturum } from "./yardim/akis_ornek.mjs";
import { depoSahtesi } from "./yardim/depo_sahtesi.mjs";

const K = "0123456789abcdef";
const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../src/${yol}`, import.meta.url)), "utf8");

let dizin;
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "kayitlar-")); });
afterEach(() => { rmSync(dizin, { recursive: true, force: true }); });

// Duzenek: depoya `bayt` yazilir; istemci dosyayi depo sahtesinden (yerel adres yerine) okur.
async function duzenek({ bayt = null, kartDurum = { durum: "bagli", adres: "192.168.1.7:80", kimlik: K }, dizinYaniti = null, sonKimlik = () => null } = {}) {
  const ek = depoSahtesi(dizin);
  const depo = depoKur(ek, K);
  if (bayt) {
    await depo.veriEkle(bayt);
    await depo.durumYaz({ son_sira: 1, bayt: bayt.length, onaylanan: 0, kimlik: 7 });
  }
  const okunan = [];
  const istemci = kayitIstemciKur({
    isciKur: null,
    yedekKur: () => islemciKur({ getir: async (url) => { okunan.push(url); return ek.dosya(K) || new Uint8Array(0); } }),
  });
  const istekler = [];
  const kart = {
    d: kartDurum,
    durum() { return this.d; },
    async istek(yontem, yol) {
      istekler.push([yontem, yol]);
      if (dizinYaniti === null) throw Object.assign(new Error("x"), { tur: "ag" });
      return { json: async () => (typeof dizinYaniti === "function" ? dizinYaniti() : dizinYaniti) };
    },
  };
  const k = kayitlarKur({ istemci, kartAl: async () => kart, depoAl: (kimlik) => depoKur(ek, kimlik), sonKimlik });
  return { k, kart, ek, depo, okunan, istekler };
}

describe("kayitlar — liste", () => {
  it("kart bagli: dosya YEREL adresten okunur, kartin dizini imzali GET /kayit/liste ile; satirlar birlesir", async () => {
    const { bayt, a, b } = ikiOturum();
    const dz = { kimlik: 7, aktif: 0, oturumlar: [{ id: a, tur: 1, hiz_ms: 1000, unix_s: 1790000000, nokta: 60, durum: 2, son: 1 }, { id: 500, tur: 2, hiz_ms: 1000, unix_s: 1, nokta: 3, durum: 2, son: 600 }] };
    const s = await duzenek({ bayt, dizinYaniti: dz });
    const l = await s.k.liste();
    expect(l).toMatchObject({ kimlik: K, kartVar: true, bayt: bayt.length });
    expect(l.satirlar.map((x) => [x.oturum, x.nerede])).toEqual([[500, "kart"], [b, "telefon"], [a, "ikisi"]]);
    expect(s.okunan).toEqual([depoAdresi(K)]);
    expect(s.istekler).toEqual([["GET", "/kayit/liste"]]);
  });

  it("dosya yalniz DEGISTIYSE yeniden cozulur (boy / akis kimligi); arama ve tur suzgeci yeniden okutmaz", async () => {
    const { bayt } = ikiOturum();
    const s = await duzenek({ bayt, dizinYaniti: null });
    await s.k.liste();
    await s.k.liste({ arama: "aku" });
    await s.k.liste({ tur: "pil" });
    expect(s.okunan.length).toBe(1);
    const akis = new Akis(900);
    const yeni = akis.basla({ unix: 1790009999 });
    akis.noktalar(yeni, { adet: 3 });
    await s.depo.veriEkle(akis.bayt());                     // esitleme yeni kayit ekledi
    const l = await s.k.liste();
    expect(s.okunan.length).toBe(2);
    expect(l.satirlar.length).toBe(3);
    // Boy ayni kalsa da akis kimligi degistiyse (kopya sifirlanip baska akis indi) yeniden okunur.
    await s.depo.durumYaz({ son_sira: 1, bayt: 1, onaylanan: 0, kimlik: 8 });
    await s.k.liste();
    expect(s.okunan.length).toBe(3);
    s.k.bosalt();
    await s.k.liste();
    expect(s.okunan.length).toBe(4);
  });

  it("kartin dizini okunamazsa / kart bagli degilse: liste TELEFONDAN, kartVar false, HATA DEGIL", async () => {
    const { bayt } = ikiOturum();
    const agHatasi = await duzenek({ bayt, dizinYaniti: null });
    expect(await agHatasi.k.liste()).toMatchObject({ kartVar: false, satirlar: [{ nerede: "telefon" }, { nerede: "telefon" }] });
    rmSync(join(dizin, K), { recursive: true, force: true });
    const eslesmemis = await duzenek({ bayt, kartDurum: { durum: "eslesmemis", adres: "x", kimlik: K }, dizinYaniti: { oturumlar: [] } });
    expect((await eslesmemis.k.liste()).kartVar).toBe(false);
    expect(eslesmemis.istekler).toEqual([]);                // eslesmemis karta imzali istek atilmaz
  });

  it("DISARIDA (kart bagli degil): hangi kartin kopyasi oldugu son baglanilan karttan; hic kart bilinmiyorsa bos", async () => {
    const { bayt } = ikiOturum();
    const disarida = await duzenek({ bayt, kartDurum: { durum: "bagli-degil", adres: null, kimlik: null }, sonKimlik: () => K });
    const l = await disarida.k.liste();
    expect(l).toMatchObject({ kimlik: K, kartVar: false });
    expect(l.satirlar.length).toBe(2);
    expect(disarida.istekler).toEqual([]);
    for (const sonKimlik of [() => null, () => "bozuk", () => { throw new Error("depo kapali"); }]) {
      const yok = await duzenek({ kartDurum: { durum: "bagli-degil", adres: null, kimlik: null }, sonKimlik });
      expect(await yok.k.liste()).toEqual({ satirlar: [], kimlik: null, kartVar: false, bayt: 0 });
      expect(yok.okunan).toEqual([]);
    }
  });

  it("telefonda kopya yokken kart bagliysa: kartin oturumlari 'kart' olarak listelenir", async () => {
    const s = await duzenek({ dizinYaniti: { kimlik: 7, aktif: 41, oturumlar: [{ id: 41, tur: 1, hiz_ms: 0, unix_s: 5, nokta: 9, durum: 1, son: 50 }] } });
    const l = await s.k.liste();
    expect(l.satirlar).toMatchObject([{ oturum: 41, nerede: "kart", tur: "ayrinti", durum: "kayitta", yerelde: false }]);
  });

  it("kartAl atarsa liste telefondan (son kimlikle); depo okunamazsa KayitlarHatasi(tur), mesaj disari cikmaz", async () => {
    const { bayt } = ikiOturum();
    const s = await duzenek({ bayt, sonKimlik: () => K });
    const k2 = kayitlarKur({
      istemci: kayitIstemciKur({ isciKur: null, yedekKur: () => islemciKur({ getir: async () => s.ek.dosya(K) }) }),
      kartAl: async () => { throw new Error("kopru yok"); }, depoAl: (kimlik) => depoKur(s.ek, kimlik), sonKimlik: () => K,
    });
    expect((await k2.liste()).satirlar.length).toBe(2);
    const k3 = kayitlarKur({
      istemci: kayitIstemciKur({ isciKur: null, yedekKur: () => islemciKur({ getir: async () => null }) }),
      kartAl: async () => s.kart, depoAl: () => ({ veriBoyu: async () => { throw Object.assign(new Error("/data/gizli"), { tur: "okunamadi" }); }, durumOku: async () => null }),
    });
    const h = await k3.liste().catch((e) => e);
    expect(h).toBeInstanceOf(KayitlarHatasi);
    expect(h.tur).toBe("okunamadi");
    expect(h.message).not.toContain("gizli");
    expect(() => kayitlarKur({})).toThrow(TypeError);
  });

  it("durum.json bozuksa kopya yine de GOSTERILIR (salt okuma)", async () => {
    const { bayt } = ikiOturum();
    const s = await duzenek({ bayt });
    s.ek.bozDurum(K, Buffer.from("{bozuk"));
    expect((await s.k.liste()).satirlar.length).toBe(2);
  });

  it("KART degisince kopya yeniden cozulur: boy ve akis kimligi AYNI olsa da baska kartin listesi gosterilmez (curutucu 5D Y4)", async () => {
    const K2 = "fedcba9876543210";
    const kur = (ad) => { const ak = new Akis(100); const id = ak.basla(); ak.noktalar(id, { adet: 5 }); ak.ad(id, ad); ak.bitir(id, 5); return ak.bayt(); };
    const b1 = kur("kart-bir"), b2 = kur("kart-iki");
    expect(b1.length).toBe(b2.length);                         // on kosul: AYNI boy
    const s = await duzenek({ bayt: b1 });
    const d2 = depoKur(s.ek, K2);
    await d2.veriEkle(b2);
    await d2.durumYaz({ son_sira: 1, bayt: b2.length, onaylanan: 0, kimlik: 7 });   // AYNI akis kimligi
    const okunan = [];
    const istemci = kayitIstemciKur({ isciKur: null, yedekKur: () => islemciKur({ getir: async (url) => { okunan.push(url); return s.ek.dosya(url.includes(K2) ? K2 : K); } }) });
    const k = kayitlarKur({ istemci, kartAl: async () => s.kart, depoAl: (kimlik) => depoKur(s.ek, kimlik) });
    expect((await k.liste()).satirlar[0].ad).toBe("kart-bir");
    s.kart.d = { durum: "bagli", adres: "192.168.1.9:80", kimlik: K2 };
    const l2 = await k.liste();
    expect(l2.kimlik).toBe(K2);
    expect(l2.satirlar[0].ad).toBe("kart-iki");
    expect(okunan).toEqual([depoAdresi(K), depoAdresi(K2)]);
  });

  it("kopyanin AKIS kimligi isciye gider: kartin guncel akisi baskaysa telefondaki satirlar 'eski akis' isaretlenir, 'Kart + telefon' DENMEZ (curutucu 5D Y5)", async () => {
    const { bayt, a } = ikiOturum();
    // Telefondaki kopya akis 7'den; kart bicimlenmis, guncel akisi 8 ve AYNI numarali bir oturumu var.
    const dz = { kimlik: 8, aktif: 0, oturumlar: [{ id: a, tur: 1, hiz_ms: 1000, unix_s: 1790009000, nokta: 3, durum: 2, son: 200 }] };
    const s = await duzenek({ bayt, dizinYaniti: dz });
    const l = await s.k.liste();
    const ayni = l.satirlar.filter((x) => x.oturum === a);
    expect(ayni.map((x) => [x.nerede, x.eskiKart]).sort()).toEqual([["kart", false], ["telefon", true]]);
    expect(new Set(l.satirlar.map((x) => x.anahtar)).size).toBe(l.satirlar.length);
    expect(l.satirlar.some((x) => x.nerede === "ikisi")).toBe(false);
    // Akis ayniysa (7): birlesir.
    const s2 = await duzenek({ bayt: null, dizinYaniti: { ...dz, kimlik: 7 } });
    expect((await s2.k.liste()).satirlar.find((x) => x.oturum === a)).toMatchObject({ nerede: "ikisi", eskiKart: false });
  });

  it("art arda cagrilar SIRAYLA kosar: dosya ayni anda iki kez cozulmez", async () => {
    const { bayt } = ikiOturum();
    const s = await duzenek({ bayt });
    const [x, y, z] = await Promise.all([s.k.liste(), s.k.liste({ arama: "aku" }), s.k.liste()]);
    expect(s.okunan.length).toBe(1);
    expect([x.satirlar.length, y.satirlar.length, z.satirlar.length]).toEqual([2, 1, 2]);
  });
});

describe("kayitlar — oturum ve okuma", () => {
  it("oturum(no): liste cagrilmadan da kopyayi yukler; olmayan oturum null; okuma aralik istatistigi", async () => {
    const { bayt, a } = ikiOturum();
    const s = await duzenek({ bayt });
    expect(await s.k.okuma(a, 1000, 5000)).toBe(null);      // yuklenmeden okuma: null (atmaz)
    const g = await s.k.oturum(a);
    expect(g).toMatchObject({ oturum: a, tur: "nokta", adet: 60, gecerli: 60 });
    expect(s.okunan.length).toBe(1);
    expect(await s.k.oturum(99999)).toBe(null);
    expect((await s.k.okuma(a, 1000, 10000)).v.adet).toBe(10);
    const bos = await duzenek({ kartDurum: { durum: "bagli-degil", adres: null, kimlik: null } });
    expect(await bos.k.oturum(a)).toBe(null);
  });

  it("gecerli: ADC okunamadan kaydedilmis oturumda noktalar VAR ama gecerli olcum 0 (gercek kartta goruldu)", () => {
    const akis = new Akis(10);
    const id = akis.basla();
    // bayrak 6 = V_HATA | I_HATA, n = 0: kartin ADC'siz yazdigi nokta.
    {
      const u32 = new Uint8Array(4);
      const hatali = Kayit.noktaPaketle({ kart_ms: 6000, n: 0, bayrak: Kayit.KN_V_HATA | Kayit.KN_I_HATA, v_ort_kod: 0, v_min_kod: 0, v_maks_kod: 0, i_ort_kod: 0, i_min_kod: 0, i_maks_kod: 0, w_ort: 0, w_min: 0, w_maks: 0 });
      const yuk = new Uint8Array(4 + hatali.length);
      yuk.set(u32, 0);
      yuk.set(hatali, 4);
      akis.ekle(Kayit.T_NOKTA, id, yuk);
      const g = oturumGorunumu(veriKur(akis.bayt()), id);
      expect(g).toMatchObject({ tur: "nokta", adet: 1, gecerli: 0 });
      expect(Number.isNaN(g.seriler[0].y[0])).toBe(true);    // 0 V diye CIZILMEZ
    }
  });
});

describe("gorunum yardimcilari (saf)", () => {
  it("satirGorunumu: ad / tur / nerede anahtarlari; yalniz telefonda kopyasi olan acilabilir", () => {
    const s = { oturum: 41, tur: "olcum", ad: "Akü şarj", nerede: "ikisi", tarih: "2026-09-23 10:00:00", sure: "00:01:00", durum: "bitti", eksik: false, yerelde: true };
    expect(satirGorunumu(s)).toEqual({ anahtar: "41", eskiKart: false, oturum: 41, ad: "Akü şarj", tur: "m.ky.tur_olcum", nerede: "m.ky.nerede_ikisi", neredeSinif: "iyi", tarih: "2026-09-23 10:00:00", sure: "00:01:00", kayitta: false, eksik: false, acilabilir: true });
    expect(satirGorunumu({ ...s, ad: null, nerede: "kart", yerelde: false, durum: "kayitta", eksik: true, tarih: null, sure: null })).toMatchObject({ ad: null, nerede: "m.ky.nerede_kart", neredeSinif: "uyari", kayitta: true, eksik: true, acilabilir: false, tarih: null, sure: null });
    expect(satirGorunumu({ ...s, nerede: "telefon" })).toMatchObject({ nerede: "m.ky.nerede_telefon", neredeSinif: "" });
    for (const [tur, anahtar] of [["ayrinti", "m.ky.tur_ayrinti"], ["pil", "m.ky.tur_pil"], ["skop", "m.ky.tur_skop"], ["bilinmeyen", "m.ky.tur_bilinmeyen"], ["toString", "m.ky.tur_bilinmeyen"], [undefined, "m.ky.tur_bilinmeyen"]]) {
      expect(satirGorunumu({ ...s, tur }).tur, String(tur)).toBe(anahtar);
    }
    expect(satirGorunumu({ ...s, nerede: "constructor" }).nerede).toBe("m.ky.nerede_telefon");
    expect(satirGorunumu({ ...s, ad: "" }).ad).toBe(null);
    expect(satirGorunumu({ ...s, yerelde: 1 }).acilabilir).toBe(false);
    // Liste anahtari akis + oturum; eski akistan kalan satir isaretlenir (curutucu 5D B9).
    expect(satirGorunumu({ ...s, anahtar: "7:41", eskiKart: true })).toMatchObject({ anahtar: "7:41", eskiKart: true });
    expect(satirGorunumu({ ...s, anahtar: "", eskiKart: 1 })).toMatchObject({ anahtar: "41", eskiKart: false });
  });

  it("kartNotu: dizin listeye katilmadiysa NEDENI soylenir (kart agdayken 'bu agda degil' denmez)", () => {
    expect(kartNotu({ durum: "bagli" }, true)).toBe(null);
    expect(kartNotu(null, true)).toBe(null);
    expect(kartNotu({ durum: "bagli" }, false)).toBe("m.ky.kart_okunamadi");
    for (const d of ["eslesmemis", "kimlik-uymuyor", "kasa-bozuk"]) expect(kartNotu({ durum: d }, false), d).toBe("m.ky.kart_eslesmemis");
    for (const b of [null, undefined, {}, { durum: "bulunamadi" }, { durum: "bagli-degil" }, { durum: 5 }]) expect(kartNotu(b, false)).toBe("m.ky.kart_yok");
    expect(kartNotu({ durum: "bagli" }, 1)).toBe("m.ky.kart_okunamadi");            // yalniz kesin true "katildi" demek
    for (const a of ["m.ky.kart_okunamadi", "m.ky.kart_eslesmemis", "m.ky.kart_yok"]) expect(SOZLUK_MOBIL[a], a).toBeDefined();
  });

  it("okumaTablosu ve sayiYaz: sabit hane, sonlu olmayan '—'", () => {
    expect([sayiYaz(11.2244, 3), sayiYaz(0, 2), sayiYaz(NaN, 2), sayiYaz(null, 1), sayiYaz(Infinity, 1)]).toEqual(["11.224", "0.00", "—", "—", "—"]);
    const k = (ort, min, maks, birim) => ({ birim, adet: 32, ort, min, maks, rms: ort });
    const t = okumaTablosu({ dt: 31000, sure: "00:00:31", v: k(11.2244, 11.185, 11.272, "V"), i: k(0.0091, 0, 0.018, "A"), w: k(0.1, 0, 0.2, "W"), enerji: { wh: 0.00088, mah: 0.0731 } });
    expect(t).toEqual({ sure: "00:00:31", adet: 32, mah: "0.07", wh: "0.001", satirlar: [
      { anahtar: "m.cn.gerilim", birim: "V", ort: "11.224", min: "11.185", maks: "11.272" },
      { anahtar: "m.cn.akim", birim: "A", ort: "0.009", min: "0.000", maks: "0.018" },
      { anahtar: "m.cn.guc", birim: "W", ort: "0.10", min: "0.00", maks: "0.20" },
    ] });
    expect(okumaTablosu(null)).toBe(null);
    expect(okumaTablosu({ sure: null, v: null, i: k(null, null, null, "A"), w: null, enerji: null })).toEqual({ sure: "—", adet: 32, mah: "—", wh: "—", satirlar: [{ anahtar: "m.cn.akim", birim: "A", ort: "—", min: "—", maks: "—" }] });
  });

  it("secenek listeleri ve sozluk: her anahtar sozlukte; alt rota ust sekmenin basligini tasir", () => {
    expect(TUR_SECENEKLERI.map((t) => t.deger)).toEqual(["hepsi", "olcum", "pil", "skop"]);
    expect(SAG_EKSENLER.map((e) => e.deger)).toEqual(["akim", "guc"]);
    for (const a of [...TUR_SECENEKLERI.map((t) => t.anahtar), "m.ky.tur_ayrinti", "m.ky.tur_pil", "m.ky.tur_skop", "m.ky.nerede_kart", "m.kg.olcumsuz", "m.ky.adsiz"]) {
      expect(SOZLUK_MOBIL[a], a).toBeDefined();
    }
    expect(SOZLUK_MOBIL["m.ky.yakinda"]).toBeUndefined();
    expect(ALT_ROTALAR).toEqual({ kayit: "kayitlar" });
    expect(sekmeBul("kayit").ad).toBe("kayitlar");
    expect(sekmeBul("kayitlar").ad).toBe("kayitlar");
    expect(sekmeBul("toString")).toBe(SEKMELER[0]);
    expect(sekmeBul(undefined)).toBe(SEKMELER[0]);
  });
});

describe("ekran baglantilari (kaynak)", () => {
  it("rota: kayit gorunumu yalniz SAYISAL oturumla, tembel yuklenir; ust sekme secili gorunur", () => {
    const y = kaynak("yonlendirme.js");
    expect(y).toContain('{ path: "/kayitlar/:oturum(\\\\d+)", name: "kayit", component: () => import("./ekran/Kayit.vue") },');
    expect(y).not.toMatch(/^import Kayit from/m);
    expect(kaynak("App.vue")).toContain(':class="{ secili: sekme.ad === s.ad }"');
    expect(kaynak("tema.css")).toContain('.sekme a.secili, .sekme a[aria-current="page"] {');
  });

  it("Kayitlar: satira dokunus yalniz acilabilir oturumu acar; eski yanit yeni aramayi EZMEZ; esitleme bitince yenilenir", () => {
    const k = kaynak("ekran/Kayitlar.vue");
    expect(k).toContain("if (s.acilabilir) yonlendirici.push(`/kayitlar/${s.oturum}`);");
    expect(k).toContain("if (no !== sira) return;              // daha yeni bir istek var: eski yanit ekrani EZMEZ");
    expect(k).toContain("watch(() => [kabuk.esitleme.value.sonMs, kabuk.baglanti.value && kabuk.baglanti.value.durum], yenile);");
    expect(k).toMatch(/<button type="button" class="satir" :aria-disabled="!s\.acilabilir" @click="ac\(s\)">/);
    expect(k).toContain('<input id="ky-arama" v-model="arama" class="arama" type="search"');
  });

  it("Kayit: grafik ortak Grafik sinifiyla; istatistik GORUNEN aralikta ve gecikmeli; gecerli olcum yoksa acikca soyler", () => {
    const k = kaynak("ekran/Kayit.vue");
    expect(k).toContain('import { Grafik } from "@ortak/grafik.js";');
    expect(k).toContain("grafik = new Grafik(el, { zamanKokeni: 0, onDegisim: pencereDegisti });");
    expect(k).toContain("gecikme = setTimeout(() => { gecikme = null; okumaIste(durum.t0, durum.t1); }, 150);");
    expect(k).toContain("if (no === okumaNo) okuma.value = ok;");
    expect(k).toContain('if (g.gecerli === 0) { hal.value = "olcumsuz"; return; }');
    expect(k).toContain("if (grafik) grafik.yokEt();");
    expect(k).toMatch(/<canvas id="kg-grafik" ref="tuval" class="grafik buyuk dokun" role="img" :aria-label=/);
    const css = kaynak("tema.css");
    expect(css).toContain(".grafik.dokun { pointer-events: auto; }");
    expect(/\n\.satir \{([^}]*)\}/.exec(css)[1]).toContain("min-height: var(--dokunma)");
    expect(/\n\.arama \{([^}]*)\}/.exec(css)[1]).toContain("min-height: var(--dokunma)");
  });

  it("uygulama: kayit modulleri tembel; Worker yoksa yedek AYNI okuyucuyla (depo_oku.js); son kimlik kesif onbelleginden", () => {
    const u = kaynak("cekirdek/uygulama.js");
    expect(u).toContain("isciKur: w.kayitIsciKur,");
    expect(u).toContain("return v.islemciKur({ getir: o.yerelOku });");
    expect(u).toContain("try { const k = yerelOnbellek(localStorage).oku(); return k ? k.kimlik : null; } catch { return null; }");
    expect(u.match(/^ {4}sonKimlik,$/gm).length).toBe(2);              // esitleme (sifirlama) ve kayitlar
    expect(u).toContain("if (kimlik === null) kimlik = sonKimlik();");    // Ayarlar'in kopya boyutu da kartsiz calisir
    expect(u).not.toMatch(/^import .*(kayitlar|kayit_veri|kayit_istemci|isci_kur|depo_oku)\.js/m);
  });
});
