// kart.js (A2, A12–A19): baglanti durumu, eslestirme, imzali istek — sahte kart + KartAg sahtesi +
// Kasa sahtesi ile uctan uca. "Uygulamayi yeniden baslatmak" = ayni disk ve onbellekle yeni telefon().
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { agKur } from "../src/cekirdek/ag.js";
import { kartKur, KartHatasi } from "../src/cekirdek/kart.js";
import { kasaKur } from "../src/cekirdek/kasa.js";
import { kesifKur } from "../src/cekirdek/kesif.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kasaDiski, kasaSahtesi } from "./yardim/kasa_sahtesi.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";
import { taklitKartAc } from "./yardim/taklit_kart.mjs";

const PAROLA = "sinama-parolasi-1";
const YANLIS = "sinama-yanlis-parola";
const K1 = "00112233aabbccdd";
const K2 = "ffeeddcc99887766";

function bellekOnbellek() {
  let kayit = null;
  return { oku: () => kayit, yaz: (k) => { kayit = k; } };
}

async function hata(soz) {
  try { await soz; } catch (e) { return e; }
  throw new Error("hata bekleniyordu");
}

const yazi = (e) => JSON.stringify(e, Object.getOwnPropertyNames(e));
const hex = (b) => Buffer.from(b).toString("hex");

describe("kart", () => {
  let acik;
  const kapatilacak = (k) => { acik.push(() => k.kapat()); return k; };
  const kartAc = async (secenek = {}) => kapatilacak(await sahteKartAc({ parola: PAROLA, kimlik: K1, ...secenek }));
  const adres = (k) => `127.0.0.1:${k.port}`;

  // Bir "telefon": ayni disk + onbellek ile yeniden kurmak = uygulamayi yeniden baslatmak.
  function telefon(dunya, { saat = Date.now } = {}) {
    const ham = kopruSahtesi();
    const ihlal = [];
    const kopru = {
      cagrilar: ham.cagrilar,
      // A16 degismezi HER imzali istekte olculur: istek yola ciktigi anda diskteki isaret, o istegin
      // sayacindan kucuk olamaz.
      istek(c) {
        const s = c.basliklar["X-Sayac"];
        if (s !== undefined) {
          const isaret = [...dunya.disk.isaretler.values()].reduce((m, v) => (v > m ? v : m), 0n);
          if (isaret < BigInt(s)) ihlal.push({ sayac: s, isaret: isaret.toString() });
        }
        return ham.istek(c);
      },
    };
    const ag = agKur(kopru, { yerelDongu: true, zamanAsimiMs: 3000 });
    const kesif = kesifKur({
      kartFetch: ag.kartFetch, onbellek: dunya.onbellek, yerelDongu: true, zamanAsimiMs: 500,
      sabitAdaylar: dunya.adaylar.map((a) => ({ adres: a, kaynak: "ap" })),
    });
    const kasaEk = kasaSahtesi(dunya.disk);
    const kasa = kasaKur(kasaEk, { simdiMs: saat });
    const kart = kartKur({ ag, kesif, kasa, simdiMs: saat });
    const imzalilar = () => ham.cagrilar.filter((c) => c.basliklar["X-Imza"] !== undefined);
    return { kopru: ham, kasaEk, kasa, kart, ihlal, imzalilar };
  }

  const dunyaKur = (...kartlar) => ({ disk: kasaDiski(), onbellek: bellekOnbellek(), adaylar: kartlar.map(adres) });

  async function eslesmis(secenek) {
    const k = await kartAc(secenek);
    const dunya = dunyaKur(k);
    const t = telefon(dunya);
    expect((await t.kart.baglan()).durum).toBe("eslesmemis");
    await t.kart.esles("sinama telefonu", PAROLA);
    return { k, dunya, t };
  }

  beforeEach(() => { acik = []; });
  afterEach(async () => { for (const k of acik) await k(); });

  it("esles -> sakla -> yeniden baslat -> imzali /kayit/liste gecer", async () => {
    const k = await kartAc();
    const dunya = dunyaKur(k);
    const t = telefon(dunya);
    const b = await t.kart.baglan();
    expect(b).toMatchObject({ durum: "eslesmemis", adres: adres(k), kimlik: K1 });
    expect(b.bilgi.tur).toBe(10000);
    // Eslesmeden imzali istek atilamaz.
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");

    const s = await t.kart.esles("sinama telefonu", PAROLA);
    expect(s).toEqual({ kimlik: K1, n: 1 });
    expect(k.durum.cihazlar.size).toBe(1);
    expect(dunya.disk.anahtarlar.size).toBe(1);
    expect(Buffer.from(dunya.disk.anahtarlar.get(K1).anahtar, "base64")).toEqual(Buffer.from(k.durum.cihazlar.get(1).K));
    // Ayni oturumda hemen kullanilabilir.
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);

    const t2 = telefon(dunya);
    expect((await hata(t2.kart.istek("GET", "/kayit/liste"))).tur).toBe("bagli-degil");
    expect(await t2.kart.baglan()).toMatchObject({ durum: "bagli", adres: adres(k), kimlik: K1 });
    const once = k.durum.imzali;
    const y = await t2.kart.istek("GET", "/kayit/liste");
    expect(y.status).toBe(200);
    expect((await y.json()).surum).toBe(2);
    expect(k.durum.imzali).toBe(once + 1);
    // POST + govde + arguman
    expect((await t2.kart.istek("POST", "/komut", [], "G?")).status).toBe(204);
    expect(k.durum.komutlar.at(-1)).toBe("G?");
    expect((await t2.kart.istek("GET", "/kayit/veri", [["sira", "1"], ["bayt", "512"]])).status).toBe(200);
    expect(t.ihlal).toEqual([]);
    expect(t2.ihlal).toEqual([]);
  });

  it("kart yeniden baslar -> istek gecer (yeni acilisla BIR yeniden deneme)", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    await t.kart.istek("GET", "/kayit/liste");
    k.ayarla({ yenidenBasla: true });
    const once = t.imzalilar().length;
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    expect(t.imzalilar().length).toBe(once + 2);
    expect(t.ihlal).toEqual([]);
  });

  it("cihaz kartta silinmis (401, ayni acilis) -> 'cihaz-silinmis'; K SILINMEZ (A17)", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    const K = hex(k.durum.cihazlar.get(1).K);
    k.durum.cihazlar.clear();
    const e = await hata(t.kart.istek("GET", "/kayit/liste"));
    expect(e).toBeInstanceOf(KartHatasi);
    expect(e.tur).toBe("cihaz-silinmis");
    expect(yazi(e)).not.toContain(K);
    expect(yazi(e)).not.toContain("127.0.0.1");
    // K yerinde: yeniden baslatinca yuklenir.
    expect(dunya.disk.anahtarlar.size).toBe(1);
    const c = await telefon(dunya).kasa.cihazYukle(K1);
    expect(hex(c.K)).toBe(K);
    // Kart ayrica yeniden baslamis olsa da (once yeni acilis, sonra yine 401) sonuc ayni.
    k.ayarla({ yenidenBasla: true });
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("cihaz-silinmis");
    expect(dunya.disk.anahtarlar.size).toBe(1);
  });

  it("yanlis parola -> 'parola-yanlis', kasa BOS; hemen yeniden -> 'bekle' + saniye; parola hicbir hata nesnesinde yok", async () => {
    const k = await kartAc();
    const dunya = dunyaKur(k);
    const t = telefon(dunya);
    await t.kart.baglan();
    const e = await hata(t.kart.esles("sinama telefonu", YANLIS));
    expect(e).toBeInstanceOf(KartHatasi);
    expect(e.tur).toBe("parola-yanlis");
    expect(dunya.disk.anahtarlar.size).toBe(0);
    expect(t.kasaEk.cagrilar.filter((c) => c.ad === "anahtarYaz")).toEqual([]);
    expect(k.durum.cihazlar.size).toBe(0);
    const e2 = await hata(t.kart.esles("sinama telefonu", YANLIS));
    expect(e2.tur).toBe("bekle");
    expect(e2.saniye).toBeGreaterThanOrEqual(1);
    expect(e2.saniye).toBeLessThanOrEqual(256);
    for (const x of [e, e2]) {
      expect(yazi(x)).not.toContain(YANLIS);
      expect(yazi(x)).not.toContain("127.0.0.1");
    }
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");
  });

  it("kisa parola (< 12 UTF-8 bayt) -> 'parola-kisa', karta HIC istek gitmez; gecersiz ad -> 'ad-gecersiz'", async () => {
    const k = await kartAc();
    const t = telefon(dunyaKur(k));
    await t.kart.baglan();
    const once = t.kopru.cagrilar.length;
    for (const kisa of ["", "sinama-11ba", "şşşşş", null, 12345678901234]) {
      const e = await hata(t.kart.esles("sinama telefonu", kisa));
      expect(e.tur, String(kisa)).toBe("parola-kisa");
    }
    for (const kotuAd of ["", "x".repeat(25), "a\nb", null]) {
      expect((await hata(t.kart.esles(kotuAd, PAROLA))).tur, String(kotuAd)).toBe("ad-gecersiz");
    }
    expect(t.kopru.cagrilar.length).toBe(once);
  });

  it("cihaz listesi dolu -> 'liste-dolu'; tur sinir disi -> 'tur-sinir-disi' (kanit YOLLANMAZ)", async () => {
    const dolu = await kartAc();
    for (let n = 1; n <= 8; n++) dolu.durum.cihazlar.set(n, { K: Buffer.alloc(32, n), ad: "x", eklenme: 0, son: 0 });
    const t = telefon(dunyaKur(dolu));
    await t.kart.baglan();
    expect((await hata(t.kart.esles("sinama telefonu", PAROLA))).tur).toBe("liste-dolu");

    for (const tur of [9999, 1, 1_000_001]) {
      const zayif = await kartAc({ tur });
      const dunya = dunyaKur(zayif);
      const t2 = telefon(dunya);
      await t2.kart.baglan();
      const e = await hata(t2.kart.esles("sinama telefonu", PAROLA));
      expect(e.tur, String(tur)).toBe("tur-sinir-disi");
      expect(t2.kopru.cagrilar.filter((c) => c.yontem === "POST")).toEqual([]);
      expect(dunya.disk.anahtarlar.size).toBe(0);
    }
  });

  it("kart kaniti YANLIS (parolayi bilmeyen taklit kart) -> 'kart-sahte', cihaz SAKLANMAZ", async () => {
    const taklit = kapatilacak(await taklitKartAc({ kimlik: K1, parola: PAROLA, kanitDogru: false }));
    const dunya = dunyaKur(taklit);
    const t = telefon(dunya);
    expect((await t.kart.baglan()).durum).toBe("eslesmemis");
    const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
    expect(e.tur).toBe("kart-sahte");
    expect(taklit.durum.kanitIstegi).toBe(1);
    expect(dunya.disk.anahtarlar.size).toBe(0);
    expect(t.kasaEk.cagrilar.filter((c) => c.ad === "anahtarYaz")).toEqual([]);
    expect(yazi(e)).not.toContain(PAROLA);
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");
    expect(taklit.durum.imzali).toBe(0);
  });

  it("kimligi FARKLI kart ayni adreste -> 'kimlik-uymuyor', imzali istek SAYISI 0 (A2)", async () => {
    const { k, dunya } = await eslesmis();
    const port = k.port;
    await k.kapat();
    const baska = await kartAc({ kimlik: K2, port });
    const t = telefon(dunya);
    const b = await t.kart.baglan();
    expect(b.durum).toBe("kimlik-uymuyor");
    expect(b.adres).toBe(null);
    const e = await hata(t.kart.istek("POST", "/komut", [], "Gb1000"));
    expect(e.tur).toBe("bagli-degil");
    expect(t.imzalilar()).toEqual([]);
    expect(baska.durum.imzali).toBe(0);
    expect(baska.durum.ret401).toBe(0);
    expect(baska.durum.komutlar).toEqual([]);
    // Saat de verilmez, eslesme kaldirma karta gitmez.
    expect(await t.kart.saatVer()).toBe(false);
    expect(t.imzalilar()).toEqual([]);
  });

  it("kart yok -> 'bulunamadi'", async () => {
    const { k, dunya } = await eslesmis();
    await k.kapat();
    const t = telefon(dunya);
    expect((await t.kart.baglan()).durum).toBe("bulunamadi");
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("bagli-degil");
  });

  it("baglanti SURERKEN kart degisirse (401 + yeni acilis) kimlik yeniden dogrulanir; yeniden deneme GITMEZ", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    await t.kart.istek("GET", "/kayit/liste");
    const port = k.port;
    await k.kapat();
    const baska = await kartAc({ kimlik: K2, port });
    const once = t.imzalilar().length;
    const e = await hata(t.kart.istek("POST", "/komut", [], "Gb1000"));
    expect(e.tur).toBe("kimlik-uymuyor");
    expect(t.imzalilar().length).toBe(once + 1);          // yalniz ilk deneme; ikincisi atilmadi
    expect(baska.durum.imzali).toBe(0);
    expect(baska.durum.komutlar).toEqual([]);
    // Baglanti dustu: yeniden baglan() gerekir.
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("bagli-degil");
    expect(t.imzalilar().length).toBe(once + 1);
  });

  it("baglan ile esles ARASINDA kart degisirse -> 'kimlik-uymuyor', kanit yollanmaz", async () => {
    const k = await kartAc();
    const dunya = dunyaKur(k);
    const t = telefon(dunya);
    await t.kart.baglan();
    const port = k.port;
    await k.kapat();
    const baska = await kartAc({ kimlik: K2, port });
    const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
    expect(e.tur).toBe("kimlik-uymuyor");
    expect(t.kopru.cagrilar.filter((c) => c.yontem === "POST")).toEqual([]);
    expect(baska.durum.cihazlar.size).toBe(0);
    expect(dunya.disk.anahtarlar.size).toBe(0);
  });

  it("kesif yanlis kimlik dondurse bile baglanti KURULMAZ; kesfe beklenen kimlik verilir", async () => {
    const { k, dunya } = await eslesmis();
    const ag = agKur(kopruSahtesi(), { yerelDongu: true });
    const cagri = [];
    const yalanci = {
      bul: async (s) => { cagri.push(s); return { adres: adres(k), kimlik: K2, bilgi: { kimlik: K2, saat: 0 }, kaynak: "ap" }; },
    };
    const kasa = kasaKur(kasaSahtesi(dunya.disk));
    const kart = kartKur({ ag, kesif: yalanci, kasa });
    expect((await kart.baglan({ elle: "127.0.0.1" })).durum).toBe("kimlik-uymuyor");
    expect(cagri).toEqual([{ beklenenKimlik: K1, elle: "127.0.0.1" }]);
    expect((await hata(kart.istek("GET", "/kayit/liste"))).tur).toBe("bagli-degil");
    expect(k.durum.imzali).toBe(0);
    expect(k.durum.ret401).toBe(0);
  });

  it("eszamanli 50 imzali istek: sayaclarin hepsi FARKLI, kart hepsini kabul eder, disk yazimi 1", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    const once = k.durum.imzali;
    const yanitlar = await Promise.all(Array.from({ length: 50 }, () => t.kart.istek("GET", "/kayit/liste")));
    expect(yanitlar.map((y) => y.status)).toEqual(Array(50).fill(200));
    const sayaclar = t.imzalilar().map((c) => c.basliklar["X-Sayac"]);
    expect(sayaclar.length).toBe(50);
    expect(new Set(sayaclar).size).toBe(50);
    expect(k.durum.imzali).toBe(once + 50);
    expect(k.durum.ret401).toBe(0);
    expect(t.kasaEk.sayacYazimi).toBe(1);
    expect(t.ihlal).toEqual([]);
  });

  it("isaret yazimi istekten ONCE biter (yazim gecikse de istek beklemeden yola cikmaz)", async () => {
    const { dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    t.kasaEk.yazimGecikmeMs = 60;
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    expect(t.kasaEk.sayacYazimi).toBe(1);                // yeniden baslatmadan sonraki ilk istek yazar
    expect(t.imzalilar().length).toBe(1);
    expect(t.ihlal).toEqual([]);
  });

  it("saat 1 yil GERI alinip uygulama yeniden baslasa da kart istegi kabul eder (sayac geri gitmez)", async () => {
    const { k, dunya, t } = await eslesmis();
    for (let i = 0; i < 5; i++) await t.kart.istek("GET", "/kayit/liste");
    const enBuyuk = t.imzalilar().map((c) => BigInt(c.basliklar["X-Sayac"])).reduce((m, v) => (v > m ? v : m));
    const geri = () => Date.now() - 365 * 24 * 3600 * 1000;
    const t2 = telefon(dunya, { saat: geri });
    await t2.kart.baglan();
    expect((await t2.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    expect(BigInt(t2.imzalilar()[0].basliklar["X-Sayac"])).toBeGreaterThan(enBuyuk);
    expect(k.durum.ret401).toBe(0);
    expect(t2.ihlal).toEqual([]);
  });

  it("disk bizden ilerideyse ('geri') istek yeni sayacla BIR kez yeniden imzalanir ve gecer", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    const ileri = dunya.disk.isaretler.get(K1) + 1_000_000_000n;
    dunya.disk.isaretler.set(K1, ileri);                  // ikinci bir yazar isareti ileri tasidi
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    expect(t.imzalilar().length).toBe(1);
    expect(BigInt(t.imzalilar()[0].basliklar["X-Sayac"])).toBeGreaterThan(ileri);
    expect(k.durum.ret401).toBe(0);
    expect(t.ihlal).toEqual([]);
  });

  it("saatVer (A18): NTP'siz kartta baglanti basina BIR KEZ; NTP'li kartta hic; 409 sessiz", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya, { saat: () => 1_790_000_000_500 });
    await t.kart.baglan();
    expect(await t.kart.saatVer()).toBe(true);
    expect(k.durum.saat).toBe(1_790_000_000);
    expect(await t.kart.saatVer()).toBe(false);
    expect(t.imzalilar().filter((c) => c.url.includes("/saat")).length).toBe(1);
    expect(t.imzalilar()[0].yontem).toBe("POST");

    // Yeni baglanti: kart artik saati biliyor (kaynak 2) ama NTP degil -> yine bir kez verilir.
    const t2 = telefon(dunya);
    await t2.kart.baglan();
    expect(await t2.kart.saatVer()).toBe(true);
    // NTP'li kart (bilgi.saat === 1): hic istek yok.
    k.ayarla({ saatKaynak: 1 });
    const t3 = telefon(dunya);
    await t3.kart.baglan();
    expect(await t3.kart.saatVer()).toBe(false);
    expect(t3.imzalilar()).toEqual([]);
    // Bilgi "NTP yok" derken kart o arada NTP almis: 409 sessizce gecilir.
    k.ayarla({ saatKaynak: 0 });
    const t4 = telefon(dunya);
    await t4.kart.baglan();
    k.ayarla({ saatNtp: true });
    expect(await t4.kart.saatVer()).toBe(false);
    expect(t4.imzalilar().length).toBe(1);
  });

  it("eslesmeyiKaldir (A19): kart ulasiliyorsa kartta da silinir; ulasilmiyorsa yalniz yerelde", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    expect(await t.kart.eslesmeyiKaldir()).toEqual({ kartta: true });
    expect(k.durum.cihazlar.size).toBe(0);
    expect(dunya.disk.anahtarlar.size).toBe(0);
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");

    const iki = await eslesmis();
    await iki.k.kapat();
    const t2 = telefon(iki.dunya);
    expect((await t2.kart.baglan()).durum).toBe("bulunamadi");
    expect(await t2.kart.eslesmeyiKaldir()).toEqual({ kartta: false });
    expect(iki.dunya.disk.anahtarlar.size).toBe(0);
    expect(t2.imzalilar()).toEqual([]);
    // Hic baglan() cagrilmadan da yerel kayit silinir.
    const uc = await eslesmis();
    const t3 = telefon(uc.dunya);
    expect(await t3.kart.eslesmeyiKaldir()).toEqual({ kartta: false });
    expect(uc.dunya.disk.anahtarlar.size).toBe(0);
  });

  it("zaten esliyken yeniden esles -> 'zaten-esli' (karta istek gitmez)", async () => {
    const { t } = await eslesmis();
    const once = t.kopru.cagrilar.length;
    expect((await hata(t.kart.esles("sinama telefonu", PAROLA))).tur).toBe("zaten-esli");
    expect(t.kopru.cagrilar.length).toBe(once);
  });

  it("anahtar saklanamazsa: 'kasa', K sifirlanir, karttaki yetim cihaz silinir", async () => {
    const k = await kartAc();
    const dunya = dunyaKur(k);
    const t = telefon(dunya);
    await t.kart.baglan();
    t.kasaEk.anahtarYaz = async () => { const e = new Error("x"); e.code = "ic-hata"; throw e; };
    const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
    expect(e.tur).toBe("kasa");
    expect(dunya.disk.anahtarlar.size).toBe(0);
    expect(k.durum.cihazlar.size).toBe(0);
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");
  });

  it("ag hatasi -> 'ag' (alt tur ile); HTTP hatasi -> 'http' + durum; hata nesnelerinde adres/imza/K yok", async () => {
    const { k, dunya } = await eslesmis();
    const t = telefon(dunya);
    await t.kart.baglan();
    const K = hex(k.durum.cihazlar.get(1).K);
    const e1 = await hata(t.kart.istek("GET", "/boyle-bir-yol-yok"));
    expect(e1).toMatchObject({ tur: "http", durum: 404 });
    await k.kapat();
    const e2 = await hata(t.kart.istek("GET", "/kayit/liste"));
    expect(e2).toMatchObject({ tur: "ag", ag: "baglanti" });
    const imzalar = t.imzalilar().map((c) => c.basliklar["X-Imza"]);
    expect(imzalar.length).toBe(2);
    for (const e of [e1, e2]) {
      expect(e).toBeInstanceOf(KartHatasi);
      const m = yazi(e);
      for (const sir of [K, K1, "127.0.0.1", ...imzalar]) expect(m).not.toContain(sir);
      expect(Object.keys(e).sort().every((a) => ["tur", "durum", "ag", "saniye", "name"].includes(a))).toBe(true);
    }
  });
});
