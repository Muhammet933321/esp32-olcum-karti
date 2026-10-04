// CURUTUCU 5B — ortak duzenek. kart.test.js'teki "telefon" ile ayni kurulum; farki: kopru cagrilari
// bir kancadan gecer (geciktirme / siralama) ve kasa eklentisi disaridan verilebilir.
import http from "node:http";
import { agKur } from "../../src/cekirdek/ag.js";
import { kartKur } from "../../src/cekirdek/kart.js";
import { kasaKur } from "../../src/cekirdek/kasa.js";
import { kesifKur } from "../../src/cekirdek/kesif.js";
import { sahteKartAc } from "../sahte-kart/sunucu.mjs";
import { kasaDiski, kasaSahtesi } from "../yardim/kasa_sahtesi.mjs";
import { kopruSahtesi } from "../yardim/kopru_sahtesi.mjs";

export const PAROLA = "sinama-parolasi-1";
export const K1 = "00112233aabbccdd";
export const K2 = "ffeeddcc99887766";

export function bellekOnbellek() {
  let kayit = null;
  return { oku: () => kayit, yaz: (k) => { kayit = k; } };
}

export async function hata(soz) {
  try { await soz; } catch (e) { return e; }
  throw new Error("hata bekleniyordu");
}

/** Sonuc: { tamam: deger } | { tur } — Promise.all yerine her istegin akibetini ayri gormek icin. */
export async function akibet(soz) {
  try { return { tamam: await soz }; } catch (e) { return { tur: e && e.tur ? e.tur : String(e) }; }
}

export const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
export const adres = (k) => `127.0.0.1:${k.port}`;
export const dunyaKur = (...kartlar) => ({ disk: kasaDiski(), onbellek: bellekOnbellek(), adaylar: kartlar.map(adres) });

/** kanca(c, gonder) -> yanit sozu; verilmezse dogrudan gonderilir. */
export function telefon(dunya, { saat = Date.now, kanca = null } = {}) {
  const ham = kopruSahtesi();
  const kopru = { cagrilar: ham.cagrilar, istek: (c) => (kanca ? kanca(c, (x) => ham.istek(x)) : ham.istek(c)) };
  const ag = agKur(kopru, { yerelDongu: true, zamanAsimiMs: 4000 });
  const kesif = kesifKur({
    kartFetch: ag.kartFetch, onbellek: dunya.onbellek, yerelDongu: true, zamanAsimiMs: 800,
    sabitAdaylar: dunya.adaylar.map((a) => ({ adres: a, kaynak: "ap" })),
  });
  const kasaEk = kasaSahtesi(dunya.disk);
  const kasa = kasaKur(kasaEk, { simdiMs: saat });
  const kart = kartKur({ ag, kesif, kasa, simdiMs: saat });
  const imzalilar = () => ham.cagrilar.filter((c) => c.basliklar["X-Imza"] !== undefined);
  return { kopru: ham, kasaEk, kasa, kart, imzalilar };
}

/** Sahte kart + eslesmis telefon. kapat() ikisini de birakir. */
export async function eslesmis(secenek = {}) {
  const k = await sahteKartAc({ port: 0, parola: PAROLA, kimlik: K1, ...secenek });
  const dunya = dunyaKur(k);
  const t = telefon(dunya);
  await t.kart.baglan();
  await t.kart.esles("sinama telefonu", PAROLA);
  return { k, dunya, t };
}

/**
 * KOTU NIYETLI kart: her ucu testin verdigi islev yanitlar. isleyici(yol, istek, u) ->
 *   { kod, basliklar, govde } | null (404). durum.istekler: [{ yol, basliklar, sorgu }].
 */
export function kotuKartAc(isleyici) {
  const durum = { istekler: [] };
  const sunucu = http.createServer((istek, yanit) => {
    const u = new URL(istek.url, "http://x");
    istek.resume();
    durum.istekler.push({ yol: u.pathname, basliklar: { ...istek.headers }, sorgu: u.search });
    const s = isleyici(u.pathname, istek, u);
    if (!s) { yanit.writeHead(404); yanit.end(); return; }
    const g = typeof s.govde === "string" ? s.govde : JSON.stringify(s.govde ?? "");
    yanit.writeHead(s.kod ?? 200, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(g), ...(s.basliklar || {}) });
    yanit.end(g);
  });
  return new Promise((coz) => {
    sunucu.listen(0, "127.0.0.1", () => coz({
      port: sunucu.address().port, durum,
      imzalilar: () => durum.istekler.filter((i) => i.basliklar["x-imza"] !== undefined),
      kapat: () => new Promise((c) => { sunucu.closeAllConnections(); sunucu.close(c); }),
    }));
  });
}

export const bilgiYaniti = (ek = {}) => ({
  surum: "OK1", kimlik: K1, acilis: "ab".repeat(16), tuz: "cd".repeat(16), tur: 10000, zorunlu: 0, misafir: 0, saat: 1,
  cihaz_azami: 8, ...ek,
});
