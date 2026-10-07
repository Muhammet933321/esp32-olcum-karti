// CURUTUCU 5C — ACIL DURDUR'un JS tarafindaki kenar durumlari (durdur.js) + komut beyaz listesi.
import { describe, it, expect } from "vitest";
import { durdurKur } from "../../src/cekirdek/durdur.js";
import { komutGecerli, canliKur } from "../../src/cekirdek/canli.js";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Telefonda kaydi PANEL baslatir (arayuz3/app.js KAYIT_HIZLARI -> `Gb<ms>`; 5P P6'dan once canli_gorunum.js HIZLAR).
const PANEL = readFileSync(fileURLToPath(new URL("../../../arayuz3/app.js", import.meta.url)), "utf8");
const PANEL_HIZLARI = JSON.parse(`[${/const KAYIT_HIZLARI = Object\.freeze\(\[([^\]]*)\]\);/.exec(PANEL)[1]}]`);

describe("curutucu 5C: durdur.js", () => {
  it("'ASLA reddetmez': p0 ESZAMANLI atarsa da durdur() atmamali ve hal 'ulasilamadi' olmali", () => {
    const d = durdurKur({ p0: () => { throw new Error("eklenti koprusu yok"); }, adresler: () => ["192.168.1.7:80"] });
    let atti = false;
    try { d.durdur(); } catch { atti = true; }
    // KIRMIZI: istisna dokunus isleyicisine cikar; hal "bos" kalir — serit hicbir sey soylemez.
    expect({ atti, hal: d.durum() }).toEqual({ atti: false, hal: "ulasilamadi" });
  });

  it("iki hizli dokunus: ILK p0 karti durdurdu, ikincisi yanit alamadi -> serit 'ULASILAMADI' dememeli", async () => {
    const sozler = [];
    const d = durdurKur({ p0: () => new Promise((coz) => sozler.push(coz)), adresler: () => ["192.168.1.7:80"] });
    const s1 = d.durdur();
    const s2 = d.durdur();                                     // 2. dokunus (ilki henuz donmedi)
    sozler[0]({ tamam: true, adres: "192.168.1.7:80", sureMs: 120 });   // kart DURDU
    sozler[1]({ tamam: false, adres: null, sureMs: 4400 });             // ikinci istek ulasmadi (kart o an mesgul / ag takildi)
    await Promise.all([s1, s2]);
    // KIRMIZI: yalniz SON dokunusun sonucu sayiliyor; kart durmusken kalici kirmizi "ULASILAMADI".
    expect(d.durum()).toBe("durduruldu");
  });

  it("(karsit yon, guvenli taraf) ilk dokunus ulasamadi, ikincisi durdurdu -> 'durduruldu'", async () => {
    const sozler = [];
    const d = durdurKur({ p0: () => new Promise((coz) => sozler.push(coz)), adresler: () => [] });
    const s1 = d.durdur();
    const s2 = d.durdur();
    sozler[1]({ tamam: true, adres: "192.168.4.1", sureMs: 90 });
    sozler[0]({ tamam: false, adres: null, sureMs: 4400 });
    await Promise.all([s1, s2]);
    expect(d.durum()).toBe("durduruldu");                      // yesil
  });
});

describe("curutucu 5C: komut beyaz listesi (ACIK ARANDI)", () => {
  const YASAK = [
    "Gb1000\u0000", "Gb1000\n", "\nGb1000", " Gb1000", "Gb1000 ", "Gb١٠٠٠", "Gb１０００", "Gb1e3", "Gb+100",
    "Gb-0", "Gb00", "Gb0100", "Gb100.0", "Gb0x64", "Gb60001", "Gb19", "Gb99999999999999999999", "Gb", "gb100", "GB100",
    "Gd​", "﻿Gd", "Gd;N?", "Gd\r\nN?", "G?\u0000", "?\n", "??", "N?", "E?", "QH", "k?", "GF!", "p1", "p0", "Go5", "Gp-", "Gt0", "Ga1 x", "Ns",
    "", null, undefined, 0, ["Gd"], { toString: () => "Gd" }, new String("Gd"), Object.assign(["Gb100"], { toString: () => "N?" }),
  ];

  it("yasak / bicimsiz girdilerin HEPSI reddedilir; reddedilen komut karta istek OLMAZ", async () => {
    const giden = [];
    const kart = { durum: () => ({ durum: "bagli" }), istek: async (y, yol, a, govde) => { giden.push(new TextDecoder().decode(govde)); return {}; } };
    const canli = canliKur({ kart, ag: { akisAc: async () => ({ kimlik: "a1" }), akisKapat: async () => {} }, eklenti: { addListener: () => {} } });
    const gecen = [];
    for (const k of YASAK) {
      if (komutGecerli(k)) gecen.push(k);
      await expect(canli.komut(k)).rejects.toMatchObject({ tur: "komut-yasak" });
    }
    expect(gecen).toEqual([]);
    expect(giden).toEqual([]);
  });

  it("izinli komut karta AYNI baytlarla gider; panelin kurdugu her hiz komutu beyaz listede", async () => {
    const giden = [];
    const kart = { durum: () => ({ durum: "bagli" }), istek: async (y, yol, a, govde) => { giden.push([y, yol, Array.from(govde)]); return {}; } };
    const canli = canliKur({ kart, ag: { akisAc: async () => ({ kimlik: "a1" }), akisKapat: async () => {} }, eklenti: { addListener: () => {} } });
    await canli.komut("Gb1000");
    expect(giden).toEqual([["POST", "/komut", [71, 98, 49, 48, 48, 48]]]);
    expect(PANEL_HIZLARI.length).toBeGreaterThan(3);
    for (const h of PANEL_HIZLARI) expect(komutGecerli(`Gb${h}`), `Gb${h}`).toBe(true);
  });

  it("beyaz liste kartin KABUL ETMEDIGI araliklari da geciriyor (plan: Gb<0|50…60000>; kart: 0,20,100,200,1000,10000,60000)", () => {
    // Bilgi amacli: yorum (canli.js GB_EN_AZ_MS) ile plan metni ayrisiyor; panel yalniz KAYIT_HIZLARI'ni kullandigi icin etkisi yok.
    const gecen = ["Gb21", "Gb37", "Gb59999", "Gb20"].filter(komutGecerli);
    console.log(`[beyaz-liste] kartin hiz listesinde olmayip gecen: ${gecen.join(" ")}`);
    expect(gecen.length).toBeGreaterThan(0);                   // yesil: belgelenen gevseklik
  });
});
