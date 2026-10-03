// 4D (PC10/PC11) — PANEL PC KOPRUSUNDE: "bu PC'deki arsiv" METINLERI (TR/EN).
//
// ACILIS sozlugunden (sozluk.js) AYRI (EU30 deseni): yalniz Kayitlar zinciri (ekran/kayitlar.js,
// ekran/kayit_gorunum.js) statik, Ayarlar (ekran/ayarlar.js) YALNIZ kopru kokeninde dinamik olarak
// indirir — kartin sundugu panelin acilisi ve kartta Ayarlar'in Gelismis bolumu bu dosyayi istemez
// (tasarim/2026-10-03-alt-proje-4-pc.md "4D uygulama kararlari").
// Kurallar sozluk.js'inkiyle AYNI (test/sozluk_pc.test.js): her anahtarda bos olmayan tr VE en, yer
// tutucular iki dilde ayni, kullanilmayan anahtar yok, kullanilan her anahtar var, sozluklar ayrik.
// ceviriPc: once bu sozluk, yoksa sozluk.js — ceviri() gibi HICBIR ZAMAN ATMAZ.

import { ceviri, sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_PC = Object.freeze({
  // ── Kayitlar (ekran/kayitlar.js, kayit_gorunum.js NEREDE_METIN)
  "pc.nerede": S("bu PC'de (köprü arşivi)", "on this PC (bridge archive)"),
  "pc.kl_ozet": S("Bu PC'deki arşiv (köprü): {akis} akış · {oturum} oturum · {boyut}",
    "Archive on this PC (bridge): {akis} stream(s) · {oturum} session(s) · {boyut}"),
  "pc.kl_salt": S("Salt okuma: arşivi köprü (kopru/pc.py) kartın kayıtlarından WiFi'den yazar; panel ondan okur, hiçbir şey yazmaz, silmez ve karta onay göndermez.",
    "Read-only: the bridge (kopru/pc.py) writes this archive from the board's recordings over WiFi; the panel reads it and never writes, deletes or sends acknowledgements to the board."),
  "pc.kl_kopyalar": S("Bu PC'deki arşiv", "Archive on this PC"),
  "pc.kl_kopya_satir": S("Kart {kart} · akış {kimlik} · {oturum} oturum · {boyut} · son sıra {son}",
    "Board {kart} · stream {kimlik} · {oturum} session(s) · {boyut} · last sequence {son}"),
  "pc.kl_neden_arsiv": S("Bu PC'deki arşiv okunamadı ({mesaj}) — köprü çalışıyor mu? Yenile'ye basın.",
    "The archive on this PC could not be read ({mesaj}) — is the bridge running? Press Refresh."),
  // ── koprunun arka plan esitlemesi (/esitleme/durum)
  "pc.es_tamam": S("Köprü eşitlemesi: son başarılı {zaman} · son turda {yeni} yeni kayıt (açılıştan beri {toplam}) · kartın son sırası {kart_son} · karta onay {onay}.",
    "Bridge sync: last success {zaman} · {yeni} new record(s) in the last round ({toplam} since start) · board's last sequence {kart_son} · acknowledgements {onay}."),
  "pc.es_hata": S("Köprü eşitlemesi şu an başarısız ({mesaj}) — {sn} s sonra yeniden. Son başarılı: {zaman} · karta onay {onay}.",
    "Bridge sync is failing right now ({mesaj}) — retrying in {sn} s. Last success: {zaman} · acknowledgements {onay}."),
  "pc.es_atlandi": S("Köprü eşitlemesi atlandı ({mesaj}). Son başarılı: {zaman} · karta onay {onay}.",
    "Bridge sync was skipped ({mesaj}). Last success: {zaman} · acknowledgements {onay}."),
  "pc.es_bekliyor": S("Köprü eşitlemesi henüz bir tur tamamlamadı · karta onay {onay}.",
    "Bridge sync has not finished a round yet · acknowledgements {onay}."),
  "pc.es_kapali": S("Köprü eşitlemesi kapalı ({neden}) — listede yalnız daha önce eşitlenmiş kayıtlar var.",
    "Bridge sync is off ({neden}) — the list shows only recordings synced earlier."),
  "pc.es_yok": S("Köprü eşitleme durumunu vermedi ({mesaj}).", "The bridge did not report its sync state ({mesaj})."),
  "pc.onay_acik": S("açık (kart, PC'ye kopyalanan eski kayıtları yer gerekince silebilir)",
    "on (the board may delete old recordings already copied to this PC when it needs space)"),
  "pc.onay_kapali": S("kapalı (kart bu kopyayı yedek saymaz)", "off (the board does not count this copy as a backup)"),
  "pc.zaman_yok": S("henüz yok", "none yet"),
  // ── Ayarlar (ekran/ayarlar.js; yalniz kopru kokeninde iner)
  "pc.ay_kal_kaynak": S("Kaynak: bu PC'deki arşivin kopyası (köprü) — kart {kart}, akış {kimlik}, son eşitleme {zaman}. Kartın şu anki geçmişi farklı olabilir.",
    "Source: the copy in this PC's archive (bridge) — board {kart}, stream {kimlik}, last sync {zaman}. The board's current history may differ."),
  "pc.ay_kal_neden_kopru": S("köprü karta WiFi'den ulaşamadı ({mesaj})", "the bridge could not reach the board over WiFi ({mesaj})"),
  "pc.ay_depo_pc": S("köprü (PC)", "bridge (PC)"),
  "pc.ay_depo_salt": S("salt okuma", "read-only"),
  "pc.ay_depo_ipucu": S("Bu tablo bu PC'deki arşivi gösterir: köprü yazar, panel yalnız okur. Panelden silinmez — gerekirse köprüyü durdurup arşiv dizininden (olcum-karti/arsiv) elle silin.",
    "This table shows the archive on this PC: the bridge writes it, the panel only reads it. It cannot be deleted from the panel — if needed, stop the bridge and delete it from the archive folder (olcum-karti/arsiv) by hand."),
});

/** PC metni: SOZLUK_PC'de varsa oradan, yoksa acilis sozlugunden (ceviri). ATMAZ. */
export function ceviriPc(anahtar, dil = "tr", degiskenler = null) {
  const a = typeof anahtar === "string" ? anahtar : String(anahtar);
  return Object.prototype.hasOwnProperty.call(SOZLUK_PC, a)
    ? sozluktenCeviri(SOZLUK_PC, a, dil, degiskenler) : ceviri(a, dil, degiskenler);
}
