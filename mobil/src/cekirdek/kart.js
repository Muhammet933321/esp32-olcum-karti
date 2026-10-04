// Kart baglantisi: durum + eslestirme + imzali istek (tasarim A2, A12–A19). Kripto YOK: protokol
// ortak/src/imza.js'tedir (esles, ac); burasi yalnizca KIME ve NE ZAMAN imzali istek atilacagini
// ve anahtarin NE ZAMAN saklanacagini belirler.
//
//   const kart = kartKur({ ag, kesif, kasa, simdiMs });
//   await kart.baglan({ elle })   -> { durum: "bagli" | "eslesmemis" | "bulunamadi" | "kimlik-uymuyor", adres, kimlik, bilgi }
//   await kart.esles(ad, parola)  -> { kimlik, n }
//   await kart.istek("GET", "/kayit/liste")           -> yanit (2xx)
//   await kart.saatVer()          -> true (verildi) | false
//   await kart.eslesmeyiKaldir()  -> { kartta }
//
// A2: imzali istek yalnizca BU baglantida kimligi `/eslestir/bilgi` ile dogrulanmis ve kasadaki
// kimlikle AYNI olan adrese gider. Baglanti surerken kart degisirse (401 + yeni acilis) kimlik
// yeniden sorulur; uymuyorsa yeniden deneme ATILMAZ.
//
// Hata: KartHatasi(tur). Yalniz tur ve sir OLMAYAN uc sayi/ad tasir (durum, saniye, ag). Parola, K, P,
// imza, kimlik, adres, alttaki istisnanin mesaji hata nesnesine GIRMEZ (A45).
//   bagli-degil | eslesmemis | zaten-esli | kimlik-uymuyor | cihaz-silinmis | http | ag | kasa | ic-hata
//   ad-gecersiz | parola-kisa | parola-yanlis | parola-yok | bekle | liste-dolu | sure-doldu
//   kart-sahte | tur-sinir-disi | kart-gecersiz

import {
  CalismaHatasi, HttpHatasi, PAROLA_EN_AZ, TUR_EN_AZ, TUR_EN_COK, ac, adGecerli, esles as ortakEsles,
} from "@ortak/imza.js";
import { utf8Kodla } from "@ortak/kripto.js";
import { KartAgHatasi } from "./ag.js";
import { KasaHatasi } from "./kasa.js";
import { KesifHatasi } from "./kesif.js";

const ACILIS = /^[0-9a-f]{32}$/;
const BEKLE_AZAMI_S = 3600;

export class KartHatasi extends Error {
  constructor(tur, ek = null) {
    super(tur);
    this.name = "KartHatasi";
    this.tur = tur;
    if (ek && Number.isInteger(ek.durum)) this.durum = ek.durum;
    if (ek && Number.isInteger(ek.saniye)) this.saniye = ek.saniye;
    if (ek && typeof ek.ag === "string") this.ag = ek.ag;
  }
}

// Kartin eslestirme retleri (kaynak: sahte kart = kartin guvenlik.h'si): "<yol> <durum>" -> tur.
const ESLES_RET = Object.freeze({
  "/eslestir/baslat 403": "parola-yok",        // kartta web parolasi yok ya da 12 bayttan kisa
  "/eslestir/baslat 409": "liste-dolu",
  "/eslestir/baslat 429": "bekle",
  "/eslestir/kanit 403": "parola-yanlis",
  "/eslestir/kanit 409": "liste-dolu",
  "/eslestir/kanit 410": "sure-doldu",
});

export function kartKur({ ag, kesif, kasa, simdiMs = Date.now }) {
  if (!ag || typeof ag.kartFetch !== "function") throw new TypeError("ag.kartFetch gerekli");
  if (!kesif || typeof kesif.bul !== "function") throw new TypeError("kesif.bul gerekli");
  if (!kasa || typeof kasa.kaydet !== "function") throw new TypeError("kasa.kaydet gerekli");

  let baglanti = null;                 // { adres, kimlik, bilgi, saatVerildi } — kimligi DOGRULANMIS adres
  let cihaz = null;                    // kasadaki tek cihaz nesnesi (A15)

  const tabanAl = (b) => `http://${b.adres}`;

  async function kasadan(is) {
    try {
      return await is();
    } catch (e) {
      throw e instanceof KasaHatasi ? new KartHatasi("kasa") : e;
    }
  }

  async function baglan({ elle = null } = {}) {
    baglanti = null;
    cihaz = await kasadan(async () => {
      const kayitlar = await kasa.liste();
      return kayitlar.length ? kasa.cihazYukle(kayitlar[0].kimlik) : null;
    });
    const yok = (durum) => ({ durum, adres: null, kimlik: null, bilgi: null });
    let s;
    try {
      s = await kesif.bul({ beklenenKimlik: cihaz ? cihaz.kimlik : null, elle });
    } catch (e) {
      if (e instanceof KesifHatasi) return yok(e.tur === "kimlik-uymuyor" ? "kimlik-uymuyor" : "bulunamadi");
      throw e;                         // HedefHatasi: elle girilen adres kuraldan gecmedi
    }
    // Kesfe guvenilmez: eslesmis cihaz varken baska kimlikli adres baglanti OLAMAZ.
    if (cihaz && s.kimlik !== cihaz.kimlik) return yok("kimlik-uymuyor");
    baglanti = { adres: s.adres, kimlik: s.kimlik, bilgi: s.bilgi, saatVerildi: false };
    if (cihaz && s.bilgi && typeof s.bilgi.acilis === "string" && ACILIS.test(s.bilgi.acilis)) cihaz.acilis = s.bilgi.acilis;
    return { durum: cihaz ? "bagli" : "eslesmemis", adres: s.adres, kimlik: s.kimlik, bilgi: s.bilgi };
  }

  function durum() {
    if (!baglanti) return { durum: "bagli-degil", adres: null, kimlik: null };
    return { durum: cihaz ? "bagli" : "eslesmemis", adres: baglanti.adres, kimlik: baglanti.kimlik };
  }

  // ── imzali istek ───────────────────────────────────────────────────────
  function cevir(e) {
    if (e instanceof KartHatasi) return e;
    // A17: 401 + AYNI acilis (yeni acilista ac() zaten bir kez yeniden denedi). K SILINMEZ.
    if (e instanceof HttpHatasi) return e.durum === 401 ? new KartHatasi("cihaz-silinmis") : new KartHatasi("http", { durum: e.durum });
    if (e instanceof KartAgHatasi) return new KartHatasi("ag", { ag: e.tur });
    if (e instanceof KasaHatasi) return new KartHatasi("kasa");
    return new KartHatasi("ic-hata");
  }

  async function istek(yontem, yol, argumanlar = [], govde = new Uint8Array(0)) {
    const b = baglanti, c = cihaz;
    if (!b) throw new KartHatasi("bagli-degil");
    if (!c || b.kimlik !== c.kimlik) throw new KartHatasi("eslesmemis");
    const taban = tabanAl(b);

    // 401 + YENI acilis: kart yeniden baslamis OLABILIR — ya da adreste artik baska bir kart vardir.
    // ac() yeniden denemeden once kimlik yeniden sorulur.
    async function imzaliFetch(url, secenek) {
      const y = await ag.kartFetch(url, secenek);
      const yeni = y.status === 401 ? y.headers.get("X-Acilis") : null;
      if (yeni && yeni !== c.acilis) {
        const bilgiYaniti = await ag.kartFetch(`${taban}/eslestir/bilgi`, { method: "GET", headers: {} });
        let kimlik = null;
        try { kimlik = bilgiYaniti.status === 200 ? (await bilgiYaniti.json()).kimlik : null; } catch { kimlik = null; }
        if (kimlik !== c.kimlik) {
          if (baglanti === b) baglanti = null;
          throw new KartHatasi("kimlik-uymuyor");
        }
      }
      return y;
    }
    const ortam = { fetch: imzaliFetch, kaydet: kasa.kaydet, simdiMs };

    for (let deneme = 0; ; deneme++) {
      try {
        return await ac(c, taban, yontem, yol, argumanlar, govde, ortam);
      } catch (e) {
        // Disk bizden ilerideydi: kasa sayaci ileri cekti, istek HIC gitmedi -> bir kez yeniden imzala.
        if (e instanceof KasaHatasi && e.tur === "sayac-geride" && deneme === 0) continue;
        throw cevir(e);
      }
    }
  }

  // ── eslestirme (A12, A13) ──────────────────────────────────────────────
  function eslesHatasi(e, son) {
    if (e instanceof KartHatasi) return e;
    if (e instanceof KartAgHatasi) return new KartHatasi("ag", { ag: e.tur });
    if (e instanceof CalismaHatasi) {
      // Kart 2xx dondu ama esles() yine de reddetti: kart kaniti yanlis (parolayi bilmiyor).
      if (son && son.durum >= 200 && son.durum < 300) return new KartHatasi("kart-sahte");
      const tur = son ? ESLES_RET[`${son.yol} ${son.durum}`] : null;
      if (tur === "bekle") {
        const s = /^[0-9]{1,5}$/.test(son.bekle || "") ? Number(son.bekle) : NaN;
        return new KartHatasi("bekle", s >= 1 && s <= BEKLE_AZAMI_S ? { saniye: s } : null);
      }
      return new KartHatasi(tur || "kart-gecersiz");
    }
    return new KartHatasi("kart-gecersiz");       // bicimsiz yanit (JSON, nk, n, kanit ...)
  }

  async function esles(ad, parola) {
    const b = baglanti;
    if (!b) throw new KartHatasi("bagli-degil");
    if (cihaz) throw new KartHatasi("zaten-esli");
    if (typeof ad !== "string" || !adGecerli(ad)) throw new KartHatasi("ad-gecersiz");
    // Kisa parola karta HIC istek gitmeden reddedilir (kart UTF-8 BAYT sayar).
    if (typeof parola !== "string" || utf8Kodla(parola).length < PAROLA_EN_AZ) throw new KartHatasi("parola-kisa");
    const taban = tabanAl(b);
    let son = null;                    // son yanit: { yol, durum, bekle } — hata turunu secmek icin

    async function eslesFetch(url, secenek) {
      const y = await ag.kartFetch(url, secenek);
      const yol = url.slice(taban.length).split("?")[0];
      son = { yol, durum: y.status, bekle: y.headers.get("Retry-After") };
      if (yol === "/eslestir/bilgi" && y.status === 200) {
        let j = null;
        try { j = await y.json(); } catch { j = null; }
        // Kullanicinin ekranda GORDUGU kart bu olmali; degilse hicbir kanit yollanmaz.
        if (!j || j.kimlik !== b.kimlik) throw new KartHatasi("kimlik-uymuyor");
        // Sahte kart tur = 1 dayatip parolayi HMAC hizinda tahmin edemesin (imza.js de reddeder).
        if (!Number.isInteger(j.tur) || j.tur < TUR_EN_AZ || j.tur > TUR_EN_COK) throw new KartHatasi("tur-sinir-disi");
      }
      return y;
    }

    let yeni;
    try {
      yeni = await ortakEsles(taban, ad, parola, { fetch: eslesFetch, simdiMs });
    } catch (e) {
      throw eslesHatasi(e, son);
    }
    try {
      await kasa.cihazSakla(yeni);
    } catch {
      // Anahtar saklanamadi: karttaki kayit yetim kalmasin (liste 8 cihazla sinirli) — elden gelen yapilir.
      try {
        await ac(yeni, taban, "POST", "/cihaz/sil", [["n", String(yeni.n)]], new Uint8Array(0), { fetch: ag.kartFetch, simdiMs });
      } catch { /* kart ulasilamiyor: USB'den Ex<n> */ }
      yeni.K.fill(0);
      throw new KartHatasi("kasa");
    }
    cihaz = yeni;
    return { kimlik: yeni.kimlik, n: yeni.n };
  }

  // ── cihazdan saat (A18) ────────────────────────────────────────────────
  async function saatVer() {
    const b = baglanti;
    if (!b || !cihaz || b.saatVerildi) return false;
    if (b.bilgi && b.bilgi.saat === 1) return false;       // kartin NTP saati var
    b.saatVerildi = true;                                  // baglanti basina BIR KEZ (es zamanli cagrida da)
    try {
      await istek("POST", "/saat", [["unix", String(Math.floor(simdiMs() / 1000))]]);
      return true;
    } catch (e) {
      if (e instanceof KartHatasi && e.tur === "http" && e.durum === 409) return false;   // NTP o arada gelmis
      if (e instanceof KartHatasi && e.tur === "ag") b.saatVerildi = false;               // gitmedi: sonra yeniden
      throw e;
    }
  }

  // ── eslesmeyi kaldir (A19) ─────────────────────────────────────────────
  async function eslesmeyiKaldir() {
    let kartta = false;
    if (cihaz && baglanti) {
      try {
        await istek("POST", "/cihaz/sil", [["n", String(cihaz.n)]]);
        kartta = true;
      } catch (e) {
        kartta = e instanceof KartHatasi && e.tur === "cihaz-silinmis";      // kartta zaten yok
      }
    }
    await kasadan(async () => {
      const kimlikler = cihaz ? [cihaz.kimlik] : (await kasa.liste()).map((k) => k.kimlik);
      for (const kimlik of kimlikler) await kasa.sil(kimlik);
    });
    cihaz = null;
    return { kartta };
  }

  return { baglan, durum, istek, esles, saatVer, eslesmeyiKaldir };
}
