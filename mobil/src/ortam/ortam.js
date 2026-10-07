// Telefon ortami nesnesi (5P, plan "Sozlesme: __olcumOrtam" surum 1). Panel (arayuz3/) bu nesneyi gorurse
// telefon kipine gecer ve YALNIZ asagidaki anahtarlari kullanir. Bagimliliklar enjekte: Node'da sahte kart
// + sahte eklentilerle sinanir (test/ortam_*.test.js); gercek baglama index.js'te.
//
//   const { ortam, arka } = ortamOlustur({ kartAl, canliAl, esitlemeAl, depoAl, bildirimIzle, izlemeSorusu,
//     pilOku, acilDurdur, paylas, yazdirEklenti, ayarBolumuYukle, belge, ... });
//   arka.baslat();     // arka plan isleri (K17) — index.js ortamKur() yapar

import { arkaPlanKur } from "./arka_plan.js";
import { dosyaKur } from "./dosya.js";
import { istekKur } from "./istek.js";
import { kopyaKur } from "./kopya.js";
import { metin } from "./metin.js";
import { soruKur } from "./soru.js";
import { tasiyiciKur } from "./tasiyici.js";

export const SURUM = 1;
// Sozlesmenin anahtarlari (plan). Panel bunlarin ALT kumesini kullanir (B7 iddiasi); fazlasi yok.
export const SOZLESME_ANAHTARLARI = Object.freeze([
  "ad", "surum", "tasiyici", "istek", "p0", "serit", "akislar", "depo", "esitle", "dosyaVer", "yazdir", "ayarBolumu", "komutGitti",
]);

export function ortamOlustur({
  kartAl, canliAl, esitlemeAl, depoAl, bildirimIzle = null, izlemeSorusu = null, pilOku = null,
  bildirimDil = null, acilDurdur, paylas, yazdirEklenti = null, ayarBolumuYukle = null,
  sonKimlik = () => null, yerel = null, belge = null, mesgulMu = () => false, ciz = () => {},
  simdiMs = Date.now, araliKur, araliSil,
}) {
  if (typeof acilDurdur !== "function") throw new TypeError("acilDurdur gerekli");
  // Panelin dili: app.js dilUygula() belgenin `lang`ini yazar (telefon kipinde de).
  const dilAl = () => (belge && belge.documentElement && belge.documentElement.lang === "en" ? "en" : "tr");
  const zaman = {};
  if (araliKur) zaman.araliKur = araliKur;
  if (araliSil) zaman.araliSil = araliSil;

  const arka = arkaPlanKur({
    kartAl, canliAl, esitlemeAl, bildirimIzle, pilOku, izlemeSorusu, bildirimDil, dilOku: dilAl, mesgulMu, belge, simdiMs, ...zaman,
  });

  // K8: ACIL DURDUR. ASLA reddetmez; true = kart 204 dedi (en az bir adres). Imza / baglanti BEKLENMEZ.
  async function p0() {
    try {
      const s = await acilDurdur();
      return Boolean(s) && s.tamam === true;
    } catch {
      return false;
    }
  }

  const tasiyici = tasiyiciKur({ arka, kartAl, p0 });
  const istek = istekKur({ arka, kartAl, p0, dilAl });
  const kopya = kopyaKur({ kartAl, depoAl, esitlemeAl, arka, sonKimlik, yerel, dilAl, simdiMs, ...zaman });
  const dosya = dosyaKur({ paylas, yazdirEklenti, belge, dilAl });
  const soru = izlemeSorusu ? soruKur({ izlemeSorusu, ciz }) : null;

  // K9: serit YALNIZ pil testinin surmedigi KESINSE gizli. Panelin bilgisi (true | false | null) ile
  // ortaminki (kartin /pil durumu + akisin tazeligi + etkin oturum turu) birlesir: biri "suruyor / bilinmiyor"
  // derse GORUNUR.
  function serit(pilSuruyor) {
    if (pilSuruyor === true) return true;
    try { return arka.seritGorunur() !== false; } catch { return true; }
  }

  // K13: "Bu telefon" bolumu (mobil/src/telefon/index.js `bolum()`), tembel yuklenir.
  async function ayarBolumu() {
    const yok = () => new Error(metin("or.bolum_yok", dilAl()));
    if (typeof ayarBolumuYukle !== "function") throw yok();
    const m = await ayarBolumuYukle();
    if (!m || typeof m.bolum !== "function") throw yok();
    return m.bolum();
  }

  function komutGitti(metin) {
    if (soru) soru.komutGitti(metin);
  }

  const ortam = Object.freeze({
    ad: "telefon",
    surum: SURUM,
    tasiyici,
    istek,
    p0,
    serit,
    akislar: () => kopya.akislar(),
    depo: (kimlik) => kopya.depo(kimlik),
    esitle: (secenek) => kopya.esitle(secenek || {}),
    dosyaVer: (d) => dosya.dosyaVer(d || {}),
    yazdir: () => dosya.yazdir(),
    ayarBolumu,
    komutGitti,
  });
  return { ortam, arka, soru };
}
