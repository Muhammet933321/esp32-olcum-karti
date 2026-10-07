// 5P (P3) — cekirdege eklenen KUCUK yollar: canli.hamDinle (panelin satirIsle'si icin ham satirlar),
// kart.istek'in istege bagli `ek`i (azamiGovde / zamanAsimiMs / hamYanit), paylas.gonderGenis (html, pdf).
// Eski davranis degismedi: ek verilmezse kart.istek AYNI (2xx disi atar, 64 KiB tavan).
import { describe, it, expect, afterEach } from "vitest";
import { canliKur } from "../src/cekirdek/canli.js";
import { KartHatasi } from "../src/cekirdek/kart.js";
import { AD_DESENI, AD_DESENI_GENIS, PaylasHatasi, UZANTI_MIME, genisTurDenetle, paylasKur } from "../src/cekirdek/paylas.js";
import { eslesmis, hata } from "./curutucu-5b/yardim.mjs";

const bosalt = () => new Promise((r) => setImmediate(r));

describe("canli.hamDinle: her ham satir gelis sirasiyla", () => {
  function dunya() {
    const d = { dinleyici: {} };
    const kart = { durum: () => ({ durum: "bagli" }), istek: async () => ({ status: 204 }), akisUrl: async () => "http://127.0.0.1:1/akis?_c=1&_s=1&_i=x" };
    const ag = { akisAc: async () => ({ kimlik: "a1" }), akisKapat: async () => {} };
    const eklenti = { addListener: (o, fn) => { d.dinleyici[o] = fn; return Promise.resolve({ remove: async () => {} }); } };
    const canli = canliKur({ kart, ag, eklenti, zamanla: () => 0, zamaniBirak: () => {} });
    return { d, canli };
  }

  it("D, G, K, metin satirlari ve taninmayan satir: HEPSI ham olarak; birak sonrasi gelmez; dinleyici hatasi akisi bozmaz", async () => {
    const { d, canli } = dunya();
    const ham = [];
    const birak = canli.hamDinle((s) => ham.push(s));
    canli.hamDinle(() => { throw new Error("panel hatasi"); });
    canli.baslat();
    await bosalt();
    d.dinleyici.akisDurum({ kimlik: "a1", hal: "acik" });
    const satirlar = ["D 12.0000 0.500000 6.00000 1.0000 0.0002778 1000 97 0 0", "G 1 0 0 61300 61276 137 4 0 1850 24100 3 912 0", "* serbest", "M f=1 T=2"];
    d.dinleyici.akis({ kimlik: "a1", satirlar });
    expect(ham).toEqual(satirlar);
    expect(canli.durum().son).toMatchObject({ tur: "D", v: 12 });       // ayristirma da surdu
    d.dinleyici.akis({ kimlik: "baskasi", satirlar: ["D 1"] });          // baska akisin satiri gelmez
    birak();
    d.dinleyici.akis({ kimlik: "a1", satirlar: ["K 1 2 3"] });
    expect(ham).toEqual(satirlar);
    expect(() => canli.hamDinle(null)).toThrow(TypeError);
  });
});

describe("kart.istek ek secenekleri (sahte kart, imzali)", () => {
  const acik = [];
  afterEach(async () => { for (const k of acik.splice(0)) await k(); });

  it("azamiGovde / zamanAsimiMs kartFetch'e gecer; ek yoksa varsayilan (64 KiB, 4 s) AYNI", async () => {
    const { k, t } = await eslesmis();
    acik.push(() => k.kapat());
    await t.kart.istek("GET", "/kayit/liste");
    const once = t.kopru.cagrilar.at(-1);
    expect(once.azamiGovde).toBe(64 * 1024);
    expect(once.zamanAsimiMs).toBe(4000);
    await t.kart.istek("GET", "/kayit/liste", [], undefined, { azamiGovde: 200000, zamanAsimiMs: 9000 });
    const sonra = t.kopru.cagrilar.at(-1);
    expect(sonra.azamiGovde).toBe(200000);
    expect(sonra.zamanAsimiMs).toBe(9000);
    expect(sonra.basliklar["X-Imza"]).toMatch(/^[0-9a-f]{64}$/);
    // bicimsiz ek yok sayilir
    await t.kart.istek("GET", "/kayit/liste", [], undefined, { azamiGovde: -5, zamanAsimiMs: "x" });
    expect(t.kopru.cagrilar.at(-1).azamiGovde).toBe(64 * 1024);
  });

  it("hamYanit: 401 DISI HTTP hatasi yanit olarak doner (govdesiyle); verilmezse AYNI KartHatasi('http')", async () => {
    const { k, t } = await eslesmis();
    acik.push(() => k.kapat());
    const govde = new TextEncoder().encode("E1");
    const e = await hata(t.kart.istek("POST", "/komut", [], govde));
    expect(e).toBeInstanceOf(KartHatasi);
    expect(e).toMatchObject({ tur: "http", durum: 403 });
    const y = await t.kart.istek("POST", "/komut", [], govde, { hamYanit: true });
    expect(y.status).toBe(403);
    expect(y.ok).toBe(false);
    expect(await y.text()).toContain("E komutlari yalniz USB");
  });
});

describe("paylas: Kotlin ile ayni uzanti + MIME kumesi; MIME uzantiya uymali", () => {
  function eklenti() {
    const cagrilar = [];
    const e = {};
    for (const ad of ["baslat", "yaz", "gonder"]) e[ad] = async (v) => { cagrilar.push([ad, v]); return {}; };
    return { e, cagrilar };
  }
  const tur = async (s) => { try { await s; return "tamam"; } catch (x) { return x instanceof PaylasHatasi ? x.tur : "?"; } };

  it("desen ve tablo", () => {
    expect(AD_DESENI_GENIS).toBe(AD_DESENI);
    for (const ad of ["rapor.html", "rapor.pdf", "olcum-2026-10-07-12-00-00.csv", "kayit-5.kyt", "kayit-5-rapor.txt"]) expect(ad).toMatch(AD_DESENI);
    expect(Object.keys(UZANTI_MIME).sort()).toEqual(["csv", "html", "kyt", "pdf", "txt"]);
    expect(genisTurDenetle("a.csv", "text/csv;charset=utf-8")).toBe("text/csv");
    expect(genisTurDenetle("a.csv", "text/csv; charset=UTF-8")).toBe("text/csv");
    expect(genisTurDenetle("a.pdf", "application/pdf;charset=utf-8")).toBeNull();      // charset yalniz metinde
    expect(genisTurDenetle("a.csv", "application/pdf")).toBeNull();
    expect(genisTurDenetle("a.html", "text/html")).toBe("text/html");
    expect(genisTurDenetle("../a.html", "text/html")).toBeNull();
    expect(genisTurDenetle("a.exe", "application/octet-stream")).toBeNull();
  });

  it("gonder ve gonderGenis: html / pdf eklentiye yalin MIME ile; uymayan cift eklentiye GITMEZ", async () => {
    const { e, cagrilar } = eklenti();
    const p = paylasKur({ eklenti: e });
    const b = new Uint8Array([1, 2, 3]);
    expect(await tur(p.gonderGenis({ ad: "rapor.html", mime: "text/html; charset=utf-8", bayt: b }))).toBe("tamam");
    expect(cagrilar.at(-1)).toEqual(["gonder", { ad: "rapor.html", mime: "text/html", boy: 3 }]);
    expect(await tur(p.gonder({ ad: "rapor.pdf", mime: "application/pdf", bayt: b }))).toBe("tamam");
    expect(cagrilar.at(-1)).toEqual(["gonder", { ad: "rapor.pdf", mime: "application/pdf", boy: 3 }]);
    const n = cagrilar.length;
    for (const [ad, mime] of [["k.csv", "text/html"], ["k.pdf", "text/plain"], ["k.html", "application/pdf"], ["k.kyt", "text/csv"]]) {
      expect(await tur(p.gonder({ ad, mime, bayt: b })), `${ad} ${mime}`).toBe("bicim");
      expect(await tur(p.gonderGenis({ ad, mime, bayt: b })), `${ad} ${mime}`).toBe("bicim");
    }
    expect(await tur(p.gonderGenis({ ad: "k.html", mime: "text/html", bayt: new Uint8Array(0) }))).toBe("bos");
    expect(cagrilar.length).toBe(n);
  });
});
