// canli.js (5C-1, A6/A7/A40): akis durum makinesi + komut beyaz listesi.
//   1. bolum: elle surulen sahte eklenti + elle saat — yeniden baglanma sureleri, sira, yaris halleri.
//   2. bolum: sahte kart (127.0.0.1) + KartAg sahtesi + gercek kart.js / kasa.js — uctan uca, IMZALI.
import { describe, it, expect, afterEach } from "vitest";
import http from "node:http";
import { akisUrl } from "@ortak/imza.js";
import { agKur, KartAgHatasi } from "../src/cekirdek/ag.js";
import {
  CanliHatasi, DOLU_BEKLE_MS, SERI_SURE_MS, SESSIZ_MS, YENIDEN_BUL_HER, YENIDEN_MS, canliKur, komutGecerli,
} from "../src/cekirdek/canli.js";
import { kartKur } from "../src/cekirdek/kart.js";
import { kasaKur } from "../src/cekirdek/kasa.js";
import { kesifKur } from "../src/cekirdek/kesif.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kasaDiski, kasaSahtesi } from "./yardim/kasa_sahtesi.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";

const D1 = "D 12.0000 0.500000 6.00000 1.0000 0.0002778 1000 97 0 0";
const D2 = "D 12.5000 0.400000 5.00000 2.0000 0.0005556 1200 97 0 0";
const G15 = "G 2 41 120 61300 61276 137 4 0 1850 24100 3 912 0 0 0";
const G13 = "G 1 0 0 61300 61276 137 4 0 1850 24100 3 912 0";
const bosalt = () => new Promise((r) => setImmediate(r));

async function hata(soz) {
  try { await soz; } catch (e) { return e; }
  throw new Error("hata bekleniyordu");
}

// ── elle surulen dunya ────────────────────────────────────────────────────────────────────────
function dunya({ kartDurumu = "bagli", kartAkisUrl = false, ...secenek } = {}) {
  let simdi = 1_000_000;
  const isler = [];
  const d = {
    kartDurumu, urlSayisi: 0, acilan: [], kapanan: [], istekler: [], baglanSayisi: 0,
    urlAl: null, acCevap: null, dinleyici: {}, istekCevap: null,
  };
  const zamanla = (fn, ms) => { const k = { fn, ms, an: simdi + ms }; isler.push(k); return k; };
  const zamaniBirak = (k) => { const i = isler.indexOf(k); if (i >= 0) isler.splice(i, 1); };
  const urlUret = async () => {
    d.urlSayisi += 1;
    if (d.urlAl) return d.urlAl(d.urlSayisi);
    return `http://127.0.0.1:1/akis?_c=1&_s=${d.urlSayisi}&_i=${"ab".repeat(32)}`;
  };
  const kart = {
    durum: () => ({ durum: d.kartDurumu, adres: d.kartDurumu === "bagli-degil" ? null : "127.0.0.1:1", kimlik: null }),
    istek: async (...a) => { d.istekler.push(a); if (d.istekCevap) return d.istekCevap(...a); return { status: 204 }; },
    baglan: async () => { d.baglanSayisi += 1; return { durum: d.kartDurumu }; },
  };
  if (kartAkisUrl) kart.akisUrl = urlUret;
  const ag = {
    akisAc: (url) => {
      d.acilan.push(url);
      if (d.acCevap) return d.acCevap(d.acilan.length);
      return Promise.resolve({ kimlik: `a${d.acilan.length}` });
    },
    akisKapat: (kimlik) => { d.kapanan.push(kimlik); return Promise.resolve(); },
  };
  const eklenti = { addListener: (olay, fn) => { d.dinleyici[olay] = fn; return Promise.resolve({ remove: async () => {} }); } };
  const canli = canliKur({
    kart, ag, eklenti, simdiMs: () => simdi, zamanla, zamaniBirak,
    ...(kartAkisUrl ? {} : { akisUrlAl: urlUret }), ...secenek,
  });
  return {
    d, canli, kart,
    bekleyenler: () => isler.map((k) => k.ms).sort((x, y) => x - y),
    async ilerlet(ms) {
      const hedef = simdi + ms;
      for (;;) {
        const k = isler.filter((x) => x.an <= hedef).sort((x, y) => x.an - y.an)[0];
        if (!k) break;
        simdi = k.an;
        zamaniBirak(k);
        k.fn();
        await bosalt();
      }
      simdi = hedef;
      await bosalt();
    },
    durumOlayi: (kimlik, hal, ek = {}) => d.dinleyici.akisDurum({ kimlik, hal, ...ek }),
    satirOlayi: (kimlik, ...satirlar) => d.dinleyici.akis({ kimlik, satirlar }),
  };
}

async function acikDunya(secenek) {
  const w = dunya(secenek);
  w.canli.baslat();
  await bosalt();
  w.durumOlayi("a1", "acik");
  await bosalt();
  return w;
}

describe("canli: akis durum makinesi (elle saat)", () => {
  it("baslat: kapali -> baglaniyor -> acik; acilinca BIR kez G? sorulur", async () => {
    const w = dunya();
    expect(w.canli.durum()).toEqual({ bagli: false, hal: "kapali", sebep: null, kod: null, son: null, kayit: null, yas_ms: null, ayrinti: {} });
    w.canli.baslat();
    expect(w.canli.durum().hal).toBe("baglaniyor");
    await bosalt();
    expect(w.d.acilan.length).toBe(1);
    expect(w.canli.durum().hal).toBe("baglaniyor");
    w.durumOlayi("a1", "acik");
    await bosalt();
    expect(w.canli.durum()).toMatchObject({ bagli: true, hal: "acik", sebep: null });
    expect(w.d.istekler.length).toBe(1);
    expect(w.d.istekler[0].slice(0, 2)).toEqual(["POST", "/komut"]);
    expect(new TextDecoder().decode(w.d.istekler[0][3])).toBe("G?");
    // ikinci baslat hicbir sey yapmaz
    w.canli.baslat();
    await bosalt();
    expect(w.d.acilan.length).toBe(1);
  });

  it("D ve G satirlari: son, kayit, yas_ms, seri, dinleyici", async () => {
    const w = await acikDunya();
    const gorulen = [];
    const birak = w.canli.dinle((s) => gorulen.push(s));
    w.satirOlayi("a1", D1);
    await w.ilerlet(200);
    w.satirOlayi("a1", D2, G15, "K 1 2 3", "* serbest metin");
    expect(w.canli.durum().son).toMatchObject({ tur: "D", v: 12.5, a: 0.4, w: 5 });
    expect(w.canli.durum().kayit).toMatchObject({ tur: "G", durum: 2, oturum: 41, son_not: 0 });
    expect(w.canli.durum().ayrinti.K).toMatchObject({ kayip_ms: 1 });
    expect(w.canli.durum().yas_ms).toBe(0);
    await w.ilerlet(700);
    expect(w.canli.durum().yas_ms).toBe(700);
    expect(gorulen.length).toBe(3);                              // D, D, G (K ve serbest metin bildirilmez)
    expect(gorulen[2].kayit.oturum).toBe(41);
    const s = w.canli.seri();
    expect(s.n).toBe(2);
    expect(s.t).toBeInstanceOf(Float64Array);
    expect(Array.from(s.t)).toEqual([1_000_000, 1_000_200]);
    expect(Array.from(s.v)).toEqual([12, 12.5]);
    expect(Array.from(s.a)).toEqual([0.5, 0.4]);
    expect(Array.from(s.w)).toEqual([6, 5]);
    birak();
    w.satirOlayi("a1", D1);
    expect(gorulen.length).toBe(3);
    // 13 alanli G de kayit durumudur
    w.satirOlayi("a1", G13);
    expect(w.canli.durum().kayit).toMatchObject({ durum: 1, son_not: null, mesaj_dusen: null });
  });

  it("hal degisimi dinleyiciye bildirilir; dinleyicinin hatasi akisi bozmaz", async () => {
    const w = dunya();
    const haller = [];
    w.canli.dinle(() => { throw new Error("arayuz hatasi"); });
    w.canli.dinle((s) => haller.push(s.hal));
    w.canli.baslat();
    await bosalt();
    w.durumOlayi("a1", "acik");
    w.satirOlayi("a1", D1);
    w.canli.durdur();
    expect(haller).toEqual(["baglaniyor", "acik", "acik", "kapali"]);
  });

  it("yeniden baglanma 1, 2, 4, 8, 16, 30, 30 s; her denemede YENI adres", async () => {
    expect([...YENIDEN_MS]).toEqual([1000, 2000, 4000, 8000, 16000, 30000]);
    const w = await acikDunya();
    const beklenen = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000];
    for (let i = 0; i < beklenen.length; i++) {
      w.durumOlayi(`a${i + 1}`, "hata", { tur: "baglanti" });
      expect(w.canli.durum()).toMatchObject({ bagli: false, hal: "hata", sebep: "baglanti" });
      expect(w.bekleyenler()).toEqual([beklenen[i]]);
      await w.ilerlet(beklenen[i] - 1);
      expect(w.d.acilan.length).toBe(i + 1);
      await w.ilerlet(1);
      expect(w.d.acilan.length).toBe(i + 2);
      expect(w.canli.durum().hal).toBe("baglaniyor");
    }
    expect(new Set(w.d.acilan).size).toBe(w.d.acilan.length);    // hicbir adres iki kez kullanilmadi
    expect(w.d.urlSayisi).toBe(w.d.acilan.length);
  });

  it("veri gelince bekleme 1 s'ye doner; yalniz 'acik' olmak donmez", async () => {
    const w = await acikDunya();
    w.durumOlayi("a1", "kapandi");
    await w.ilerlet(1000);
    w.durumOlayi("a2", "acik");                                  // acildi ama veri yok
    w.durumOlayi("a2", "hata", { tur: "zaman-asimi" });
    expect(w.bekleyenler()).toEqual([2000]);
    await w.ilerlet(2000);
    w.durumOlayi("a3", "acik");
    w.satirOlayi("a3", D1);
    w.durumOlayi("a3", "kapandi");
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "kapandi" });
    expect(w.bekleyenler()).toEqual([1000]);
  });

  it("dolu: hal 'dolu', TAM 10 s sonra yeniden dener (yeni adresle)", async () => {
    expect(DOLU_BEKLE_MS).toBe(10000);
    const w = await acikDunya();
    w.durumOlayi("a1", "dolu");
    expect(w.canli.durum()).toMatchObject({ bagli: false, hal: "dolu" });
    expect(w.bekleyenler()).toEqual([10000]);
    await w.ilerlet(9999);
    expect(w.d.acilan.length).toBe(1);
    await w.ilerlet(1);
    expect(w.d.acilan.length).toBe(2);
    expect(w.d.acilan[1]).not.toBe(w.d.acilan[0]);
    // art arda dolu: bekleme uzamaz
    w.durumOlayi("a2", "dolu");
    expect(w.bekleyenler()).toEqual([10000]);
  });

  it("durdur: akis HEMEN kapatilir, zamanlayici kalmaz, gec gelen olaylar yok sayilir", async () => {
    const w = await acikDunya();
    w.satirOlayi("a1", D1);
    w.canli.durdur();
    expect(w.d.kapanan).toEqual(["a1"]);
    expect(w.canli.durum()).toMatchObject({ bagli: false, hal: "kapali" });
    expect(w.bekleyenler()).toEqual([]);
    w.durumOlayi("a1", "kapandi");
    w.durumOlayi("a1", "hata", { tur: "baglanti" });
    w.satirOlayi("a1", D2);
    expect(w.canli.durum().hal).toBe("kapali");
    expect(w.bekleyenler()).toEqual([]);
    expect(w.canli.seri().n).toBe(1);
    // yeniden baslat: yeni adres, bekleme bastan
    w.canli.baslat();
    await bosalt();
    expect(w.d.acilan.length).toBe(2);
    expect(w.d.acilan[1]).not.toBe(w.d.acilan[0]);
  });

  it("yeniden baglanma beklerken durdur: deneme yapilmaz", async () => {
    const w = await acikDunya();
    w.durumOlayi("a1", "hata", { tur: "baglanti" });
    w.canli.durdur();
    await w.ilerlet(60000);
    expect(w.d.acilan.length).toBe(1);
    expect(w.canli.durum().hal).toBe("kapali");
  });

  it("akisAc donmeden durdur: acilan akis sahipsiz kalmaz, kapatilir", async () => {
    const w = dunya();
    let coz;
    w.d.acCevap = () => new Promise((c) => { coz = c; });
    w.canli.baslat();
    await bosalt();
    w.canli.durdur();
    expect(w.d.kapanan).toEqual([]);
    coz({ kimlik: "a9" });
    await bosalt();
    expect(w.d.kapanan).toEqual(["a9"]);
    expect(w.canli.durum().hal).toBe("kapali");
    expect(w.bekleyenler()).toEqual([]);
  });

  it("akisAc donmeden gelen olaylar saklanir ve kimlik belli olunca islenir; baska akisin olaylari islenmez", async () => {
    const w = dunya();
    let coz;
    w.d.acCevap = () => new Promise((c) => { coz = c; });
    w.canli.baslat();
    await bosalt();
    w.durumOlayi("a7", "acik");
    w.satirOlayi("a7", D1);
    w.satirOlayi("yabanci", D2);
    w.durumOlayi("yabanci", "dolu");
    expect(w.canli.durum().hal).toBe("baglaniyor");
    coz({ kimlik: "a7" });
    await bosalt();
    expect(w.canli.durum()).toMatchObject({ hal: "acik", bagli: true });
    expect(w.canli.durum().son.v).toBe(12);
    expect(w.canli.seri().n).toBe(1);
    w.satirOlayi("yabanci", D2);
    w.durumOlayi("yabanci", "hata", { tur: "baglanti" });
    expect(w.canli.durum().hal).toBe("acik");
    expect(w.canli.seri().n).toBe(1);
  });

  it("akisAc reddederse: hal 'hata', tur tasinir, yeniden denenir", async () => {
    const w = dunya();
    w.d.acCevap = (n) => (n === 1 ? Promise.reject(new KartAgHatasi("wifi-yok")) : Promise.resolve({ kimlik: "a2" }));
    w.canli.baslat();
    await bosalt();
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "wifi-yok" });
    await w.ilerlet(1000);
    expect(w.d.acilan.length).toBe(2);
  });

  it("sessizlik bekcisi: 45 s hic olay gelmezse akis kapatilir ve yeniden denenir", async () => {
    expect(SESSIZ_MS).toBe(45000);
    const w = await acikDunya();
    await w.ilerlet(30000);
    w.satirOlayi("a1", D1);                                      // olay bekciyi kurar
    await w.ilerlet(44999);
    expect(w.canli.durum().hal).toBe("acik");
    expect(w.d.kapanan).toEqual([]);
    await w.ilerlet(1);
    expect(w.d.kapanan).toEqual(["a1"]);
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "sessiz" });
    await w.ilerlet(1000);
    expect(w.d.acilan.length).toBe(2);
  });

  it("sessizlik bekcisi baglanirken de calisir (eklenti 'acik' demezse)", async () => {
    const w = dunya();
    w.canli.baslat();
    await bosalt();
    await w.ilerlet(SESSIZ_MS);
    expect(w.d.kapanan).toEqual(["a1"]);
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "sessiz" });
  });

  it("kart bagli degil / eslesmemis: akis ACILMAZ, adres istenmez, sebep soylenir, sonra yeniden bakilir", async () => {
    for (const durum of ["bagli-degil", "eslesmemis"]) {
      const w = dunya({ kartDurumu: durum });
      w.canli.baslat();
      await bosalt();
      expect(w.canli.durum()).toMatchObject({ bagli: false, hal: "hata", sebep: durum });
      expect(w.d.urlSayisi).toBe(0);
      expect(w.d.acilan).toEqual([]);
      w.d.kartDurumu = "bagli";
      await w.ilerlet(1000);
      expect(w.d.acilan.length).toBe(1);
      expect(w.d.baglanSayisi).toBe(0);                          // varsayilan: kesfi kendi baslatmaz
    }
  });

  it("yenidenBul acikken: kart bagli degilse ve her 3. basarisiz denemede kart.baglan() cagrilir", async () => {
    expect(YENIDEN_BUL_HER).toBe(3);
    const w = dunya({ kartDurumu: "bagli-degil", yenidenBul: true });
    w.canli.baslat();
    await bosalt();
    expect(w.d.baglanSayisi).toBe(1);                            // bagli degil: hemen
    w.d.kartDurumu = "bagli";
    await w.ilerlet(1000);
    expect(w.d.acilan.length).toBe(1);
    const once = w.d.baglanSayisi;
    for (let i = 1; i <= 3; i++) {
      w.durumOlayi(`a${i}`, "hata", { tur: "baglanti" });
      await w.ilerlet(30000);
    }
    expect(w.d.baglanSayisi).toBe(once + 1);
  });

  it("akis 401: yeniden baglanmadan once imzali bir istekle acilis tazelenir", async () => {
    const w = await acikDunya();
    const once = w.d.istekler.length;
    w.durumOlayi("a1", "hata", { tur: "http", kod: 401 });
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "http", kod: 401 });
    await w.ilerlet(1000);
    expect(w.d.istekler.length).toBe(once + 1);
    expect(w.d.acilan.length).toBe(2);
    // 401 disindaki kodda tazeleme yok
    w.durumOlayi("a2", "hata", { tur: "http", kod: 503 });
    await w.ilerlet(2000);
    expect(w.d.istekler.length).toBe(once + 1);
    expect(w.d.acilan.length).toBe(3);
  });

  it("tazeleme istegi 'cihaz-silinmis' derse sebep odur; deneme surer", async () => {
    const w = await acikDunya();
    w.d.istekCevap = () => { const e = new Error("x"); e.tur = "cihaz-silinmis"; throw e; };
    w.durumOlayi("a1", "hata", { tur: "http", kod: 401 });
    await w.ilerlet(1000);
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "cihaz-silinmis" });
    expect(w.d.acilan.length).toBe(1);
    expect(w.bekleyenler()).toEqual([2000]);
  });

  it("kart.akisUrl varsa o kullanilir; ikisi de yoksa 'ic-hata' (kurulum atmaz)", async () => {
    const w = dunya({ kartAkisUrl: true });
    w.canli.baslat();
    await bosalt();
    expect(w.d.acilan.length).toBe(1);
    const yalinKart = { durum: () => ({ durum: "bagli" }), istek: async () => ({ status: 204 }) };
    const c = canliKur({ kart: yalinKart, ag: { akisAc: async () => ({ kimlik: "x" }), akisKapat: async () => {} }, eklenti: { addListener: () => ({ remove() {} }) }, zamanla: () => 0, zamaniBirak: () => {} });
    c.baslat();
    await bosalt();
    expect(c.durum()).toMatchObject({ hal: "hata", sebep: "ic-hata" });
  });

  it("akis adresi hicbir duruma / hataya girmez (A45)", async () => {
    const w = dunya();
    w.d.urlAl = () => { throw new Error("http://127.0.0.1:1/akis?_c=1&_s=5&_i=sinama-imza"); };
    w.canli.baslat();
    await bosalt();
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "ic-hata" });
    w.d.urlAl = null;
    await w.ilerlet(1000);
    w.durumOlayi("a1", "hata", { tur: "http://127.0.0.1/akis?_i=sinama-imza", kod: "401 _i=sinama-imza" });
    const yazi = JSON.stringify(w.canli.durum());
    expect(yazi).not.toMatch(/_i=|_s=|_c=|sinama-imza|127\.0\.0\.1/);
    expect(w.canli.durum()).toMatchObject({ hal: "hata", sebep: "ic-hata", kod: null });
  });

  it("bozuk olay verisi cokertmez: satirlar dizi degil, satir metin degil, dev satir, cok satir", async () => {
    const w = await acikDunya();
    const f = w.d.dinleyici;
    for (const veri of [null, undefined, 5, {}, { kimlik: "a1" }, { kimlik: "a1", satirlar: "D 1" }, { kimlik: "a1", satirlar: [null, 5, {}, "D " + "9".repeat(50000), "D 1 2"] }]) {
      expect(() => f.akis(veri)).not.toThrow();
      expect(() => f.akisDurum(veri)).not.toThrow();
    }
    expect(w.canli.durum().son).toBe(null);
    expect(w.canli.seri().n).toBe(0);
    expect(w.canli.durum().hal).toBe("acik");
    // tek olayda en cok 256 satir islenir
    f.akis({ kimlik: "a1", satirlar: Array.from({ length: 1000 }, () => D1) });
    expect(w.canli.seri().n).toBe(256);
  });

  it("seri: son 5 dakika; eski noktalar dusurulur; kapasite asilinca en eskiler gider", async () => {
    expect(SERI_SURE_MS).toBe(300000);
    const w = await acikDunya({ seriKapasite: 8 });
    for (let i = 0; i < 20; i++) {
      w.satirOlayi("a1", `D ${i}.0000 0.500000 6.00000 1.0000 0.0002778 ${1000 + i} 97 0 0`);
      await w.ilerlet(1000);
    }
    let s = w.canli.seri();
    expect(s.n).toBe(8);
    expect(Array.from(s.v)).toEqual([12, 13, 14, 15, 16, 17, 18, 19]);
    expect(s.t.length).toBe(8);
    for (let i = 1; i < s.n; i++) expect(s.t[i] - s.t[i - 1]).toBe(1000);
    await w.ilerlet(SERI_SURE_MS - 5000);                        // en yeni nokta 4 dk 56 s once; 4 nokta 5 dk'dan eski
    s = w.canli.seri();
    expect(Array.from(s.v)).toEqual([16, 17, 18, 19]);
    await w.ilerlet(5000);
    expect(w.canli.seri().n).toBe(0);
    expect(w.canli.seri().t.length).toBe(0);
  });

  it("ADC hatasinda NaN deger seriye NaN girer (grafikte bosluk)", async () => {
    const w = await acikDunya();
    w.satirOlayi("a1", "D nan 0.500000 nan 1.0000 0.0002778 1000 97 0 1");
    expect(Number.isNaN(w.canli.seri().v[0])).toBe(true);
    expect(w.canli.seri().a[0]).toBe(0.5);
  });
});

describe("canli: komut beyaz listesi", () => {
  const IZINLI = ["Gb0", "Gb20", "Gb50", "Gb200", "Gb1000", "Gb60000", "Gd", "G?", "?"];
  const YASAK = [
    "p0", "p1", "p", "N?", "Ns", "Nasinama", "E?", "Ex1", "Q?", "Q1", "k?", "kk", "GF!", "Go61276", "Gt0", "Gtd", "Gp-", "Gp?", "Ga1 ad",
    "Gb", "Gb19", "Gb1", "Gb60001", "Gb100000", "Gb050", "Gb00", "Gb-5", "Gb5.5", "Gb200 ", " Gb200", "Gb200\n", "Gb200\nN?", "Gb200;N?",
    "gd", "GD", "Gd ", "Gd\n", "G??", "??", "? ", "", " ", "s0.005", "m1", "t", "r20", "z",
    null, undefined, 5, {}, ["Gd"],
  ];

  it("komutGecerli: yalniz Gb<0|50…60000>, Gd, G?, ?", () => {
    for (const k of IZINLI) expect(komutGecerli(k), String(k)).toBe(true);
    for (const k of YASAK) expect(komutGecerli(k), String(k)).toBe(false);
  });

  it("yasak komut kart.istek'e HIC gitmez; izinli komut imzali POST /komut olur", async () => {
    const w = dunya();
    for (const k of YASAK) {
      const e = await hata(w.canli.komut(k));
      expect(e).toBeInstanceOf(CanliHatasi);
      expect(e.tur).toBe("komut-yasak");
      expect(e.message).toBe("komut-yasak");
    }
    expect(w.d.istekler).toEqual([]);
    expect(await w.canli.komut("Gb200")).toBe(true);
    expect(w.d.istekler.length).toBe(1);
    const [yontem, yol, arg, govde] = w.d.istekler[0];
    expect([yontem, yol, arg]).toEqual(["POST", "/komut", []]);
    expect(new TextDecoder().decode(govde)).toBe("Gb200");
  });

  it("kart.istek'in hatasi aynen cagirana doner", async () => {
    const w = dunya();
    w.d.istekCevap = () => { const e = new Error("bagli-degil"); e.tur = "bagli-degil"; throw e; };
    expect((await hata(w.canli.komut("Gd"))).tur).toBe("bagli-degil");
  });
});

describe("canliKur: kurulum", () => {
  it("eksik parca TypeError", () => {
    const ag = { akisAc: async () => ({}), akisKapat: async () => {} };
    const kart = { durum: () => ({}), istek: async () => {} };
    const eklenti = { addListener: () => {} };
    expect(() => canliKur({ kart: {}, ag, eklenti })).toThrow(TypeError);
    expect(() => canliKur({ kart, ag: {}, eklenti })).toThrow(TypeError);
    expect(() => canliKur({ kart, ag, eklenti: {} })).toThrow(TypeError);
    expect(() => canliKur({ kart, ag, eklenti })).not.toThrow();
  });
});

// ── uctan uca: sahte kart ─────────────────────────────────────────────────────────────────────
const PAROLA = "sinama-parolasi-1";
const K1 = "00112233aabbccdd";
const OLCEK = 50;                                  // 1 s -> 20 ms, 10 s -> 200 ms, 45 s -> 900 ms

async function bekle(kosul, ms = 4000) {
  const son = Date.now() + ms;
  for (;;) {
    if (kosul()) return;
    if (Date.now() > son) throw new Error("kosul saglanmadi");
    await new Promise((r) => setTimeout(r, 5));
  }
}

function hamIzleyici(port) {                       // imzasiz, ham SSE izleyicisi (misafir aciksa yuva tutar)
  return new Promise((coz, reddet) => {
    const r = http.get({ host: "127.0.0.1", port, path: "/akis" }, (y) => { y.resume(); coz({ kod: y.statusCode, kapat: () => r.destroy() }); });
    r.on("error", reddet);
  });
}

describe("canli: sahte kartla uctan uca (imzali akis)", () => {
  const acik = [];
  afterEach(async () => {
    for (const kapat of acik.splice(0).reverse()) await kapat();
  });

  async function kur({ zorunlu = 1 } = {}) {
    const k = await sahteKartAc({ parola: PAROLA, kimlik: K1, zorunlu, akisAralikMs: 20 });
    acik.push(() => k.kapat());
    const kopru = kopruSahtesi();
    const ag = agKur(kopru, { yerelDongu: true, zamanAsimiMs: 3000 });
    let kayit = null;
    const kesif = kesifKur({
      kartFetch: ag.kartFetch, onbellek: { oku: () => kayit, yaz: (x) => { kayit = x; } }, yerelDongu: true, zamanAsimiMs: 500,
      sabitAdaylar: [{ adres: `127.0.0.1:${k.port}`, kaynak: "ap" }],
    });
    const kasa = kasaKur(kasaSahtesi(kasaDiski()));
    const kart = kartKur({ ag, kesif, kasa });
    expect((await kart.baglan()).durum).toBe("eslesmemis");
    await kart.esles("sinama telefonu", PAROLA);
    expect(kart.durum().durum).toBe("bagli");
    const cihaz = await kasa.cihazYukle(K1);
    // kart.js'e eklenmesi onerilen `akisUrl()` yonteminin yaptigi is (canli.js'e enjekte edilir).
    const akisUrlAl = () => akisUrl(cihaz, k.taban, { fetch: ag.kartFetch, kaydet: kasa.kaydet });
    const canli = canliKur({ kart, ag, eklenti: kopru, akisUrlAl, zamanla: (fn, ms) => setTimeout(fn, ms / OLCEK), zamaniBirak: clearTimeout });
    acik.push(async () => { canli.durdur(); });
    return { k, kopru, kart, canli };
  }

  const sayac = (url) => Number(/[?&]_s=([0-9]+)/.exec(url)[1]);

  it("D satirlari akar: seri dolar, hal 'acik', adres imzali; imzasiz izleyici reddedilir", async () => {
    const { k, kopru, canli } = await kur();
    expect((await hamIzleyici(k.port)).kod).toBe(401);           // zorunlu: imzasiz akis yok (test ayirt ediyor)
    canli.baslat();
    await bekle(() => canli.seri().n >= 5);
    expect(canli.durum()).toMatchObject({ bagli: true, hal: "acik" });
    expect(canli.durum().son).toMatchObject({ tur: "D", menzil: 0, adcHata: 0 });
    expect(canli.durum().son.v).toBeGreaterThan(11.9);
    expect(k.durum.akisAcik).toBe(1);
    expect(kopru.akisCagrilari.length).toBe(1);
    expect(kopru.akisCagrilari[0].url).toMatch(/\/akis\?_c=[0-9]+&_s=[0-9]+&_i=[0-9a-f]{64}$/);
    const s = canli.seri();
    for (let i = 1; i < s.n; i++) expect(s.t[i]).toBeGreaterThanOrEqual(s.t[i - 1]);
    await bekle(() => k.durum.komutlar.includes("G?"));          // acilinca kayit durumu soruldu (imzali)
  });

  it("kart yeniden baslar: hal 'hata' -> yeni imzali adresle yeniden baglanir (sayac artar)", async () => {
    const { k, kopru, canli } = await kur();
    const haller = [];
    canli.dinle((s) => { if (haller[haller.length - 1] !== s.hal) haller.push(s.hal); });
    canli.baslat();
    await bekle(() => canli.seri().n >= 2);
    const n0 = canli.seri().n;
    k.ayarla({ yenidenBasla: true });                            // akislar duser, acilis degisir
    await bekle(() => haller.includes("hata"));
    await bekle(() => canli.durum().hal === "acik" && canli.seri().n > n0 + 2, 6000);
    const adresler = kopru.akisCagrilari.map((c) => c.url);
    expect(adresler.length).toBeGreaterThanOrEqual(2);
    expect(new Set(adresler).size).toBe(adresler.length);
    for (let i = 1; i < adresler.length; i++) expect(sayac(adresler[i])).toBeGreaterThan(sayac(adresler[i - 1]));
    expect(k.durum.akisAcik).toBe(1);
  });

  it("5. izleyici: hal 'dolu'; yuva bosalinca kendiliginden acilir", async () => {
    const { k, canli } = await kur();
    k.ayarla({ misafir: 1 });
    const izleyiciler = [];
    for (let i = 0; i < 4; i++) izleyiciler.push(await hamIzleyici(k.port));
    acik.push(async () => { for (const i of izleyiciler) i.kapat(); });
    await bekle(() => k.durum.akisAcik === 4);
    canli.baslat();
    await bekle(() => canli.durum().hal === "dolu");
    expect(canli.durum().bagli).toBe(false);
    expect(canli.seri().n).toBe(0);
    izleyiciler[0].kapat();
    await bekle(() => canli.durum().hal === "acik" && canli.seri().n > 0, 6000);
    expect(k.durum.akisAcik).toBe(4);
  });

  it("durdur (arka plan): kartin akis yuvasi bosalir; baslat ile yeniden acilir", async () => {
    const { k, kopru, canli } = await kur();
    canli.baslat();
    await bekle(() => canli.seri().n >= 1);
    expect(k.durum.akisAcik).toBe(1);
    canli.durdur();
    expect(canli.durum().hal).toBe("kapali");
    await bekle(() => k.durum.akisAcik === 0);
    const n = canli.seri().n;
    await new Promise((r) => setTimeout(r, 120));
    expect(canli.seri().n).toBe(n);                              // kapaliyken veri islenmez
    expect(kopru.akisCagrilari.length).toBe(1);                  // kapaliyken yeniden baglanma yok
    canli.baslat();
    await bekle(() => canli.seri().n > n);
    expect(k.durum.akisAcik).toBe(1);
    expect(sayac(kopru.akisCagrilari[1].url)).toBeGreaterThan(sayac(kopru.akisCagrilari[0].url));
  });

  it("komut: 'Gb200' imzali gider; yasak komutta kartin komut listesi DEGISMEZ", async () => {
    const { k, canli } = await kur();
    const imzali0 = k.durum.imzali;
    expect(await canli.komut("Gb200")).toBe(true);
    expect(k.durum.komutlar).toEqual(["Gb200"]);
    expect(k.durum.imzali).toBe(imzali0 + 1);
    for (const yasak of ["N?", "Ex1", "Q?", "k?", "GF!", "p1", "p0", "Go5", "Gb19", "Gb200\nN?"]) {
      expect((await hata(canli.komut(yasak))).tur).toBe("komut-yasak");
    }
    expect(k.durum.komutlar).toEqual(["Gb200"]);
    expect(k.durum.imzali).toBe(imzali0 + 1);
    await canli.komut("Gd");
    expect(k.durum.komutlar).toEqual(["Gb200", "Gd"]);
  });
});

describe("ag.js akis sarmalayicisi", () => {
  const IMZALI = `http://127.0.0.1:1/akis?_c=1&_s=2&_i=${"ab".repeat(32)}`;

  it("akisAc: eklentiye yalniz { url } gider, { kimlik } doner", async () => {
    const cagri = [];
    const ag = agKur({ istek: async () => ({}), akisAc: async (c) => { cagri.push(c); return { kimlik: "a1", fazla: 1 }; } }, { yerelDongu: true });
    expect(await ag.akisAc(IMZALI)).toEqual({ kimlik: "a1" });
    expect(cagri).toEqual([{ url: IMZALI }]);
  });

  it("akisAc: hedef kurali ve yol denetimi eklentiden ONCE; hata yalniz TUR tasir", async () => {
    const cagri = [];
    const ag = agKur({ istek: async () => ({}), akisAc: async (c) => { cagri.push(c); return { kimlik: "a1" }; } }, { yerelDongu: true });
    for (const [url, tur] of [
      ["http://8.8.8.8/akis?_c=1&_s=2&_i=ab", "ozel-degil"],
      ["https://127.0.0.1:1/akis", "bicim"],
      ["http://127.0.0.1:1/komut", "bicim"],
      ["http://127.0.0.1:1/akis/x", "bicim"],
      ["http://127.0.0.1:1/akisx?_c=1", "bicim"],
      ["http://127.0.0.1:1/", "bicim"],
      ["http://127.0.0.1:1", "bicim"],
      [null, "bicim"],
    ]) {
      const e = await hata(ag.akisAc(url));
      expect(e, String(url)).toBeInstanceOf(KartAgHatasi);
      expect(e.tur, String(url)).toBe(tur);
      expect(JSON.stringify(e, Object.getOwnPropertyNames(e))).not.toMatch(/_i=|8\.8\.8\.8/);
    }
    expect(cagri).toEqual([]);
    expect((await ag.akisAc("http://127.0.0.1:1/akis")).kimlik).toBe("a1");   // imzasiz adres de bicimce gecerli
  });

  it("akisAc: eklentinin reddi TUR'e cevrilir; bilinmeyen kod / bozuk yanit 'ic-hata'; eklenti donmezse 'zaman-asimi'", async () => {
    const red = (code) => agKur({ istek: async () => ({}), akisAc: async () => { const e = new Error(IMZALI); e.code = code; throw e; } }, { yerelDongu: true });
    expect((await hata(red("mesgul").akisAc(IMZALI))).tur).toBe("mesgul");
    expect((await hata(red("wifi-yok").akisAc(IMZALI))).tur).toBe("wifi-yok");
    const e = await hata(red("garip " + IMZALI).akisAc(IMZALI));
    expect(e.tur).toBe("ic-hata");
    expect(JSON.stringify(e, Object.getOwnPropertyNames(e)).includes("_i=")).toBe(false);
    for (const yanit of [null, {}, { kimlik: 5 }, { kimlik: "" }]) {
      const ag = agKur({ istek: async () => ({}), akisAc: async () => yanit }, { yerelDongu: true });
      expect((await hata(ag.akisAc(IMZALI))).tur).toBe("ic-hata");
    }
    expect((await hata(agKur({ istek: async () => ({}) }, { yerelDongu: true }).akisAc(IMZALI))).tur).toBe("ic-hata");
    const asili = agKur({ istek: async () => ({}), akisAc: () => new Promise(() => {}) }, { yerelDongu: true, akisAcSureMs: 30 });
    expect((await hata(asili.akisAc(IMZALI))).tur).toBe("zaman-asimi");
  });

  it("akisKapat: asla atmaz (eklenti atsa, reddetse, hic olmasa da)", async () => {
    const kapanan = [];
    await agKur({ istek: async () => ({}), akisKapat: async (c) => { kapanan.push(c); } }).akisKapat("a1");
    expect(kapanan).toEqual([{ kimlik: "a1" }]);
    await agKur({ istek: async () => ({}), akisKapat: () => { throw new Error("x"); } }).akisKapat("a1");
    await agKur({ istek: async () => ({}), akisKapat: () => Promise.reject(new Error("x")) }).akisKapat("a1");
    await agKur({ istek: async () => ({}) }).akisKapat("a1");
  });
});
