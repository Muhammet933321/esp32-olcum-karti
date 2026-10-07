// 5P (P3) — telefon tasiyicisi + arka plan, SAHTE KARTLA uctan uca (gercek kart.js / kasa / kesif / ag /
// canli.js; kopru = Kotlin KartAg sahtesi). Panelin `uyg`'si sahte: satirIsle, hata, uyari, dil, baglan.
import { describe, it, expect, afterEach } from "vitest";
import http from "node:http";
import { agKur } from "../src/cekirdek/ag.js";
import { canliKur } from "../src/cekirdek/canli.js";
import { kartKur } from "../src/cekirdek/kart.js";
import { kasaKur } from "../src/cekirdek/kasa.js";
import { kesifKur } from "../src/cekirdek/kesif.js";
import { arkaPlanKur } from "../src/ortam/arka_plan.js";
import { YETENEK, tasiyiciKur } from "../src/ortam/tasiyici.js";
import { metin } from "../src/ortam/metin.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kasaDiski, kasaSahtesi } from "./yardim/kasa_sahtesi.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";

const PAROLA = "sinama-parolasi-1";
const K1 = "00112233aabbccdd";
const OLCEK = 50;                       // canli.js yeniden baglanma sureleri: 1 s -> 20 ms

async function bekle(kosul, ms = 5000) {
  const son = Date.now() + ms;
  for (;;) {
    if (kosul()) return;
    if (Date.now() > son) throw new Error("kosul saglanmadi");
    await new Promise((r) => setTimeout(r, 5));
  }
}

function belgeSahtesi() {
  const dinleyici = new Set();
  return {
    visibilityState: "visible", documentElement: { lang: "tr" },
    addEventListener: (ad, fn) => { if (ad === "visibilitychange") dinleyici.add(fn); },
    removeEventListener: (ad, fn) => { dinleyici.delete(fn); },
    gizle() { this.visibilityState = "hidden"; for (const fn of dinleyici) fn(); },
    goster() { this.visibilityState = "visible"; for (const fn of dinleyici) fn(); },
  };
}

function uygSahtesi() {
  const u = { satirlar: [], hata: "", uyari: "", dil: "tr", bagli: false, baglanSayisi: 0, olaylar: [] };
  u.satirIsle = (s) => { u.satirlar.push(s); };
  u.baglan = async () => { u.baglanSayisi += 1; };
  u.olayEkle = (s) => { u.olaylar.push(s); };
  return u;
}

function hamIzleyici(port) {
  return new Promise((coz, reddet) => {
    const r = http.get({ host: "127.0.0.1", port, path: "/akis" }, (y) => { y.resume(); coz({ kod: y.statusCode, kapat: () => r.destroy() }); });
    r.on("error", reddet);
  });
}

describe("telefon tasiyicisi: sahte kartla uctan uca", () => {
  const acik = [];
  afterEach(async () => { for (const k of acik.splice(0).reverse()) await k(); });

  async function kur({ eslesmeli = true, kartSecenek = {} } = {}) {
    const k = await sahteKartAc({ parola: PAROLA, kimlik: K1, zorunlu: 1, akisAralikMs: 20, ...kartSecenek });
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
    if (eslesmeli) {
      await kart.baglan();
      await kart.esles("sinama telefonu", PAROLA);
    }
    const canli = canliKur({ kart, ag, eklenti: kopru, yenidenBul: true, zamanla: (fn, ms) => setTimeout(fn, ms / OLCEK), zamaniBirak: clearTimeout });
    const belge = belgeSahtesi();
    const p0Cagri = [];
    const arka = arkaPlanKur({ kartAl: async () => kart, canliAl: async () => canli, belge, araliKur: () => 1, araliSil: () => {} });
    const tasiyici = tasiyiciKur({ arka, kartAl: async () => kart, p0: async () => { p0Cagri.push(1); return true; } });
    acik.push(async () => { arka.birak(); tasiyici.birak(); });
    arka.baslat();
    return { k, kopru, kart, canli, belge, arka, tasiyici, p0Cagri };
  }

  it("sozlesme yuzu: ad, yetenek (K6), destekli()", async () => {
    const { tasiyici } = await kur();
    expect(tasiyici.ad).toBe("telefon");
    expect(tasiyici.yetenek).toEqual({ ad: "telefon", komut: "hepsi", skop: "ikili", skop_azami: 4000, gecmis_s: 86400, cok_istemci: false, surucu: false });
    expect(tasiyici.yetenek).toBe(YETENEK);
    expect(tasiyici.destekli()).toBe(true);
  });

  it("ac: kartin ham satirlari uyg.satirIsle'ye (kirpilmis); akis IMZALI adresle; kapat: satir durur, yuva bosalir", async () => {
    const { k, kopru, tasiyici } = await kur();
    const u = uygSahtesi();
    await tasiyici.ac(u);
    await bekle(() => u.satirlar.filter((s) => s.startsWith("D ")).length >= 3);
    expect(u.satirlar.every((s) => s === s.trim() && s !== "")).toBe(true);
    expect(k.durum.akisAcik).toBe(1);
    expect(kopru.akisCagrilari[0].url).toMatch(/\/akis\?_c=[0-9]+&_s=[0-9]+&_i=[0-9a-f]{64}$/);
    expect(u.hata).toBe("");
    await tasiyici.kapat(u);
    await bekle(() => k.durum.akisAcik === 0);
    const n = u.satirlar.length;
    await new Promise((r) => setTimeout(r, 120));
    expect(u.satirlar.length).toBe(n);
  });

  it("gonder: imzali POST /komut (X-Olcum: 1, Content-Type: text/plain, govde = komut); kart reddederse sebebiyle uyg.hata", async () => {
    const { k, kopru, tasiyici } = await kur();
    const u = uygSahtesi();
    await tasiyici.ac(u);
    await tasiyici.gonder(u, "Gb1000");
    expect(k.durum.komutlar).toContain("Gb1000");
    // (canli akis acilinca kendisi de `G?` sorar: Gb1000'in cagrisi govdesinden bulunur)
    const c = kopru.cagrilar.filter((x) => x.url.endsWith("/komut") && Buffer.from(x.govde || "", "base64").toString("utf8") === "Gb1000").at(-1);
    expect(c.yontem).toBe("POST");
    expect(c.basliklar["X-Olcum"]).toBe("1");
    expect(c.basliklar["Content-Type"]).toBe("text/plain");
    expect(c.basliklar["X-Imza"]).toMatch(/^[0-9a-f]{64}$/);
    expect(Buffer.from(c.govde, "base64").toString("utf8")).toBe("Gb1000");
    expect(u.hata).toBe("");
    await tasiyici.gonder(u, "E1");                                   // kart Wi-Fi'den E'yi reddeder (403 + sebep)
    expect(u.hata).toBe(`${metin("or.komut_gitmedi", "tr")} (403): E komutlari yalniz USB seri konsoldan`);
  });

  it("gonder 'p0': kart.istek'e GIRMEZ, ACIL DURDUR yoluna gider", async () => {
    const { kopru, tasiyici, p0Cagri } = await kur();
    const u = uygSahtesi();
    const n = kopru.cagrilar.length;
    await tasiyici.gonder(u, "p0");
    expect(p0Cagri.length).toBe(1);
    expect(kopru.cagrilar.length).toBe(n);
    expect(u.hata).toBe("");
  });

  it("eslesmemis: ac REDDEDER (mesaj Bu telefon -> Kart), akis ACILMAZ, dongu yok; eslesince panel kendiliginden yeniden baglanir", async () => {
    const { k, kopru, kart, arka, tasiyici } = await kur({ eslesmeli: false });
    const u = uygSahtesi();
    const e = await tasiyici.ac(u).then(() => null, (x) => x);
    expect(e).toBeInstanceOf(Error);
    expect(e.message).toBe(metin("or.eslesmemis", "tr"));
    expect(e.message).toContain("Bu telefon");
    const e2 = await tasiyici.ac({ ...u, dil: "en" }).then(() => null, (x) => x);
    expect(e2.message).toBe(metin("or.eslesmemis", "en"));
    await new Promise((r) => setTimeout(r, 100));
    expect(kopru.akisCagrilari.length).toBe(0);
    expect(k.durum.akisAcik).toBe(0);
    // "Bu telefon -> Kart"ta eslesildi (olay.js baglantiDinle -> baglantiDegisti): bekleyen panel yeniden baglanir.
    const u3 = uygSahtesi();
    await tasiyici.ac(u3).catch(() => {});
    await kart.esles("sinama telefonu", PAROLA);
    await arka.baglantiDegisti(kart.durum());
    expect(u3.baglanSayisi).toBe(1);
  });

  it("akis 'dolu' (4 izleyici / PC koprusu): uyg.uyari; yer acilinca akis acilir ve uyari silinir", async () => {
    const { k, tasiyici } = await kur({ kartSecenek: { zorunlu: 0 } });
    k.ayarla({ misafir: 1 });
    const iz = [];
    for (let i = 0; i < 4; i++) iz.push(await hamIzleyici(k.port));
    acik.push(async () => { for (const i of iz) i.kapat(); });
    await bekle(() => k.durum.akisAcik === 4);
    const u = uygSahtesi();
    await tasiyici.ac(u);
    await bekle(() => u.uyari !== "");
    expect(u.uyari).toBe(metin("or.dolu", "tr"));
    expect(u.hata).toBe("");
    iz[0].kapat();
    await bekle(() => u.satirlar.some((s) => s.startsWith("D ")), 6000);
    expect(u.uyari).toBe("");
  });

  it("arka plana gecis: akis HEMEN kapanir, hata YAZILMAZ; one donunce satirlar yeniden gelir (yeni imzali adres)", async () => {
    const { k, kopru, belge, tasiyici } = await kur();
    const u = uygSahtesi();
    await tasiyici.ac(u);
    await bekle(() => u.satirlar.some((s) => s.startsWith("D ")));
    belge.gizle();
    await bekle(() => k.durum.akisAcik === 0);
    await new Promise((r) => setTimeout(r, 60));
    const n = u.satirlar.length;
    expect(u.hata).toBe("");
    belge.goster();
    await bekle(() => u.satirlar.length > n + 2);
    expect(k.durum.akisAcik).toBe(1);
    expect(kopru.akisCagrilari.length).toBe(2);
    expect(kopru.akisCagrilari[1].url).not.toBe(kopru.akisCagrilari[0].url);
    expect(u.hata).toBe("");
  });

  it("kart yeniden baslar: uyg.hata 'Akış koptu — yeniden bağlanılıyor'; akis yeniden acilinca hata silinir", async () => {
    const { k, tasiyici } = await kur();
    const u = uygSahtesi();
    await tasiyici.ac(u);
    await bekle(() => u.satirlar.some((s) => s.startsWith("D ")));
    const hatalar = [];
    const izle = setInterval(() => { if (u.hata && !hatalar.includes(u.hata)) hatalar.push(u.hata); }, 1);
    k.ayarla({ yenidenBasla: true });
    const n = u.satirlar.length;
    await bekle(() => hatalar.length > 0);
    expect(hatalar[0]).toBe(metin("or.koptu", "tr"));
    await bekle(() => u.satirlar.length > n + 2 && u.hata === "", 6000);
    clearInterval(izle);
  });

  it("panelin KENDI hatasina dokunulmaz (yalniz ortamin yazdigi metin silinir)", async () => {
    const { tasiyici } = await kur();
    const u = uygSahtesi();
    await tasiyici.ac(u);
    u.hata = "panelin kendi hatasi";
    await bekle(() => u.satirlar.some((s) => s.startsWith("D ")));
    await tasiyici.kapat(u);
    expect(u.hata).toBe("panelin kendi hatasi");
  });
});

describe("telefon tasiyicisi: yanit satirlari ve hata eslemesi (sahte kart nesnesi)", () => {
  function kur(istek, durum = "bagli") {
    const arka = { baglan: async () => ({ durum: "bagli" }), dinle: () => () => {}, hamDinle: () => () => {}, akisIste: () => {} };
    const kart = { durum: () => ({ durum }), istek };
    return tasiyiciKur({ arka, kartAl: async () => kart, p0: async () => false });
  }

  it("2xx yanit govdesinin her dolu satiri satirIsle'ye (kirpilmis, sirayla)", async () => {
    const t = kur(async () => ({ ok: true, status: 200, text: async () => "A menzil=NORMAL oto=1\r\n\n  G 1 0 0 1 1 0 0 0 0 0 0 0 0 \n" }));
    const u = uygSahtesi();
    await t.gonder(u, "?");
    expect(u.satirlar).toEqual(["A menzil=NORMAL oto=1", "G 1 0 0 1 1 0 0 0 0 0 0 0 0"]);
  });

  it("ag / bagli degil: panelin 'kart yok' metni (uyg.metin) + olay; eslesmemis / cihaz silinmis: Bu telefon metni; p0 ulasmadi", async () => {
    const hataAt = (tur) => async () => { throw Object.assign(new Error(tur), { tur, ag: tur === "ag" ? "zaman-asimi" : undefined }); };
    const u = uygSahtesi();
    u.metin = (a) => (a === "kb.komut_kart_yok" ? "PANEL: kart yok" : a);
    await kur(hataAt("ag")).gonder(u, "G?");
    expect(u.hata).toBe("PANEL: kart yok");
    expect(u.olaylar).toEqual(["! komut: ag zaman-asimi"]);
    const u2 = uygSahtesi();
    await kur(hataAt("bagli-degil")).gonder(u2, "G?");
    expect(u2.hata).toBe(metin("or.kart_yok", "tr"));
    const u3 = uygSahtesi();
    await kur(hataAt("eslesmemis")).gonder(u3, "G?");
    expect(u3.hata).toBe(metin("or.eslesmemis", "tr"));
    const u4 = uygSahtesi();
    await kur(hataAt("cihaz-silinmis")).gonder(u4, "G?");
    expect(u4.hata).toBe(metin("or.cihaz_silinmis", "tr"));
    const u5 = uygSahtesi();
    await kur(hataAt("x")).gonder(u5, "p0");
    expect(u5.hata).toBe(metin("or.p0_ulasmadi", "tr"));
  });
});
