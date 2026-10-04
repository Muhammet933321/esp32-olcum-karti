// Karti bulma (tasarim A1–A3). Adaylar ESZAMANLI yoklanir; her aday `/eslestir/bilgi` ile kimligini
// soyler. Hicbir akis NSD'ye bagimli degildir: eklenti yoksa / bos donerse oteki adaylar yeter.
//
//   const k = kesifKur({ kartFetch, onbellek, eklenti, yerelDongu });
//   const s = await k.bul({ beklenenKimlik, elle });
//   -> { adres, kimlik, bilgi, kaynak, sureMs, txtKimlik, denenenler }   | KesifHatasi(tur, denenenler)
//
// kaynak: "elle" | "onbellek" | "ad" | "nsd" | "ap".   tur: "bulunamadi" | "kimlik-uymuyor".
// Elle girilen adres hedef kuralindan gecmezse HedefHatasi (istek ATILMAZ).

import { sureli } from "./ag.js";
import { hedefAyir, hedefYazi } from "./hedef.js";

export const KIMLIK_DESENI = /^[0-9a-f]{16}$/;
export const SABIT_ADAYLAR = Object.freeze([
  Object.freeze({ adres: "olcum.local", kaynak: "ad" }),
  Object.freeze({ adres: "192.168.4.1", kaynak: "ap" }),       // kartin kendi erisim noktasi
]);
const AZAMI_BILGI = 4096;
export const NSD_AZAMI_KAYIT = 64;       // eklentiden okunan duyuru (sel korumasi)
export const NSD_AZAMI_ADAY = 8;         // siralamadan SONRA yoklanan aday
// Duyuru taramasi EN AZ 3 s (kullanici karari 2026-10-04): 1.2 s'lik pencerede kartin duyurusu kacabiliyordu
// (telefonda goruldu: ad cozulemedi, son bilinen adres yanit vermedi, NSD adayi hic gelmedi; kart saglamdi).
// Basari bu sureyi BEKLEMEZ: uygun ilk aday yanit verince arama biter.
export const NSD_SURE_MS = 3000;
const NSD_PAYI_MS = 1000;
const TOPLAM_PAYI_MS = 700;           // kartFetch'in kendi payindan (500) buyuk olmali

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
  nsdSureMs = NSD_SURE_MS, sabitAdaylar = SABIT_ADAYLAR, simdi = Date.now,
  yenidenDene = 1, yenidenBekleMs = 300,
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
    // Tarama eklentide hic donmezse de kesif asili kalmaz.
    try { bulunan = (await sureli(eklenti.nsdTara({ sureMs: nsdSureMs }), nsdSureMs + NSD_PAYI_MS))?.servisler; } catch { return []; }
    if (!Array.isArray(bulunan)) return [];
    const adaylar = new Map();                            // adres -> aday (ayni adres bir kez)
    for (const s of bulunan.slice(0, NSD_AZAMI_KAYIT)) {
      if (!s || typeof s.ip !== "string" || !Number.isInteger(s.port)) continue;
      let adres;
      try { adres = hedefYazi(hedefAyir(`${s.ip}:${s.port}`, { yerelDongu })); } catch { continue; }
      const txtKimlik = typeof s.kimlik === "string" && KIMLIK_DESENI.test(s.kimlik) ? s.kimlik : null;
      const onceki = adaylar.get(adres);
      // Ayni adres icin kimligi uyan duyuru, uymayani ezer (tersi olmaz).
      if (!onceki || (beklenenKimlik && txtKimlik === beklenenKimlik)) adaylar.set(adres, { adres, kaynak: "nsd", txtKimlik });
    }
    // TXT kimligi DOGRULANMAMIS bir ipucudur: uymayan duyuru ELENMEZ (saldirgan gercek kartin adresini
    // yanlis kimlikle duyurup karti gizleyebilirdi — curutucu 5A-7, K4). Yalnizca SIRALAMADA kullanilir:
    // kimligi uyanlar once, sonra kimliksizler, en sonda uymayanlar; yoklanan aday sayisi sinirlidir.
    const puan = (a) => (!beklenenKimlik || a.txtKimlik === beklenenKimlik ? 0 : a.txtKimlik === null ? 1 : 2);
    return [...adaylar.values()].sort((a, b) => puan(a) - puan(b)).slice(0, NSD_AZAMI_ADAY);
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

  // Tek tur: adaylar + duyuru taramasi. -> { sonuc | null, denenenler }
  async function turAt({ beklenenKimlik, ilk }) {
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
        // Yoklamanin kendi suresi (kartFetch'inkine ek): hicbir aday yarisi asili birakamaz.
        sureli(yokla(aday), zamanAsimiMs + TOPLAM_PAYI_MS).catch(() => ({ ...aday, sonuc: "zaman-asimi" })).then((s) => {
          // Ayni karta iki yoldan (ad + IP) varildiysa listede bir kez gorunur.
          if (!(s.sonuc === "tamam" && denenenler.some((d) => d.sonuc === "tamam" && d.adres === s.adres))) {
            denenenler.push({ adres: s.adres, kaynak: s.kaynak, sonuc: s.sonuc, kimlik: s.kimlik ?? null });
          }
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

    return { sonuc, denenenler };
  }

  async function bul({ beklenenKimlik = null, elle = null } = {}) {
    const t0 = simdi();
    const ilk = sabitler({ elle });                       // HedefHatasi burada atilir, istekten ONCE
    let { sonuc, denenenler } = await turAt({ beklenenKimlik, ilk });
    // HICBIR aday kart olarak yanit vermediyse "bulunamadi" demeden once BIR KEZ daha denenir (gecici
    // ag takilmasi, kacan duyuru). Bir kart yanit verip kimligi uymadiysa yeniden denenmez: sonuc degismez.
    for (let i = 0; i < yenidenDene && !sonuc && !denenenler.some((d) => d.sonuc === "tamam"); i++) {
      await new Promise((coz) => setTimeout(coz, yenidenBekleMs));
      ({ sonuc, denenenler } = await turAt({ beklenenKimlik, ilk }));
    }
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
