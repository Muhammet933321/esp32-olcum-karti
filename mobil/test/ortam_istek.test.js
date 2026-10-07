// 5P (P3) — ORTAM.istek (K7): fetch'e benzer imzali istek, GERCEK `Response`. Sahte kartla uctan uca
// (gercek kart.js / kasa / kesif / ag) + sahte kart nesnesiyle iptal / buyuk govde / hata eslemesi.
import { describe, it, expect, afterEach } from "vitest";
import { arkaPlanKur } from "../src/ortam/arka_plan.js";
import {
  AKTARILAN_BASLIKLAR, AZAMI_SKOP, AZAMI_UST, AZAMI_VARSAYILAN, ISTEK_SURE_MS, IstekHatasi, azamiGovde, istekKur, yanitCevir, yolAyir,
} from "../src/ortam/istek.js";
import { metin } from "../src/ortam/metin.js";
import { T_NOKTA, kayitPaketle } from "../../ortak/src/kayit.js";
import { eslesmis, telefon, dunyaKur, PAROLA } from "./curutucu-5b/yardim.mjs";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";

const kayit = (sira) => kayitPaketle(T_NOKTA, sira, 3, Uint8Array.from({ length: 36 }, (_, j) => (sira * 7 + j) & 255));
const akisKur = (ilk, son) => Buffer.concat(Array.from({ length: son - ilk + 1 }, (_, i) => kayit(ilk + i)));

describe("yolAyir / azamiGovde (saf)", () => {
  it("yol + sorgu: + bosluktur, %xx cozulur, '=' siz arguman bos deger, # atilir", () => {
    expect(yolAyir("/kayit/veri?sira=5&bayt=8192")).toEqual({ yol: "/kayit/veri", argumanlar: [["sira", "5"], ["bayt", "8192"]] });
    expect(yolAyir("/pil?sira=2147483647")).toEqual({ yol: "/pil", argumanlar: [["sira", "2147483647"]] });
    expect(yolAyir("/x?a=b+c&d=%C3%A7&e&&f=")).toEqual({ yol: "/x", argumanlar: [["a", "b c"], ["d", "ç"], ["e", ""], ["f", ""]] });
    expect(yolAyir("/kunye.json#x")).toEqual({ yol: "/kunye.json", argumanlar: [] });
    expect(yolAyir("/bozuk?a=%E0%A4%A")).toEqual({ yol: "/bozuk", argumanlar: [["a", "%E0%A4%A"]] });
    for (const kotu of ["", "kayit", "http://x/kayit", "//baska/x", "/a b", null, 5]) expect(yolAyir(kotu), String(kotu)).toBeNull();
  });

  it("yanit tavani: skop.bin en kotu 131 102 B'yi, kayit/veri istenen parcayi karsilar; ust sinir 1 MiB", () => {
    expect(32 + 2 * 65535).toBeLessThanOrEqual(AZAMI_SKOP);
    expect(azamiGovde("/skop.bin")).toBe(AZAMI_SKOP);
    expect(azamiGovde("/kayit/veri", [["bayt", "8192"]])).toBe(AZAMI_VARSAYILAN);
    expect(azamiGovde("/kayit/veri", [["bayt", "1000000"]])).toBe(AZAMI_UST);
    expect(azamiGovde("/kayit/veri", [["bayt", "-3"]])).toBe(AZAMI_VARSAYILAN);
    expect(azamiGovde("/kayit/veri", [["bayt", "400000"]])).toBe(400000 + 64 * 1024);
    expect(azamiGovde("/kal/liste")).toBe(256 * 1024);
    expect(AZAMI_UST).toBe(1024 * 1024);                     // Kotlin HttpIstek.AZAMI_GOVDE_SINIR
  });
});

describe("istek: sahte kartla uctan uca", () => {
  const acik = [];
  afterEach(async () => { for (const k of acik.splice(0)) await k(); });

  async function kur({ eslesmeli = true } = {}) {
    let k, t;
    if (eslesmeli) ({ k, t } = await eslesmis());
    else {
      k = await sahteKartAc({ port: 0, parola: PAROLA, kimlik: "00112233aabbccdd" });
      t = telefon(dunyaKur(k));
    }
    acik.push(() => k.kapat());
    const arka = arkaPlanKur({ kartAl: async () => t.kart, canliAl: async () => { throw new Error("yok"); }, araliKur: () => 1, araliSil: () => {} });
    const p0 = [];
    const istek = istekKur({ arka, kartAl: async () => t.kart, p0: async () => { p0.push(1); return true; } });
    return { k, t, istek, p0 };
  }

  it("GET /kayit/liste: gercek Response (ok, json), IMZALI, istek basina tavan + sure; kart bulunmamissa once baglanir", async () => {
    const { k, t, istek } = await kur({ eslesmeli: false });
    // eslesmemis telefon: anlasilir red (IstekHatasi bir TypeError: fetch'in ag hatasi gibi)
    const e = await istek("/kayit/liste").then(() => null, (x) => x);
    expect(e).toBeInstanceOf(TypeError);
    expect(e).toBeInstanceOf(IstekHatasi);
    expect(e.message).toBe(metin("or.eslesmemis", "tr"));
    await t.kart.esles("sinama telefonu", PAROLA);
    k.ayarla({ kayitlar: akisKur(1, 30) });
    const y = await istek("/kayit/liste", { method: "GET", headers: { "Cache-Control": "no-store" } });
    expect(y).toBeInstanceOf(Response);
    expect(y.ok).toBe(true);
    expect(y.status).toBe(200);
    expect(y.headers.get("content-type")).toMatch(/json/);
    const l = await y.json();
    expect(Array.isArray(l.oturumlar)).toBe(true);
    const c = t.kopru.cagrilar.at(-1);
    expect(c.url).toMatch(/\/kayit\/liste$/);
    expect(c.basliklar["X-Imza"]).toMatch(/^[0-9a-f]{64}$/);
    expect(c.azamiGovde).toBe(AZAMI_VARSAYILAN);
    expect(c.zamanAsimiMs).toBe(ISTEK_SURE_MS);
  });

  it("GET /kayit/veri?sira&bayt: sorgu imzaya ve adrese girer, govde bayt bayt", async () => {
    const { k, t, istek } = await kur();
    k.ayarla({ kayitlar: akisKur(1, 300) });
    const y = await istek("/kayit/veri?sira=1&bayt=8192");
    expect(y.status).toBe(200);
    const b = new Uint8Array(await y.arrayBuffer());
    expect(b.length).toBeGreaterThan(7000);
    expect(b.length).toBeLessThanOrEqual(8192);
    expect(Buffer.from(b).equals(akisKur(1, 300).subarray(0, b.length))).toBe(true);
    expect(t.kopru.cagrilar.at(-1).url).toMatch(/\/kayit\/veri\?sira=1&bayt=8192$/);
  });

  it("buyuk govde (/kal/liste ~200 KB; eski 64 KiB varsayilani 'govde-buyuk' derdi) eksiksiz gelir", async () => {
    const { k, t, istek } = await kur();
    const kayitlar = Array.from({ length: 40 }, (_, i) => ({ no: i + 1, tur: 1, kaynak: 1, not: "x".repeat(5000), kal: {} }));
    k.ayarla({ kalListe: { surum: 1, adet: 40, taslak: 0, etkin: 40, azami: 40, kayitlar } });
    const y = await istek("/kal/liste");
    expect(y.ok).toBe(true);
    const metinGovde = await y.text();
    expect(metinGovde.length).toBeGreaterThan(64 * 1024);
    expect(JSON.parse(metinGovde).kayitlar.length).toBe(40);
    await expect(t.kart.istek("GET", "/kal/liste")).rejects.toMatchObject({ tur: "ag", ag: "govde-buyuk" });   // eski yol
  });

  it("HTTP hatasi: Response.ok = false, durum ve govde korunur (skop.bin: 192 KiB tavan)", async () => {
    const { t, istek } = await kur();
    const y = await istek("/skop.bin");                       // sahte kartta /skop.bin yok -> 404
    expect(y).toBeInstanceOf(Response);
    expect(y.ok).toBe(false);
    expect(y.status).toBe(404);
    expect(t.kopru.cagrilar.at(-1).azamiGovde).toBe(AZAMI_SKOP);
    const r = await istek("/komut", { method: "POST", headers: { "Content-Type": "text/plain", "X-Olcum": "1" }, body: "Q1" });
    expect(r.status).toBe(403);
    expect(await r.text()).toContain("Q komutlari yalniz USB");
  });

  it("POST govde string / Uint8Array; 204'te govde yok; p0 IMZASIZ yoldan (kart.istek'e girmez); PUT -> 405", async () => {
    const { k, t, istek, p0 } = await kur();
    const y = await istek("/komut", { method: "POST", body: "G?" });
    expect(y.status).toBe(204);
    expect(await y.text()).toBe("");
    await istek("/komut", { method: "post", body: new TextEncoder().encode("Gd") });
    expect(k.durum.komutlar).toEqual(["G?", "Gd"]);
    const n = t.kopru.cagrilar.length;
    const d = await istek("/komut", { method: "POST", body: "p0" });
    expect(d.status).toBe(204);
    expect(p0.length).toBe(1);
    expect(t.kopru.cagrilar.length).toBe(n);
    const put = await istek("/kayit/liste", { method: "PUT" });
    expect(put.status).toBe(405);
  });
});

describe("istek: sahte kart nesnesiyle", () => {
  function kur(kartIstek, { p0 = async () => true } = {}) {
    const kart = { durum: () => ({ durum: "bagli" }), istek: kartIstek };
    const arka = { baglan: async () => ({ durum: "bagli" }) };
    return istekKur({ arka, kartAl: async () => kart, p0 });
  }
  const yanit = (status, bayt, basliklar = {}) => ({
    status, ok: status >= 200 && status < 300,
    headers: { get: (a) => (Object.hasOwn(basliklar, a.toLowerCase()) ? basliklar[a.toLowerCase()] : null) },
    arrayBuffer: async () => bayt.buffer.slice(bayt.byteOffset, bayt.byteOffset + bayt.byteLength),
  });

  it("buyuk ikili govde (skop.bin 4000 ornek ve 150 KB) bayt bayt; yalniz izinli basliklar aktarilir", async () => {
    for (const boy of [32 + 2 * 4000, 150000]) {
      const b = Uint8Array.from({ length: boy }, (_, i) => (i * 13) & 255);
      const ist = kur(async () => yanit(200, b, { "content-type": "application/octet-stream", "x-acilis": "ab", "x-gizli": "s" }));
      const y = await ist("/skop.bin");
      const g = new Uint8Array(await y.arrayBuffer());
      expect(g.length).toBe(boy);
      expect(Buffer.from(g).equals(Buffer.from(b))).toBe(true);
      expect(y.headers.get("x-acilis")).toBe("ab");
      expect(y.headers.get("x-gizli")).toBeNull();
    }
    expect(AKTARILAN_BASLIKLAR).toContain("x-kayit-kimlik");
  });

  it("yanitCevir: gecersiz durum 502 olur; 304 govdesiz", async () => {
    expect((await yanitCevir(yanit(42, new Uint8Array(1)))).status).toBe(502);
    expect((await yanitCevir(yanit(304, new Uint8Array(0)))).status).toBe(304);
  });

  it("AbortSignal: once iptalse istek GITMEZ; yolda iptal reddeder (AbortError / sebep)", async () => {
    let cagri = 0;
    const ist = kur(() => { cagri += 1; return new Promise(() => {}); });
    const once = new AbortController();
    once.abort();
    await expect(ist("/kayit/liste", { signal: once.signal })).rejects.toMatchObject({ name: "AbortError" });
    expect(cagri).toBe(0);
    const yolda = new AbortController();
    const s = ist("/kayit/liste", { signal: yolda.signal });
    await new Promise((r) => setTimeout(r, 5));
    yolda.abort();
    await expect(s).rejects.toMatchObject({ name: "AbortError" });
    expect(cagri).toBe(1);
    const sure = ist("/kayit/liste", { signal: AbortSignal.timeout(5) });
    await expect(sure).rejects.toMatchObject({ name: "TimeoutError" });
  });

  it("hata eslemesi: ag -> TypeError (tur + ag ayrintisi), cihaz-silinmis -> Response 401, eslesmemis -> Bu telefon metni", async () => {
    const at = (tur, ek = {}) => async () => { throw Object.assign(new Error(tur), { tur, ...ek }); };
    const e = await kur(at("ag", { ag: "zaman-asimi" }))("/pil?sira=1").then(() => null, (x) => x);
    expect(e).toBeInstanceOf(TypeError);
    expect(e.tur).toBe("ag");
    expect(e.message).toContain("zaman-asimi");
    const y = await kur(at("cihaz-silinmis"))("/pil");
    expect(y.status).toBe(401);
    expect(await y.text()).toBe(metin("or.cihaz_silinmis", "tr"));
    const e2 = await kur(at("eslesmemis"))("/pil").then(() => null, (x) => x);
    expect(e2.message).toBe(metin("or.eslesmemis", "tr"));
    await expect(kur(at("ag"))("kayit")).rejects.toBeInstanceOf(TypeError);
  });

  it("p0 ulasamazsa 503 (asla reddetmez)", async () => {
    const y = await kur(async () => { throw new Error("gitmemeli"); }, { p0: async () => { throw new Error("eklenti"); } })("/komut", { method: "POST", body: " p0\n" });
    expect(y.status).toBe(503);
  });
});
