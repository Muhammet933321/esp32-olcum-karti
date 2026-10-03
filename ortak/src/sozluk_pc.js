// 4D (PC10/PC11) — PANEL PC KOPRUSUNDE: "bu PC'deki arsiv" METINLERI (TR/EN).
//
// ACILIS sozlugunden (sozluk.js) AYRI (EU30 deseni): yalniz Kayitlar zinciri (ekran/kayitlar.js,
// ekran/kayit_gorunum.js) statik, Ayarlar (ekran/ayarlar.js) YALNIZ kopru kokeninde dinamik olarak
// indirir — kartin sundugu panelin acilisi ve kartta Ayarlar'in Gelismis bolumu bu dosyayi istemez
// (tasarim/2026-10-03-alt-proje-4-pc.md "4D uygulama kararlari").
// 4H: ekran/pc_kopru.js (bildirim bolumu, yerel ag uyarisi) de statik ice aktarir — o modul YALNIZ
// kopruda iner (ayarlar.js Gelismis'te kaynak 'pc' iken, app.js koprunun isaretli 403'unde).
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
  // ── 4H: Ayarlar > Gelismis (ekran/ayarlar.js) + bildirim bolumu (ekran/pc_kopru.js; yalniz kopruda iner)
  "pc.ay_kabuk": S("Bu PC'nin panel kabuğu (köprünün sunduğu sürüm)", "This PC's panel shell (version served by the bridge)"),
  "pc.bl_baslik": S("Bildirimler (bu bilgisayar)", "Notifications (this computer)"),
  "pc.bl_aciklama": S("Köprü, kartın MQTT bildirimlerine yalnız abone olur ve Windows bildirimi gösterir. Seçimler bu bilgisayarın ayar dosyasına (olcum-karti/ayar.json) yazılır ve hemen uygulanır. Aracı parolaları burada değil: kartta, yalnız USB konsolundan (Q komutları).",
    "The bridge only subscribes to the board's MQTT notifications and shows Windows notifications. Choices are written to this computer's settings file (olcum-karti/ayar.json) and apply immediately. Broker passwords are not here: they live on the board, set only from the USB console (Q commands)."),
  "pc.bl_kapali": S("Bildirimler kapalı ({neden}).", "Notifications are off ({neden})."),
  "pc.bl_abone": S("Aracıya bağlı, dinliyor · kart {kart}.", "Connected to the broker, listening · board {kart}."),
  "pc.bl_bagli_degil": S("Aracıya bağlı değil ({mesaj}) · kart {kart}.", "Not connected to the broker ({mesaj}) · board {kart}."),
  "pc.bl_kart_acik": S("çevrimiçi", "online"),
  "pc.bl_kart_kapali": S("çevrimdışı", "offline"),
  "pc.bl_kart_bilinmiyor": S("durumu bilinmiyor", "state unknown"),
  "pc.bl_alinamadi": S("Köprü bildirim durumunu vermedi ({mesaj}).", "The bridge did not report its notification state ({mesaj})."),
  "pc.bl_son": S("Son olay: {zaman} ({tur}).", "Last event: {zaman} ({tur})."),
  "pc.bl_son_yok": S("Son olay: henüz yok.", "Last event: none yet."),
  "pc.bl_siniflar": S("Bildirilecek olaylar", "Events to notify"),
  "pc.bl_s_kopuk": S("Karttan haber yok / ev interneti koptu (kayıt sürerken)", "No word from the board / home internet down (while recording)"),
  "pc.bl_s_bitti": S("Kayıt ya da pil testi bitti", "Recording or battery test finished"),
  "pc.bl_s_dolu": S("Kayıt belleği doldu", "Recording memory full"),
  "pc.bl_s_esik": S("Eşik aşıldı", "Threshold crossed"),
  "pc.bl_s_yeniden_basladi": S("Kart yeniden başladı (kayıt kesildi)", "Board restarted (recording interrupted)"),
  "pc.bl_s_kacirilan": S("Kaçırılan olayların özeti", "Summary of missed events"),
  "pc.bl_s_deneme": S("Deneme bildirimi (Qt)", "Test notification (Qt)"),
  "pc.bl_dil": S("Bildirim dili", "Notification language"),
  "pc.bl_uyari": S("Ayar dosyası: {mesaj}", "Settings file: {mesaj}"),
  "pc.bl_kaydedildi": S("Kaydedildi — köprü yeni seçimi hemen kullanır.", "Saved — the bridge uses the new choice right away."),
  "pc.bl_kayit_hata": S("Kaydedilemedi: {mesaj}", "Could not save: {mesaj}"),
  // ── 4H: yerel ag istemcisi (app.js, koprunun 403 + X-Kopru-Ret: lan yaniti)
  "pc.lan_salt": S("Yerel ağdan salt okuma: bu bağlantı köprüyü yalnız izleyebilir (DURDUR — p0 — her zaman geçer). Komut ve ayar için paneli köprünün çalıştığı bu bilgisayarda açın ya da karta doğrudan bağlanın (olcum.local).",
    "Read-only from the local network: this connection can only watch the bridge (STOP — p0 — always works). For commands and settings, open the panel on the computer running the bridge, or connect to the board directly (olcum.local)."),
});

/** PC metni: SOZLUK_PC'de varsa oradan, yoksa acilis sozlugunden (ceviri). ATMAZ. */
export function ceviriPc(anahtar, dil = "tr", degiskenler = null) {
  const a = typeof anahtar === "string" ? anahtar : String(anahtar);
  return Object.prototype.hasOwnProperty.call(SOZLUK_PC, a)
    ? sozluktenCeviri(SOZLUK_PC, a, dil, degiskenler) : ceviri(a, dil, degiskenler);
}
