// ACIL DURDURMA (A8–A11, Ö7): hicbir seyi beklemez, asla atmaz, eslesmeden calisir.
import { describe, it, expect, afterEach } from "vitest";
import http from "node:http";
import { readFileSync } from "node:fs";
import { agKur, P0_SURE_MS } from "../src/cekirdek/ag.js";
import { durdurKur, KART_AP_ADRESI } from "../src/cekirdek/durdur.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";

// Kotlin KartAg.p0'in Node sahtesi: P0.kt ile AYNI kural (adreslere ayni anda; 503 / ag hatasinda
// 150-300-450 ms ile en fazla 4 deneme; baska kod denenmez; ilk basari doner).
function p0Sahtesi({ baglantiMs = 800 } = {}) {
  const cagrilar = [];
  const gonder = (adres) => new Promise((coz) => {
    const [host, port] = adres.split(":");
    if (host !== "127.0.0.1") return coz(-1);
    const r = http.request({ host, port: port || 80, path: "/komut", method: "POST", headers: { "X-Olcum": "1", "Content-Type": "text/plain", "Content-Length": 2 } }, (y) => { y.resume(); y.on("end", () => coz(y.statusCode)); });
    r.setTimeout(baglantiMs, () => { r.destroy(); coz(-1); });
    r.on("error", () => coz(-1));
    r.end("p0");
  });
  const bekle = (ms) => new Promise((c) => setTimeout(c, ms));
  async function adresiDene(adres, bitti) {
    for (let d = 1; d <= 4; d++) {
      if (bitti()) return 0;
      const kod = await gonder(adres);
      if (kod >= 200 && kod <= 299) return d;
      if (kod !== 503 && kod !== -1) return 0;
      if (d < 4) await bekle([150, 300, 450][d - 1]);
    }
    return 0;
  }
  function p0({ adresler }) {
    cagrilar.push(adresler);
    return new Promise((coz) => {
      let kalan = adresler.length, bitti = false;
      for (const a of adresler) {
        adresiDene(a, () => bitti).then((d) => {
          if (d > 0 && !bitti) { bitti = true; coz({ tamam: true, adres: a, deneme: d }); }
          if (--kalan === 0 && !bitti) coz({ tamam: false, deneme: 4 });
        });
      }
    });
  }
  return { p0, istek: async () => { throw Object.assign(new Error("x"), { code: "baglanti" }); }, cagrilar };
}

describe("p0 — acil durdurma", () => {
  const acik = [];
  afterEach(async () => { for (const k of acik.splice(0)) await k(); });
  const kart = async (s) => { const k = await sahteKartAc(s); acik.push(() => k.kapat()); return k; };

  it("eklenti cagrisi durdur() ICINDE, ilk await'ten ONCE yapilir (hicbir sey araya giremez)", () => {
    let cagrildi = 0;
    const d = durdurKur({ p0: () => { cagrildi++; return new Promise(() => {}); }, adresler: () => ["192.168.1.7"] });
    d.durdur();                                   // beklenmiyor
    expect(cagrildi).toBe(1);                     // ayni gorev turunda
    expect(d.durum()).toBe("gonderiliyor");
    // ag.p0 da ayni: eklentiye es zamanli gider.
    let ek = 0;
    agKur({ istek: async () => ({}), p0: () => { ek++; return new Promise(() => {}); } }).p0(["192.168.1.7"]);
    expect(ek).toBe(1);
  });

  it("durdur.js kasa / imza / kart / kesif modullerini ICE AKTARMAZ ve await kullanmaz", () => {
    const k = readFileSync(new URL("../src/cekirdek/durdur.js", import.meta.url), "utf8").split("\n").filter((l) => !l.startsWith("//")).join("\n");
    expect(k).not.toMatch(/import /);
    expect(k).not.toMatch(/\bawait\b|\basync\b/);
  });

  it("sahte karta gider: imzasiz, X-Olcum'lu, 204; komut p0; eslesme gerekmez", async () => {
    const k = await kart();
    const e = p0Sahtesi();
    const d = durdurKur({ p0: agKur(e).p0, adresler: () => [`127.0.0.1:${k.port}`] });
    const s = await d.durdur();
    expect(s.tamam).toBe(true);
    expect(s.adres).toBe(`127.0.0.1:${k.port}`);
    expect(d.durum()).toBe("durduruldu");
    expect(k.durum.komutlar).toEqual(["p0"]);
    expect(k.durum.cihazlar.size).toBe(0);
    expect(k.durum.imzali).toBe(0);
    // Kartin kendi erisim noktasi adresi her zaman listede.
    expect(e.cagrilar[0]).toEqual([`127.0.0.1:${k.port}`, KART_AP_ADRESI]);
  });

  it("kart mesgul (503 x2) -> yeniden dener ve durdurur; sure 1 s'nin altinda", async () => {
    const k = await kart();
    k.ayarla({ hata503: 2 });
    const d = durdurKur({ p0: agKur(p0Sahtesi()).p0, adresler: () => [`127.0.0.1:${k.port}`] });
    const t0 = Date.now();
    const s = await d.durdur();
    expect(s.tamam).toBe(true);
    expect(Date.now() - t0).toBeLessThan(1000);
    expect(k.durum.komutlar).toEqual(["p0"]);
  });

  it("asili / olu adres saglam karti BEKLETMEZ", async () => {
    const k = await kart();
    const sessiz = http.createServer(() => {});
    await new Promise((c) => sessiz.listen(0, "127.0.0.1", c));
    acik.push(() => new Promise((c) => { sessiz.closeAllConnections(); sessiz.close(c); }));
    const d = durdurKur({ p0: agKur(p0Sahtesi()).p0, adresler: () => [`127.0.0.1:${sessiz.address().port}`, "127.0.0.1:9", `127.0.0.1:${k.port}`] });
    const t0 = Date.now();
    const s = await d.durdur();
    expect(s.tamam).toBe(true);
    expect(Date.now() - t0).toBeLessThan(500);
  });

  it("hic ulasilamiyorsa ATMAZ: ulasilamadi; adres yok / adresler() atiyor / eklenti atiyor / eklenti yok", async () => {
    const olu = durdurKur({ p0: agKur(p0Sahtesi({ baglantiMs: 100 })).p0, adresler: () => ["127.0.0.1:9"] });
    expect((await olu.durdur()).tamam).toBe(false);
    expect(olu.durum()).toBe("ulasilamadi");
    for (const adresler of [() => [], () => { throw new Error("x"); }, () => null, () => [null, 5, ""]]) {
      const cagri = [];
      const d = durdurKur({ p0: agKur({ istek: async () => ({}), p0: async (v) => { cagri.push(v.adresler); return { tamam: false }; } }).p0, adresler });
      expect((await d.durdur()).tamam).toBe(false);
      expect(cagri).toEqual([[KART_AP_ADRESI]]);          // adres bilinmese de AP adresi denenir
    }
    const atan = agKur({ istek: async () => ({}), p0: () => { throw new Error("x"); } });
    expect(await atan.p0(["192.168.1.7"])).toMatchObject({ tamam: false, adres: null });
    const reddeden = agKur({ istek: async () => ({}), p0: async () => { throw new Error("x"); } });
    expect(await reddeden.p0(["192.168.1.7"])).toMatchObject({ tamam: false, adres: null });
    expect(await agKur({ istek: async () => ({}) }).p0(["192.168.1.7"])).toMatchObject({ tamam: false });
    const kiran = durdurKur({ p0: () => Promise.reject(new Error("x")), adresler: () => [] });
    expect((await kiran.durdur()).tamam).toBe(false);
  });

  it("eklenti hic donmezse de biter (P0_SURE_MS); art arda basista son basis gecerli", async () => {
    expect(P0_SURE_MS).toBeGreaterThanOrEqual(4400);
    expect(P0_SURE_MS).toBeLessThanOrEqual(6000);
    let n = 0;
    const cozuculer = [];
    const d = durdurKur({ p0: () => new Promise((c) => { cozuculer[n++] = c; }), adresler: () => [] });
    const ilk = d.durdur();
    const ikinci = d.durdur();
    cozuculer[1]({ tamam: true, adres: "a" });
    await ikinci;
    expect(d.durum()).toBe("durduruldu");
    cozuculer[0]({ tamam: false });               // gec gelen ESKI sonuc durumu bozmaz
    await ilk;
    expect(d.durum()).toBe("durduruldu");
  });

  it("arayuz geri cagrisi atsa da durdurma etkilenmez", async () => {
    const d = durdurKur({ p0: async () => ({ tamam: true, adres: "a" }), adresler: () => [], degisti: () => { throw new Error("x"); } });
    expect((await d.durdur()).tamam).toBe(true);
  });
});
