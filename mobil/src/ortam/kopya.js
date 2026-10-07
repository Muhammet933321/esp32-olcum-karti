// Telefondaki kayit kopyasi panelin gozunden (5P K10): panelin EsitlemeDenetcisi 'telefon' kaynagi.
// Kopya kart basina `files/kart/<kart kimligi>/` (cekirdek/depo.js; PC ile ayni dosyalar), icinde TEK
// kayit akisi (durum.json `kimlik` = kartin /kayit/liste `kimlik`i). Panel akislari AKIS kimligiyle tanir.
//
//   await k.akislar()              -> [{ kimlik, kart, bayt, durum, olusma, guncelleme, kalVar, telefon: true }]
//   await k.depo(akisKimlik)       -> salt okunur DEPO (esitle.js sozlesmesinin okuma yarisi) + `kart`
//   await k.esitle({ kimlik, ilerleme }) -> { durum: "tamam", sonuc: { yeni_kayit, son_sira, ... }, bayt }
//                                     | { durum, mesaj, bayt }   (panelin EsitlemeDenetcisi.esitle bicimi)
//
// Eslesmeyi Android eşitleyicisi yurutur (TEK eşitleyici, tek kopya; cekirdek/esitleme.js): `esitle` onun
// `simdi()`sini cagirir (suren tura baglanir). "Bu telefon da onaylar" ayari (A21) orada okunur; panelin
// onay islevi burada KULLANILMAZ. Hangi kartlarin kopyasi oldugu: bagli kart + son baglanilan kart (eklenti
// dizin listelemez). Olusma / guncelleme anlari yerel depoda (sir degil) tutulur.

import { dilSec, metin } from "./metin.js";

export const ZAMAN_ANAHTARI = "olcum.telefon.kopya";
export const YOKLA_MS = 1000;
const KIMLIK = /^[0-9a-f]{16}$/;

// Android eşitleyicisinin hata turu -> panelin esitleme sonucu `durum`u (ekran/esitleme.js hataSinifla).
export const HATA_DURUMU = Object.freeze({
  "kopya-uyusmuyor": "akis",
  "yanit-bozuk": "bozuk",
  mesgul: "kilit",
  depo: "depo",
  "depo-bozuk": "depo",
  "cihaz-silinmis": "imza",
  eslesmemis: "imza",
  "kimlik-uymuyor": "imza",
  http: "hata",
  ag: "ag",
  "bagli-degil": "ag",
});

function zamanlariOku(depo) {
  try {
    const v = JSON.parse(depo.getItem(ZAMAN_ANAHTARI));
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  } catch { return {}; }
}

function zamanlariYaz(depo, v) {
  try { depo.setItem(ZAMAN_ANAHTARI, JSON.stringify(v)); } catch { /* depo kapali: bu oturumda gecerli */ }
}

export function kopyaKur({
  kartAl, depoAl, esitlemeAl, arka = null, sonKimlik = () => null, yerel = null, dilAl = () => "tr",
  simdiMs = Date.now, yoklaMs = YOKLA_MS, araliKur = (fn, ms) => setInterval(fn, ms), araliSil = (n) => clearInterval(n),
}) {
  if (typeof kartAl !== "function" || typeof depoAl !== "function" || typeof esitlemeAl !== "function") {
    throw new TypeError("kartAl, depoAl ve esitlemeAl gerekli");
  }
  const harita = new Map();             // akis kimligi -> kart kimligi (son akislar() listesinden)
  let bellek = null;                    // yerel depo yoksa zamanlar bellekte
  let izleniyor = false;

  const zamanlar = () => (yerel ? zamanlariOku(yerel) : (bellek || (bellek = {})));
  const zamanYaz = (v) => { if (yerel) zamanlariYaz(yerel, v); else bellek = v; };

  function zamanAl(kart) {
    const z = zamanlar();
    const k = z[kart];
    if (k && Number.isFinite(k.olusma)) return { olusma: k.olusma, guncelleme: Number.isFinite(k.guncelleme) ? k.guncelleme : k.olusma };
    const t = simdiMs();
    z[kart] = { olusma: t, guncelleme: t };
    zamanYaz(z);
    return { olusma: t, guncelleme: t };
  }

  function guncellemeYaz(kart) {
    if (typeof kart !== "string" || !KIMLIK.test(kart)) return;
    const z = zamanlar();
    const t = simdiMs();
    z[kart] = { olusma: z[kart] && Number.isFinite(z[kart].olusma) ? z[kart].olusma : t, guncelleme: t };
    zamanYaz(z);
  }

  async function bagliKart() {
    try {
      const d = (await kartAl()).durum();
      return d && d.durum === "bagli" && typeof d.kimlik === "string" && KIMLIK.test(d.kimlik) ? d.kimlik : null;
    } catch { return null; }
  }

  // Arka plandaki eşitleme turlari da "guncelleme" anini tazeler (bir kez baglanir).
  function izle() {
    if (izleniyor) return;
    izleniyor = true;
    Promise.resolve().then(esitlemeAl).then((e) => {
      e.dinle((h) => { if (h && h.hal === "tamam") bagliKart().then(guncellemeYaz); });
    }).catch(() => { izleniyor = false; });
  }

  async function adaylar() {
    const liste = [];
    try {
      const d = (await kartAl()).durum();
      if (d && typeof d.kimlik === "string" && KIMLIK.test(d.kimlik)) liste.push(d.kimlik);
    } catch { /* kart nesnesi yok */ }
    let s = null;
    try { s = sonKimlik(); } catch { s = null; }
    if (typeof s === "string" && KIMLIK.test(s) && !liste.includes(s)) liste.push(s);
    return liste;
  }

  async function akislar() {
    izle();
    const cikti = [];
    harita.clear();
    for (const kart of await adaylar()) {
      const depo = depoAl(kart);
      let d = null;
      try {
        d = await depo.durumOku();
      } catch (e) {
        if (e && e.tur === "bozuk") continue;           // durum okunamiyor: akis kimligi bilinmez, listelenmez
        throw e;
      }
      if (!d || !Number.isSafeInteger(d.kimlik)) continue;   // bu kartin kopyasi yok (hic eşitlenmemis)
      const bayt = await depo.veriBoyu();
      let kalVar = false;
      try { const k = await depo.kalOku(); kalVar = Boolean(k) && k.length > 0; } catch { kalVar = false; }
      const z = zamanAl(kart);
      if (!harita.has(d.kimlik)) harita.set(d.kimlik, kart);
      cikti.push({ kimlik: d.kimlik, kart, bayt, durum: d, olusma: z.olusma, guncelleme: z.guncelleme, kalVar, telefon: true });
    }
    return cikti.sort((x, y) => (y.olusma || 0) - (x.olusma || 0));
  }

  function akisNo(kimlik) {
    if (typeof kimlik === "number") return kimlik;
    if (typeof kimlik === "string" && /^[0-9]{1,15}$/.test(kimlik)) return Number(kimlik);
    return NaN;
  }

  async function depo(kimlik) {
    const no = akisNo(kimlik);
    let kart = harita.get(no);
    if (!kart) { await akislar(); kart = harita.get(no); }
    if (!kart) throw new Error(metin("or.kopya_yok", dilSec(dilAl())));
    const d = depoAl(kart);
    const saltOkuma = async () => { throw new Error(metin("or.kopya_salt_okuma", dilSec(dilAl()))); };
    // Panel YALNIZ okur. Yazma yollari bilerek yok (tek yazar Android eşitleyicisi).
    return Object.freeze({
      kart, telefon: true,
      veriBoyu: () => d.veriBoyu(),
      veriOku: (bas = 0) => d.veriOku(bas),
      durumOku: () => d.durumOku(),
      kalOku: () => d.kalOku(),
      boyutlar: () => d.boyutlar(),
      durumYaz: saltOkuma, veriEkle: saltOkuma, veriKirp: saltOkuma, kalYaz: saltOkuma, kalArsivle: saltOkuma, sifirla: saltOkuma,
    });
  }

  async function boyOku(d) {
    try { return await d.veriBoyu(); } catch { return null; }
  }

  async function esitle({ ilerleme = null } = {}) {
    const dil = dilSec(dilAl());
    izle();
    let e;
    try { e = await esitlemeAl(); } catch { return { durum: "depo", mesaj: metin("or.esitleme_yok", dil), bayt: 0 }; }
    if (arka) { try { await arka.baglan(); } catch { /* asagida bagli degil denir */ } }
    const kart = await bagliKart();
    if (kart === null) return { durum: "ag", mesaj: metin("or.bagli_degil", dil), bayt: 0 };
    const d = depoAl(kart);
    const bas = (await boyOku(d)) ?? 0;
    let son = bas;
    const bildir = (b) => {
      if (typeof ilerleme !== "function" || b === null || b <= son) return;
      son = b;
      try { ilerleme(b - bas); } catch { /* panelin hatasi eşitlemeyi etkilemez */ }
    };
    let yoklaniyor = false;
    const z = araliKur(() => {
      if (yoklaniyor) return;
      yoklaniyor = true;
      boyOku(d).then(bildir).finally(() => { yoklaniyor = false; });
    }, yoklaMs);
    let hal;
    try {
      hal = await e.simdi();
    } catch {
      hal = { hal: "hata", hata: "ic-hata" };
    } finally {
      araliSil(z);
    }
    const bitis = await boyOku(d);
    bildir(bitis);
    const bayt = Math.max(0, (bitis ?? son) - bas);
    if (hal && hal.hal === "tamam") {
      guncellemeYaz(kart);
      return {
        durum: "tamam",
        sonuc: {
          yeni_kayit: Number.isInteger(hal.yeni) ? hal.yeni : 0,
          son_sira: Number.isInteger(hal.sonSira) ? hal.sonSira : null,
          bekleyen: Number.isInteger(hal.bekleyen) ? hal.bekleyen : 0,
          bosluk_adet: Number.isInteger(hal.bosluk) ? hal.bosluk : 0,
          onayli: hal.onayli === true,
        },
        bayt,
      };
    }
    if (!hal || hal.hal !== "hata") return { durum: "kilit", mesaj: metin("or.esitleme_mesgul", dil), bayt };
    const tur = typeof hal.hata === "string" ? hal.hata : "ic-hata";
    const durum = HATA_DURUMU[tur] || "hata";
    const mesaj = durum === "akis" ? metin("or.akis_degisti", dil) : `${metin("or.esitleme_hata", dil)} (${tur})`;
    return { durum, mesaj, bayt, sifirlaOner: hal.sifirlaOner === true };
  }

  return { akislar, depo, esitle };
}
