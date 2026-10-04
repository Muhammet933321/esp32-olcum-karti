// Karti bulma (tasarim A1–A3). Adaylar ESZAMANLI yoklanir; her aday `/eslestir/bilgi` ile kimligini
// soyler. Hicbir akis NSD'ye bagimli degildir: eklenti yoksa / bos donerse oteki adaylar yeter.
//
//   const k = kesifKur({ kartFetch, onbellek, eklenti, yerelDongu });
//   const s = await k.bul({ beklenenKimlik, elle });
//   -> { adres, kimlik, bilgi, kaynak, sureMs, txtKimlik, denenenler }   | KesifHatasi(tur, denenenler)
//
// kaynak: "elle" | "onbellek" | "ad" | "nsd" | "ap".   tur: "bulunamadi" | "kimlik-uymuyor".
// Elle girilen adres hedef kuralindan gecmezse HedefHatasi (istek ATILMAZ).

import { hedefAyir, hedefYazi } from "./hedef.js";

export const KIMLIK_DESENI = /^[0-9a-f]{16}$/;
export const SABIT_ADAYLAR = Object.freeze([
  Object.freeze({ adres: "olcum.local", kaynak: "ad" }),
  Object.freeze({ adres: "192.168.4.1", kaynak: "ap" }),       // kartin kendi erisim noktasi
]);
const AZAMI_BILGI = 4096;

export class KesifHatasi extends Error {
  constructor(tur, denenenler) {
    super(tur);
    this.name = "KesifHatasi";
    this.tur = tur;
    this.denenenler = denenenler;
  }
}

export function kesifKur({
  kartFetch, onbellek = null, eklenti = null, yerelDongu = false, zamanAsimiMs = 1500,
  nsdSureMs = 1200, sabitAdaylar = SABIT_ADAYLAR, simdi = Date.now,
}) {
  if (typeof kartFetch !== "function") throw new TypeError("kartFetch gerekli");

  // Bir adayi yokla -> { adres (IP:port — eklentinin baglandigi), kimlik, bilgi } | hata turu (metin).
  async function yokla(aday) {
    let y;
    try {
      y = await kartFetch(`http://${aday.adres}/eslestir/bilgi`, { method: "GET", headers: {}, zamanAsimiMs, azamiGovde: AZAMI_BILGI });
    } catch (e) {
      return { ...aday, sonuc: typeof e?.tur === "string" ? e.tur : "ic-hata" };
    }
    if (y.status !== 200) return { ...aday, sonuc: "yanit-gecersiz" };
    let b;
    try { b = await y.json(); } catch { return { ...aday, sonuc: "yanit-gecersiz" }; }
    if (b === null || typeof b !== "object" || typeof b.kimlik !== "string" || !KIMLIK_DESENI.test(b.kimlik)) {
      return { ...aday, sonuc: "yanit-gecersiz" };
    }
    // Onbellege ad degil, baglanilan IP yazilir (A3). Eklenti soylemezse adayin kendi adresi.
    let adres = aday.adres;
    if (typeof y.adres === "string") {
      try { adres = hedefYazi(hedefAyir(y.adres, { yerelDongu })); } catch { /* adayin adresi kalir */ }
    }
    return { ...aday, adres, sonuc: "tamam", kimlik: b.kimlik, bilgi: b };
  }

  async function nsdAdaylari(beklenenKimlik) {
    if (!eklenti || typeof eklenti.nsdTara !== "function") return [];
    let bulunan;
    try { bulunan = (await eklenti.nsdTara({ sureMs: nsdSureMs }))?.servisler; } catch { return []; }
    if (!Array.isArray(bulunan)) return [];
    const cikti = [];
    for (const s of bulunan.slice(0, 8)) {
      if (!s || typeof s.ip !== "string" || !Number.isInteger(s.port)) continue;
      let adres;
      try { adres = hedefYazi(hedefAyir(`${s.ip}:${s.port}`, { yerelDongu })); } catch { continue; }
      const txtKimlik = typeof s.kimlik === "string" && KIMLIK_DESENI.test(s.kimlik) ? s.kimlik : null;
      // TXT'deki kimlik yalnizca ELEME icindir (bos istek atmamak); dogrulama yine /eslestir/bilgi.
      if (beklenenKimlik && txtKimlik && txtKimlik !== beklenenKimlik) continue;
      cikti.push({ adres, kaynak: "nsd", txtKimlik });
    }
    return cikti;
  }

  function sabitler({ elle }) {
    const liste = [];
    if (elle != null && elle !== "") liste.push({ adres: hedefYazi(hedefAyir(elle, { yerelDongu })), kaynak: "elle" });
    const kayit = onbellek ? onbellek.oku() : null;
    if (kayit && typeof kayit.adres === "string") {
      try { liste.push({ adres: hedefYazi(hedefAyir(kayit.adres, { yerelDongu })), kaynak: "onbellek" }); } catch { /* bozuk kayit */ }
    }
    for (const a of sabitAdaylar) liste.push({ ...a });
    return liste;
  }

  async function bul({ beklenenKimlik = null, elle = null } = {}) {
    const t0 = simdi();
    const ilk = sabitler({ elle });                       // HedefHatasi burada atilir, istekten ONCE
    const denenenler = [];
    const gorulen = new Set();
    const uygun = (s) => s.sonuc === "tamam" && (!beklenenKimlik || s.kimlik === beklenenKimlik);

    const sonuc = await new Promise((coz) => {
      let bekleyen = 0;
      let bitti = false;
      let elleBekliyor = ilk.some((a) => a.kaynak === "elle") && !beklenenKimlik;
      let yedek = null;                                   // elle'yi beklerken gelen ilk uygun
      const kapat = (s) => { if (!bitti) { bitti = true; coz(s); } };
      const baslat = (aday) => {
        if (gorulen.has(aday.adres)) return;
        gorulen.add(aday.adres);
        bekleyen++;
        yokla(aday).then((s) => {
          denenenler.push({ adres: s.adres, kaynak: s.kaynak, sonuc: s.sonuc, kimlik: s.kimlik ?? null });
          if (s.kaynak === "elle") {
            elleBekliyor = false;
            if (uygun(s)) kapat(s); else if (yedek) kapat(yedek);
          } else if (uygun(s)) {
            if (elleBekliyor) yedek = yedek || s; else kapat(s);
          }
          if (--bekleyen === 0) kapat(yedek);
        });
      };
      bekleyen++;                                         // NSD taramasi da bir "bekleyen"
      for (const a of ilk) baslat(a);
      nsdAdaylari(beklenenKimlik).then((nsd) => {
        for (const a of nsd) baslat(a);
        if (--bekleyen === 0) kapat(yedek);
      });
    });

    if (!sonuc) {
      const yanlis = denenenler.some((d) => d.sonuc === "tamam");
      throw new KesifHatasi(yanlis ? "kimlik-uymuyor" : "bulunamadi", denenenler);
    }
    if (onbellek) onbellek.yaz({ adres: sonuc.adres, kimlik: sonuc.kimlik, ms: simdi() });
    return {
      adres: sonuc.adres, kimlik: sonuc.kimlik, bilgi: sonuc.bilgi, kaynak: sonuc.kaynak,
      txtKimlik: sonuc.txtKimlik ?? null, sureMs: simdi() - t0, denenenler,
    };
  }

  return { bul };
}

// localStorage sarmalayicisi (5A). Bozuk kayit = kayit yok.
export function yerelOnbellek(depo, anahtar = "kart.son") {
  return {
    oku() {
      try {
        const k = JSON.parse(depo.getItem(anahtar));
        return k && typeof k.adres === "string" && typeof k.kimlik === "string" ? k : null;
      } catch { return null; }
    },
    yaz(kayit) { try { depo.setItem(anahtar, JSON.stringify(kayit)); } catch { /* dolu */ } },
  };
}
