// Ayarlar › Bildirimler'in saf yardimcilari (DOM'suz sinanir).
import { SINIFLAR } from "../cekirdek/bildirim.js";

const IZLEME = {
  durduruldu: "m.bl.izleme_durduruldu", baglaniyor: "m.bl.izleme_baglaniyor", izleniyor: "m.bl.izleme_izleniyor",
  internet: "m.bl.izleme_internet", guven: "m.bl.izleme_guven", araci: "m.bl.izleme_araci",
  "kayit-bitti": "m.bl.izleme_kayit_bitti", ayar: "m.bl.izleme_ayar", "ic-hata": "m.bl.izleme_ic_hata",
};

// Sinif -> sozluk anahtari (acik yazili: sozluk testi her anahtarin kaynakta gectigini denetler).
const SINIF = {
  kopuk: "m.bl.sinif_kopuk", bitti: "m.bl.sinif_bitti", dolu: "m.bl.sinif_dolu", esik: "m.bl.sinif_esik",
  yeniden_basladi: "m.bl.sinif_yeniden_basladi", kacirilan: "m.bl.sinif_kacirilan", deneme: "m.bl.sinif_deneme",
};

const HATA = {
  "bagli-degil": "m.bl.hata_bagli_degil", eslesmemis: "m.bl.hata_bagli_degil", ag: "m.bl.hata_ag",
  "cihaz-silinmis": "m.bl.hata_silinmis", etiket: "m.bl.hata_zarf", icerik: "m.bl.hata_zarf", "anahtar-yok": "m.bl.hata_zarf",
  adres: "m.bl.hata_adres",
};

// Pil yoneticisi yonergesi (A37): Android'in pil muafiyeti YETMEYEBILIR — bazi ureticilerin kendi pil yoneticisi
// arka plandaki uygulamayi yine de kapatir. Adimlar ureticiye gore; menu adlari surume gore degisebilir (not).
const YONERGE = {
  honor: ["m.bl.yn_honor_1", "m.bl.yn_honor_2", "m.bl.yn_honor_3", "m.bl.yn_honor_4"],
  huawei: ["m.bl.yn_honor_1", "m.bl.yn_honor_2", "m.bl.yn_honor_3", "m.bl.yn_honor_4"],
  xiaomi: ["m.bl.yn_xiaomi_1", "m.bl.yn_xiaomi_2", "m.bl.yn_xiaomi_3"],
  samsung: ["m.bl.yn_samsung_1", "m.bl.yn_samsung_2"],
  diger: ["m.bl.yn_diger_1", "m.bl.yn_diger_2"],
};

// uretici sinifi -> { adimlar: [anahtar], ozel: uretici taninan biri mi }
export function pilYonergesi(uretici) {
  const u = Object.hasOwn(YONERGE, uretici) ? uretici : "diger";
  return { uretici: u, adimlar: [...YONERGE[u]], ozel: u !== "diger" };
}

// Hata turu -> { anahtar, degerler } (bilinmeyen tur genel metne, turun ADIYLA).
export function hataMetni(tur) {
  const t = typeof tur === "string" ? tur : "?";
  return Object.hasOwn(HATA, t) ? { anahtar: HATA[t], degerler: null } : { anahtar: "m.bl.hata_genel", degerler: { tur: t } };
}

// Eklentinin durumu (+ son yenilemenin sonucu) -> ekranin gosterecekleri.
//   d: bildirim.durum() | null (okunamadi)      son: null | "yazildi" | "kartta-ayarsiz" | hata turu
export function bildirimGorunumu(d, { kimlik = null, son = null } = {}) {
  if (!d) return null;
  const zarf = d.zarf === true;
  let ayar = zarf ? "m.bl.zarf_var" : "m.bl.zarf_yok";
  // Kart "ayarli degil" dedi: zarf DURUYORSA bu da soylenir (silinmez — K-10), kullanici uyarilir.
  const ayarsiz = son === "kartta-ayarsiz";
  if (ayarsiz) ayar = zarf ? "m.bl.kartta_ayarsiz_zarf" : "m.bl.kartta_ayarsiz";
  if (kimlik === null) ayar = "m.bl.kart_yok";
  return {
    ayar,
    ayarUyari: !zarf || (ayarsiz && kimlik !== null),
    izin: d.izin ? "m.bl.izin_var" : "m.bl.izin_yok",
    izinIste: !d.izin && d.izinGerekli === true,
    anlik: d.anlik === true,
    // Pil kisitlamasi yalniz anlik izleme ACIKKEN konu edilir (A37: ilk acildiginda, nedeni yazilarak).
    pilGoster: d.anlik === true,
    pil: d.pilMuaf ? "m.bl.pil_muaf" : "m.bl.pil_kisitli",
    pilIste: d.anlik === true && !d.pilMuaf,
    yonerge: pilYonergesi(d.uretici),
    izleme: Object.hasOwn(IZLEME, d.izleme) ? IZLEME[d.izleme] : IZLEME.durduruldu,
    izlemeUyari: ["internet", "guven", "araci", "ayar", "ic-hata"].includes(d.izleme),
    siniflar: SINIFLAR.map((s) => ({ sinif: s, anahtar: SINIF[s], acik: !d.kapali.includes(s) })),
  };
}

// Bir sinifin anahtari cevrilince yeni "kapali" listesi (SINIFLAR sirasinda).
export function sinifCevir(kapali, sinif) {
  if (!SINIFLAR.includes(sinif)) return SINIFLAR.filter((s) => kapali.includes(s));
  const simdiKapali = kapali.includes(sinif);
  return SINIFLAR.filter((s) => (s === sinif ? !simdiKapali : kapali.includes(s)));
}
