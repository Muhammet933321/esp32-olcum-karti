// 5A-3 — sahte kart (test/sahte-kart/sunucu.mjs) ve bagimsiz imza dogrulayicisi.
// Istekler YALNIZ 127.0.0.1'deki sahte sunucuya gider; gercek karta hic istek yok.
import { describe, it, expect, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import http from "node:http";

import * as IM from "../../ortak/src/imza.js";
import { hex, hexten, utf8Kodla } from "../../ortak/src/kripto.js";
import { T_NOKTA, kayitPaketle } from "../../ortak/src/kayit.js";
import { Esitleyici, bellekDepo, imzaliIstek, imzaliOnay } from "../../ortak/src/esitle.js";
import { bilgiCoz } from "../../ortak/src/zarf.js";
import * as G from "./sahte-kart/imza_dogrula.mjs";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";

const V = JSON.parse(readFileSync(new URL("../../uretim/vektor_guvenlik.json", import.meta.url), "utf8"));
const PAROLA = "sinama-parolasi-1";
const ortam = { fetch: (u, s) => fetch(u, s) };
const BOS = new Uint8Array(0);

const acik = [];
async function kartAc(secenek) {
  const k = await sahteKartAc(secenek);
  acik.push(k);
  return k;
}
afterEach(async () => {
  while (acik.length) await acik.pop().kapat();
});

/** Ham HTTP istegi (Node fetch `Host` basligini degistirtmez). */
function ham(port, { yontem = "GET", yol = "/", basliklar = {}, govde = null } = {}) {
  return new Promise((coz, reddet) => {
    const i = http.request({ host: "127.0.0.1", port, method: yontem, path: yol, headers: basliklar, agent: false }, (y) => {
      const p = [];
      y.on("data", (x) => p.push(x));
      y.on("end", () => coz({ durum: y.statusCode, basliklar: y.headers, govde: Buffer.concat(p).toString("utf8") }));
      y.on("error", reddet);
    });
    i.on("error", reddet);
    i.end(govde);
  });
}

function komutGonder(kart, metin, basliklar = { "X-Olcum": "1" }) {
  return fetch(kart.taban + "/komut", { method: "POST", headers: { "Content-Type": "text/plain", ...basliklar }, body: metin });
}

/** SSE akisini ac; `kosul(metin)` dogru olana ya da akis bitene dek oku. */
async function akisAc(url, kosul) {
  const denetci = new AbortController();
  const y = await fetch(url, { signal: denetci.signal });
  let metin = "";
  if (y.status === 200) {
    const okuyucu = y.body.getReader();
    const coz = new TextDecoder();
    while (!kosul(metin)) {
      const { done, value } = await okuyucu.read();
      if (done) break;
      metin += coz.decode(value, { stream: true });
    }
  }
  return { durum: y.status, yanit: y, metin: () => metin, kapat: () => denetci.abort() };
}

async function bekle(kosul, ms = 2000) {
  const son = Date.now() + ms;
  while (!kosul() && Date.now() < son) await new Promise((r) => setTimeout(r, 10));
  return kosul();
}

async function hata(soz) {
  try {
    await soz;
  } catch (h) {
    return h;
  }
  return null;
}

// ── bagimsiz dogrulayici ─────────────────────────────────────────────────
describe("imza_dogrula (node:crypto, ortak/'tan bagimsiz)", () => {
  it("HMAC ve PBKDF2 vektorleri", () => {
    expect(V.hmac.length).toBeGreaterThan(3);
    for (const v of V.hmac) {
      expect(G.hmac(Buffer.from(v.anahtar, "hex"), Buffer.from(v.veri, "hex")).toString("hex")).toBe(v.hmac);
    }
    expect(V.pbkdf2.length).toBeGreaterThan(0);
    for (const v of V.pbkdf2) {
      expect(G.pbkdf2(v.parola, Buffer.from(v.tuz, "hex"), v.tur, v.dk.length / 2).toString("hex")).toBe(v.dk);
    }
    for (const ad of ["pbkdf2_kisa", "pbkdf2_uc"]) {
      const v = V.protokol[ad];
      expect(G.pbkdf2(v.parola, Buffer.from(v.tuz, "hex"), v.tur).toString("hex")).toBe(v.P);
    }
  });

  it("eslestirme vektoru: istemci kaniti, kart kaniti, K", () => {
    const p = V.protokol;
    const P = Buffer.from(p.P, "hex"), nk = Buffer.from(p.nk, "hex"), nc = Buffer.from(p.nc, "hex");
    expect(G.kanitIstemci(P, p.kimlik, nk, nc, p.ad).toString("hex")).toBe(p.kanit_istemci);
    expect(G.kanitKart(P, p.kimlik, nk, nc, p.n).toString("hex")).toBe(p.kanit_kart);
    expect(G.anahtarTuret(P, p.kimlik, nk, nc, p.n).toString("hex")).toBe(p.K);
  });

  it("kanonik metin + imza vektorleri; ortak/src/imza.js ile ayni sonuc", () => {
    expect(V.imza.length).toBeGreaterThan(3);
    for (const v of V.imza) {
      const K = Buffer.from(v.K, "hex"), govde = Buffer.from(v.govde, "hex");
      expect(G.kanonikMetin(v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde).toString("hex")).toBe(v.kanonik);
      expect(G.imzaHesapla(K, v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde)).toBe(v.imza);
      expect(G.imzaDogru(K, v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde, v.imza)).toBe(true);
      expect(G.imzaDogru(K, v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac + 1, govde, v.imza)).toBe(false);
      expect(G.imzaDogru(K, v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, govde, v.imza.slice(2))).toBe(false);
      // iki uygulama uzlasiyor
      expect(IM.imzala(hexten(v.K), v.yontem, v.yol, v.argumanlar, v.acilis, v.sayac, hexten(v.govde))).toBe(v.imza);
    }
  });

  it("64'luk kayan pencere (guv_imza_bit ile ayni sinirlar)", () => {
    const p = G.pencereYeni();
    expect(G.pencereKabul(p, 0)).toBe(false);          // sayac 0 hic kabul edilmez
    expect(G.pencereKabul(p, 1000)).toBe(true);
    expect(G.pencereKabul(p, 1000)).toBe(false);       // tekrar
    expect(G.pencereKabul(p, 937)).toBe(true);         // 63 geride: pencerede
    expect(G.pencereKabul(p, 937)).toBe(false);
    expect(G.pencereKabul(p, 936)).toBe(false);        // 64 geride: disarida
    expect(G.pencereKabul(p, 1001)).toBe(true);
    expect(G.pencereKabul(p, 937)).toBe(false);        // kaydirma goruleni UNUTMAZ
    expect(G.pencereKabul(p, 5000)).toBe(true);        // buyuk sicrama pencereyi sifirlar
    expect(G.pencereKabul(p, 4999)).toBe(true);
    expect(G.pencereKabul(p, 1001)).toBe(false);
    expect(G.pencereKabul(p, 1759000000123n)).toBe(true);
  });
});

// ── eslestirme ───────────────────────────────────────────────────────────
describe("sahte kart: eslestirme", () => {
  it("/eslestir/bilgi kartin alanlarini verir, ortak bilgiDenetle kabul eder", async () => {
    const kart = await kartAc({ kimlik: "a1b2c3d4e5f60718" });
    const y = await fetch(kart.taban + "/eslestir/bilgi");
    expect(y.status).toBe(200);
    expect(y.headers.get("content-type")).toBe("application/json");
    const b = await y.json();
    expect(Object.keys(b)).toEqual(["surum", "kimlik", "acilis", "tuz", "tur", "zorunlu", "misafir", "saat", "cihaz_azami"]);
    expect(b).toMatchObject({ surum: "OK1", kimlik: "a1b2c3d4e5f60718", tur: 10000, zorunlu: 0, misafir: 0, cihaz_azami: 8 });
    expect(b.acilis).toBe(kart.durum.acilis);
    expect(IM.bilgiDenetle(b).kimlik).toBe("a1b2c3d4e5f60718");
    kart.ayarla({ kimlik: "ffeeddccbbaa9988" });
    expect((await (await fetch(kart.taban + "/eslestir/bilgi")).json()).kimlik).toBe("ffeeddccbbaa9988");
  });

  it("ortak esles() bastan sona: K iki tarafta ayni", async () => {
    const kart = await kartAc();
    const cihaz = await IM.esles(kart.taban, "Telefon ğ", PAROLA, ortam);
    expect(cihaz.n).toBe(1);
    expect(cihaz.kimlik).toBe("0123456789abcdef");
    expect(cihaz.acilis).toBe(kart.durum.acilis);
    const kayit = kart.durum.cihazlar.get(1);
    expect(kayit.ad).toBe("Telefon ğ");
    expect(hex(cihaz.K)).toBe(Buffer.from(kayit.K).toString("hex"));
    expect(cihaz.K.length).toBe(32);
    const ikinci = await IM.esles(kart.taban, "Tablet", PAROLA, ortam);
    expect(ikinci.n).toBe(2);
    expect(hex(ikinci.K)).not.toBe(hex(cihaz.K));
  });

  it("yanlis parola: ret + 2^k s bekleme (429, Retry-After), dogru parola sifirlar", async () => {
    let t = 1_000_000;
    const kart = await kartAc({ saat: () => t });
    const dene = (parola) => hata(IM.esles(kart.taban, "Telefon", parola, ortam));
    let h = await dene("sinama-YANLIS-parola");
    expect(h).toBeInstanceOf(IM.CalismaHatasi);
    expect(h.message).toMatch(/\/eslestir\/kanit: 403/);
    expect(kart.durum.cihazlar.size).toBe(0);

    const baslat = () => fetch(kart.taban + "/eslestir/baslat?ad=Telefon&nc=" + "ab".repeat(16),
      { method: "POST", headers: { "X-Olcum": "1" } });
    let y = await baslat();
    expect(y.status).toBe(429);
    expect(y.headers.get("retry-after")).toBe("1");
    t += 999;
    expect((await baslat()).status).toBe(429);
    t += 1;
    h = await dene("sinama-YANLIS-parola");            // 2. yanlis: bekleme 2 s
    expect(h.message).toMatch(/\/eslestir\/kanit: 403/);
    y = await baslat();
    expect(y.status).toBe(429);
    expect(y.headers.get("retry-after")).toBe("2");
    t += 1999;
    expect((await baslat()).status).toBe(429);
    t += 1;
    expect(await dene(PAROLA)).toBe(null);            // dogru parola
    expect(kart.durum.cihazlar.size).toBe(1);
    h = await dene("sinama-YANLIS-parola");            // sayac sifirlandi: yine 1 s
    expect(h.message).toMatch(/403/);
    expect((await baslat()).headers.get("retry-after")).toBe("1");
  });

  it("bekleme olcegi enjekte edilebilir (gercek saatle hizli test)", async () => {
    const kart = await kartAc({ beklemeOlcek: 0.4 });     // 2^0 s -> 400 ms
    expect((await hata(IM.esles(kart.taban, "Telefon", "sinama-YANLIS-parola", ortam))).message).toMatch(/403/);
    expect((await hata(IM.esles(kart.taban, "Telefon", PAROLA, ortam))).message).toMatch(/\/eslestir\/baslat: 429/);
    await new Promise((r) => setTimeout(r, 450));
    expect((await IM.esles(kart.taban, "Telefon", PAROLA, ortam)).n).toBe(1);
  });

  it("tek bekleyen eslestirme, 60 s gecerlilik, bekleyen basina tek deneme", async () => {
    let t = 5_000_000;
    const kart = await kartAc({ saat: () => t });
    const post = async (yol) => {
      const y = await fetch(kart.taban + yol, { method: "POST", headers: { "X-Olcum": "1" } });
      return { durum: y.status, govde: y.status === 200 ? await y.json() : await y.text() };
    };
    const baslat = () => post("/eslestir/baslat?ad=Telefon&nc=" + "cd".repeat(16));
    const sahte = "00".repeat(32);

    const ilk = (await baslat()).govde, ikinci = (await baslat()).govde;
    expect(Object.keys(ilk)).toEqual(["eno", "nk"]);
    expect(ilk.nk).toMatch(/^[0-9a-f]{32}$/);
    expect(ikinci.eno).not.toBe(ilk.eno);
    expect((await post(`/eslestir/kanit?eno=${ilk.eno}&kanit=${sahte}`)).durum).toBe(410);   // yerine yenisi gecti

    t += 60_001;                                         // suresi doldu: kanit denenmez bile
    expect((await post(`/eslestir/kanit?eno=${ikinci.eno}&kanit=${sahte}`)).durum).toBe(410);
    const ucuncu = (await baslat()).govde;               // 410 bekleme baslatmadi
    expect(ucuncu.eno).toBeGreaterThan(0);
    t += 60_000;                                         // tam 60 s: hala gecerli -> yanlis kanit 403
    expect((await post(`/eslestir/kanit?eno=${ucuncu.eno}&kanit=${sahte}`)).durum).toBe(403);
    expect((await post(`/eslestir/kanit?eno=${ucuncu.eno}&kanit=${sahte}`)).durum).toBe(410);  // tek deneme

    expect((await post("/eslestir/baslat?ad=Telefon&nc=kisa")).durum).toBe(400);
    expect((await post(`/eslestir/kanit?eno=1&kanit=kisa`)).durum).toBe(400);
  });

  it("kisa web parolasi olan kart eslestirmeyi reddeder (403)", async () => {
    const kart = await kartAc({ parola: "sinama-kisa" });
    const y = await fetch(kart.taban + "/eslestir/baslat?ad=Telefon&nc=" + "ab".repeat(16),
      { method: "POST", headers: { "X-Olcum": "1" } });
    expect(y.status).toBe(403);
  });
});

// ── imzali istekler ──────────────────────────────────────────────────────
describe("sahte kart: imzali istekler", () => {
  async function eslesmis(secenek = { zorunlu: 1 }) {
    const kart = await kartAc(secenek);
    const cihaz = await IM.esles(kart.taban, "Telefon", PAROLA, ortam);
    return { kart, cihaz };
  }
  const gonder = ({ url, secenekler }) => fetch(url, secenekler);

  it("ac() ile imzali /kayit/liste; imzasiz 401 + X-Acilis", async () => {
    const { kart, cihaz } = await eslesmis();
    const y = await IM.ac(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ortam);
    expect(y.status).toBe(200);
    const liste = await y.json();
    expect(Object.keys(liste)).toEqual(["surum", "durum", "sektor", "sektor_bayt", "sonraki", "onay", "doluluk_binde",
      "onaysiz_binde", "aktif", "acilis", "unix", "kimlik", "temiz_kalan", "oturumlar"]);
    expect(liste.sonraki).toBe(1);
    expect(kart.durum.imzali).toBe(1);

    const imzasiz = await fetch(kart.taban + "/kayit/liste");
    expect(imzasiz.status).toBe(401);
    expect(imzasiz.headers.get("x-acilis")).toBe(kart.durum.acilis);
    expect(kart.durum.ret401).toBe(1);
    expect(kart.durum.imzali).toBe(1);
  });

  it("zorunlu 0: okuma imzasiz acik, ama BOZUK imza yine 401 (imzasiz dala dusmez)", async () => {
    const { kart, cihaz } = await eslesmis({ zorunlu: 0 });
    expect((await fetch(kart.taban + "/kayit/liste")).status).toBe(200);
    const istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, 50);
    istek.secenekler.headers["X-Imza"] = "0".repeat(64);
    expect((await gonder(istek)).status).toBe(401);
    expect((await fetch(kart.taban + "/cihaz/liste")).status).toBe(401);   // CIHAZ sinifi her zaman imzali
  });

  it("ayni istegin tekrar oynatilmasi 401", async () => {
    const { kart, cihaz } = await eslesmis();
    const istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, 1234);
    expect((await gonder(istek)).status).toBe(200);
    const tekrar = await gonder(istek);
    expect(tekrar.status).toBe(401);
    expect(tekrar.headers.get("x-acilis")).toBe(kart.durum.acilis);
    expect(kart.durum.imzali).toBe(1);
    expect(kart.durum.ret401).toBe(1);
  });

  it("kayan pencere: 63 geri kabul, 64 geri ret, sayac 0 ret", async () => {
    const { kart, cihaz } = await eslesmis();
    const dene = async (sayac) => (await gonder(IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, sayac))).status;
    expect(await dene(1000)).toBe(200);
    expect(await dene(937)).toBe(200);
    expect(await dene(936)).toBe(401);
    expect(await dene(937)).toBe(401);
    expect(await dene(0)).toBe(401);
    expect(await dene(1001)).toBe(200);
  });

  it("govdesi / yolu / yontemi / argumani degistirilmis istek 401", async () => {
    const { kart, cihaz } = await eslesmis();
    let s = 100;
    // govde
    let istek = IM.istekKur(cihaz, kart.taban, "POST", "/komut", [], utf8Kodla("Gd"), ++s);
    istek.secenekler.body = utf8Kodla("GF!");
    expect((await gonder(istek)).status).toBe(401);
    expect(kart.durum.komutlar).toEqual([]);
    // yol
    istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ++s);
    istek.url = kart.taban + "/kal/liste";
    expect((await gonder(istek)).status).toBe(401);
    // yontem (/kayit/liste kartta her yontemi kabul eder; imza yontemi baglar)
    istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ++s);
    istek.secenekler.method = "POST";
    expect((await gonder(istek)).status).toBe(401);
    // arguman
    istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/veri", [["sira", "1"]], BOS, ++s);
    istek.url = kart.taban + "/kayit/veri?sira=2";
    expect((await gonder(istek)).status).toBe(401);
    // baska cihaz numarasi
    istek = IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ++s);
    istek.secenekler.headers["X-Cihaz"] = "2";
    expect((await gonder(istek)).status).toBe(401);
    // degistirilmemis hali gecer; reddedilen sayaclar pencereyi ILERLETMEDI
    expect((await gonder(IM.istekKur(cihaz, kart.taban, "POST", "/komut", [], utf8Kodla("Gd"), 101))).status).toBe(204);
    expect(kart.durum.komutlar).toEqual(["Gd"]);
    expect(kart.durum.ret401).toBe(5);
    // form kodlamali imzali istek 400
    istek = IM.istekKur(cihaz, kart.taban, "POST", "/komut", [], utf8Kodla("Gd"), ++s);
    istek.secenekler.headers["Content-Type"] = "application/x-www-form-urlencoded";
    expect((await gonder(istek)).status).toBe(400);
  });

  it("yenidenBasla: yeni acilis, pencere sifir; ac() BIR kez yeniden dener ve gecer", async () => {
    const { kart, cihaz } = await eslesmis();
    expect((await IM.ac(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ortam)).status).toBe(200);
    // pencereyi COK ileri tasi: sifirlanmazsa asagidaki ac() (sayac ~ simdi) pencerenin gerisinde kalir
    const ileri = Date.now() + 10_000_000;
    expect((await gonder(IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ileri))).status).toBe(200);
    expect((await gonder(IM.istekKur(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ileri - 1000))).status).toBe(401);
    const eski = kart.durum.acilis;
    kart.ayarla({ yenidenBasla: true });
    expect(kart.durum.acilis).not.toBe(eski);
    expect(kart.durum.acilis).toMatch(/^[0-9a-f]{32}$/);
    expect(kart.durum.cihazlar.size).toBe(1);            // cihazlar NVS'te: kalir

    const once = kart.durum.ret401;
    const y = await IM.ac(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ortam);
    expect(y.status).toBe(200);
    expect(kart.durum.ret401).toBe(once + 1);            // eski acilisla 401, yenisiyle gecti
    expect(cihaz.acilis).toBe(kart.durum.acilis);
  });

  it("/kayit/veri: ayarla({kayitlar}) akisindan, kartin basliklariyla; ortak Esitleyici bayt bayt alir", async () => {
    const { kart, cihaz } = await eslesmis();
    const kay = [];
    for (let s = 1; s <= 40; s++) kay.push(kayitPaketle(T_NOKTA, s, 3, Uint8Array.from({ length: 36 }, (_, j) => (s * 7 + j) & 255)));
    const akis = Buffer.concat(kay);
    kart.ayarla({ kayitlar: akis });

    const y = await IM.ac(cihaz, kart.taban, "GET", "/kayit/veri", [["sira", "39"], ["bayt", "8192"]], BOS, ortam);
    expect(y.headers.get("content-type")).toBe("application/octet-stream");
    expect(y.headers.get("x-kayit-kimlik")).toBe("7");
    expect(y.headers.get("x-ilk-sira")).toBe("39");
    expect(y.headers.get("x-son-sira")).toBe("40");
    expect(y.headers.get("x-sonraki-sira")).toBe("41");
    expect(y.headers.get("x-onay")).toBe("0");
    expect(Buffer.from(await y.arrayBuffer()).equals(Buffer.concat(kay.slice(38)))).toBe(true);
    // kayit bolunmez: 52 B'lik kayitlardan 120 B'a iki tane sigar
    const kisa = await IM.ac(cihaz, kart.taban, "GET", "/kayit/veri", [["sira", "1"], ["bayt", "120"]], BOS, ortam);
    expect((await kisa.arrayBuffer()).byteLength).toBe(104);

    const depo = bellekDepo();
    const e = new Esitleyici({
      tabanUrl: kart.taban, fetch: ortam.fetch, depo, bayt: 1100, onayBekleMs: 5,
      istek: imzaliIstek(cihaz, ortam), onay: imzaliOnay(cihaz, kart.taban, ortam),
    });
    const sonuc = await e.esitle();
    expect(sonuc.yeni_kayit).toBe(40);
    expect(sonuc.son_sira).toBe(40);
    expect(sonuc.onay_dogrulandi).toBe(true);
    expect(Buffer.from(depo.anlik().veri).equals(akis)).toBe(true);
    expect(kart.durum.komutlar.at(-1)).toBe("Go40");
    const liste = await (await IM.ac(cihaz, kart.taban, "GET", "/kayit/liste", [], BOS, ortam)).json();
    expect(liste).toMatchObject({ sonraki: 41, onay: 40, kimlik: 7 });
    expect(liste.oturumlar).toMatchObject([{ id: 3, ilk: 1, son: 40 }]);
  });

  it("/cihaz/liste, /cihaz/sil, /saat, /kal/liste, /bildirim/bilgi", async () => {
    const { kart, cihaz } = await eslesmis();
    const ikinci = await IM.esles(kart.taban, "Tablet", PAROLA, ortam);
    const al = (yontem, yol, arg = []) => IM.ac(cihaz, kart.taban, yontem, yol, arg, BOS, ortam);

    const liste = await (await al("GET", "/cihaz/liste")).json();
    expect(liste.cihazlar.map((c) => [c.n, c.ad])).toEqual([[1, "Telefon"], [2, "Tablet"]]);
    expect(Object.keys(liste.cihazlar[0])).toEqual(["n", "ad", "eklenme", "son"]);   // anahtar yanitta YOK

    expect((await al("POST", "/cihaz/sil", [["n", "2"]])).status).toBe(204);
    expect(kart.durum.cihazlar.has(2)).toBe(false);
    expect((await hata(IM.ac(ikinci, kart.taban, "GET", "/cihaz/liste", [], BOS, ortam))).durum).toBe(401);
    expect((await hata(al("POST", "/cihaz/sil", [["n", "2"]]))).durum).toBe(404);
    expect((await hata(al("POST", "/cihaz/sil", [["n", "9"]]))).durum).toBe(400);

    expect((await hata(al("POST", "/saat", [["unix", "1600000000"]]))).durum).toBe(400);
    expect((await al("POST", "/saat", [["unix", "1790000000"]])).status).toBe(204);
    expect((await (await fetch(kart.taban + "/eslestir/bilgi")).json()).saat).toBe(2);
    kart.ayarla({ saatNtp: true });
    expect((await hata(al("POST", "/saat", [["unix", "1790000000"]]))).durum).toBe(409);

    const kal = await (await al("GET", "/kal/liste")).json();
    expect(Object.keys(kal)).toEqual(["surum", "adet", "taslak", "etkin", "azami", "kayitlar"]);

    const zarf = new Uint8Array(await (await al("GET", "/bildirim/bilgi")).arrayBuffer());
    const b = bilgiCoz(cihaz.K, cihaz.kimlik, cihaz.n, zarf);
    expect(b.uri).toMatch(/^mqtts:\/\//);
    expect(b.onek).toMatch(/^[0-9a-f]{32}$/);
    expect(b.anahtar.length).toBe(32);
    kart.ayarla({ bildirim: null });
    expect((await hata(al("GET", "/bildirim/bilgi"))).durum).toBe(404);
  });
});

// ── Host, X-Olcum, CORS ──────────────────────────────────────────────────
describe("sahte kart: Host beyaz listesi ve basliklar", () => {
  it("yabanci Host 403; olcum.local, olcum ve baglanilan IP kabul (port atilir)", async () => {
    const kart = await kartAc();
    const dene = async (host, yol = "/eslestir/bilgi") => (await ham(kart.port, { yol, basliklar: { Host: host } })).durum;
    expect(await dene("yabanci.invalid")).toBe(403);
    expect(await dene("localhost")).toBe(403);
    expect(await dene("olcum.local.yabanci.invalid")).toBe(403);
    expect(await dene("yabanci.invalid", "/kayit/liste")).toBe(403);
    expect(await dene("yabanci.invalid", "/kal/liste")).toBe(403);
    expect(await dene("olcum.local")).toBe(200);
    expect(await dene("OLCUM.local:80")).toBe(200);
    expect(await dene("olcum")).toBe(200);
    expect(await dene(`127.0.0.1:${kart.port}`)).toBe(200);
    const y = await ham(kart.port, {
      yontem: "POST", yol: "/komut", basliklar: { Host: "yabanci.invalid", "X-Olcum": "1", "Content-Type": "text/plain" }, govde: "p0",
    });
    expect(y.durum).toBe(403);                           // p0 bile yabanci Host'tan gecmez
    expect(kart.durum.komutlar).toEqual([]);
  });

  it("X-Olcum: kartin istedigi uclarda yoksa 400; hicbir yanitta Access-Control-Allow-Origin yok", async () => {
    const kart = await kartAc();
    const yanitlar = [
      await fetch(kart.taban + "/eslestir/bilgi"),                       // GET: X-Olcum aranmaz
      await fetch(kart.taban + "/eslestir/baslat?ad=T&nc=" + "ab".repeat(16), { method: "POST" }),
      await fetch(kart.taban + "/eslestir/kanit?eno=1&kanit=" + "ab".repeat(32), { method: "POST" }),
      await komutGonder(kart, "p0", {}),
      await komutGonder(kart, "p0", { Origin: "http://yabanci.invalid", "X-Olcum": "1" }),
      await fetch(kart.taban + "/kayit/liste", { headers: { Origin: "http://yabanci.invalid" } }),
      await fetch(kart.taban + "/yok"),
      await fetch(kart.taban + "/komut"),                                 // GET /komut: uc yok
      await fetch(kart.taban + "/cihaz/liste"),
    ];
    expect(yanitlar.map((y) => y.status)).toEqual([200, 400, 400, 400, 204, 200, 404, 404, 401]);
    for (const y of yanitlar) {
      expect(y.headers.get("access-control-allow-origin")).toBe(null);
      await y.arrayBuffer();
    }
    expect(kart.durum.komutlar).toEqual(["p0"]);
  });
});

// ── /komut ───────────────────────────────────────────────────────────────
describe("sahte kart: /komut", () => {
  it("p0 ve ? imzasiz serbest (zorunlu 1'de de); baska komut imzasiz ret", async () => {
    const kart = await kartAc({ zorunlu: 1 });
    const p0 = await komutGonder(kart, "p0");
    expect(p0.status).toBe(204);                         // kart 204 doner: govde bos, cevap SSE'den
    expect((await komutGonder(kart, "?")).status).toBe(204);
    expect((await komutGonder(kart, " p0\n")).status).toBe(204);          // kart kirpar
    for (const k of ["p1", "p0!", "?x", "Gd", "GF!"]) {
      const y = await komutGonder(kart, k);
      expect(y.status, k).toBe(401);
      expect(y.headers.get("x-acilis")).toBe(kart.durum.acilis);
    }
    expect((await komutGonder(kart, "")).status).toBe(400);
    expect((await komutGonder(kart, "E?")).status).toBe(403);
    expect(kart.durum.komutlar).toEqual(["p0", "?", "p0"]);
  });

  it("zorunlu 0: imzasiz komut jeton ister (403), p0 yine serbest", async () => {
    const kart = await kartAc();
    expect((await komutGonder(kart, "Gd")).status).toBe(403);
    expect((await komutGonder(kart, "p0")).status).toBe(204);
    expect(kart.durum.komutlar).toEqual(["p0"]);
  });

  it("imzali komut gecer ve durum.komutlar'a duser; E/Q imzali da olsa 403; uzun komut 413", async () => {
    const kart = await kartAc({ zorunlu: 1 });
    const cihaz = await IM.esles(kart.taban, "Telefon", PAROLA, ortam);
    const yolla = (k) => IM.ac(cihaz, kart.taban, "POST", "/komut", [], utf8Kodla(k), ortam);
    expect((await yolla("Gb1000")).status).toBe(204);
    expect((await yolla("p0")).status).toBe(204);
    expect((await hata(yolla("Ez0"))).durum).toBe(403);
    expect((await hata(yolla("Q?"))).durum).toBe(403);
    expect((await yolla("G".repeat(175))).status).toBe(204);
    expect((await hata(yolla("G".repeat(176)))).durum).toBe(413);
    expect(kart.durum.komutlar).toEqual(["Gb1000", "p0", "G".repeat(175)]);
  });
});

// ── /akis ────────────────────────────────────────────────────────────────
describe("sahte kart: /akis", () => {
  it("4 yuva; 5. baglantiya 200 + `event: dolu`; yuva bosalinca yeniden alinir; D satiri kartin biciminde", async () => {
    const kart = await kartAc({ akisAralikMs: 20 });
    const hazir = (m) => m.includes("event: kimlik") && /\ndata: D [^\n]*\n\n/.test(m);
    const acilan = [];
    for (let i = 0; i < 4; i++) acilan.push(await akisAc(kart.taban + "/akis", hazir));
    expect(kart.durum.akisAcik).toBe(4);
    for (const a of acilan) {
      expect(a.yanit.headers.get("content-type")).toBe("text/event-stream");
      expect(a.yanit.headers.get("access-control-allow-origin")).toBe(null);
      expect(a.metin().startsWith('retry: 3000\n\nevent: kimlik\ndata: {"jeton":"')).toBe(true);
      expect(a.metin()).toMatch(/"surucu":true\}\n\n/);
      // "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u %u"
      expect(a.metin()).toMatch(/\nid: \d+\ndata: D -?\d+\.\d{4} -?\d+\.\d{6} -?\d+\.\d{5} \d+\.\d{4} \d+\.\d{7} \d+ \d+ \d+ \d+\n\n/);
    }
    const besinci = await akisAc(kart.taban + "/akis", () => false);       // sunucu kapatana dek oku
    expect(besinci.durum).toBe(200);
    expect(besinci.metin()).toBe("event: dolu\ndata: 4\n\n");
    expect(kart.durum.akisAcik).toBe(4);

    acilan[0].kapat();
    expect(await bekle(() => kart.durum.akisAcik === 3)).toBe(true);
    const yeni = await akisAc(kart.taban + "/akis", (m) => m.includes("event: kimlik"));
    expect(yeni.metin()).toContain("event: kimlik");
    expect(kart.durum.akisAcik).toBe(4);
    for (const a of [...acilan.slice(1), yeni]) a.kapat();
    expect(await bekle(() => kart.durum.akisAcik === 0)).toBe(true);
  });

  it("zorunlu 1: imzasiz akis 401; `_c _s _i` imzali akis acilir; ayni URL tekrar 401", async () => {
    const kart = await kartAc({ zorunlu: 1, akisAralikMs: 20 });
    const cihaz = await IM.esles(kart.taban, "Telefon", PAROLA, ortam);
    const imzasiz = await fetch(kart.taban + "/akis");
    expect(imzasiz.status).toBe(401);
    expect(imzasiz.headers.get("x-acilis")).toBe(kart.durum.acilis);

    const url = await IM.akisUrl(cihaz, kart.taban, ortam);
    const a = await akisAc(url, (m) => /\ndata: D /.test(m));
    expect(a.durum).toBe(200);
    expect(a.metin()).toContain("event: kimlik");
    expect((await fetch(url)).status).toBe(401);          // tekrar oynatma
    a.kapat();
    expect(await bekle(() => kart.durum.akisAcik === 0)).toBe(true);

    kart.ayarla({ misafir: 1 });                          // misafir izleme: imzasiz akis acik
    const m = await akisAc(kart.taban + "/akis", (x) => x.includes("event: kimlik"));
    expect(m.durum).toBe(200);
    m.kapat();
  });
});

// ── hata enjeksiyonu ─────────────────────────────────────────────────────
describe("sahte kart: hata enjeksiyonu", () => {
  it("hata503: sonraki N istege 503, sonra normal", async () => {
    const kart = await kartAc();
    kart.ayarla({ hata503: 2 });
    const kodlar = [];
    for (let i = 0; i < 3; i++) kodlar.push((await fetch(kart.taban + "/eslestir/bilgi")).status);
    expect(kodlar).toEqual([503, 503, 200]);
    kart.ayarla({ hata503: 1 });
    expect((await komutGonder(kart, "p0")).status).toBe(503);              // p0 da etkilenir
    expect(kart.durum.komutlar).toEqual([]);
  });

  it("gecikmeMs: her yanit o kadar gecikir", async () => {
    const kart = await kartAc();
    let t = Date.now();
    await (await fetch(kart.taban + "/eslestir/bilgi")).arrayBuffer();
    const hizli = Date.now() - t;
    kart.ayarla({ gecikmeMs: 250 });
    t = Date.now();
    expect((await fetch(kart.taban + "/eslestir/bilgi")).status).toBe(200);
    const yavas = Date.now() - t;
    expect(yavas).toBeGreaterThanOrEqual(240);
    expect(hizli).toBeLessThan(240);
    kart.ayarla({ gecikmeMs: 0 });
  });

  it("yarimYanit: govde yarida kesilir (istemci hata gorur), kapaninca duzelir", async () => {
    const kart = await kartAc();
    kart.ayarla({ yarimYanit: true });
    const h = await hata((async () => (await fetch(kart.taban + "/eslestir/bilgi")).arrayBuffer())());
    expect(h).toBeInstanceOf(Error);
    kart.ayarla({ yarimYanit: false });
    expect((await fetch(kart.taban + "/eslestir/bilgi")).status).toBe(200);
  });

  it("bilinmeyen ayar adi hata (yazim hatasi sessizce yutulmaz)", async () => {
    const kart = await kartAc();
    expect(() => kart.ayarla({ gecikme: 5 })).toThrow(/bilinmeyen ayar/);
  });
});

// ── komut satiri ─────────────────────────────────────────────────────────
describe("sahte kart: komut satiri", () => {
  it("`node sunucu.mjs --port 0` konsola YALNIZ portu yazar ve yanit verir", async () => {
    const dosya = fileURLToPath(new URL("./sahte-kart/sunucu.mjs", import.meta.url));
    const surec = spawn(process.execPath, [dosya, "--port", "0"], { stdio: ["ignore", "pipe", "inherit"] });
    try {
      const cikti = await new Promise((coz, reddet) => {
        surec.stdout.once("data", (d) => coz(d.toString("utf8")));
        surec.once("exit", (k) => reddet(new Error(`surec cikti: ${k}`)));
      });
      expect(cikti).toMatch(/^\d+\r?\n$/);
      const y = await fetch(`http://127.0.0.1:${Number(cikti)}/eslestir/bilgi`);
      expect(IM.bilgiDenetle(await y.json()).kimlik).toBe("0123456789abcdef");
    } finally {
      surec.kill();
    }
  });
});
