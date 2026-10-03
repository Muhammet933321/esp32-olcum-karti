// 5A-3 — SAHTE KART: gercek kartin (kod/olcum-karti-a3/olcum-karti-a3.ino, guvenlik.h) HTTP
// yuzunun Node taklidi. Bagimliliksiz (node:http). Testler ve telefon duman testi buna baglanir;
// gercek karta HIC istek atilmaz.
//
//   node mobil/test/sahte-kart/sunucu.mjs --port 18080 [--host 0.0.0.0]     (konsola yalniz port)
//
// Kartla AYNI olan (kaynaktan okundu, tahmin degil):
//   * Host beyaz listesi (host_gecerli): olcum.local, olcum, baglanilan IP; ilk ':' sonrasi atilir
//     -> 403. Kartta `/akis` ve `/` Host'a BAKMAZ; burada da bakmaz.
//   * Kapi (guv_kapi): imza VARSA sonuc dogrulamadir (401 + X-Acilis); imzasiz: ACIK serbest,
//     CIHAZ her zaman 401, zorunlu 0 ise serbest, IZLEME + misafir serbest, KOMUT isleyiciye.
//   * `X-Olcum: 1` yalniz /eslestir/baslat, /eslestir/kanit, /cihaz/sil, /saat, /komut'ta aranir
//     ve eksigi **400**'dur (403 degil); kapidan SONRA denetlenir.
//   * /komut: `p0` ve `?` (tam esleme) imzasiz serbest; E… ve Q… imzali olsa da 403; basari 204.
//   * /akis: en fazla 4 yuva; doluysa YINE 200 + `event: dolu\ndata: 4\n\n` ve kapanir.
//   * Eslestirme (guv_esles_*): tek bekleyen, 60 s, bekleyen basina tek deneme, yanlis kanitta
//     2^k s bekleme (k <= 8) -> 429 + Retry-After.
//   * Hicbir yanitta Access-Control-Allow-Origin yok.
// Kart taklidinin SINIRLARI: /kayit/liste oturum ozetleri kayit basliklarindan kabaca kurulur
// (hiz_ms, unix_s... 0); eski Basic-Auth yolunun 2^k beklemesi yok; /pil, /skop.bin yok.
//
// Imza dogrulama ./imza_dogrula.mjs'te (ortak/src/imza.js'ten BAGIMSIZ). ortak/ yalniz
// /bildirim/bilgi zarfini KURMAK icin kullanilir.

import http from "node:http";
import { randomBytes } from "node:crypto";
import { pathToFileURL } from "node:url";
import {
  PAROLA_EN_AZ, adGecerli, anahtarTuret, baytEsit, imzaDogru, kanitIstemci, kanitKart, pbkdf2,
  pencereKabul, pencereYeni,
} from "./imza_dogrula.mjs";
import { zarfKur } from "../../../ortak/src/zarf.js";

const AKIS_AZAMI = 4;             // kartta AKIS_AZAMI
const CIHAZ_AZAMI = 8;            // GUV_CIHAZ_AZAMI
const ESLES_SURE_MS = 60000;      // GUV_ESLES_SURE_MS
const BEKLE_AZAMI_K = 8;          // GUV_BEKLE_AZAMI_K
const KOMUT_AZAMI = 176;          // sizeof(KomutKalem::m): 175 karakter + son
const KAYIT_VERI_AZAMI = 8192;    // /kayit/veri tek yanit tavani
const KAYIT_SEKTOR = 4096;
const KAYIT_BASLIK = 16;          // imza(1) tur(1) yuk_bayt(2) sira(4) oturum(4) crc(4)
const KAYIT_IMZA = 0xa5;
const GOVDE_AZAMI = 16384;
const JETON_ABC = "abcdefghjkmnpqrstuvwxyz23456789";

const ACIK = 0, IZLEME = 1, OKUMA = 2, KOMUT = 3, CIHAZ = 4;

function yuzdeCoz(s) {
  try {
    return decodeURIComponent(s.replace(/\+/g, " "));
  } catch {
    return s;
  }
}

function sorguAyir(metin) {
  const c = [];
  if (!metin) return c;
  for (const p of metin.split("&")) {
    if (!p) continue;
    const e = p.indexOf("=");
    c.push(e < 0 ? [yuzdeCoz(p), ""] : [yuzdeCoz(p.slice(0, e)), yuzdeCoz(p.slice(e + 1))]);
  }
  return c;
}

function govdeOku(istek) {
  return new Promise((coz, reddet) => {
    const parcalar = [];
    let n = 0;
    istek.on("data", (p) => {
      n += p.length;
      if (n > GOVDE_AZAMI) {
        reddet(new Error("govde cok buyuk"));
        istek.destroy();
        return;
      }
      parcalar.push(p);
    });
    istek.on("end", () => coz(Buffer.concat(parcalar)));
    istek.on("error", reddet);
  });
}

/** Kayit akisi (ortak/src/kayit.js kayitPaketle ciktilari art arda) -> [{sira, oturum, tur, ham}]. */
function kayitlariAyir(veri) {
  const v = Buffer.from(veri);
  const c = [];
  let a = 0;
  while (a < v.length) {
    if (a + KAYIT_BASLIK > v.length || v[a] !== KAYIT_IMZA) throw new Error(`kayitlar: ${a}. baytta gecersiz kayit`);
    const toplam = Math.floor((KAYIT_BASLIK + v.readUInt16LE(a + 2) + 3) / 4) * 4;
    if (a + toplam > v.length) throw new Error(`kayitlar: ${a}. bayttaki kayit yarim`);
    c.push({ tur: v[a + 1], sira: v.readUInt32LE(a + 4), oturum: v.readUInt32LE(a + 8), ham: v.subarray(a, a + toplam) });
    a += toplam;
  }
  return c;
}

export async function sahteKartAc({
  port = 0, host = "127.0.0.1", kimlik = "0123456789abcdef", parola = "sinama-parolasi-1",
  tur = 10000, zorunlu = 0,
  // test icin: saat (ms; eslestirme suresi ve bekleme bununla olculur) ve 2^k s beklemenin olcegi
  saat = () => Date.now(), beklemeOlcek = 1, akisAralikMs = 200,
} = {}) {
  const ayar = {
    gecikmeMs: 0, hata503: 0, yarimYanit: false, kimlik, parola, tur, zorunlu: zorunlu ? 1 : 0, misafir: 0,
    saatNtp: false, saatKaynak: 0, kayitKimlik: 7,
    bildirim: {
      u: "mqtts://araci.sinama.invalid:8883", k: "sinama-kullanici", p: "sinama-araci-parolasi",
      o: "5a".repeat(16), a: "c3".repeat(32),
    },
    kalListe: { surum: 1, adet: 0, taslak: 0, etkin: 0, azami: 40, kayitlar: [] },
  };
  const tuz = randomBytes(16);
  const durum = { komutlar: [], imzali: 0, ret401: 0, cihazlar: new Map(), akisAcik: 0, acilis: "" };
  const pencereler = new Map();                 // n -> tekrar penceresi (acilis basina)
  const akislar = new Set();                    // acik SSE yanitlari
  const soketler = new Set();
  let jeton = "", acilisMs = saat();
  let bekleyen = null;                          // { eno, nk, nc, ad, bas }
  let eno = 0, denemeK = 0, denemeVar = false, serbestMs = 0;
  let pOnbellek = null;                         // { anahtar, P }
  let kayitlar = [], onay = 0, akisSira = 0, enerjiJ = 0;

  function acilisYenile() {
    durum.acilis = randomBytes(16).toString("hex");
    jeton = Array.from(randomBytes(16), (b) => JETON_ABC[b % JETON_ABC.length]).join("");
    pencereler.clear();
    bekleyen = null;
    denemeVar = false;                          // K7: deneme siniri acilista sifirlanir
    denemeK = 0;
    acilisMs = saat();
    for (const y of akislar) y.destroy();
  }
  acilisYenile();

  // P kartta parola degisince / acilista hesaplanir; burada ilk kullanimda (ayni sonuc)
  function P() {
    if (Buffer.byteLength(ayar.parola, "utf8") < PAROLA_EN_AZ) return null;
    const anahtar = `${ayar.parola}\n${ayar.tur}`;
    if (!pOnbellek || pOnbellek.anahtar !== anahtar) pOnbellek = { anahtar, P: pbkdf2(ayar.parola, tuz, ayar.tur) };
    return pOnbellek.P;
  }

  function bosNumara() {
    for (let n = 1; n <= CIHAZ_AZAMI; n++) if (!durum.cihazlar.has(n)) return n;
    return 0;
  }

  function unix() {
    return Math.floor(Date.now() / 1000);
  }

  // ── yanit ──────────────────────────────────────────────────────────────
  function gonder(b, kod, turu, govde = "", ek = {}) {
    const g = typeof govde === "string" ? Buffer.from(govde, "utf8") : Buffer.from(govde);
    const basliklar = { "Content-Type": turu, Connection: "close", ...ek };
    if (ayar.yarimYanit) {                       // baslik "uzun" der, govde yarida kesilir
      b.yanit.writeHead(kod, { ...basliklar, "Content-Length": g.length + 64 });
      b.yanit.write(g.subarray(0, g.length >> 1), () => b.istek.socket.destroy());
      return;
    }
    b.yanit.writeHead(kod, { ...basliklar, "Content-Length": g.length });
    b.yanit.end(g);
  }

  function metin(b, kod, m, ek) {
    gonder(b, kod, "text/plain", m, ek);
  }

  function json(b, nesne) {
    gonder(b, 200, "application/json", JSON.stringify(nesne));
  }

  function red(b, m) {                           // guv__red
    durum.ret401 += 1;
    metin(b, 401, m, { "X-Acilis": durum.acilis });
  }

  function arg(b, ad) {
    const a = b.args.find(([x]) => x === ad);
    return a ? a[1] : "";
  }

  function argVar(b, ad) {
    return b.args.some(([x]) => x === ad);
  }

  function hostGecerli(b) {
    let h = String(b.istek.headers.host || "");
    const k = h.indexOf(":");
    if (k >= 0) h = h.slice(0, k);
    const ip = String(b.istek.socket.localAddress || "").replace(/^::ffff:/, "");
    return h === ip || h.toLowerCase() === "olcum.local" || h.toLowerCase() === "olcum";
  }

  function hostRed(b) {
    metin(b, 403, "Host reddedildi");
  }

  function olcumBasligi(b) {
    if (b.istek.headers["x-olcum"] === "1") return true;
    metin(b, 400, "X-Olcum basligi gerekli");
    return false;
  }

  // ── kapi ───────────────────────────────────────────────────────────────
  function dogrula(b) {
    const h = b.istek.headers;
    const basliktan = h["x-imza"] !== undefined;
    const cs = basliktan ? String(h["x-cihaz"] ?? "") : arg(b, "_c");
    const ss = basliktan ? String(h["x-sayac"] ?? "") : arg(b, "_s");
    const is = basliktan ? String(h["x-imza"]) : arg(b, "_i");
    if (b.post && String(h["content-type"] || "").includes("x-www-form-urlencoded")) {
      metin(b, 400, "imzali istek form kodlamali olamaz (text/plain gonder)");
      return false;
    }
    const n = /^\d{1,3}$/.test(cs) ? Number(cs) : 0;
    const sayac = /^\d{1,20}$/.test(ss) ? BigInt(ss) : 0n;
    const cihaz = durum.cihazlar.get(n);
    if (!cihaz) {
      red(b, "imza: cihaz kayitli degil");
      return false;
    }
    const args = b.args.filter(([a]) => a !== "plain" && a !== "_c" && a !== "_s" && a !== "_i");
    if (!imzaDogru(cihaz.K, b.post ? "POST" : "GET", b.yol, args, durum.acilis, sayac, b.post ? b.govde : Buffer.alloc(0), is)) {
      red(b, "imza gecersiz (acilis degistiyse /eslestir/bilgi)");
      return false;
    }
    if (!pencereler.has(n)) pencereler.set(n, pencereYeni());
    if (!pencereKabul(pencereler.get(n), sayac)) {
      red(b, "imza: sayac tekrar ya da cok eski");
      return false;
    }
    cihaz.son = unix();
    durum.imzali += 1;
    b.imzali = n;
    return true;
  }

  function kapi(b, sinif) {
    b.imzali = 0;
    if (b.istek.headers["x-imza"] !== undefined || argVar(b, "_i")) return dogrula(b);
    if (sinif === ACIK) return true;
    if (sinif === CIHAZ) {
      red(b, "imza gerekli");
      return false;
    }
    if (!ayar.zorunlu) return true;
    if (sinif === IZLEME && ayar.misafir) return true;
    if (sinif === KOMUT) return true;            // isleyici: p0 ve ? serbest
    red(b, "imza gerekli (zorunluluk yalniz USB'den Ez0 ile kapanir)");
    return false;
  }

  // ── uclar ──────────────────────────────────────────────────────────────
  function kok(b) {
    if (!kapi(b, ACIK)) return;
    metin(b, 200, "Olcum Karti — sahte kart (sinama)\n");
  }

  function eslestirBilgi(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, ACIK)) return;
    json(b, {
      surum: "OK1", kimlik: ayar.kimlik, acilis: durum.acilis, tuz: tuz.toString("hex"), tur: ayar.tur,
      zorunlu: ayar.zorunlu, misafir: ayar.misafir, saat: ayar.saatKaynak, cihaz_azami: CIHAZ_AZAMI,
    });
  }

  function eslestirBaslat(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, ACIK)) return;
    if (!olcumBasligi(b)) return;
    const ncHex = arg(b, "nc");
    if (!/^[0-9a-fA-F]{32}$/.test(ncHex)) return metin(b, 400, "nc: 32 hex karakter");
    const ad = arg(b, "ad");
    if (!P()) return metin(b, 403, "web parolasi yok ya da 12 karakterden kisa");
    if (!adGecerli(ad)) return metin(b, 400, "ad 1-24 bayt olmali, kontrol karakteri yok");
    const simdi = saat();
    if (denemeVar && simdi < serbestMs) {
      const kalan = serbestMs - simdi;
      return metin(b, 429, "cok fazla yanlis deneme — Retry-After kadar bekle",
        { "Retry-After": String(kalan > 0 ? Math.floor((kalan + 999) / 1000) : 1) });
    }
    if (!bosNumara()) return metin(b, 409, "cihaz listesi dolu (8) — USB'den Ex<n> ile sil");
    eno = (eno + 1) & 0xff || 1;
    bekleyen = { eno, nk: randomBytes(16), nc: Buffer.from(ncHex, "hex"), ad, bas: simdi };   // oncekinin YERINE
    json(b, { eno, nk: bekleyen.nk.toString("hex") });
  }

  function eslestirKanit(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, ACIK)) return;
    if (!olcumBasligi(b)) return;
    const kanitHex = arg(b, "kanit");
    if (!/^[0-9a-fA-F]{64}$/.test(kanitHex)) return metin(b, 400, "kanit: 64 hex karakter");
    const istenen = Number.parseInt(arg(b, "eno"), 10) & 0xff;
    const yok = () => metin(b, 410, "bekleyen eslestirme yok ya da 60 s gecti — bastan basla");
    if (!bekleyen || istenen !== bekleyen.eno) return yok();
    const simdi = saat();
    if (simdi - bekleyen.bas > ESLES_SURE_MS) {
      bekleyen = null;
      return yok();
    }
    const p = P();
    if (!p) return metin(b, 403, "web parolasi yok ya da 12 karakterden kisa");
    const e = bekleyen;
    bekleyen = null;                             // her bekleyen icin TEK deneme
    if (!baytEsit(kanitIstemci(p, ayar.kimlik, e.nk, e.nc, e.ad), Buffer.from(kanitHex, "hex"))) {
      denemeVar = true;
      serbestMs = simdi + (1000 << denemeK) * beklemeOlcek;
      if (denemeK < BEKLE_AZAMI_K) denemeK += 1;
      return metin(b, 403, "kanit yanlis (parola?)");
    }
    denemeVar = false;
    denemeK = 0;
    const n = bosNumara();
    if (!n) return metin(b, 409, "cihaz listesi dolu (8) — USB'den Ex<n> ile sil");
    const K = anahtarTuret(p, ayar.kimlik, e.nk, e.nc, n);
    durum.cihazlar.set(n, { K, ad: e.ad, eklenme: unix(), son: unix() });
    pencereler.set(n, pencereYeni());
    json(b, { n, kart_kanit: kanitKart(p, ayar.kimlik, e.nk, e.nc, n).toString("hex") });
  }

  function cihazListe(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, CIHAZ)) return;
    const cihazlar = [];
    for (let n = 1; n <= CIHAZ_AZAMI; n++) {
      const c = durum.cihazlar.get(n);
      if (c) cihazlar.push({ n, ad: c.ad, eklenme: c.eklenme, son: c.son });   // anahtar ASLA yanita girmez
    }
    json(b, { cihazlar });
  }

  function cihazSil(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, CIHAZ)) return;
    if (!olcumBasligi(b)) return;
    const n = Number.parseInt(arg(b, "n"), 10) || 0;
    if (n < 1 || n > CIHAZ_AZAMI) return metin(b, 400, "n: 1..8");
    if (!durum.cihazlar.delete(n)) return metin(b, 404, "silinemedi");
    pencereler.delete(n);
    metin(b, 204, "");
  }

  function saatUcu(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, CIHAZ)) return;
    if (!olcumBasligi(b)) return;
    if (ayar.saatNtp) return metin(b, 409, "kartin NTP saati var — cihaz saati kullanilmaz");
    const u = Number.parseInt(arg(b, "unix"), 10) || 0;
    if (u < 1700000000) return metin(b, 400, "unix >= 1700000000 olmali");
    ayar.saatKaynak = 2;
    durum.saat = u;
    metin(b, 204, "");
  }

  function bildirimBilgi(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, CIHAZ)) return;
    if (!ayar.bildirim) return metin(b, 404, "bildirim ayarlanmamis (USB: Qu, Qc, Qd, Q1)");
    const K = durum.cihazlar.get(b.imzali).K;
    const { u, k, p, o, a } = ayar.bildirim;
    // zarfKur'un `konu`su AAD'dir: "OK1-bildirim\n<kimlik>\n<n>"
    gonder(b, 200, "application/octet-stream",
      zarfKur(new Uint8Array(K), `OK1-bildirim\n${ayar.kimlik}\n${b.imzali}`, { u, k, p, o, a }));
  }

  function sonrakiSira() {
    return kayitlar.reduce((m, k) => Math.max(m, k.sira), 0) + 1;
  }

  function kayitListe(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, OKUMA)) return;
    const oturumlar = new Map();
    for (const k of kayitlar) {
      if (!k.oturum) continue;                   // NOT kayitlari (oturum 0) dizine girmez
      const o = oturumlar.get(k.oturum);
      if (!o) {
        oturumlar.set(k.oturum, {
          id: k.oturum, tur: 1, hiz_ms: 0, unix_s: 0, kart_ms: 0, acilis: 1, ilk: k.sira, son: k.sira,
          nokta: 0, durum: 0, basi_silindi: 0,
        });
      } else {
        o.son = k.sira;
      }
    }
    const bayt = kayitlar.reduce((t, k) => t + k.ham.length, 0);
    json(b, {
      surum: 2, durum: 1, sektor: 2784, sektor_bayt: KAYIT_SEKTOR, sonraki: sonrakiSira(), onay,
      doluluk_binde: Math.min(1000, Math.floor((bayt * 1000) / (2784 * KAYIT_SEKTOR))), onaysiz_binde: 0,
      aktif: 0, acilis: 1, unix: unix(), kimlik: ayar.kayitKimlik, temiz_kalan: 0,
      oturumlar: Array.from(oturumlar.values()),
    });
  }

  function kayitVeri(b) {                        // kg_oku: `sira` ve sonrasi, kayit BOLUNMEDEN `bayt`a kadar
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, OKUMA)) return;
    const sira = argVar(b, "sira") ? Number.parseInt(arg(b, "sira"), 10) || 1 : 1;
    let kap = argVar(b, "bayt") ? Number.parseInt(arg(b, "bayt"), 10) || 0 : KAYIT_VERI_AZAMI;
    if (kap > KAYIT_VERI_AZAMI) kap = KAYIT_VERI_AZAMI;
    const parcalar = [];
    let n = 0, ilk = 0, son = 0;
    for (const k of kayitlar) {
      if (k.sira < sira) continue;
      if (n + k.ham.length > kap) break;
      parcalar.push(k.ham);
      n += k.ham.length;
      if (!ilk) ilk = k.sira;
      son = k.sira;
    }
    gonder(b, 200, "application/octet-stream", Buffer.concat(parcalar), {
      "X-Kayit-Kimlik": String(ayar.kayitKimlik), "X-Ilk-Sira": String(ilk), "X-Son-Sira": String(son),
      "X-Sonraki-Sira": String(sonrakiSira()), "X-Onay": String(onay),
    });
  }

  function kalListe(b) {
    if (!hostGecerli(b)) return hostRed(b);
    if (!kapi(b, OKUMA)) return;
    if (!ayar.kalListe) return metin(b, 503, "kalibrasyon gecmisi yok");
    json(b, ayar.kalListe);
  }

  function komutSerbest(k) {                     // tam esleme: `?x` ya da `p0!` gecmez
    return k === "p0" || k === "?";
  }

  function komut(b) {
    if (!hostGecerli(b)) return metin(b, 403, "Host reddedildi (DNS rebinding korumasi)");
    if (!kapi(b, KOMUT)) return;
    if (!olcumBasligi(b)) return;
    const k = b.govde.toString("utf8").trim();
    if (!k.length) return metin(b, 400, "bos komut");
    if (Buffer.byteLength(k, "utf8") >= KOMUT_AZAMI) return metin(b, 413, "komut cok uzun (en fazla 175 karakter)");
    if (k[0] === "E") return metin(b, 403, "E komutlari yalniz USB seri konsoldan");
    if (k[0] === "Q") return metin(b, 403, "Q komutlari yalniz USB seri konsoldan");
    if (!b.imzali && !komutSerbest(k)) {
      if (ayar.zorunlu) return red(b, "imza gerekli (zorunlu) — p0 ve ? serbest");
      if (b.istek.headers["x-jeton"] !== jeton) {
        return metin(b, 403, "gecersiz oturum jetonu. `p0` (durdur) ve `?` serbest.");
      }
      const beklenen = "Basic " + Buffer.from(`olcum:${ayar.parola}`, "utf8").toString("base64");
      if (ayar.parola && b.istek.headers.authorization !== beklenen) {
        return metin(b, 401, "", { "WWW-Authenticate": 'Basic realm="Login Required"' });
      }
    }
    durum.komutlar.push(k);
    const go = /^Go(\d+)$/.exec(k);              // esitleme onayi: yalniz ileri, var olan siraya
    if (go && Number(go[1]) < sonrakiSira() && Number(go[1]) > onay) onay = Number(go[1]);
    metin(b, 204, "");                           // govde BOS: kartin cevabi SSE'den gelir
  }

  function akis(b) {                             // kartta Host denetimi YOK
    if (!kapi(b, IZLEME)) return;
    const y = b.yanit;
    y.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
    if (ayar.yarimYanit) {
      b.istek.socket.destroy();
      return;
    }
    if (akislar.size >= AKIS_AZAMI) {            // sessiz kapanma yok
      y.end(`event: dolu\ndata: ${AKIS_AZAMI}\n\n`);
      return;
    }
    akislar.add(y);
    durum.akisAcik = akislar.size;
    y.on("close", () => {
      akislar.delete(y);
      durum.akisAcik = akislar.size;
    });
    y.write("retry: 3000\n\n");
    y.write(`event: kimlik\ndata: {"jeton":"${jeton}","surucu":true}\n\n`);
  }

  const UCLAR = new Map([
    ["/", [null, kok]],
    ["/akis", [null, akis]],
    ["/kayit/liste", [null, kayitListe]],
    ["/kayit/veri", [null, kayitVeri]],
    ["/kal/liste", [null, kalListe]],
    ["/eslestir/bilgi", ["GET", eslestirBilgi]],
    ["/eslestir/baslat", ["POST", eslestirBaslat]],
    ["/eslestir/kanit", ["POST", eslestirKanit]],
    ["/cihaz/liste", ["GET", cihazListe]],
    ["/cihaz/sil", ["POST", cihazSil]],
    ["/saat", ["POST", saatUcu]],
    ["/bildirim/bilgi", ["GET", bildirimBilgi]],
    ["/komut", ["POST", komut]],
  ]);

  async function isle(istek, yanit) {
    const govde = await govdeOku(istek);
    const ham = String(istek.url || "/");
    const s = ham.indexOf("?");
    const b = {
      istek, yanit, govde, imzali: 0, post: istek.method === "POST",
      yol: yuzdeCoz(s < 0 ? ham : ham.slice(0, s)), args: sorguAyir(s < 0 ? "" : ham.slice(s + 1)),
    };
    // WebServer form kodlamali govdeyi argumanlara karistirir (imzali istekte bu yuzden 400)
    if (b.post && String(istek.headers["content-type"] || "").includes("x-www-form-urlencoded")) {
      b.args.push(...sorguAyir(govde.toString("utf8")));
    }
    if (ayar.gecikmeMs > 0) await new Promise((r) => setTimeout(r, ayar.gecikmeMs));
    if (ayar.hata503 > 0) {
      ayar.hata503 -= 1;
      return metin(b, 503, "sahte kart: hata503");
    }
    const uc = UCLAR.get(b.yol);
    if (!uc || (uc[0] && uc[0] !== istek.method)) return metin(b, 404, `Not found: ${b.yol}`);
    return uc[1](b);
  }

  const sunucu = http.createServer((istek, yanit) => {
    isle(istek, yanit).catch(() => yanit.destroy());
  });
  sunucu.on("connection", (s) => {
    soketler.add(s);
    s.on("close", () => soketler.delete(s));
  });

  // D satiri: kartin bicimi "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u %u"
  //   volt amper watt joule wh millis ornek menzil adc_hata
  const dZamanlayici = setInterval(() => {
    akisSira += 1;
    const ms = Math.max(0, Math.floor(saat() - acilisMs));
    const v = 12 + 0.05 * Math.sin(akisSira / 7), i = 0.5 + 0.01 * Math.cos(akisSira / 5), w = v * i;
    enerjiJ += (w * akisAralikMs) / 1000;
    const satir = `D ${v.toFixed(4)} ${i.toFixed(6)} ${w.toFixed(5)} ${enerjiJ.toFixed(4)} ${(enerjiJ / 3600).toFixed(7)} `
      + `${ms} ${Math.max(1, Math.round(akisAralikMs / 2))} 0 0`;
    for (const y of akislar) y.write(`id: ${akisSira}\ndata: ${satir}\n\n`);
  }, akisAralikMs);
  const kalpZamanlayici = setInterval(() => {
    for (const y of akislar) y.write(": kalp\n\n");
  }, 15000);
  dZamanlayici.unref();
  kalpZamanlayici.unref();

  await new Promise((coz, reddet) => {
    sunucu.once("error", reddet);
    sunucu.listen(port, host, coz);
  });
  const gercekPort = sunucu.address().port;

  function ayarla(parca) {
    for (const [a, v] of Object.entries(parca)) {
      if (a === "yenidenBasla") {
        if (v) acilisYenile();
      } else if (a === "kayitlar") {
        kayitlar = kayitlariAyir(v);
        onay = Math.min(onay, sonrakiSira() - 1);
      } else if (a === "zorunlu" || a === "misafir") {
        ayar[a] = v ? 1 : 0;
      } else if (Object.hasOwn(ayar, a)) {
        ayar[a] = v;
      } else {
        throw new Error(`sahte kart: bilinmeyen ayar '${a}'`);
      }
    }
  }

  function kapat() {
    clearInterval(dZamanlayici);
    clearInterval(kalpZamanlayici);
    return new Promise((coz) => {
      sunucu.close(() => coz());
      for (const s of soketler) s.destroy();
    });
  }

  const yerel = host === "0.0.0.0" || host === "::" ? "127.0.0.1" : host;
  return { port: gercekPort, taban: `http://${yerel}:${gercekPort}`, kapat, durum, ayarla };
}

// ── komut satiri ─────────────────────────────────────────────────────────
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const a = process.argv.slice(2);
  const al = (ad, varsayilan) => (a.includes(ad) ? a[a.indexOf(ad) + 1] : varsayilan);
  const kart = await sahteKartAc({ port: Number(al("--port", "18080")), host: al("--host", "127.0.0.1") });
  console.log(kart.port);
}
