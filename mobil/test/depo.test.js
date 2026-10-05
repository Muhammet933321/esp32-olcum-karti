// 5D-1 — depo.js: esitle.js DEPO arayuzunun KartDepo eklentisi uzerindeki uygulamasi.
// Eklenti SAHTE (test/yardim/depo_sahtesi.mjs: gercek dosyalar, gecici dizinde); kart SAHTE (127.0.0.1).
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mkdtempSync, rmSync, appendFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import * as IM from "../../ortak/src/imza.js";
import { T_NOKTA, kayitPaketle } from "../../ortak/src/kayit.js";
import { DOSYA, DURUM, KAL_DOSYA, Esitleyici, EsitlemeHatasi, bellekDepo, imzaliIstek } from "../../ortak/src/esitle.js";
import { DepoHatasi, OKUMA_PARCA, YAZMA_PARCA, depoKur } from "../src/cekirdek/depo.js";
import { depoSahtesi } from "./yardim/depo_sahtesi.mjs";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";

const K = "0123456789abcdef";
const PAROLA = "sinama-parolasi-1";
const ortam = { fetch: (u, s) => fetch(u, s) };

let dizin;
const acik = [];
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "depo-")); });
afterEach(async () => {
  while (acik.length) await acik.pop().kapat();
  rmSync(dizin, { recursive: true, force: true });
});

const kur = (secenek) => { const e = depoSahtesi(dizin); return { e, depo: depoKur(e, K, secenek) }; };
const tur = async (soz) => { try { await soz; return null; } catch (h) { return h instanceof DepoHatasi ? h.tur : `baska:${h && h.name}`; } };
const kayit = (sira, oturum = 3) => kayitPaketle(T_NOKTA, sira, oturum, Uint8Array.from({ length: 36 }, (_, j) => (sira * 7 + j) & 255));
const akisKur = (ilk, son) => Buffer.concat(Array.from({ length: son - ilk + 1 }, (_, i) => kayit(ilk + i)));

describe("depo.js — sozlesme", () => {
  it("dosya adlari PC ile ayni; bos depo: boy 0, durum null, kal null", async () => {
    expect([DOSYA, DURUM, KAL_DOSYA]).toEqual(["kayitlar.kyt", "durum.json", "kalibrasyon.json"]);
    const { depo } = kur();
    expect(await depo.veriBoyu()).toBe(0);
    expect(await depo.veriOku(0)).toEqual(new Uint8Array(0));
    expect(await depo.durumOku()).toBe(null);
    expect(await depo.kalOku()).toBe(null);
  });

  it("veriEkle / veriOku / veriKirp: baytlar AYNEN; parcali okuma ve yazma birlestirilir", async () => {
    expect([OKUMA_PARCA, YAZMA_PARCA]).toEqual([262144, 262144]);
    const { e, depo } = kur({ okumaParca: 7, yazmaParca: 5 });
    const veri = Uint8Array.from({ length: 23 }, (_, i) => (i * 37 + 200) & 255);      // 0x00 ve >0x7f baytlar dahil
    await depo.veriEkle(veri);
    expect(e.cagrilar.filter(([ad]) => ad === "veriEkle").length).toBe(5);              // 5+5+5+5+3
    expect(Buffer.from(e.dosya(K)).equals(Buffer.from(veri))).toBe(true);
    expect(await depo.veriBoyu()).toBe(23);
    expect(await depo.veriOku(0)).toEqual(veri);
    expect(await depo.veriOku(20)).toEqual(veri.subarray(20));
    expect(await depo.veriOku(23)).toEqual(new Uint8Array(0));
    expect(await depo.veriOku(999)).toEqual(new Uint8Array(0));
    // Baska gorunumler (Buffer, DataView, ArrayBuffer) de bayt bayt eklenir.
    await depo.veriEkle(Buffer.from([1, 2]));
    await depo.veriEkle(new DataView(new Uint8Array([9, 3, 4, 9]).buffer, 1, 2));
    await depo.veriEkle(new Uint8Array([5]).buffer);
    expect([...(await depo.veriOku(23))]).toEqual([1, 2, 3, 4, 5]);
    await depo.veriKirp(24);
    expect(await depo.veriBoyu()).toBe(24);
    await depo.veriKirp(26);                                                            // uzatirsa sifir (Python truncate)
    expect([...(await depo.veriOku(23))]).toEqual([1, 0, 0]);
    await expect(depo.veriKirp(-1)).rejects.toBeInstanceOf(RangeError);
    await expect(depo.veriKirp(1.5)).rejects.toBeInstanceOf(RangeError);
    expect(await tur(depo.veriEkle("metin"))).toBe("bicim");
    expect(await tur(depo.veriOku(-1))).toBe("bicim");
  });

  it("durum: nesne gidip gelir (ek alanlar korunur); bozuk dosya 'bos' SAYILMAZ -> DepoHatasi('bozuk')", async () => {
    const { e, depo } = kur();
    const d = { son_sira: 40, bayt: 2080, onaylanan: 0, kimlik: 7, ek: { a: [1, "ş"] } };
    await depo.durumYaz(d);
    expect(await depo.durumOku()).toEqual(d);
    expect(JSON.parse(e.dosya(K, "durum.json").toString("utf8"))).toEqual(d);
    for (const bozuk of [Buffer.from("{\"son_si"), Buffer.from("[1]"), Buffer.from("null"), Buffer.from("7"), Buffer.from([0xff, 0xfe]), Buffer.alloc(0)]) {
      e.bozDurum(K, bozuk);
      expect(await tur(depo.durumOku()), bozuk.toString("hex")).toBe("bozuk");
    }
    for (const kotu of [null, [1], "x", 5]) expect(await tur(depo.durumYaz(kotu))).toBe("bicim");
  });

  it("kalibrasyon: ham bayt; arsiv zaman damgali ad doner ve asil dosyayi degistirmez", async () => {
    const e = depoSahtesi(dizin, { simdi: () => new Date(2026, 9, 5, 7, 8, 9) });
    const depo = depoKur(e, K);
    const kal = new TextEncoder().encode("{\n \"surum\": 1\n}");
    await depo.kalYaz(kal);
    expect(await depo.kalOku()).toEqual(kal);
    expect(await depo.kalArsivle(new Uint8Array([1]))).toBe("kalibrasyon-20261005-070809.json");
    expect(await depo.kalArsivle(new Uint8Array([2]))).toBe("kalibrasyon-20261005-070809-1.json");
    expect(await depo.kalOku()).toEqual(kal);
    expect(await depo.boyutlar()).toEqual({ veri: 0, toplam: kal.length + 2, arsiv: 2 });
  });

  it("kilit: ayni kimlige iki esitleme OLMAZ (ayri nesnelerle de); birakinca alinir; baska kimlik bagimsiz", async () => {
    const e = depoSahtesi(dizin);
    const a = depoKur(e, K), b = depoKur(e, K), oteki = depoKur(e, "fedcba9876543210");
    const birak = await a.kilitAl();
    await expect(b.kilitAl()).rejects.toBeInstanceOf(IM.CalismaHatasi);
    await expect(a.kilitAl()).rejects.toBeInstanceOf(IM.CalismaHatasi);
    await expect(a.sifirla()).rejects.toBeInstanceOf(IM.CalismaHatasi);        // esitleme surerken silinmez
    const birakOteki = await oteki.kilitAl();
    await birak();
    await birak();                                                             // iki kez birakmak baskasinin kilidini ACMAZ
    const birakB = await b.kilitAl();
    await birak();
    await expect(a.kilitAl()).rejects.toBeInstanceOf(IM.CalismaHatasi);
    await birakB();
    await birakOteki();
  });

  it("kimlik yalniz 16 kucuk onaltilik hane; eklentinin hatasi TUR olarak doner, mesaji DISARI CIKMAZ", async () => {
    const e = depoSahtesi(dizin);
    for (const k of [null, "", "abc", "0123456789ABCDEF", "../../x", "0123456789abcdef/"]) {
      expect(() => depoKur(e, k), String(k)).toThrow(DepoHatasi);
    }
    expect(e.cagrilar.length).toBe(0);
    expect(() => depoKur(null, K)).toThrow(TypeError);
    const gizli = "/data/user/0/ozel/yol";
    const atan = { veriBoyu: async () => { throw Object.assign(new Error(gizli), { code: "okunamadi" }); },
      durumOku: async () => { throw Object.assign(new Error(gizli), { code: gizli }); },
      kalOku: async () => { throw new Error(gizli); } };
    const depo = depoKur(atan, K);
    for (const [soz, beklenen] of [[depo.veriBoyu(), "okunamadi"], [depo.durumOku(), "ic-hata"], [depo.kalOku(), "ic-hata"], [depo.veriEkle(new Uint8Array(1)), "ic-hata"]]) {
      try { await soz; expect.unreachable(); } catch (h) {
        expect(h).toBeInstanceOf(DepoHatasi);
        expect(h.tur).toBe(beklenen);
        expect(h.message + String(h.stack)).not.toContain(gizli);
      }
    }
    // Eklenti sacma yanit verirse (boy sayi degil, veri metin degil) sessizce 0 / bos SAYILMAZ.
    expect(await tur(depoKur({ veriBoyu: async () => ({ boy: "5" }) }, K).veriBoyu())).toBe("ic-hata");
    expect(await tur(depoKur({ veriOku: async () => ({ var: true, veri: 5 }) }, K).veriOku(0))).toBe("ic-hata");
    expect(await tur(depoKur({ veriOku: async ({ bas }) => ({ var: true, veri: bas === 0 ? "AAAAAAAAAAAA" : "" }) }, K, { okumaParca: 4 }).veriOku(0))).toBe("ic-hata");
  });

  it("sifirla: kartin butun dosyalari gider, depo bos depo gibi davranir", async () => {
    const { e, depo } = kur();
    await depo.veriEkle(new Uint8Array([1, 2, 3]));
    await depo.durumYaz({ son_sira: 1 });
    await depo.kalYaz(new Uint8Array([4]));
    await depo.sifirla();
    expect(e.dosya(K)).toBe(null);
    expect(await depo.veriBoyu()).toBe(0);
    expect(await depo.durumOku()).toBe(null);
    expect(await depo.boyutlar()).toEqual({ veri: 0, toplam: 0, arsiv: 0 });
  });
});

describe("depo.js — ortak Esitleyici ile (sahte kart)", () => {
  async function eslesmis() {
    const kart = await sahteKartAc({ zorunlu: 1, parola: PAROLA });
    acik.push(kart);
    const cihaz = await IM.esles(kart.taban, "Telefon", PAROLA, ortam);
    return { kart, cihaz };
  }
  const esitleyici = (kart, cihaz, depo) => new Esitleyici({
    tabanUrl: kart.taban, fetch: ortam.fetch, depo, bayt: 1100, onayBekleMs: 5, istek: imzaliIstek(cihaz, ortam), onay: null,
  });

  it("dosya deposuna esitlenen akis = bellek deposuna esitlenen akis = kartin akisi (bayt bayt); durum ayni; ONAY GITMEZ", async () => {
    const { kart, cihaz } = await eslesmis();
    const akis = akisKur(1, 120);                                  // 120 x 52 B = 6240 B: birkac tur
    kart.ayarla({ kayitlar: akis });
    const bellek = bellekDepo();
    const { e, depo } = kur({ okumaParca: 1000, yazmaParca: 700 });
    const s1 = await esitleyici(kart, cihaz, bellek).esitle();
    const s2 = await esitleyici(kart, cihaz, depo).esitle();
    expect(s2).toEqual(s1);
    expect(s2).toMatchObject({ yeni_kayit: 120, son_sira: 120 });
    expect(Buffer.from(e.dosya(K)).equals(akis)).toBe(true);
    expect(Buffer.from(bellek.anlik().veri).equals(akis)).toBe(true);
    expect(await depo.durumOku()).toEqual(bellek.anlik().durum);
    expect(await depo.durumOku()).toMatchObject({ son_sira: 120, bayt: akis.length, onaylanan: 0, kimlik: 7 });
    expect(kart.durum.komutlar.some((k) => /^Go/.test(k))).toBe(false);          // A21: varsayilan ONAYSIZ
    // Kalibrasyon dosyasi da iki depoda ayni baytlar.
    expect(Buffer.from(await depo.kalOku()).equals(Buffer.from(bellek.anlik().kal))).toBe(true);
    // Ikinci kosu: yeni kayit yok, dosya degismez.
    const tekrar = await esitleyici(kart, cihaz, depo).esitle();
    expect(tekrar.yeni_kayit).toBe(0);
    expect(Buffer.from(e.dosya(K)).equals(akis)).toBe(true);
  });

  it("A23: yarim kuyruk (yarida kesilen ekleme) kirpilir, sonraki esitleme dosyayi kartin akisina esitler", async () => {
    const { kart, cihaz } = await eslesmis();
    kart.ayarla({ kayitlar: akisKur(1, 30) });
    const { e, depo } = kur();
    await esitleyici(kart, cihaz, depo).esitle();
    // Cokme: bir sonraki kaydin ilk 20 bayti diske indi, durum YAZILMADI.
    appendFileSync(join(dizin, K, "kayitlar.kyt"), kayit(31).subarray(0, 20));
    expect(await depo.veriBoyu()).toBe(30 * 52 + 20);
    kart.ayarla({ kayitlar: akisKur(1, 45) });
    const s = await esitleyici(kart, cihaz, depo).esitle();
    expect(s.son_sira).toBe(45);
    expect(Buffer.from(e.dosya(K)).equals(akisKur(1, 45))).toBe(true);
    expect(await depo.durumOku()).toMatchObject({ son_sira: 45, bayt: 45 * 52 });
  });

  it("A23: durum yazilmadan TAM kayitlar diske indiyse ileri sarilir (yeniden indirilmez, cift yazilmaz)", async () => {
    const { kart, cihaz } = await eslesmis();
    kart.ayarla({ kayitlar: akisKur(1, 30) });
    const { e, depo } = kur();
    await esitleyici(kart, cihaz, depo).esitle();
    appendFileSync(join(dizin, K, "kayitlar.kyt"), Buffer.concat([kayit(31), kayit(32)]));
    kart.ayarla({ kayitlar: akisKur(1, 40) });
    await esitleyici(kart, cihaz, depo).esitle();
    expect(Buffer.from(e.dosya(K)).equals(akisKur(1, 40))).toBe(true);
  });

  it("A23: dosya durumdan KISAYSA esitleme DURUR (EsitlemeHatasi), dosyaya dokunulmaz; sifirla sonrasi bastan alinir", async () => {
    const { kart, cihaz } = await eslesmis();
    const akis = akisKur(1, 30);
    kart.ayarla({ kayitlar: akis });
    const { e, depo } = kur();
    await esitleyici(kart, cihaz, depo).esitle();
    await depo.veriKirp(10 * 52);                                    // dosya elle / hatayla kisaldi
    const onceki = Buffer.from(e.dosya(K));
    await expect(esitleyici(kart, cihaz, depo).esitle()).rejects.toBeInstanceOf(EsitlemeHatasi);
    expect(Buffer.from(e.dosya(K)).equals(onceki)).toBe(true);
    await depo.sifirla();
    const s = await esitleyici(kart, cihaz, depo).esitle();
    expect(s.yeni_kayit).toBe(30);
    expect(Buffer.from(e.dosya(K)).equals(akis)).toBe(true);
  });

  it("kartin akis kimligi degisirse esitleme DURUR; eldeki kopya AYNEN kalir", async () => {
    const { kart, cihaz } = await eslesmis();
    const akis = akisKur(1, 20);
    kart.ayarla({ kayitlar: akis });
    const { e, depo } = kur();
    await esitleyici(kart, cihaz, depo).esitle();
    kart.ayarla({ kayitKimlik: 8, kayitlar: akisKur(1, 25) });      // kart bicimlendi (GF!), yeni akis DAHA UZUN: tek fark kimlik
    await expect(esitleyici(kart, cihaz, depo).esitle()).rejects.toBeInstanceOf(EsitlemeHatasi);
    expect(Buffer.from(e.dosya(K)).equals(akis)).toBe(true);
    expect(readFileSync(join(dizin, K, "durum.json"), "utf8")).toContain("\"kimlik\":7");
  });

  it("kilit: suren esitleme varken ikincisi baslamaz ve dosyayi bozmaz", async () => {
    const { kart, cihaz } = await eslesmis();
    const akis = akisKur(1, 60);
    kart.ayarla({ kayitlar: akis, gecikmeMs: 20 });
    const { e, depo } = kur();
    const ilk = esitleyici(kart, cihaz, depo).esitle();
    await new Promise((c) => setTimeout(c, 30));
    await expect(esitleyici(kart, cihaz, depoKur(e, K)).esitle()).rejects.toBeInstanceOf(IM.CalismaHatasi);
    await ilk;
    expect(Buffer.from(e.dosya(K)).equals(akis)).toBe(true);
  });
});
