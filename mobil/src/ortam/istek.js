// Panelin kart istekleri (5P K7): fetch'e benzer imzali istek. Panel telefon kipinde kartIstek /
// `/pil` / `/kal/liste` / `/kunye.json` / `/kayit/*` / `/skop.bin` / `/cihaz/*` / `/saat` isteklerini
// buradan yollar; hepsi Android `kart.istek`ten (imzali, yalniz kimligi dogrulanmis karta — A2, A14, A15).
//
//   const r = await istek("/kayit/veri?sira=5&bayt=8192", { method: "GET", signal });
//   r: GERCEK `Response` — HTTP hatasi r.ok = false (govdesiyle); ag hatasi / eslesmemis -> REDDEDER (TypeError)
//
// Yanit tavani istek basina (kartFetch `azamiGovde`; Kotlin ust siniri 1 MiB — HttpIstek.AZAMI_GOVDE_SINIR):
//   /skop.bin   32 B S3B baslik + 2 B x ornek. Kart en cok 4000 ornek yollar (8032 B); baslik u16 sayac
//               tasidigi icin en kotu 32 + 2 x 65535 = 131 102 B -> 192 KiB.
//   /kayit/veri kart tek yanitta en cok KAYIT_VERI_AZAMI = 8192 B (+ basliklar); panelin parcasi
//               PARCA_BAYT = 8192. Istenen `bayt` + 64 KiB pay, en az varsayilan.
//   digerleri   256 KiB (kayit / kalibrasyon listeleri JSON; eski 64 KiB varsayilani buyuk listede yetmezdi).
// `p0` buradan da gelirse imzasiz ACIL DURDUR yoluna gider (asla imza beklemez).

import { dilSec, metin } from "./metin.js";

export const AZAMI_VARSAYILAN = 256 * 1024;
export const AZAMI_SKOP = 192 * 1024;
export const AZAMI_UST = 1024 * 1024;
export const KAYIT_VERI_PAY = 64 * 1024;
export const ISTEK_SURE_MS = 10000;             // panelin EsitlemeDenetcisi zamanAsimiMs ile ayni

// Kartin yanit basliklarindan panele aktarilanlar (panel / ortak bunlari okur; geri kalani gerekmez).
export const AKTARILAN_BASLIKLAR = Object.freeze([
  "content-type", "cache-control", "retry-after", "x-acilis", "x-onay", "x-kayit-kimlik", "x-sonraki-sira",
]);

const YOL = /^\/[\x21-\x7e]*$/;

export class IstekHatasi extends TypeError {
  constructor(tur, mesaj) {
    super(mesaj);
    this.name = "IstekHatasi";
    this.tur = tur;
  }
}

function coz(s) {
  const t = s.replace(/\+/g, " ");                // kartin sorgu cozucusu gibi: + bosluktur
  try { return decodeURIComponent(t); } catch { return t; }
}

// "/a/b?x=1&y=2#z" -> { yol: "/a/b", argumanlar: [["x","1"],["y","2"]] }. Gecersizse null. Saf.
export function yolAyir(tam) {
  if (typeof tam !== "string") return null;
  const diyez = tam.indexOf("#");
  const s = diyez >= 0 ? tam.slice(0, diyez) : tam;
  const soru = s.indexOf("?");
  const yol = soru >= 0 ? s.slice(0, soru) : s;
  if (!YOL.test(yol) || yol.startsWith("//")) return null;
  const sorgu = soru >= 0 ? s.slice(soru + 1) : "";
  const argumanlar = [];
  for (const p of sorgu.split("&")) {
    if (!p) continue;
    const e = p.indexOf("=");
    argumanlar.push(e < 0 ? [coz(p), ""] : [coz(p.slice(0, e)), coz(p.slice(e + 1))]);
  }
  return { yol, argumanlar };
}

export function azamiGovde(yol, argumanlar = []) {
  if (yol === "/skop.bin") return AZAMI_SKOP;
  if (yol === "/kayit/veri") {
    const a = argumanlar.find(([ad]) => ad === "bayt");
    const n = a ? Number(a[1]) : NaN;
    if (Number.isSafeInteger(n) && n > 0) return Math.min(AZAMI_UST, Math.max(AZAMI_VARSAYILAN, n + KAYIT_VERI_PAY));
  }
  return AZAMI_VARSAYILAN;
}

function govdeBayt(g) {
  if (g === undefined || g === null) return new Uint8Array(0);
  if (typeof g === "string") return new TextEncoder().encode(g);
  if (g instanceof Uint8Array) return g;
  if (g instanceof ArrayBuffer) return new Uint8Array(g);
  if (ArrayBuffer.isView(g)) return new Uint8Array(g.buffer, g.byteOffset, g.byteLength);
  return null;
}

function iptalHatasi(sinyal) {
  if (sinyal && sinyal.reason !== undefined) return sinyal.reason;
  try { return new DOMException("İstek iptal edildi", "AbortError"); } catch { return Object.assign(new Error("AbortError"), { name: "AbortError" }); }
}

// soz'u AbortSignal ile yaristir. (Eklentideki istek kesilemez; yaniti beklenmez, atilir.)
function iptalli(soz, sinyal) {
  if (!sinyal) return soz;
  if (sinyal.aborted) return Promise.reject(iptalHatasi(sinyal));
  return new Promise((coz_, reddet) => {
    const iptal = () => reddet(iptalHatasi(sinyal));
    sinyal.addEventListener("abort", iptal, { once: true });
    soz.then(
      (v) => { sinyal.removeEventListener("abort", iptal); coz_(v); },
      (e) => { sinyal.removeEventListener("abort", iptal); reddet(e); },
    );
  });
}

// kartFetch yaniti ({ status, headers.get, arrayBuffer }) -> gercek Response.
export async function yanitCevir(y) {
  const durum = Number.isInteger(y.status) && y.status >= 200 && y.status <= 599 ? y.status : 502;
  const basliklar = new Headers();
  for (const ad of AKTARILAN_BASLIKLAR) {
    let v = null;
    try { v = y.headers && typeof y.headers.get === "function" ? y.headers.get(ad) : null; } catch { v = null; }
    if (typeof v === "string") basliklar.set(ad, v);
  }
  const govdesiz = durum === 204 || durum === 205 || durum === 304;
  const bayt = govdesiz ? null : new Uint8Array(await y.arrayBuffer());
  return new Response(bayt, { status: durum, headers: basliklar });
}

const P0_GOVDE = /^\s*p0\s*$/;

export function istekKur({ arka, kartAl, p0, dilAl = () => "tr" }) {
  if (!arka || typeof kartAl !== "function" || typeof p0 !== "function") throw new TypeError("arka, kartAl ve p0 gerekli");

  async function istek(tamYol, sec = {}) {
    const dil = dilSec(dilAl());
    const sinyal = sec && sec.signal ? sec.signal : null;
    if (sinyal && sinyal.aborted) throw iptalHatasi(sinyal);
    const a = yolAyir(tamYol);
    if (!a) throw new IstekHatasi("bicim", metin("or.istek_hata", dil));
    const yontem = String((sec && sec.method) || "GET").toUpperCase();
    if (yontem !== "GET" && yontem !== "POST") {
      return new Response(metin("or.yontem", dil), { status: 405, headers: { "content-type": "text/plain;charset=utf-8" } });
    }
    const govde = govdeBayt(sec ? sec.body : null);
    if (govde === null) throw new IstekHatasi("bicim", metin("or.istek_hata", dil));

    // ACIL DURDUR: imza / baglanti beklemeden kendi yolundan. Asla reddetmez -> 204 ya da 503.
    if (yontem === "POST" && a.yol === "/komut" && P0_GOVDE.test(new TextDecoder().decode(govde))) {
      let tamam = false;
      try { tamam = (await p0()) === true; } catch { tamam = false; }
      return tamam ? new Response(null, { status: 204 }) : new Response(metin("or.p0_ulasmadi", dil), { status: 503 });
    }

    const is = (async () => {
      const kart = await kartAl();
      if (kart.durum().durum === "bagli-degil") await arka.baglan();
      const y = await kart.istek(yontem, a.yol, a.argumanlar, yontem === "POST" ? govde : new Uint8Array(0), {
        azamiGovde: azamiGovde(a.yol, a.argumanlar), zamanAsimiMs: ISTEK_SURE_MS, hamYanit: true,
      });
      return yanitCevir(y);
    })();
    try {
      return await iptalli(is, sinyal);
    } catch (e) {
      if (sinyal && sinyal.aborted) throw iptalHatasi(sinyal);
      const tur = e && typeof e.tur === "string" ? e.tur : "ic-hata";
      // 401 (cihaz kartta yok / imza): panel bunu HTTP 401 olarak gorur — "ag hatasi" sanilip yeniden denenmesin.
      if (tur === "cihaz-silinmis") return new Response(metin("or.cihaz_silinmis", dil), { status: 401 });
      const anahtar = { eslesmemis: "or.eslesmemis", "kimlik-uymuyor": "or.kimlik_uymuyor", kasa: "or.kasa" }[tur];
      const ek = e && typeof e.ag === "string" ? ` ${e.ag}` : "";
      throw new IstekHatasi(tur, anahtar ? metin(anahtar, dil) : `${metin("or.istek_hata", dil)} (${tur}${ek})`);
    }
  }

  return istek;
}
