// kasa.js (A14, A16, S1): anahtar kasasi sarmalayicisi + blok ayirmali kalici sayac.
// "Uygulamayi yeniden baslatmak" = ayni sahte diskle yeni kasaSahtesi + yeni kasaKur.
import { describe, it, expect } from "vitest";
import { sonrakiSayac } from "@ortak/imza.js";
import { kasaKur, KasaHatasi } from "../src/cekirdek/kasa.js";
import { kasaDiski, kasaSahtesi } from "./yardim/kasa_sahtesi.mjs";

const KIMLIK = "0123456789abcdef";
const YIL_MS = 365 * 24 * 3600 * 1000;
const T0 = 1_790_000_000_000;

function anahtar(tohum = 7) {
  return Uint8Array.from({ length: 32 }, (_, i) => (i * 31 + tohum) & 0xff);
}

function yeniCihaz(ek = {}) {
  return { kimlik: KIMLIK, n: 3, K: anahtar(), ad: "sinama telefonu", sayac: 0, acilis: "ab".repeat(16), ...ek };
}

const isaret = (disk) => Number(disk.isaretler.get(KIMLIK) ?? 0n);

async function turu(soz) {
  try { await soz; return "hata-yok"; } catch (e) { return e instanceof KasaHatasi ? e.tur : `baska:${e.name}`; }
}

// Bir "istek": imza.js ac()'in yaptigi gibi once sayac secilir, sonra kaydet BEKLENIR.
async function istek(kasa, cihaz, saat) {
  const s = sonrakiSayac(cihaz, saat());
  await kasa.kaydet(cihaz);
  return s;
}

describe("kasa: anahtar", () => {
  it("kayit yokken cihazYukle null", async () => {
    const kasa = kasaKur(kasaSahtesi(kasaDiski()));
    expect(await kasa.cihazYukle(KIMLIK)).toBe(null);
    expect(await kasa.liste()).toEqual([]);
  });

  it("sakla -> yeniden baslat -> yukle: K, n, ad ayni; acilis null; sayac = diskteki isaret", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    await kasa.cihazSakla(yeniCihaz());
    expect(await kasa.liste()).toEqual([{ kimlik: KIMLIK, n: 3, ad: "sinama telefonu" }]);

    const kasa2 = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    const c = await kasa2.cihazYukle(KIMLIK);
    expect(c.K).toBeInstanceOf(Uint8Array);
    expect([...c.K]).toEqual([...anahtar()]);
    expect(c).toMatchObject({ kimlik: KIMLIK, n: 3, ad: "sinama telefonu", acilis: null });
    expect(c.sayac).toBe(isaret(disk));
    expect(c.sayac).toBeGreaterThan(0);
  });

  it("cihazYukle iki kez cagrilinca AYNI nesne (tek cihaz nesnesi, A15)", async () => {
    const disk = kasaDiski();
    await kasaKur(kasaSahtesi(disk)).cihazSakla(yeniCihaz());
    const kasa = kasaKur(kasaSahtesi(disk));
    expect(await kasa.cihazYukle(KIMLIK)).toBe(await kasa.cihazYukle(KIMLIK));
  });

  it("bozuk kayit / yanlis boyda anahtar / bicimsiz isaret -> KasaHatasi(bozuk)", async () => {
    const disk = kasaDiski();
    await kasaKur(kasaSahtesi(disk)).cihazSakla(yeniCihaz());
    disk.anahtarlar.get(KIMLIK).bozuk = true;
    expect(await turu(kasaKur(kasaSahtesi(disk)).cihazYukle(KIMLIK))).toBe("bozuk");
    delete disk.anahtarlar.get(KIMLIK).bozuk;

    disk.anahtarlar.get(KIMLIK).anahtar = Buffer.alloc(31, 1).toString("base64");
    expect(await turu(kasaKur(kasaSahtesi(disk)).cihazYukle(KIMLIK))).toBe("bozuk");
    disk.anahtarlar.get(KIMLIK).anahtar = "bu base64 degil!!";
    expect(await turu(kasaKur(kasaSahtesi(disk)).cihazYukle(KIMLIK))).toBe("bozuk");
    disk.anahtarlar.get(KIMLIK).anahtar = Buffer.from(anahtar()).toString("base64");

    disk.isaretler.set(KIMLIK, "bozuk");
    expect(await turu(kasaKur(kasaSahtesi(disk)).cihazYukle(KIMLIK))).toBe("bozuk");
    // Eklenti bicimsiz isaret dondururse de (eksi, kesirli, cok uzun) bozuk sayilir.
    for (const kotu of ["-5", "1.5", "1e9", "", "99999999999999999999", null, 12]) {
      const ek = kasaSahtesi(disk);
      ek.sayacOku = async () => ({ isaret: kotu });
      expect(await turu(kasaKur(ek).cihazYukle(KIMLIK)), String(kotu)).toBe("bozuk");
    }
  });

  it("liste acilamayan kaydi GIZLEMEZ ({ kimlik, bozuk: true }); sil ile kurtarilir", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk));
    await kasa.cihazSakla(yeniCihaz());
    disk.anahtarlar.get(KIMLIK).bozuk = true;
    const kasa2 = kasaKur(kasaSahtesi(disk));
    expect(await kasa2.liste()).toEqual([{ kimlik: KIMLIK, bozuk: true }]);
    expect(await turu(kasa2.cihazYukle(KIMLIK))).toBe("bozuk");
    await kasa2.sil(KIMLIK);
    expect(await kasa2.liste()).toEqual([]);
    // Eklenti bicimsiz kayit dondururse liste de bozuk sayilir.
    const ek = kasaSahtesi(disk);
    ek.liste = async () => ({ kayitlar: [{ kimlik: "kisa", n: 1, ad: "x" }] });
    expect(await turu(kasaKur(ek).liste())).toBe("bozuk");
  });

  it("bozuk sayac dosyasi: kaydet 'bozuk' ile REDDEDER (sessizce 0'dan baslamaz, ustune yazmaz)", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    disk.isaretler.set(KIMLIK, "bozuk");
    c.sayac = T0 + 1_000_000;
    expect(await turu(kasa.kaydet(c))).toBe("bozuk");
    expect(disk.isaretler.get(KIMLIK)).toBe("bozuk");
    // cihazSakla da bozuk sayacin ustune yazmaz.
    expect(await turu(kasaKur(kasaSahtesi(disk)).cihazSakla(yeniCihaz()))).toBe("bozuk");
    expect(disk.isaretler.get(KIMLIK)).toBe("bozuk");
  });

  it("eklentiye n TAMSAYI, isaret METIN, anahtar standart base64 gider; bicimsiz cihaz 'bicim'", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    c.sayac = T0 + 1_000_000;
    await kasa.kaydet(c);
    const yaz = ek.cagrilar.find((x) => x.ad === "anahtarYaz").veri;
    expect(yaz).toEqual({ kimlik: KIMLIK, n: 3, ad: "sinama telefonu", anahtar: Buffer.from(anahtar()).toString("base64") });
    for (const s of ek.cagrilar.filter((x) => x.ad === "sayacYaz")) expect(s.veri.isaret).toMatch(/^[1-9][0-9]{0,18}$/);
    for (const kotu of [{ n: 1.5 }, { n: "3" }, { n: 0 }, { n: 256 }, { ad: 5 }, { K: new Uint8Array(31) }, { K: [...anahtar()] }, { kimlik: "KISA" }]) {
      expect(await turu(kasaKur(kasaSahtesi(kasaDiski())).cihazSakla(yeniCihaz(kotu))), JSON.stringify(kotu)).toBe("bicim");
    }
  });

  it("sil: kayit gider, bellekteki K sifirlanir", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk));
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    await kasa.sil(KIMLIK);
    expect([...c.K].every((b) => b === 0)).toBe(true);
    expect(disk.anahtarlar.size).toBe(0);
    expect(await kasa.cihazYukle(KIMLIK)).toBe(null);
  });

  it("ayni kimlige yeni cihaz saklaninca ESKI K sifirlanir; sayac geri gitmez", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    const eski = yeniCihaz();
    await kasa.cihazSakla(eski);
    const once = isaret(disk);
    const yeni = yeniCihaz({ K: anahtar(99), n: 4 });
    await kasa.cihazSakla(yeni);
    expect([...eski.K].every((b) => b === 0)).toBe(true);
    expect([...yeni.K]).toEqual([...anahtar(99)]);
    expect(isaret(disk)).toBeGreaterThanOrEqual(once);
    expect(yeni.sayac).toBeGreaterThanOrEqual(once);
  });

  it("hata nesneleri yalniz TUR tasir (K, eklenti mesaji sizmaz)", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek);
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    const sizinti = "gizli-sinama " + Buffer.from(c.K).toString("hex");
    ek.sayacYaz = async () => { const e = new Error(sizinti); e.code = sizinti; throw e; };
    c.sayac = Number.MAX_SAFE_INTEGER - 10_000_000;
    try {
      await kasa.kaydet(c);
      expect.unreachable();
    } catch (e) {
      expect(e).toBeInstanceOf(KasaHatasi);
      expect(e.tur).toBe("ic-hata");
      const yazi = JSON.stringify(e, Object.getOwnPropertyNames(e));
      expect(yazi).not.toContain("gizli-sinama");
      expect(yazi).not.toContain(Buffer.from(anahtar()).toString("hex"));
      expect(yazi).not.toContain(Buffer.from(anahtar()).toString("base64"));
    }
  });
});

describe("kasa: kalici sayac (A16)", () => {
  it("cokme + saat 1 yil GERI: yeniden yuklenen sayac kullanilmis hicbir degerin altina inmez", async () => {
    const disk = kasaDiski();
    let simdi = T0;
    const saat = () => simdi;
    const kasa = kasaKur(kasaSahtesi(disk), { simdiMs: saat });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    let enBuyuk = 0;
    for (let i = 0; i < 1000; i++) {
      simdi += 1 + (i % 7);
      const s = await istek(kasa, c, saat);
      expect(s).toBeGreaterThan(enBuyuk);
      enBuyuk = s;
      // HER an cokebilir: kullanilan deger diskteki isareti gecmemis olmali.
      expect(isaret(disk)).toBeGreaterThanOrEqual(s);
    }
    simdi -= YIL_MS;
    const kasa2 = kasaKur(kasaSahtesi(disk), { simdiMs: saat });
    const c2 = await kasa2.cihazYukle(KIMLIK);
    const sonraki = await istek(kasa2, c2, saat);
    expect(sonraki).toBeGreaterThan(enBuyuk);
    // Saat geride kalmaya devam ederken de ilerler ve yeniden baslatmalara dayanir.
    let son = sonraki;
    for (let tur = 0; tur < 3; tur++) {
      const k = kasaKur(kasaSahtesi(disk), { simdiMs: saat });
      const cx = await k.cihazYukle(KIMLIK);
      for (let i = 0; i < 5; i++) {
        const s = await istek(k, cx, saat);
        expect(s).toBeGreaterThan(son);
        son = s;
      }
    }
  });

  it("her istekte disk yazimi YOK: N istekte yazim ~ N / blok + 1", async () => {
    const disk = kasaDiski();
    let simdi = T0;
    const saat = () => simdi;
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: saat, blok: 4096 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    ek.sayacYazimi = 0;
    const N = 10_000;
    for (let i = 0; i < N; i++) { simdi += 1; await istek(kasa, c, saat); }
    expect(ek.sayacYazimi).toBeGreaterThanOrEqual(1);
    expect(ek.sayacYazimi).toBeLessThanOrEqual(Math.ceil(N / 4096) + 1);
    // blok secenegi gercekten kullaniliyor
    const ek2 = kasaSahtesi(kasaDiski());
    const kasa2 = kasaKur(ek2, { simdiMs: saat, blok: 100 });
    const d = yeniCihaz();
    await kasa2.cihazSakla(d);
    ek2.sayacYazimi = 0;
    for (let i = 0; i < 1000; i++) { simdi += 1; await istek(kasa2, d, saat); }
    expect(ek2.sayacYazimi).toBeGreaterThanOrEqual(9);
    expect(ek2.sayacYazimi).toBeLessThanOrEqual(11);
  });

  it("yeniden yuklemeden sonraki ILK istek isareti yazar (yuklenen sayac = isaret)", async () => {
    const disk = kasaDiski();
    await kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 }).cihazSakla(yeniCihaz());
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 - YIL_MS });
    const c = await kasa.cihazYukle(KIMLIK);
    const once = isaret(disk);
    const s = await istek(kasa, c, () => T0 - YIL_MS);
    expect(s).toBe(once + 1);
    expect(ek.sayacYazimi).toBe(1);
    expect(isaret(disk)).toBe(s + 4096);
  });

  it("kaydet, isaret diske yazilmadan DONMEZ (yazim gecikse de)", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    ek.yazimGecikmeMs = 60;
    c.sayac = isaret(disk) + 5;
    const hedef = c.sayac;
    let dondu = false;
    const soz = kasa.kaydet(c).then(() => { dondu = true; });
    await new Promise((r) => setTimeout(r, 20));
    expect(dondu).toBe(false);
    expect(isaret(disk)).toBeLessThan(hedef);
    await soz;
    expect(isaret(disk)).toBeGreaterThanOrEqual(hedef);
  });

  it("eszamanli 50 kaydet: tek yazim kuyrugu (yazimlar ust uste binmez), hepsi isaretin altinda", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    ek.yazimGecikmeMs = 15;
    ek.sayacYazimi = 0;
    const saat = () => T0 + 10_000_000;
    const sayaclar = [];
    await Promise.all(Array.from({ length: 50 }, async () => {
      const s = sonrakiSayac(c, saat());
      await kasa.kaydet(c);
      expect(isaret(disk)).toBeGreaterThanOrEqual(s);
      sayaclar.push(s);
    }));
    expect(new Set(sayaclar).size).toBe(50);
    expect(ek.azamiEszamanli).toBe(1);
    expect(ek.sayacYazimi).toBe(1);
  });

  it("isaret yazilamazsa kaydet REDDEDER (istek gitmez); sonraki kaydet yeniden dener", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    c.sayac = isaret(disk) + 1;
    ek.bozYazim = "ic-hata";
    expect(await turu(kasa.kaydet(c))).toBe("ic-hata");
    expect(isaret(disk)).toBeLessThan(c.sayac);
    await kasa.kaydet(c);
    expect(isaret(disk)).toBe(c.sayac + 4096);
  });

  it("geri: disk bizden ilerideyse sayac diske cekilir ve 'sayac-geride' atilir; bekleyen eski degerler de reddedilir", async () => {
    const disk = kasaDiski();
    await kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 }).cihazSakla(yeniCihaz());
    const a = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    const ca = await a.cihazYukle(KIMLIK);
    // Ikinci bir yazar (S1'e gore olmamali) saati ileride calisip isareti cok ileri tasir.
    const b = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 + YIL_MS });
    const cb = await b.cihazYukle(KIMLIK);
    const sb = await istek(b, cb, () => T0 + YIL_MS);
    expect(isaret(disk)).toBe(sb + 4096);

    // a: es zamanli uc istek; hepsi diskteki isaretin GERISINDE kalan degerler secti.
    const secilen = [1, 2, 3].map(() => sonrakiSayac(ca, T0 + 5));
    const sonuclar = await Promise.all(secilen.map(() => turu(a.kaydet(ca))));
    expect(sonuclar).toEqual(["sayac-geride", "sayac-geride", "sayac-geride"]);
    expect(ca.sayac).toBe(sb + 4096);
    // Yeniden imzalama: yeni deger oteki yazarin kullandigi her seyden buyuk ve kaydedilebilir.
    const yeni = await istek(a, ca, () => T0 + 5);
    expect(yeni).toBeGreaterThan(sb);
    expect(yeni).toBe(sb + 4096 + 1);
    expect(isaret(disk)).toBe(yeni + 4096);
  });

  it("kayitli olmayan (baska) cihaz nesnesiyle kaydet -> 'kayitsiz'; bicimsiz sayac -> 'bicim'", async () => {
    const disk = kasaDiski();
    const kasa = kasaKur(kasaSahtesi(disk), { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    expect(await turu(kasa.kaydet({ ...c }))).toBe("kayitsiz");
    expect(await turu(kasa.kaydet(yeniCihaz({ kimlik: "ffffffffffffffff" })))).toBe("kayitsiz");
    for (const kotu of [-1, 1.5, NaN, "12", Number.MAX_SAFE_INTEGER]) {
      const once = c.sayac;
      c.sayac = kotu;
      expect(await turu(kasa.kaydet(c)), String(kotu)).toBe("bicim");
      c.sayac = once;
    }
  });

  it("acilis degisikligi (sayac ayni) diske dokunmaz", async () => {
    const disk = kasaDiski();
    const ek = kasaSahtesi(disk);
    const kasa = kasaKur(ek, { simdiMs: () => T0 });
    const c = yeniCihaz();
    await kasa.cihazSakla(c);
    const once = ek.cagrilar.length;
    c.acilis = "cd".repeat(16);
    await kasa.kaydet(c);
    expect(ek.cagrilar.length).toBe(once);
  });
});
