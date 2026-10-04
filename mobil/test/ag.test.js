// ag.js: eklenti <-> ortak/ fetch bicimi. Sahte karta, eklentinin Node sahtesi uzerinden.
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { ac, bilgi, esles } from "@ortak/imza.js";
import { agKur, KartAgHatasi, urlDenetle } from "../src/cekirdek/ag.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";

const PAROLA = "sinama-parolasi-1";

async function turu(soz) {
  try { await soz; return "hata-yok"; } catch (e) { return e instanceof KartAgHatasi ? e.tur : `baska:${e.name}`; }
}

describe("agKur / kartFetch", () => {
  let kart, kopru, ag, ortam;

  beforeAll(async () => {
    kart = await sahteKartAc({ parola: PAROLA });
    kopru = kopruSahtesi();
    ag = agKur(kopru, { yerelDongu: true, zamanAsimiMs: 3000 });
    ortam = { fetch: ag.kartFetch };
  });
  afterAll(async () => { await kart.kapat(); });

  it("ortak bilgi() kartFetch'ten gecer: durum, baslik, govde", async () => {
    const b = await bilgi(kart.taban, ortam);
    expect(b.kimlik).toMatch(/^[0-9a-f]{16}$/);
    const y = await ag.kartFetch(`${kart.taban}/eslestir/bilgi`);
    expect(y.status).toBe(200);
    expect(y.ok).toBe(true);
    expect(y.headers.get("Content-Type")).toMatch(/json/);
    expect(y.headers.get("content-type")).toBe(y.headers.get("CONTENT-TYPE"));
    expect(y.headers.get("X-Yok")).toBe(null);
    expect((await y.json()).kimlik).toBe(b.kimlik);
  });

  it("ortak esles() + imzali ac() uctan uca kartFetch icinden (POST govdesi, 401 basligi)", async () => {
    const cihaz = await esles(kart.taban, "telefon", PAROLA, ortam);
    expect(kart.durum.cihazlar.size).toBe(1);
    const y = await ac(cihaz, kart.taban, "GET", "/kayit/liste", [], new Uint8Array(0), ortam);
    expect(y.status).toBe(200);
    // Kart yeniden basladi: 401 + X-Acilis basligi kopruden gecmeli ki ac() bir kez yeniden denesin.
    kart.ayarla({ yenidenBasla: true });
    const y2 = await ac(cihaz, kart.taban, "POST", "/komut", [], "G?", ortam);
    expect(y2.ok).toBe(true);
    expect(kart.durum.komutlar.at(-1)).toBe("G?");
  });

  it("ikili govde bayt bayt (0x00, 0xff, satir sonu) ve bos govde", async () => {
    const once = kopru.cagrilar.length;
    await ag.kartFetch(`${kart.taban}/komut`, { method: "POST", headers: { "X-Olcum": "1" }, body: new Uint8Array([0x70, 0x30]) });
    const c = kopru.cagrilar[once];
    expect(Buffer.from(c.govde, "base64")).toEqual(Buffer.from("p0"));
    expect(kart.durum.komutlar.at(-1)).toBe("p0");
    const g = await ag.kartFetch(`${kart.taban}/eslestir/bilgi`);
    expect(kopru.cagrilar.at(-1).govde).toBeUndefined();
    expect((await g.arrayBuffer()).byteLength).toBeGreaterThan(10);
  });

  it("hedef kurali istekten ONCE: herkese acik IP / baska ad / https / kullanici adi -> eklenti CAGRILMAZ", async () => {
    const once = kopru.cagrilar.length;
    expect(await turu(ag.kartFetch("http://8.8.8.8/eslestir/bilgi"))).toBe("ozel-degil");
    expect(await turu(ag.kartFetch("http://evil.example/eslestir/bilgi"))).toBe("ad-izinsiz");
    expect(await turu(ag.kartFetch("https://192.168.1.5/eslestir/bilgi"))).toBe("bicim");
    expect(await turu(ag.kartFetch("http://a" + String.fromCharCode(64) + "192.168.1.5/x"))).toBe("bicim");
    expect(await turu(ag.kartFetch("http://0xC0A80101/x"))).toBe("bicim");
    expect(await turu(ag.kartFetch("http://192.168.1.5/a b"))).toBe("bicim");
    // Yol yalniz yazdirilabilir ASCII: sekme, satir sonu, kontrol karakteri, ASCII disi harf ret.
    for (const kotu of ["\t", "\r\nHost: x", "\u0000", "ş", " "]) {
      expect(await turu(ag.kartFetch(`http://192.168.1.5/a${kotu}b`)), JSON.stringify(kotu)).toBe("bicim");
    }
    expect(await turu(ag.kartFetch(null))).toBe("bicim");
    expect(await turu(ag.kartFetch(`${kart.taban}/x`, { method: "DELETE" }))).toBe("bicim");
    expect(kopru.cagrilar.length).toBe(once);
  });

  it("yerel dongu yalniz secenekle", () => {
    expect(() => urlDenetle("http://127.0.0.1:18080/x")).toThrow(KartAgHatasi);
    expect(urlDenetle("http://127.0.0.1:18080/x", { yerelDongu: true })).toEqual({ ad: "127.0.0.1", port: 18080 });
    expect(urlDenetle("http://192.168.4.1/akis?_c=1&_s=2")).toEqual({ ad: "192.168.4.1", port: 80 });
  });

  it("eklenti hatasi TUR olarak; bilinmeyen kod ve ayrintili mesaj sizmaz", async () => {
    const sizinti = "192.168.99.99 parola=gizli-sinama";
    const kotu = (code) => agKur({ istek: async () => { const e = new Error(sizinti); e.code = code; throw e; } }, { yerelDongu: true });
    for (const tur of ["zaman-asimi", "baglanti", "wifi-yok", "cleartext", "govde-buyuk"]) {
      expect(await turu(kotu(tur).kartFetch("http://127.0.0.1/x"))).toBe(tur);
    }
    for (const kod of [undefined, 42, "boyle-bir-tur-yok", sizinti]) {
      try {
        await kotu(kod).kartFetch("http://127.0.0.1/x");
        expect.unreachable();
      } catch (e) {
        expect(e.tur).toBe("ic-hata");
        expect(e.message).toBe("ic-hata");
        expect(JSON.stringify(e, Object.getOwnPropertyNames(e))).not.toContain("gizli-sinama");
      }
    }
    expect(await turu(agKur({ istek: async () => ({}) }, { yerelDongu: true }).kartFetch("http://127.0.0.1/x"))).toBe("ic-hata");
  });

  it("zaman asimi ve govde siniri eklentiye iletilir; kart yavassa zaman-asimi", async () => {
    kart.ayarla({ gecikmeMs: 600 });
    expect(await turu(ag.kartFetch(`${kart.taban}/eslestir/bilgi`, { zamanAsimiMs: 150 }))).toBe("zaman-asimi");
    kart.ayarla({ gecikmeMs: 0 });
    expect(kopru.cagrilar.at(-1).zamanAsimiMs).toBe(150);
    expect(kopru.cagrilar.at(-1).azamiGovde).toBe(64 * 1024);
    expect(await turu(ag.kartFetch(`${kart.taban}/eslestir/bilgi`, { azamiGovde: 8 }))).toBe("govde-buyuk");
  });
});
