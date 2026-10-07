// Gelismis › "Karti ara (tani)": kesfin ve ag eklentisinin telefonda calistiginin duman testi — her adayin
// sonucu gorunur (eski ekran/KartBul.vue'nun mantigi, DOM'suz). Kart nesnesine DOKUNMAZ: kendi ag + kesif
// sarmalayicisini kurar (kart / kasa kurulmaz — S1), baglantiyi degistirmez.
//
//   const s = await kesifTanisi(bag, { elle });
//     -> { sonuc: {adres, kimlik, kaynak, sureMs, txtKimlik} | null, denenenler: [{adres, kaynak, sonuc}],
//          duyurular: [{adres, uyuyor}], hata: sozluk anahtari | null }      ASLA atmaz.
//   bag: { KartAg, Kesif, agKur, kesifKur, onbellek, KesifHatasi, HedefHatasi }

const HATA = Object.freeze({
  bulunamadi: "m.kb.hata_bulunamadi", "kimlik-uymuyor": "m.kb.hata_kimlik", bicim: "m.kb.hata_bicim",
  "ozel-degil": "m.kb.hata_ozel_degil", "ad-izinsiz": "m.kb.hata_ad_izinsiz", "wifi-yok": "m.kb.hata_wifi_yok",
});

export const KAYNAK = Object.freeze({
  elle: "m.kb.kaynak_elle", onbellek: "m.kb.kaynak_onbellek", ad: "m.kb.kaynak_ad", nsd: "m.kb.kaynak_nsd",
  ap: "m.kb.kaynak_ap", paylasim: "m.bt.kaynak_paylasim",
});

const SONUC = Object.freeze({
  tamam: "m.sonuc.tamam", "zaman-asimi": "m.sonuc.zaman_asimi", baglanti: "m.sonuc.baglanti", cleartext: "m.sonuc.cleartext",
  "yanit-gecersiz": "m.sonuc.yanit_gecersiz", "govde-buyuk": "m.sonuc.govde_buyuk", "wifi-yok": "m.sonuc.wifi_yok",
  "ozel-degil": "m.sonuc.ozel_degil", "ad-cozulmedi": "m.sonuc.ad_cozulmedi", mesgul: "m.sonuc.mesgul",
});

export const kaynakAnahtari = (k) => (Object.hasOwn(KAYNAK, k) ? KAYNAK[k] : "m.sonuc.ic_hata");
export const sonucAnahtari = (s) => (Object.hasOwn(SONUC, s) ? SONUC[s] : "m.sonuc.ic_hata");

export function taniHatasi(tur) {
  return Object.hasOwn(HATA, tur) ? HATA[tur] : "m.kb.hata_bilinmeyen";
}

export async function kesifTanisi(bag, { elle = "" } = {}) {
  const cikti = { sonuc: null, denenenler: [], duyurular: [], hata: null };
  try {
    const durum = await bag.KartAg.wifiDurumu();
    // hotspot sahibi (paylasim): istemci Wi-Fi yok ama kart telefonun kendi alt aginda olabilir
    if (!durum.wifi && !durum.paylasim && !durum.hataAyiklama) { cikti.hata = HATA["wifi-yok"]; return cikti; }
    const yerelDongu = durum.hataAyiklama === true;
    const ag = bag.agKur(bag.KartAg, { yerelDongu });
    const kesif = bag.kesifKur({ kartFetch: ag.kartFetch, eklenti: bag.Kesif, onbellek: bag.onbellek, yerelDongu });
    const s = await kesif.bul({ elle: typeof elle === "string" ? elle.trim() : "" });
    cikti.sonuc = {
      adres: s.adres, kimlik: s.kimlik, kaynak: s.kaynak, sureMs: s.sureMs, txtKimlik: s.txtKimlik ?? null,
      tur: s.bilgi && Number.isInteger(s.bilgi.tur) ? s.bilgi.tur : null,      // kartin PBKDF2 tur sayisi
    };
    cikti.denenenler = Array.isArray(s.denenenler) ? s.denenenler : [];
    // Duyurular kesfin kendi taramasi bittikten SONRA (iki es zamanli tarama eski surumlerde birbirini dusurur).
    const tarama = await bag.Kesif.nsdTara({ sureMs: 1500 }).then((t) => (t && t.servisler) || [], () => []);
    cikti.duyurular = tarama.map((d) => ({ adres: `${d.ip}:${d.port}`, uyuyor: d.kimlik === s.kimlik }));
  } catch (e) {
    const bilinen = (bag.KesifHatasi && e instanceof bag.KesifHatasi) || (bag.HedefHatasi && e instanceof bag.HedefHatasi);
    if (bag.KesifHatasi && e instanceof bag.KesifHatasi && Array.isArray(e.denenenler)) cikti.denenenler = e.denenenler;
    cikti.hata = taniHatasi(bilinen ? e.tur : "");
  }
  return cikti;
}
