// Telefona ozel metinler (TR/EN). ortak/src/sozluk.js'ten AYRI (sozluk_pc.js deseni): ortak sozluk
// degistirilmez; burada yalniz telefon ekranlarinin metinleri durur. Anahtarlar "m." ile baslar.
// Kurallar (test/sozluk.test.js): her anahtarda bos olmayan tr VE en, yer tutucular iki dilde ayni,
// kullanilmayan anahtar yok, kullanilan her anahtar var, ortak sozlukle cakisma yok.
// ceviriMobil: once bu sozluk, yoksa ortak sozluk — HICBIR ZAMAN ATMAZ.

import { ceviri, sozluktenCeviri } from "@ortak/sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_MOBIL = Object.freeze({
  "m.uygulama": S("Ölçüm Kartı", "Measurement Board"),
  // ── Karti bul (ekran/KartBul.vue)
  "m.kb.baslik": S("Kartı bul", "Find the board"),
  "m.kb.elle": S("Adres (isteğe bağlı)", "Address (optional)"),
  "m.kb.elle_ornek": S("örn. 192.168.1.20", "e.g. 192.168.1.20"),
  "m.kb.ara": S("Ara", "Search"),
  "m.kb.araniyor": S("Aranıyor…", "Searching…"),
  "m.kb.adres": S("Adres", "Address"),
  "m.kb.kimlik": S("Kart kimliği", "Board ID"),
  "m.kb.kaynak": S("Nasıl bulundu", "Found via"),
  "m.kb.sure": S("Süre", "Time"),
  "m.kb.sure_ms": S("{ms} ms", "{ms} ms"),
  "m.kb.txt": S("Duyurudaki kimlik", "Announced ID"),
  "m.kb.txt_uyuyor": S("kartınkiyle aynı", "matches the board"),
  "m.kb.txt_uymuyor": S("UYMUYOR", "DOES NOT MATCH"),
  "m.kb.duyurular": S("Ağdaki duyurular", "Network announcements"),
  "m.kb.denenenler": S("Denenen adresler", "Addresses tried"),
  "m.kb.kaynak_elle": S("elle girilen", "entered by hand"),
  "m.kb.kaynak_onbellek": S("son bilinen adres", "last known address"),
  "m.kb.kaynak_ad": S("olcum.local adı", "olcum.local name"),
  "m.kb.kaynak_nsd": S("ağ duyurusu", "network announcement"),
  "m.kb.kaynak_ap": S("kartın kendi ağı", "the board's own network"),
  "m.kb.hata_bulunamadi": S("Kart bu ağda bulunamadı.", "The board was not found on this network."),
  "m.kb.hata_kimlik": S("Bu adresteki kart, eşleştiğin kart değil.", "The board at this address is not the one you paired with."),
  "m.kb.hata_bicim": S("Adres yanlış yazılmış.", "The address is not written correctly."),
  "m.kb.hata_ozel_degil": S("Yalnız yerel ağ adresleri kabul edilir.", "Only local network addresses are accepted."),
  "m.kb.hata_ad_izinsiz": S("Ad yerine kartın IP adresini yaz.", "Enter the board's IP address instead of a name."),
  "m.kb.hata_wifi_yok": S("Wi-Fi kapalı ya da bağlı değil.", "Wi-Fi is off or not connected."),
  "m.kb.hata_bilinmeyen": S("Beklenmeyen bir hata oldu.", "An unexpected error occurred."),
});

export function ceviriMobil(anahtar, dil = "tr", degiskenler = null) {
  if (Object.hasOwn(SOZLUK_MOBIL, anahtar)) return sozluktenCeviri(SOZLUK_MOBIL, anahtar, dil, degiskenler);
  return ceviri(anahtar, dil, degiskenler);
}
