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
  "m.sonuc.tamam": S("yanıt verdi", "responded"),
  "m.sonuc.zaman_asimi": S("yanıt yok", "no response"),
  "m.sonuc.baglanti": S("bağlanılamadı", "could not connect"),
  "m.sonuc.cleartext": S("şifresiz bağlantı engellendi", "cleartext connection blocked"),
  "m.sonuc.yanit_gecersiz": S("kart değil", "not a board"),
  "m.sonuc.govde_buyuk": S("yanıt çok büyük", "response too large"),
  "m.sonuc.wifi_yok": S("Wi-Fi yok", "no Wi-Fi"),
  "m.sonuc.ozel_degil": S("yerel adres değil", "not a local address"),
  "m.sonuc.ad_cozulmedi": S("ad çözülemedi", "name not resolved"),
  "m.sonuc.mesgul": S("meşgul", "busy"),
  "m.sonuc.ic_hata": S("hata", "error"),
  "m.ws.engellendi": S("engellendi", "blocked"),
  "m.ws.bos": S("içeriksiz", "empty"),
  "m.ws.gecti": S("GEÇTİ — kapı delik", "PASSED — gate is open"),
  // ── Baglanti (ekran/Baglanti.vue) — gecici, 5C'de kabuga tasinir
  "m.bg.baslik": S("Bağlantı", "Connection"),
  "m.bg.baglan": S("Bağlan", "Connect"),
  "m.bg.durum": S("Durum", "Status"),
  "m.bg.durum_bagli": S("eşleşmiş, bağlı", "paired, connected"),
  "m.bg.durum_eslesmemis": S("kart bulundu, eşleşmemiş", "board found, not paired"),
  "m.bg.durum_bulunamadi": S("kart bulunamadı", "board not found"),
  "m.bg.durum_kimlik": S("bu adresteki kart eşleştiğin kart değil", "the board at this address is not the paired one"),
  "m.bg.esles": S("Bu kartla eşleş", "Pair with this board"),
  "m.bg.dene": S("İmzalı isteği dene", "Try a signed request"),
  "m.bg.imzali_tamam": S("İmzalı istek geçti: {oturum} oturum", "Signed request succeeded: {oturum} session(s)"),
  "m.bg.kaldir": S("Eşleşmeyi kaldır", "Remove pairing"),
  "m.bg.kaldirildi": S("Eşleşme kartta ve telefonda kaldırıldı.", "Pairing removed on the board and the phone."),
  "m.bg.kaldirildi_yerel": S("Eşleşme yalnız telefonda kaldırıldı (karta ulaşılamadı).", "Pairing removed on the phone only (board unreachable)."),
  "m.bg.kaldirildi_belirsiz": S(
    "Eşleşme telefonda kaldırıldı. Kart silmeyi onaylamadı: kayıt kartta kalmış olabilir — kartın panelinden ya da USB'den silin.",
    "Pairing removed on the phone. The board did not confirm the removal: the entry may still be on the board — delete it from the board's panel or over USB.",
  ),
  "m.bg.kasa_bozuk": S(
    "Telefondaki eşleşme kaydı bozuk ya da okunamıyor. Eşleşmeyi kaldırıp yeniden eşleş.",
    "The pairing record on the phone is damaged or unreadable. Remove the pairing and pair again.",
  ),
  "m.bg.hata": S("Olmadı ({tur}).", "Failed ({tur})."),
  "m.ol.pbkdf2": S("PBKDF2 süre ölçümü", "PBKDF2 timing"),
  "m.ol.suruyor": S("Ölçülüyor…", "Measuring…"),
  "m.ol.pbkdf2_sonuc": S("PBKDF2 {tur} tur: en az {enaz} ms · ortanca {ortanca} ms · en çok {encok} ms", "PBKDF2 {tur} rounds: min {enaz} ms · median {ortanca} ms · max {encok} ms"),
  "m.ws.dugme": S("WebView ağ sınaması", "WebView network self-test"),
  "m.ws.suruyor": S("Sınanıyor…", "Testing…"),
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
  // ── Eslestirme (ekran/Esles.vue, ekran/esles_durum.js)
  "m.es.baslik": S("Kartla eşleştir", "Pair with the board"),
  "m.es.kart_dogru_mu": S("Bu, eşleştirmek istediğin kart mı? Kimliği kontrol et.", "Is this the board you want to pair with? Check its ID."),
  "m.es.ad": S("Bu telefonun adı (kartta görünür)", "Name of this phone (shown on the board)"),
  "m.es.ad_varsayilan": S("Telefon", "Phone"),
  "m.es.parola": S("Kartın WEB parolası — Wi-Fi parolası DEĞİL", "The board's WEB password — NOT the Wi-Fi password"),
  "m.es.parola_not": S(
    "Parola yalnız eşleştirme sırasında kullanılır; telefonda saklanmaz ve ağa çıkmaz.",
    "The password is used only while pairing; it is not stored on the phone and never leaves it.",
  ),
  "m.es.gonder": S("Eşleştir", "Pair"),
  "m.es.suruyor": S("Eşleştiriliyor…", "Pairing…"),
  "m.es.suruyor_not": S("Bu birkaç saniye sürebilir.", "This may take a few seconds."),
  "m.es.tamam": S("Eşleştirildi.", "Paired."),
  "m.es.hata_parola_kisa": S("Web parolası en az 12 karakter olmalı.", "The web password must be at least 12 characters."),
  "m.es.hata_parola_yanlis": S(
    "Parola yanlış. Kartın WEB parolasını gir (Wi-Fi parolası değil).",
    "Wrong password. Enter the board's WEB password (not the Wi-Fi password).",
  ),
  "m.es.hata_parola_yok": S(
    "Kartta web parolası yok ya da çok kısa. Önce kartta en az 12 karakterlik bir web parolası belirle.",
    "The board has no web password, or it is too short. Set a web password of at least 12 characters on the board first.",
  ),
  "m.es.hata_bekle": S("Çok fazla yanlış deneme. Biraz bekleyip yeniden dene.", "Too many wrong attempts. Wait a little and try again."),
  "m.es.hata_bekle_saniye": S(
    "Çok fazla yanlış deneme. {saniye} saniye sonra yeniden dene.",
    "Too many wrong attempts. Try again in {saniye} seconds.",
  ),
  "m.es.hata_liste_dolu": S(
    "Kartın cihaz listesi dolu (8). Kullanılmayan bir cihazı karttan kaldır.",
    "The board's device list is full (8). Remove an unused device from the board.",
  ),
  "m.es.hata_sure_doldu": S("Eşleştirme süresi doldu. Yeniden dene.", "Pairing timed out. Try again."),
  "m.es.hata_kart_sahte": S(
    "Bu kart parolayı bilmiyor — senin kartın olmayabilir. Eşleştirme YAPILMADI. Kart senin değilse kartının web parolasını değiştir.",
    "This board does not know the password — it may not be your board. Pairing was NOT done. If it is not your board, change your board's web password.",
  ),
  "m.es.hata_tur": S(
    "Kart güvensiz bir ayar bildirdi; sahte olabilir. Eşleştirme YAPILMADI.",
    "The board reported an unsafe setting; it may be fake. Pairing was NOT done.",
  ),
  "m.es.hata_kart_gecersiz": S("Karttan anlaşılmayan bir yanıt geldi.", "The board sent a response that was not understood."),
  "m.es.hata_kimlik": S(
    "Bu adresteki kart değişti. Kartı yeniden bul ve kimliğini kontrol et.",
    "The board at this address has changed. Find the board again and check its ID.",
  ),
  "m.es.hata_ag": S("Karta ulaşılamadı. Wi-Fi bağlantısını kontrol et.", "Could not reach the board. Check the Wi-Fi connection."),
  "m.es.hata_kasa": S("Anahtar telefona kaydedilemedi. Eşleştirme geri alındı.", "The key could not be saved on the phone. Pairing was undone."),
  "m.es.hata_ad": S("Ad 1–24 bayt olmalı.", "The name must be 1–24 bytes."),
  "m.es.hata_bagli_degil": S("Önce kartı bul.", "Find the board first."),
  "m.es.hata_zaten_esli": S("Bu telefon zaten eşleşmiş.", "This phone is already paired."),
  "m.es.hata_bilinmeyen": S("Eşleştirme sırasında beklenmeyen bir hata oldu.", "An unexpected error occurred while pairing."),
});

export function ceviriMobil(anahtar, dil = "tr", degiskenler = null) {
  if (Object.hasOwn(SOZLUK_MOBIL, anahtar)) return sozluktenCeviri(SOZLUK_MOBIL, anahtar, dil, degiskenler);
  return ceviri(anahtar, dil, degiskenler);
}
