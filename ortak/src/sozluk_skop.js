// 5.12.118 — OSILOSKOBUN TEMBEL PARCALARININ metinleri: on suzgec menusu ("Süzgeç: Açık / Ham", SK1, Tetik kumesi)
// ve eski skop arsivinin basligi / aciklamasi (B35, 4D PC12; yalniz PC koprusunde). Gosteren bilesenler
// ekran/osiloskop.js SkopSuz / SkopArsiv; bu dosyayi YALNIZ onlar DINAMIK indirir (osiloskop ekrani acilinca).
// NEDEN AYRI: Suzgec menusu ilk yazildiginda index.html + app.js + acilis sozlugundeydi ve eslesmis tarayicinin
// acilisini (EU31, 262 144 B) 237 B asti; #/skop acilisi da 14 dosyanin sinirinda (statik ice aktarma eklenemez).
// Inmezse menu ve arsiv gorunmez; kart varsayilani (suzgec ACIK) gecerli kalir. Kurallar sozluk.js'inkiyle AYNI
// (test/sozluk_skop.test.js).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_SKOP = Object.freeze({
  "sz.suzgec": S("Süzgeç", "Filter"),
  "sz.acik": S("Açık", "On"),
  "sz.ham": S("Ham", "Raw"),
  "sz.ipucu": S("Açık: iki örnekten dar parazit darbeleri silinir, yavaş zaman tabanında örnekler ortalanır. Ham: ADC'nin okuduğu gibi.",
    "On: glitches narrower than two samples are removed and samples are averaged on slow timebases. Raw: as read by the ADC."),
  // ── eski skop arsivi (B35; 4D PC12) — ekran/osiloskop.js SkopArsiv
  "sz.eski_arsiv": S("Eski arşiv — köprünün satır günlüğündeki yakalamalar", "Legacy archive — captures in the bridge's line log"),
  "sz.eski_arsiv_ipucu": S("Salt okuma, dönüştürülmez (B35). Köprüye bağlıyken yapılan her canlı yakalama köprünün bu PC'deki satır günlüğüne (olcum-karti/satir) düşer; liste o günlükten türetilir, örnekler ham ADC kodu. Kartın kendi kaydettiği osiloskop günlükleri Kayıtlar'da.",
    "Read-only, never converted (B35). Every live capture taken through the bridge lands in the bridge's line log on this PC (olcum-karti/satir); the list is derived from that log and samples are raw ADC codes. Oscilloscope logs recorded by the board itself are under Recordings."),
});

/** Suzgec menusu metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriSkop(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_SKOP, anahtar, dil, degiskenler);
}
