// 5.12.121 (CE) — KABUGUN TEMBEL METINLERI: ust serit uyarilari (izleyici, kopru adresi, bu kipte baglanilamiyor,
// komut / devralma / baglanti hatalari), Canli'nin uzun ipucu ve Pil sekmesinin kabuktaki (index.html) metinleri
// (J7 uyarisi, bosluk uyarisi, tarayicidaki noktalari silme). Gosteren: app.js + index.html (kkMetin).
// NEDEN AYRI: bu metinler ilk karede gorunmez (baglanti / hata / sekme gerektirir); acilis sozlugu (EU32, 19 500 B)
// ve eslesmis acilis (EU31, 15 dosya) dolu. app.js bu dosyayi kurulunca (mounted) DINAMIK indirir — acilisi
// beklemez; inene dek bu metinleri tasiyan seritler cizilmez, hata metni bir kez kurulur (hataYazi).
// Kurallar sozluk.js'inkiyle AYNI (test/sozluk_kabuk.test.js).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_KABUK = Object.freeze({
  // ── ust seritler (index.html .bildirimler)
  "kk.desteksiz": S("Bu kipte bağlanılamıyor.", "Cannot connect in this mode."),
  "kk.localhost_1": S("Ayrıca sayfa", "Also, the page must be opened via"),
  "kk.localhost_2": S("üzerinden açılmalı —", "— Web Serial does not work over"),
  "kk.localhost_3": S("ile Web Serial çalışmaz. Sunucuyu başlatmak için:", "pages. To start the server:"),
  "kk.guvensiz": S("Bu sayfa güvenli bağlamda değil, o yüzden Web Serial kapalı — tarayıcının suçu değil. Web Serial yalnızca https:// ya da http://localhost üzerinde çalışır. Sayfa kartın kendisinden geldiğine göre doğru kip WiFi (akış); yukarıdan onu seçin.",
    "This page is not a secure context, so Web Serial is off — not the browser's fault. Web Serial only works on https:// or http://localhost. Since the page comes from the board itself, the right mode is Wi-Fi (stream); choose it above."),
  "kk.serial_yok": S("Bu tarayıcı Web Serial desteklemiyor. Chrome veya Edge gerekiyor; telefonda hiçbir tarayıcı desteklemiyor — telefondan bağlanmak için WiFi (akış) kipini seçin.",
    "This browser does not support Web Serial. Chrome or Edge is required; no phone browser supports it — to connect from a phone, choose Wi-Fi (stream) mode."),
  "kk.eventsource_yok": S("Bu tarayıcı EventSource desteklemiyor.", "This browser does not support EventSource."),
  "kk.demo_yok": S("Demo kartı yüklenmedi — adrese ?demo ekleyin.", "The demo board did not load — add ?demo to the address."),
  "kk.kopru_1": S("Kart bir bilgisayara bağlı. Sınırsız geçmiş ve çoklu izleyici için arayüzü",
    "The board is connected to a computer. For unlimited history and multiple viewers, open the panel at"),
  "kk.kopru_2": S("üzerinden açın.", "instead."),
  "kk.izleyici_1": S("Bu oturum", "This session is a"),
  "kk.izleyici_2": S("izleyici", "viewer"),
  "kk.izleyici_3": S("— ölçümü görüyorsunuz ama komut gönderemezsiniz. Kalibrasyon ve pil testi sürücüdeyken tek elde olmalı.",
    "— you can see the measurement but cannot send commands. Calibration and battery tests stay in one hand while a driver is active."),
  "kk.izleyici_4": S("Durdurma", "Stop"),
  "kk.izleyici_5": S("her zaman açık.", "always works."),
  "kk.devral": S("Sürücülüğü devral", "Take over as driver"),
  // ── hata metinleri (app.js; kartin / koprunun gonderdigi sebep OLDUGU GIBI eklenir)
  "kk.okuma_hatasi": S("Okuma hatası: {mesaj} — kablo çıkmış ya da kart yeniden başlamış olabilir; “Karta bağlan”a yeniden basın.",
    "Read error: {mesaj} — the cable may be out or the board restarted; press “Connect” again."),
  "kk.akis_koptu": S("Akış koptu — yeniden bağlanılıyor", "Stream lost — reconnecting"),
  "kk.akis_dolu": S("Kart açık ama canlı akışı dolu: aynı anda en çok {n} izleyici bağlanabilir (tarayıcı sekmesi, telefon, PC uygulaması). Birini kapatın; yer açılınca burası kendiliğinden bağlanır.",
    "The board is on, but its live stream is full: at most {n} viewers can connect at once (browser tab, phone, PC app). Close one of them; this page connects by itself when a slot frees up."),
  "kk.akis_dolu_kisa": S("Akış dolu — yer bekleniyor", "Stream full — waiting for a slot"),
  "kk.komut_red": S("Komut gönderilemedi ({kod})", "Command not sent ({kod})"),
  "kk.komut_baglanti_yok": S("Komut gönderilemedi — bağlantı yok", "Command not sent — no connection"),
  "kk.devral_409": S("Devralınamadı (409): Başka bir sürücü etkin — o sekmeyi kapatıp yeniden deneyin.",
    "Could not take over (409): another driver is active — close that tab and try again."),
  "kk.devral_hata": S("Devralınamadı{durum} — köprünün çalıştığını denetleyip yeniden deneyin.",
    "Could not take over{durum} — check that the bridge is running and try again."),
  "kk.demo_hata": S("Demo kipi açılamadı: {mesaj} — sayfayı yenileyip yeniden deneyin.",
    "Demo mode could not start: {mesaj} — reload the page and try again."),
  "kk.port_mesgul": S("Bağlanamadı: {mesaj} — port başka bir program (Arduino seri monitör, tezgah betiği) tarafından kullanılıyor olabilir; onu kapatıp yeniden bağlanın.",
    "Could not connect: {mesaj} — the port may be in use by another program (Arduino serial monitor, bench script); close it and connect again."),
  "kk.baglanamadi": S("Bağlanamadı: {mesaj} — kablo ve kartın açık olduğunu denetleyip yeniden deneyin.",
    "Could not connect: {mesaj} — check the cable and that the board is on, then try again."),
  // ── panelin Konsol'a dustugu kendi satirlari (kartin satirlari DEGIL; onlar oldugu gibi)
  "kk.log_bagli": S("— bağlandı, 115200 baud —", "— connected, 115200 baud —"),
  "kk.log_akis": S("— akış açıldı: {adres} —", "— stream opened: {adres} —"),
  "kk.log_tasiyici": S("— taşıyıcı değişti, bağlantı kesildi —", "— transport changed, disconnected —"),
  "kk.log_sayfa": S("— sayfa {host} üzerinden geldi: akış kipi —", "— page came via {host}: stream mode —"),
  "kk.log_kopru": S("— köprü algılandı: {kart} —", "— bridge detected: {kart} —"),
  "kk.log_demo": S("— DEMO KIPI: karta bagli degil, sahte kart calisiyor —", "— DEMO MODE: not connected to a board, simulated board running —"),
  "kk.log_sinyal": S("— test sinyali: {ad} —", "— test signal: {ad} —"),
  "kk.log_kesildi": S("— bağlantı kesildi —", "— disconnected —"),
  // ── Canli
  "kk.yenileme_ipucu": S("Kart bu aralıkta bir D satırı yollar; her nokta o aralığın ortalaması. Sadece sürücü değiştirebilir.",
    "The board sends one D line per interval; each point is that interval's average. Only the driver can change it."),
  // ── Pil sekmesinin kabuktaki metinleri (index.html)
  "kk.j7_1": S("⚠ Yükü", "⚠ Connect the load to"),
  "kk.j7_2": S("'ye bağlayın, J3'e değil. J3 doğrudan şönte gider; oraya bağlarsanız MOSFET",
    ", not J3. J3 goes straight to the shunt; connected there, the MOSFET is"),
  "kk.j7_3": S("baypas", "bypassed"),
  "kk.j7_4": S("olur ve", "and"),
  "kk.j7_5": S("kesme çalışmaz", "cut-off does not work"),
  "kk.j7_6": S(". Kart bunu başlangıçta denetleyip testi reddediyor. Pil gerilimi",
    ". The board checks this at the start and refuses the test. Battery voltage must be"),
  "kk.j7_7": S("olmalı (MOSFET V", "(MOSFET V"),
  "kk.j7_8": S("sınırı).", "limit)."),
  "kk.pil_hata": S("Pil testi: {hata}", "Battery test: {hata}"),
  "kk.pil_veri_yok": S("Pil verisi alınamıyor: {mesaj}", "Battery data unavailable: {mesaj}"),
  "kk.pil_http": S("kart yanıt vermiyor (HTTP {kod})", "the board is not responding (HTTP {kod})"),
  "kk.pil_ulasilamiyor": S("karta ulaşılamıyor: {mesaj}", "cannot reach the board: {mesaj}"),
  "kk.pil_beklenmeyen": S("beklenmeyen yanıt — kart adresi doğru mu?", "unexpected response — is the board address right?"),
  "kk.bosluk_1": S("⚠ Kayıtta", "⚠ The log has a"),
  "kk.bosluk_2": S("{n} nokta boşluk", "{n}-point gap"),
  "kk.bosluk_3": S("var — tarayıcı kartın tuttuğu 1.5 saatlik pencereden daha uzun kapalı kaldı. Boşluk eğride kesik, CSV'de işaretli (",
    "— the browser was closed longer than the 1.5-hour window the board keeps. The gap is broken in the curve and marked in the CSV ("),
  "kk.bosluk_4": S("sütunu 1);", "column 1);"),
  "kk.bosluk_5": S("mAh ve Wh toplamları etkilenmedi", "mAh and Wh totals are not affected"),
  "kk.bosluk_6": S(", çünkü sayaçlar kartta kesintisiz birikiyor. Tam eğri kartın kaydında (Kayıtlar).",
    ", because the counters keep accumulating on the board. The full curve is in the board's recording (Recordings)."),
  "kk.nokta_sil": S("Tarayıcıdaki noktaları sil", "Delete points in this browser"),
  "kk.nokta_sil_eminim": S("Eminim, sil", "Yes, delete"),
  "kk.nokta_sil_1": S("Bu tarayıcıdaki pil noktaları silinir (geri gelmez); kartın kaydı Kayıtlar'da kalır. Önce",
    "The battery points in this browser are deleted (cannot be undone); the board's recording stays in Recordings. Use"),
  "kk.nokta_sil_2": S("'ni kullanın.", "first."),
});

/** Kabuk metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriKabuk(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_KABUK, anahtar, dil, degiskenler);
}
