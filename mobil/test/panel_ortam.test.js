// 5P (P2) — panelin telefon ortamina baglandigi kancalar (arayuz3/ekran/*.js), tarayicisiz.
// Ortam (globalThis.__olcumOrtam) panel modulleri yuklenmeden ONCE kurulur — mobil giris noktasinin
// sirasi (tasarim/2026-10-07-plan-5p.md "Sozlesme"). vitest her test dosyasini ayri modul kaydinda
// kostugu icin buradaki ice aktarmalar ortami gorur; app.js'in telefon dallari B7'de (bolum 35).
import { describe, it, expect, beforeAll, afterAll } from "vitest";

const iz = { istek: [], esitle: [], depo: [], dosya: [], yazdir: 0 };
const depoT = {
  kart: "k1",
  async veriBoyu() { return 0; },
  async veriOku() { return new Uint8Array(0); },
  async kalOku() { return new TextEncoder().encode(JSON.stringify({ adet: 1 })); },
  async durumOku() { return { son_sira: 3 }; },
};
const ORTAM = {
  ad: "telefon",
  surum: 1,
  tasiyici: { ad: "telefon" },
  async istek(yol, sec) {
    iz.istek.push([yol, sec]);
    return new Response(JSON.stringify({ kimlik: 7, oturumlar: [] }), { status: 200 });
  },
  async p0() { return true; },
  serit() { return true; },
  async akislar() {
    return [{ kimlik: 7, kart: "k1", bayt: 0, durum: null, olusma: 1, guncelleme: 2, kalVar: true, telefon: true }];
  },
  async depo(kimlik) { iz.depo.push(kimlik); return depoT; },
  async esitle(a) { iz.esitle.push(a); return { durum: "tamam", sonuc: { yeni_kayit: 1, son_sira: 3 }, bayt: 5 }; },
  async dosyaVer(d) { iz.dosya.push(d); return true; },
  async yazdir() { iz.yazdir++; },
  async ayarBolumu() { return { name: "BuTelefon" }; },
  komutGitti() {},
};

let ES;
let KG;
let AY;
let fetchSayisi = 0;
const eskiFetch = globalThis.fetch;

beforeAll(async () => {
  globalThis.__olcumOrtam = ORTAM;
  globalThis.fetch = async () => { fetchSayisi++; throw new Error("telefonda fetch YOK"); };
  ES = await import("@panel/esitleme.js");
  KG = await import("@panel/kayit_gorunum.js");
  AY = await import("@panel/ayarlar.js");
});

afterAll(() => {
  delete globalThis.__olcumOrtam;
  globalThis.fetch = eskiFetch;
});

describe("esitleme.js — kaynak 'telefon' (K10)", () => {
  it("varsayilan enjeksiyon: kurucu ortami globalThis'ten alir; akislar / depo / kalibrasyon ortamdan", async () => {
    const den = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y, konum: { protocol: "https:", hostname: "localhost" } });
    expect(await den.kaynak()).toBe("telefon");
    expect((await den.akislar()).map((a) => a.kimlik)).toEqual([7]);
    const v = await den.akisVerisi(7);
    expect(v.kart).toBe("k1");
    expect(v.kal).toEqual({ adet: 1 });
    expect(v.durum).toEqual({ son_sira: 3 });
    expect(iz.depo.every((k) => k === 7)).toBe(true);
    expect(await den.esitlemeDurumu()).toBe(null);
  });

  it("esitle Android esitleyicisine gider: kimlik + ilerleme, panelin onayi GITMEZ; sonuc aynen", async () => {
    const den = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y });
    const ilerleme = () => {};
    const r = await den.esitle({ kimlik: 7, onay: async () => {}, ilerleme });
    expect(r).toEqual({ durum: "tamam", sonuc: { yeni_kayit: 1, son_sira: 3 }, bayt: 5 });
    const a = iz.esitle.at(-1);
    expect(Object.keys(a).sort()).toEqual(["ilerleme", "kimlik"]);
    expect(a.ilerleme).toBe(ilerleme);
  });

  it("kartin dizini ortam.istek'ten (gercek Response); kopya silme reddedilir; kopru sorusu yok", async () => {
    const den = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y });
    const l = await den.kartListesi();
    expect(l.durum).toBe("tamam");
    expect(iz.istek.at(-1)[0]).toBe("/kayit/liste");
    await expect(den.akisSil(7)).rejects.toThrow(/Bu telefon/);
    expect(ES.kokenSinama({ protocol: "https:", hostname: "localhost" })).toBe(false);
    expect(AY.kopruKokeni({ protocol: "https:", hostname: "localhost" })).toBe(false);
    expect(fetchSayisi).toBe(0);
  });
});

describe("kayit_gorunum.js — dosya ve yazdirma (K11 / K12)", () => {
  it("dosyaVer telefonda ortam.dosyaVer: dizge UTF-8 bayta (BOM dahil), Uint8Array AYNEN; DOM yok", async () => {
    const n = iz.dosya.length;
    await KG.dosyaVer("olcum-1.csv", "text/csv;charset=utf-8", "﻿a;ç");
    const b = new Uint8Array([1, 2, 3]);
    await KG.dosyaVer("olcum-1.kyt", "application/octet-stream", b);
    const [d1, d2] = iz.dosya.slice(n);
    expect(d1.ad).toBe("olcum-1.csv");
    expect(d1.mime).toBe("text/csv;charset=utf-8");
    expect(d1.bayt).toBeInstanceOf(Uint8Array);
    expect([...d1.bayt]).toEqual([0xef, 0xbb, 0xbf, 0x61, 0x3b, 0xc3, 0xa7]);
    expect(d2.bayt).toBe(b);
  });

  it("disa aktarma (indir) dosyayi ortamdan verir; ortam reddederse sebep ekranda", async () => {
    const m = KG.KayitGorunumu.methods;
    const bu = { hata: "", m: { disariHata: "Disa aktarilamadi." }, oturum: { id: 1, skoplar: new Map() }, veri: { kayitlar: [] } };
    const eski = ORTAM.dosyaVer;
    ORTAM.dosyaVer = async () => { throw new Error("paylasim iptal"); };
    m.indir.call(bu, "ham");
    await new Promise((c) => setTimeout(c, 0));
    ORTAM.dosyaVer = eski;
    expect(bu.hata).toMatch(/Disa aktarilamadi\. .*paylasim iptal/);
  });

  it("yazdir: acik gorunum ONCE, ortam.yazdir, sonra geri; WebView beforeprint ikinci kez uygulamaz", async () => {
    const m = KG.KayitGorunumu.methods;
    const sira = [];
    const bu = {
      rapor: true,
      hata: "",
      yazdirmaOncesi() { sira.push("once:" + !!this._elleYazdir); return m.yazdirmaOncesi.call(this); },
      yazdirmaSonrasi() { sira.push("sonra:" + !!this._elleYazdir); return m.yazdirmaSonrasi.call(this); },
      ciz() { sira.push("ciz"); },
    };
    const kok = { a: "koyu", getAttribute() { return this.a; }, setAttribute(_, v) { this.a = v; } };
    const eskiBelge = globalThis.document;
    globalThis.document = { documentElement: kok };
    const eskiYaz = ORTAM.yazdir;
    ORTAM.yazdir = async () => {
      iz.yazdir++;
      sira.push("yazdir:" + kok.a);
      bu.yazdirmaOncesi();                       // WebView'in beforeprint'i atarsa
    };
    try {
      await m.yazdir.call(bu);
    } finally {
      ORTAM.yazdir = eskiYaz;
      globalThis.document = eskiBelge;
    }
    expect(sira).toEqual(["once:false", "ciz", "yazdir:acik", "once:true", "sonra:false", "ciz"]);
    expect(kok.a).toBe("koyu");
  });
});
