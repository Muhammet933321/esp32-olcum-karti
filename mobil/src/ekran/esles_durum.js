// Eslestirme ekraninin durum mantigi (A12, A13) — sablondan ayri, DOM'suz sinanabilsin diye.
//
//   const s = eslesDurumu(kart, { kareBekle, varsayilanAd });
//   s.ad, s.parola (ref)   s.suruyor, s.tamam, s.hata (ref; hata = { anahtar, degerler } | null)
//   await s.gonder();
//
// Parola kurali (A13): alan, kart.esles cagrilmadan ONCE temizlenir; parola yalniz o cagri boyunca
// yerel degiskende yasar. Hata olarak yalnizca sozluk anahtari tutulur (istisnanin kendisi degil).

import { ref } from "vue";

export const ESLES_HATA = Object.freeze({
  "parola-kisa": "m.es.hata_parola_kisa",
  "parola-yanlis": "m.es.hata_parola_yanlis",
  "parola-yok": "m.es.hata_parola_yok",
  bekle: "m.es.hata_bekle",
  "liste-dolu": "m.es.hata_liste_dolu",
  "sure-doldu": "m.es.hata_sure_doldu",
  "kart-sahte": "m.es.hata_kart_sahte",
  "tur-sinir-disi": "m.es.hata_tur",
  "kart-gecersiz": "m.es.hata_kart_gecersiz",
  "kimlik-uymuyor": "m.es.hata_kimlik",
  ag: "m.es.hata_ag",
  kasa: "m.es.hata_kasa",
  "ad-gecersiz": "m.es.hata_ad",
  "bagli-degil": "m.es.hata_bagli_degil",
  "zaten-esli": "m.es.hata_zaten_esli",
});

function hataAnahtari(e) {
  const tur = e && typeof e.tur === "string" ? e.tur : "";
  if (tur === "bekle" && Number.isInteger(e.saniye)) return { anahtar: "m.es.hata_bekle_saniye", degerler: { saniye: e.saniye } };
  return { anahtar: Object.hasOwn(ESLES_HATA, tur) ? ESLES_HATA[tur] : "m.es.hata_bilinmeyen", degerler: null };
}

export function eslesDurumu(kart, { kareBekle, varsayilanAd }) {
  const ad = ref(varsayilanAd);
  const parola = ref("");
  const suruyor = ref(false);
  const tamam = ref(false);
  const hata = ref(null);

  async function gonder() {
    if (suruyor.value) return;
    suruyor.value = true;
    hata.value = null;
    const girilen = parola.value;
    parola.value = "";                 // alan HEMEN temizlenir: sonuc ne olursa olsun ekranda parola kalmaz
    try {
      // PBKDF2 saf JS ve es zamanli: once ilerleme gostergesi cizilsin.
      await kareBekle();
      await kart.esles(ad.value, girilen);
      tamam.value = true;
    } catch (e) {
      hata.value = hataAnahtari(e);
    } finally {
      suruyor.value = false;
    }
  }

  return { ad, parola, suruyor, tamam, hata, gonder };
}
