// Kesif (A1–A3): aday yarisi, kimlik dogrulama, onbellek, NSD'ye bagimsizlik, hedef kurali.
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import http from "node:http";
import { agKur } from "../src/cekirdek/ag.js";
import { HedefHatasi } from "../src/cekirdek/hedef.js";
import { kesifKur, KesifHatasi, yerelOnbellek } from "../src/cekirdek/kesif.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";

const K1 = "00112233aabbccdd";
const K2 = "ffeeddcc99887766";

function bellekOnbellek(ilk = null) {
  let kayit = ilk;
  const yazilan = [];
  return { oku: () => kayit, yaz: (k) => { kayit = k; yazilan.push(k); }, yazilan };
}

// Kart olmayan sunucular: ham yanit / sessiz / dev govde.
function hamSunucu(isle) {
  return new Promise((coz) => {
    const s = http.createServer(isle);
    s.listen(0, "127.0.0.1", () => coz({ adres: `127.0.0.1:${s.address().port}`, kapat: () => new Promise((c) => { s.closeAllConnections(); s.close(c); }) }));
  });
}

describe("kesif", () => {
  let acik, kopru, ag;
  const kart = async (secenek) => { const k = await sahteKartAc(secenek); acik.push(() => k.kapat()); return k; };
  const adres = (k) => `127.0.0.1:${k.port}`;
  const kur = (ek = {}) => kesifKur({ kartFetch: ag.kartFetch, yerelDongu: true, zamanAsimiMs: 500, sabitAdaylar: [], ...ek });

  beforeEach(() => { acik = []; kopru = kopruSahtesi(); ag = agKur(kopru, { yerelDongu: true }); });
  afterEach(async () => { for (const k of acik) await k(); });

  it("onbellekteki adres kazanir; kimlik ve bilgi doner; onbellek yenilenir", async () => {
    const k = await kart({ kimlik: K1 });
    const ob = bellekOnbellek({ adres: adres(k), kimlik: K1, ms: 1 });
    const s = await kur({ onbellek: ob }).bul({ beklenenKimlik: K1 });
    expect(s).toMatchObject({ adres: adres(k), kimlik: K1, kaynak: "onbellek" });
    expect(s.bilgi.acilis).toBeTypeOf("string");
    expect(ob.yazilan.at(-1)).toMatchObject({ adres: adres(k), kimlik: K1 });
  });

  it("onbellek olu -> sabit aday bulur", async () => {
    const k = await kart({ kimlik: K1 });
    const ob = bellekOnbellek({ adres: "127.0.0.1:9", kimlik: K1, ms: 1 });
    const s = await kur({ onbellek: ob, sabitAdaylar: [{ adres: adres(k), kaynak: "ap" }] }).bul({ beklenenKimlik: K1 });
    expect(s.kaynak).toBe("ap");
    expect(s.denenenler.find((d) => d.kaynak === "onbellek").sonuc).not.toBe("tamam");
  });

  it("iki kart: yanlis kimlikli ONCE yanit verse de dogru olan secilir", async () => {
    const yanlis = await kart({ kimlik: K2 });
    const dogru = await kart({ kimlik: K1 });
    dogru.ayarla({ gecikmeMs: 150 });
    const s = await kur({ sabitAdaylar: [{ adres: adres(yanlis), kaynak: "ad" }, { adres: adres(dogru), kaynak: "ap" }] })
      .bul({ beklenenKimlik: K1 });
    expect(s.adres).toBe(adres(dogru));
    expect(s.kimlik).toBe(K1);
  });

  it("yalniz yanlis kimlik yanit veriyor -> kimlik-uymuyor; onbellek YAZILMAZ", async () => {
    const yanlis = await kart({ kimlik: K2 });
    const ob = bellekOnbellek({ adres: adres(yanlis), kimlik: K1, ms: 1 });
    const h = await kur({ onbellek: ob }).bul({ beklenenKimlik: K1 }).catch((e) => e);
    expect(h).toBeInstanceOf(KesifHatasi);
    expect(h.tur).toBe("kimlik-uymuyor");
    expect(h.denenenler).toEqual([{ adres: adres(yanlis), kaynak: "onbellek", sonuc: "tamam", kimlik: K2 }]);
    expect(ob.yazilan).toEqual([]);
  });

  it("hepsi sessiz -> bulunamadi, zaman asimi + pay icinde", async () => {
    const sessiz = await hamSunucu(() => { /* yanit yok */ });
    acik.push(sessiz.kapat);
    const t0 = Date.now();
    const h = await kur({ sabitAdaylar: [{ adres: sessiz.adres, kaynak: "ad" }, { adres: "127.0.0.1:9", kaynak: "ap" }] }).bul().catch((e) => e);
    expect(h.tur).toBe("bulunamadi");
    expect(Date.now() - t0).toBeLessThan(500 + 400);
    expect(h.denenenler.find((d) => d.adres === sessiz.adres).sonuc).toBe("zaman-asimi");
  });

  it("yanit vermeyen aday otekini BEKLETMEZ", async () => {
    const sessiz = await hamSunucu(() => {});
    acik.push(sessiz.kapat);
    const k = await kart({ kimlik: K1 });
    const t0 = Date.now();
    const s = await kur({ sabitAdaylar: [{ adres: sessiz.adres, kaynak: "ad" }, { adres: adres(k), kaynak: "ap" }] }).bul();
    expect(s.adres).toBe(adres(k));
    expect(Date.now() - t0).toBeLessThan(300);
  });

  it("JSON olmayan yanit / bozuk kimlik / 404 / dev govde -> aday gecersiz, cokme yok", async () => {
    const duz = await hamSunucu((q, y) => y.end("merhaba"));
    const bozuk = await hamSunucu((q, y) => { y.setHeader("Content-Type", "application/json"); y.end(JSON.stringify({ kimlik: "XYZ" })); });
    const sayi = await hamSunucu((q, y) => y.end(JSON.stringify({ kimlik: 1234567890123456 })));
    const yok = await hamSunucu((q, y) => { y.statusCode = 404; y.end(JSON.stringify({ kimlik: K1 })); });
    const dev = await hamSunucu((q, y) => y.end(JSON.stringify({ kimlik: K1, dolgu: "x".repeat(5 * 1024 * 1024) })));
    const nul = await hamSunucu((q, y) => y.end("null"));
    for (const s of [duz, bozuk, sayi, yok, dev, nul]) acik.push(s.kapat);
    const adaylar = [duz, bozuk, sayi, yok, dev, nul].map((s) => ({ adres: s.adres, kaynak: "ad" }));
    const h = await kur({ sabitAdaylar: adaylar, zamanAsimiMs: 1500 }).bul().catch((e) => e);
    expect(h).toBeInstanceOf(KesifHatasi);
    expect(h.tur).toBe("bulunamadi");
    const sonuc = Object.fromEntries(h.denenenler.map((d) => [d.adres, d.sonuc]));
    expect(sonuc[dev.adres]).toBe("govde-buyuk");
    for (const s of [duz, bozuk, sayi, yok, nul]) expect(sonuc[s.adres]).toBe("yanit-gecersiz");
  });

  it("elle herkese acik IP / baska ad -> HedefHatasi, HICBIR istek atilmaz", async () => {
    const k = await kart({ kimlik: K1 });
    const kesif = kur({ sabitAdaylar: [{ adres: adres(k), kaynak: "ap" }] });
    for (const [elle, tur] of [["8.8.8.8", "ozel-degil"], ["evil.example", "ad-izinsiz"], ["192.168.1.5/x", "bicim"]]) {
      const h = await kesif.bul({ elle }).catch((e) => e);
      expect(h).toBeInstanceOf(HedefHatasi);
      expect(h.tur).toBe(tur);
    }
    expect(kopru.cagrilar.length).toBe(0);
  });

  it("eslesmemisken elle girilen adres, daha hizli yanit veren baska adaydan ONCE gelir", async () => {
    const elle = await kart({ kimlik: K2 });
    const hizli = await kart({ kimlik: K1 });
    elle.ayarla({ gecikmeMs: 150 });
    const s = await kur({ sabitAdaylar: [{ adres: adres(hizli), kaynak: "ap" }] }).bul({ elle: adres(elle) });
    expect(s).toMatchObject({ adres: adres(elle), kaynak: "elle", kimlik: K2 });
  });

  it("elle adres olu ise oteki aday kullanilir", async () => {
    const k = await kart({ kimlik: K1 });
    const s = await kur({ sabitAdaylar: [{ adres: adres(k), kaynak: "ap" }] }).bul({ elle: "127.0.0.1:9" });
    expect(s).toMatchObject({ adres: adres(k), kaynak: "ap" });
  });

  it("NSD: bulunan servis aday olur, TXT kimligi doner; yanlis TXT kimligi istek ATILMADAN elenir", async () => {
    const k = await kart({ kimlik: K1 });
    const baska = await kart({ kimlik: K2 });
    const eklenti = { nsdTara: async () => ({ servisler: [
      { ad: "olcum", ip: "127.0.0.1", port: baska.port, kimlik: K2 },
      { ad: "olcum", ip: "127.0.0.1", port: k.port, kimlik: K1 },
      { ad: "olcum", ip: "8.8.8.8", port: 80, kimlik: K1 },             // herkese acik: aday OLMAZ
      { ad: "olcum", ip: "127.0.0.1", port: "80" }, null,
    ] }) };
    const s = await kur({ eklenti }).bul({ beklenenKimlik: K1 });
    expect(s).toMatchObject({ adres: adres(k), kaynak: "nsd", txtKimlik: K1, kimlik: K1 });
    expect(kopru.cagrilar.map((c) => new URL(c.url).host)).toEqual([adres(k)]);
    // Herkese acik adres aday bile olmaz: denenenler listesinde de gorunmez.
    expect(s.denenenler.map((d) => d.adres)).toEqual([adres(k)]);
  });

  it("NSD eklentisi yok / hata atiyor / sacma donuyor -> akis degismez", async () => {
    const k = await kart({ kimlik: K1 });
    const sabit = [{ adres: adres(k), kaynak: "ap" }];
    for (const eklenti of [null, {}, { nsdTara: async () => { throw new Error("x"); } }, { nsdTara: async () => ({ servisler: "yok" }) }, { nsdTara: async () => null }]) {
      const s = await kur({ eklenti, sabitAdaylar: sabit }).bul({ beklenenKimlik: K1 });
      expect(s.kaynak).toBe("ap");
    }
  });

  it("ayni adres iki kaynaktan gelirse bir kez yoklanir", async () => {
    const k = await kart({ kimlik: K1 });
    const ob = bellekOnbellek({ adres: adres(k), kimlik: K1, ms: 1 });
    const h = await kur({ onbellek: ob, sabitAdaylar: [{ adres: adres(k), kaynak: "ap" }] }).bul({ beklenenKimlik: K2 }).catch((e) => e);
    expect(h.tur).toBe("kimlik-uymuyor");
    expect(kopru.cagrilar.length).toBe(1);
  });

  it("yerelOnbellek: bozuk kayit = yok; yaz/oku", () => {
    const m = new Map();
    const depo = { getItem: (a) => (m.has(a) ? m.get(a) : null), setItem: (a, d) => m.set(a, d) };
    const ob = yerelOnbellek(depo);
    expect(ob.oku()).toBe(null);
    m.set("kart.son", "{bozuk");
    expect(ob.oku()).toBe(null);
    m.set("kart.son", JSON.stringify({ adres: 5 }));
    expect(ob.oku()).toBe(null);
    ob.yaz({ adres: "192.168.1.7", kimlik: K1, ms: 3 });
    expect(ob.oku()).toEqual({ adres: "192.168.1.7", kimlik: K1, ms: 3 });
  });
});
