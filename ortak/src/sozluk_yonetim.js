// 5.12.121 (CE, Oncelik 2) — AYARLAR VE KONSOL EKRANLARININ KABUKTAKI METINLERI: index.html'deki Ayarlar kartlari
// (Baglanti, Kalibrasyon ve ayar, Ag, Gorunum; tema adlari) ve Konsol; app.js'in bu ekranlarda kurdugu metinler
// (giris denetimi hatalari, sebeke uyarisi, kartin sont degeri). Gosteren: app.js + index.html (ynMetin).
// Ayarlar modulunun (ekran/ayarlar.js) kendi metinleri ayri (sozluk_ay.js).
// NEDEN AYRI: acilis sozlugu (EU32) ve eslesmis acilis (EU31) dolu. app.js bu dosyayi Ayarlar ya da Konsol ilk
// gorunur oldugunda DINAMIK indirir; inene dek metin bos. Kurallar sozluk.js'inkiyle AYNI
// (test/sozluk_yonetim.test.js). `_html` ile biten anahtarlar satir ici isaretleme (b / strong / em / code)
// tasir ve v-html ile cizilir: icerik SABIT (kullanici / kart girdisi YOK).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_YONETIM = Object.freeze({
  // ── Baglanti karti
  "yn.baglanti_yolu": S("Bağlantı yolu", "Connection path"),
  "yn.yol_akis": S("WiFi / köprü (akış)", "Wi-Fi / bridge (stream)"),
  "yn.yol_demo": S("Demo — sahte kart", "Demo — simulated board"),
  "yn.kart_adresi": S("Kart adresi", "Board address"),
  "yn.or": S("ör.", "e.g."),
  "yn.adres_ipucu": S("Boş = sayfayı sunan adres (aynı köken).", "Empty = the address that served this page (same origin)."),
  "yn.baglanti_ipucu_html": S("Sayfayı <b>kart sunuyorsa</b> yol kendiliğinden <em>akış</em> seçilir ve bağlantı otomatik kurulur. <b>USB</b> yalnızca <code>http://localhost</code> üzerinden açıldığında çalışır (Web Serial güvenli bağlam ister). Telefonda <code>.local</code> adı Android'de çözülmez — kartın <b>IP adresini</b> kullanın.",
    "When the <b>board serves the page</b>, the path switches to <em>stream</em> by itself and the connection opens automatically. <b>USB</b> only works when the page is opened via <code>http://localhost</code> (Web Serial needs a secure context). On a phone the <code>.local</code> name does not resolve on Android — use the board's <b>IP address</b>."),
  // ── Kalibrasyon ve ayar karti
  "yn.kal_baslik": S("Kalibrasyon ve ayar", "Calibration and settings"),
  "yn.menzil": S("Gerilim menzili", "Voltage range"),
  "yn.oto_menzil": S("Otomatik menzil", "Auto range"),
  "yn.sont": S("Takılı şönt", "Fitted shunt"),
  "yn.kelvin": S("Kelvin şart", "Kelvin required"),
  "yn.kart_sont": S("kart: {deger}", "board: {deger}"),
  "yn.sont_bilinmiyor": S("— (bağlanınca okunur)", "— (read when connected)"),
  "yn.sont_uyumsuz": S("— menüyle UYUŞMUYOR, menü tercihini gösterir, kart bunu kullanıyor", "— does NOT MATCH the menu; the menu shows the preference, the board uses this"),
  "yn.ayarlari_goster": S("Ayarları göster", "Show settings"),
  "yn.i2c_tara": S("I²C tara → Konsol", "I²C scan → Console"),
  "yn.v_sifirla": S("Gerilimi sıfırla", "Zero voltage"),
  "yn.v_sifirla_emin": S("Eminim — giriş 0 V'ta", "Yes — the input is at 0 V"),
  "yn.a_sifirla": S("Akımı sıfırla", "Zero current"),
  "yn.a_sifirla_emin": S("Eminim — yük çıkarıldı", "Yes — the load is removed"),
  "yn.e_sifirla": S("Enerjiyi sıfırla", "Reset energy"),
  "yn.e_sifirla_emin": S("Eminim, enerjiyi sıfırla", "Yes, reset energy"),
  "yn.gercek_v": S("Gerçek gerilim (multimetre)", "Actual voltage (multimeter)"),
  "yn.gercek_v_ornek": S("12.34 · −24 da olur…", "12.34 · −24 also works…"),
  "yn.v_kalibre": S("Gerilimi kalibre et", "Calibrate voltage"),
  "yn.gercek_a": S("Gerçek akım, amper", "Actual current, amps"),
  "yn.gercek_a_ornek": S("0.250 · −0.25 da olur…", "0.250 · −0.25 also works…"),
  "yn.a_kalibre": S("Akımı kalibre et", "Calibrate current"),
  "yn.sebeke": S("Şebeke frekansı (ölçek düzeltmesi)", "Mains frequency (scale correction)"),
  "yn.sebeke_dc": S("DC — düzeltme KAPALI", "DC — correction OFF"),
  "yn.sebeke_50": S("50 Hz (Türkiye)", "50 Hz (Turkey)"),
  "yn.faz": S("Faz kalibrasyonu, µs (−2000 … +2000)", "Phase calibration, µs (−2000 … +2000)"),
  "yn.faz_ipucu": S("Dirençli yükte PF'yi en büyük yapan değer.", "The value that maximises PF on a resistive load."),
  "yn.faz_ayarla": S("Fazı ayarla", "Set phase"),
  "yn.faz_sor": S("Fazı sor → Konsol", "Query phase → Console"),
  "yn.fabrika_html": S("⚠ <b>Fabrika ayarları</b> tüm kalibrasyonu (gerilim/akım sıfırı ve kazancı, şönt, faz) siler ve kartı varsayılanlara döndürür. Yalnızca kalibrasyon bozulduysa kullanın — kart tekrar kalibre edilmelidir.",
    "⚠ <b>Factory reset</b> erases all calibration (voltage/current zero and gain, shunt, phase) and returns the board to its defaults. Use it only if the calibration is broken — the board must be calibrated again."),
  "yn.fabrika": S("Fabrika ayarlarına dön", "Back to factory settings"),
  "yn.fabrika_emin": S("Eminim, sıfırla", "Yes, reset"),
  "yn.sira_html": S("<strong>Sıra önemli.</strong> Önce girişi 0 V'a bağlayın ve “Gerilimi sıfırla” — bu, Vref'in gerçek değerini ölçüp çıkarır. Sonra <strong>yükü kesin</strong> ve “Akımı sıfırla”. En son bilinen bir gerilim/akım uygulayıp multimetrenin okuduğu değeri girin. Kalibrasyon her menzil için <em>ayrı</em> tutulur ve NVS'e yazılır.",
    "<strong>Order matters.</strong> First connect the input to 0 V and press “Zero voltage” — this measures and removes the real value of Vref. Then <strong>disconnect the load</strong> and press “Zero current”. Finally apply a known voltage/current and enter what the multimeter reads. Calibration is kept <em>separately</em> for each range and written to NVS."),
  "yn.negatif_html": S("Kalibrasyon değeri <strong>negatif de olabilir</strong> — kart çift yönlü. Sıfıra çok yakın bir değerle kalibre etmeye çalışırsanız kart reddeder (tam ölçeğin %5'i eşiği).",
    "The calibration value <strong>can be negative</strong> — the board is bipolar. If you try to calibrate with a value too close to zero, the board refuses (threshold: 5% of full scale)."),
  "yn.sebeke_kapali": S("Ölçek düzeltmesi KAPALI (DC). AC ölçerken güç |H|² kadar düşük okunur — 50 Hz'te yaklaşık %45.",
    "Scale correction OFF (DC). When measuring AC, power reads low by |H|² — about 45% at 50 Hz."),
  "yn.sebeke_carpan": S("Güce uygulanan ölçek çarpanı: ×{k}  ({f} Hz ayarıyla)", "Scale factor applied to power: ×{k}  (with the {f} Hz setting)"),
  "yn.sebeke_faz": S("⚠ 40–70 Hz dışında faz kalibrasyonu (F) geçerliliğini yitirir.", "⚠ Outside 40–70 Hz the phase calibration (F) is no longer valid."),
  "yn.sebeke_dc_uyari": S("⚠ DC ölçerken DC seçilmezse güç %82 yüksek okunur.", "⚠ When measuring DC without selecting DC, power reads 82% high."),
  "yn.hata_v": S("Gerilim kalibrasyonu: sıfırdan farklı bir sayı girin (ör. 12.34 ya da −24).", "Voltage calibration: enter a non-zero number (e.g. 12.34 or −24)."),
  "yn.hata_a": S("Akım kalibrasyonu: sıfırdan farklı bir sayı girin, amper (ör. 0.250).", "Current calibration: enter a non-zero number, in amps (e.g. 0.250)."),
  "yn.hata_faz": S("Faz kalibrasyonu: sayı girin (µs), ör. 120", "Phase calibration: enter a number (µs), e.g. 120"),
  "yn.hata_faz_aralik": S("Faz kalibrasyonu −2000 … +2000 µs arası olmalı", "Phase calibration must be between −2000 … +2000 µs"),
  // ── Ag karti
  "yn.ag_baslik": S("Ağ — kartı kablosuz yapma", "Network — making the board wireless"),
  "yn.ag_sira_html": S("<strong>Sıra:</strong> kartı <em>USB ile</em> bağlayın, ağı aşağıdan listeye ekleyin (en çok 8). Kart açılışta kayıtlı ağlardan birine bağlanmayı dener; 10 saniyede olmazsa <strong>kendi ağını kurar</strong> (<code>OLCUM-KARTI-XXXX</code>). AP parolası ilk açılışta rastgele üretilip <strong>seri konsola yazılır</strong> — oradan okuyun.",
    "<strong>Order:</strong> connect the board <em>over USB</em> and add the network to the list below (at most 8). At start-up the board tries to join one of the saved networks; if that fails within 10 seconds it <strong>sets up its own network</strong> (<code>OLCUM-KARTI-XXXX</code>). The AP password is generated randomly on first start and <strong>printed to the serial console</strong> — read it there."),
  "yn.ag_uyari_html": S("⚠ Şu anda <b>ağ üzerinden</b> bağlısınız. Buraya yazacağınız parolalar <b>şifrelenmeden</b> gidiyor (kartta TLS yok). Ağ kurulumunu tercihen <b>USB ile</b> yapın.",
    "⚠ You are connected <b>over the network</b> right now. Passwords typed here travel <b>unencrypted</b> (no TLS on the board). Preferably set up the network <b>over USB</b>."),
  "yn.ssid": S("Eklenecek ağın adı (SSID)", "Name of the network to add (SSID)"),
  "yn.listeye_ekle": S("Listeye ekle", "Add to list"),
  "yn.ag_parola": S("Bu ağın parolası", "Password of this network"),
  "yn.parola_yaz": S("Parolayı yaz", "Write password"),
  "yn.web_parola": S("Yeni web parolası", "New web password"),
  "yn.web_parola_yaz": S("Web parolasını yaz", "Write web password"),
  "yn.koruma_kaldir": S("Korumayı kaldır", "Remove protection"),
  "yn.koruma_kaldir_emin": S("Eminim — komut ucu parolasız kalır", "Yes — the command endpoint stays without a password"),
  "yn.ag_durum": S("Ağ durumunu sor → Konsol", "Query network status → Console"),
  "yn.ag_ac": S("Ağı aç", "Turn network on"),
  "yn.ag_kapat": S("Ağı kapat", "Turn network off"),
  "yn.ag_kapat_emin": S("Eminim — sonraki açılışta ağ kapanır, geri açmak USB ister", "Yes — the network is off from the next start; turning it back on needs USB"),
  "yn.ag_son_html": S("Listeye eklenen ağ <strong>bir sonraki bağlantı denemesinde</strong> geçerli; “Bu ağa geç” hemen. Ağ ayarları kalibrasyondan <em>ayrı</em> saklanıyor — WiFi parolası değiştirmek kalibrasyonu silmez.",
    "A network added to the list takes effect <strong>at the next connection attempt</strong>; “Switch to this network” acts immediately. Network settings are stored <em>separately</em> from calibration — changing the Wi-Fi password does not erase calibration."),
  "yn.hata_ssid": S("Ağ adı boş olamaz", "The network name cannot be empty"),
  "yn.hata_parola": S("Parola boş olamaz — parolasız (açık) ağ için Konsol'dan Np gönderin.", "The password cannot be empty — for an open network without a password, send Np from the Console."),
  "yn.hata_web_parola": S("Web parolası boş olamaz — korumayı kaldırmak için “Korumayı kaldır”ı kullanın.", "The web password cannot be empty — to remove protection, use “Remove protection”."),
  // ── Gorunum karti (tema adlari: ekran/tema.js TEMALAR kimlikleri)
  "yn.gorunum": S("Görünüm", "Appearance"),
  "yn.tema_sistem": S("Sistem", "System"),
  "yn.tema_sistem_alt": S("işletim sisteminin açık/koyu tercihine uyar", "follows the operating system's light/dark preference"),
  "yn.tema_koyu": S("Koyu", "Dark"),
  "yn.tema_koyu_alt": S("varsayılan — tezgah aleti", "default — bench instrument"),
  "yn.tema_acik": S("Açık", "Light"),
  "yn.tema_acik_alt": S("aydınlık ortam", "bright surroundings"),
  "yn.tema_onpanel": S("Ön panel", "Front panel"),
  "yn.tema_onpanel_alt": S("grafit + turuncu, cihaz ön paneli", "graphite + orange, instrument front panel"),
  "yn.gorunum_ipucu_html": S("<b>Sistem</b> işletim sisteminin açık/koyu tercihine uyar ve o değişince kendiliğinden geçer. Seçim bu tarayıcıda saklanır (cihaz başına); grafikler yeni renklerle yeniden çizilir.",
    "<b>System</b> follows the operating system's light/dark preference and switches when it changes. The choice is stored in this browser (per device); charts are redrawn in the new colours."),
  // ── Konsol
  "yn.konsol_baslik": S("Konsol — kartla ham konuşma", "Console — raw conversation with the board"),
  "yn.konsol_ipucu_html": S("Karttan gelen her satır burada — saniyede 20 kez gelen <code>D</code> ölçüm satırı, <code>W</code> hızlı ölçüm satırı ve skop dökümünün ham örnekleri hariç (onlar panelde). <code>y</code> yazıp göndermek komut listesini verir. Panelin gösterdiği her şey bu satırlardan türetiliyor — bir değerden şüphelenirseniz kaynağı burada.",
    "Every line from the board appears here — except the <code>D</code> measurement line that arrives 20 times a second, the <code>W</code> fast-measurement line and the raw samples of scope dumps (those are in the panel). Sending <code>y</code> lists the commands. Everything the panel shows is derived from these lines — if you doubt a value, its source is here."),
  "yn.komut_yaz": S("komut yazın (y = yardım)…", "type a command (y = help)…"),
  "yn.kart_komutu": S("Kart komutu", "Board command"),
  "yn.gonder": S("Gönder", "Send"),
  "yn.gunluk_temizle": S("Günlüğü temizle", "Clear log"),
  "yn.satir_yok": S("Henüz satır yok — karta bağlanın.", "No lines yet — connect to the board."),
  "yn.kart_satirlari": S("Kart satırları", "Board lines"),
});

/** Ayarlar / Konsol kabugunun metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriYonetim(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_YONETIM, anahtar, dil, degiskenler);
}
