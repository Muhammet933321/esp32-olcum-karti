// Telefon ortaminin panele soyledigi metinler (TR / EN). Panelin `uyg.hata` / `uyg.uyari` kutularina ve
// reddedilen sozlerin mesajina gider. Sir YOK: adres, kimlik, anahtar, kartin govdesindeki ayrinti metne
// girmez (A45) — yalniz durum kodu ve hata TURU.
//
// Anahtarlar "or." ile baslar (sozluk_mobil.js'in "m." anahtarlariyla karismaz; o sozlugun "kullanilmayan
// anahtar yok" kurali bu dosyayi taramaz).

const S = (tr, en) => Object.freeze({ tr, en });

export const ORTAM_METIN = Object.freeze({
  "or.eslesmemis": S(
    "Kart bu telefonla eşleşmemiş. Ayarlar → Bu telefon → Kart bölümünden eşleşin.",
    "This phone is not paired with the board. Pair it in Settings → This phone → Board.",
  ),
  "or.kimlik_uymuyor": S(
    "Bulunan kart bu telefonun eşleştiği kart değil. Ayarlar → Bu telefon → Kart bölümünü denetleyin.",
    "The board found is not the one this phone is paired with. Check Settings → This phone → Board.",
  ),
  "or.kasa": S(
    "Telefondaki eşleşme kaydı okunamadı. Ayarlar → Bu telefon → Kart bölümünden yeniden eşleşin.",
    "The pairing record on this phone could not be read. Pair again in Settings → This phone → Board.",
  ),
  "or.bulunamadi": S(
    "Kart bulunamadı — aranıyor. Telefonun kartla aynı Wi-Fi ağında olduğunu denetleyin.",
    "Board not found — still searching. Check that the phone is on the same Wi-Fi network as the board.",
  ),
  "or.dolu": S(
    "Kartın canlı akışı dolu: başka izleyiciler (PC köprüsü ya da başka bir telefon) bağlı. Yer açılınca kendiliğinden bağlanılacak; komutlar yine gider.",
    "The board's live stream is full: other viewers (the PC bridge or another phone) are connected. It reconnects by itself when a slot frees up; commands still go through.",
  ),
  "or.koptu": S("Akış koptu — yeniden bağlanılıyor", "Stream lost — reconnecting"),
  "or.wifi_yok": S(
    "Telefon Wi-Fi'ye bağlı değil — kartın ağına bağlanın; akış kendiliğinden yeniden açılır.",
    "The phone is not on Wi-Fi — join the board's network; the stream reopens by itself.",
  ),
  "or.cihaz_silinmis": S(
    "Kart bu telefonu tanımıyor (eşleşme kartta silinmiş olabilir). Ayarlar → Bu telefon → Kart bölümünden yeniden eşleşin.",
    "The board does not recognise this phone (the pairing may have been removed on the board). Pair again in Settings → This phone → Board.",
  ),
  "or.kart_yok": S("Kart yanıt vermiyor — komut gitmedi.", "The board is not responding — the command was not sent."),
  "or.komut_gitmedi": S("Komut gönderilemedi", "Command could not be sent"),
  "or.p0_ulasmadi": S(
    "DURDUR (p0) karta ulaşmadı — kartın yanındaysanız gücü kesin.",
    "STOP (p0) did not reach the board — if you are next to it, cut the power.",
  ),
  "or.istek_hata": S("Karta istek gitmedi", "Request to the board failed"),
  "or.yontem": S("Bu istek türü telefonda desteklenmiyor", "This request method is not supported on the phone"),
  "or.akis_degisti": S(
    "Kartın kayıt akışı değişmiş (kart biçimlendirilmiş olabilir). Telefondaki kopyayı Ayarlar → Bu telefon → Eşitleme'den sıfırlayın.",
    "The board's recording stream has changed (the board may have been formatted). Reset the phone copy in Settings → This phone → Sync.",
  ),
  "or.esitleme_yok": S("Telefonun eşitleyicisi yüklenemedi.", "The phone's sync could not be loaded."),
  "or.esitleme_mesgul": S("Eşitleme şu an başlatılamadı (kopya sıfırlanıyor).", "Sync could not start right now (the copy is being reset)."),
  "or.bagli_degil": S("Kart bağlı değil — eşitleme yapılamadı.", "Board not connected — could not sync."),
  "or.esitleme_hata": S("Eşitlenemedi", "Sync failed"),
  "or.kopya_yok": S("Telefonda bu kayıt akışının kopyası yok.", "There is no copy of this recording stream on the phone."),
  "or.kopya_salt_okuma": S(
    "Telefondaki kopya salt okunur; Ayarlar → Bu telefon → Eşitleme'den sıfırlayın.",
    "The phone copy is read-only; reset it in Settings → This phone → Sync.",
  ),
  "or.paylas": S("Dosya paylaşılamadı", "The file could not be shared"),
  "or.yazdir": S("Yazdırma açılamadı", "Printing could not be opened"),
  "or.bolum_yok": S("Bu telefon bölümü yüklenemedi.", "The This phone section could not be loaded."),
  "or.kuresel_yok": S(
    "Telefon ortamı kurulamadı: ortamKur({ kuresel }) küresel nesnesiz çağrıldı (src/giris.js).",
    "Phone environment not installed: ortamKur({ kuresel }) was called without the global object (src/giris.js).",
  ),
});

// Yer tutucu: {ad}. Bilinmeyen anahtar anahtarin kendisini doner (ATMAZ).
export function metin(anahtar, dil = "tr", degerler = null) {
  const g = ORTAM_METIN[anahtar];
  let s = g ? (dil === "en" ? g.en : g.tr) : anahtar;
  if (degerler) s = s.replace(/\{([a-z_]+)\}/g, (t, ad) => (Object.hasOwn(degerler, ad) ? String(degerler[ad]) : t));
  return s;
}

export const dilSec = (d) => (d === "en" ? "en" : "tr");
