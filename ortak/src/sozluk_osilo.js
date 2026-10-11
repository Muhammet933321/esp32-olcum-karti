// 5.12.121 (CE) — OSILOSKOP EKRANININ KABUKTAKI METINLERI: index.html'deki #/skop sablonu (yakinlastirma, durum
// satiri, eksen uyarilari, tetik secenekleri, CAL ipucu, hizli olcum bolumu) ve app.js'in hesapladiklari (zaman
// tabani birimi, olcum tablosu adlari, yakalama uyarilari, skop.bin hatalari). Gosteren: app.js + index.html
// (skMetin). ekran/osiloskop.js'in kendi bilesenlerinin metinleri ayri (sozluk_skop.js, sz.).
// NEDEN AYRI: acilis sozlugu (EU32) ve eslesmis acilis (EU31) dolu; #/skop acilisi 14 dosyanin sinirinda (statik
// ice aktarma 15 yapardi). app.js bu dosyayi osiloskop modulu ile BIRLIKTE DINAMIK indirir (skopYukle); ekran ancak
// ikisi inince 'hazir'. Kurallar sozluk.js'inkiyle AYNI (test/sozluk_osilo.test.js).
// ⚠ sk.menzil_1'deki sayilar tasarim3_sabit.SKOP_MENZIL_EKSI / _ARTI ile AYNI (sim3_bant.py 9 iki dili de sinar).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_OSILO = Object.freeze({
  // ── demo seridi (?demo)
  "sk.demo_sinyal": S("Prob ucundaki test sinyali", "Test signal at the probe tip"),
  "sk.demo_not": S("karta bağlı değil — sahte kart aynı protokolü konuşuyor", "not connected to a board — a simulated board speaks the same protocol"),
  // ── eski arsivden acilan yakalama seridi (B35)
  "sk.arsiv_serit": S("{gun} · köprü açıldıktan {sure} sonra yakalandı — canlı değil",
    "{gun} · captured {sure} after the bridge started — not live"),
  // ── yakinlastirma satiri
  "sk.dikey": S("Dikey", "Vertical"),
  "sk.yatay": S("Yatay", "Horizontal"),
  "sk.uzaklastir": S("Uzaklaştır", "Zoom out"),
  "sk.yakinlastir": S("Yakınlaştır", "Zoom in"),
  "sk.dikey_uzak": S("Dikey uzaklaştır", "Vertical zoom out"),
  "sk.dikey_yakin": S("Dikey yakınlaştır", "Vertical zoom in"),
  "sk.yukari": S("Yukarı kaydır", "Scroll up"),
  "sk.asagi": S("Aşağı kaydır", "Scroll down"),
  "sk.oto_olcek": S("Otomatik ölçeğe dön", "Back to auto scale"),
  "sk.oto": S("oto", "auto"),
  "sk.yatay_uzak": S("Yatay uzaklaştır", "Horizontal zoom out"),
  "sk.yatay_yakin": S("Yatay yakınlaştır", "Horizontal zoom in"),
  "sk.sola": S("Sola", "Left"),
  "sk.sola_kaydir": S("Sola kaydır", "Scroll left"),
  "sk.saga": S("Sağa", "Right"),
  "sk.saga_kaydir": S("Sağa kaydır", "Scroll right"),
  "sk.tetige_git": S("Tetik anına git", "Go to the trigger point"),
  "sk.tam_kayda": S("Tam kayda dön", "Back to the full record"),
  "sk.tam": S("tam", "full"),
  "sk.tam_kayit": S("tam kayıt", "full record"),
  "sk.yuzde": S("%{n}", "{n}%"),
  "sk.fare": S("fare tekerleği: dikey · Shift+tekerlek: yatay", "mouse wheel: vertical · Shift+wheel: horizontal"),
  // ── olcum tablosu ve durum satiri
  "sk.periyot": S("Periyot", "Period"),
  "sk.periyodik_degil": S("periyodik değil", "not periodic"),
  "sk.vort": S("Vort", "Vmean"),
  "sk.yukselme": S("Yükselme", "Rise"),
  "sk.dusme": S("Düşme", "Fall"),
  "sk.cevrim": S("Çevrim", "Cycles"),
  "sk.bol": S("/böl", "/div"),
  "sk.durum": S("{adet} örnek · {hz} kSa/s · pencere {pencere} · {tetik}", "{adet} samples · {hz} kSa/s · window {pencere} · {tetik}"),
  "sk.tetiklendi": S("tetiklendi", "triggered"),
  "sk.serbest": S("serbest koşu", "free-running"),
  "sk.yakalama_sn": S("{n} yakalama/sn", "{n} captures/s"),
  "sk.eksen_kalibre": S("eksen kalibre", "axis calibrated"),
  "sk.eksen_kalibre_ipucu": S("Gerilim ekseni çipin kendi eFuse eğrisiyle düzeltiliyor", "The voltage axis is corrected with the chip's own eFuse curve"),
  "sk.eksen_ham": S("eksen HAM", "axis RAW"),
  "sk.eksen_ham_ipucu": S("Kart kalibrasyon tablosu vermedi — eksen sabit çarpanla çiziliyor",
    "The board sent no calibration table — the axis is drawn with a fixed factor"),
  "sk.tetiklenemedi": S("tetiklenemedi — serbest koşu, iz kayabilir", "not triggered — free-running, the trace may drift"),
  "sk.cevrim_az": S("ekranda bir tam çevrim yok — zaman tabanını yavaşlat", "less than one full cycle on screen — slow down the timebase"),
  "sk.cevrim_cok": S("çok fazla çevrim — zaman tabanını hızlandır", "too many cycles — speed up the timebase"),
  // ── eksen duzeltmesiz uyarisi (yakalama yokken de)
  "sk.duz_1": S("⚠ Gerilim ekseni", "⚠ Voltage axis"),
  "sk.duz_2": S("düzeltmesiz", "uncorrected"),
  "sk.duz_3": S(": ham ADC kodu sabit bir çarpanla çevriliyor. Kartta ölçüldü — bu varsayım girişte",
    ": raw ADC codes are converted with a fixed factor. Measured on the board, this assumption is off by"),
  "sk.duz_4": S("9 V'a varan", "up to 9 V"),
  "sk.duz_5": S("sapma veriyor (tam ölçeğin %8'i). Kart", "at the input (8% of full scale). If the board answers the"),
  "sk.duz_6": S("komutuna yanıt verirse düzeltme kendiliğinden devreye girer.", "command, the correction turns on by itself."),
  "sk.esik_1": S("⚠ Tetik seviyesi ({v} V) sinyalin dışında — hiçbir zaman tetiklenmez. Kaydırıcıyı dalganın içine getir ya da",
    "⚠ The trigger level ({v} V) is outside the signal — it will never trigger. Move the slider into the waveform or press"),
  "sk.esik_2": S("'e bas.", "."),
  "sk.menzil_1": S("Menzil −63.5 … +46.8 V, çift yönlü.", "Range −63.5 … +46.8 V, bipolar."),
  "sk.menzil_2": S("Alt uç GND'de değil VREF'te; negatif sinyal de okunur. Menzil dışı kırpılır — sinyal üretecinde",
    "The low end sits at VREF, not GND, so negative signals are read too. Out-of-range input is clipped — use"),
  "sk.menzil_3": S("kullan. Örtüşme (aliasing) sınırı: girişteki 1 nF + 100 K süzgeci 25 kHz'te kesiyor, Nyquist 41.7 kHz. Bunun üstündeki bileşenler sahte, yavaş bir sinyal olarak görünür.",
    "on the signal generator. Aliasing limit: the 1 nF + 100 K input filter cuts at 25 kHz, Nyquist is 41.7 kHz. Components above that show up as a false, slow signal."),
  "sk.menzil_4": S("Şebekeye bağlanamaz", "Do not connect to mains"),
  "sk.menzil_5": S("— kart izole değil.", "— the board is not isolated."),
  // ── tetik kumesi
  "sk.kip_ipucu": S("Tetikleme kipi", "Trigger mode"),
  "sk.kenar_ipucu": S("Tetik kenarı", "Trigger edge"),
  "sk.onay_ipucu": S("Tetik onayı: iki örnek = gürültü reddi (tek-örnek iğne tetiklemez); tek örnek = yavaş tabanda tek örnek süren darbe için",
    "Trigger confirmation: two samples = noise reject (a one-sample spike does not trigger); one sample = for a pulse lasting a single sample on a slow timebase"),
  "sk.onay_iki": S("Gürültü reddi (2 örnek)", "Noise reject (2 samples)"),
  "sk.onay_tek": S("Tek örnek", "Single sample"),
  // ── kalibrasyon cikisi (CAL)
  "sk.cal_ipucu": S("GPIO10'da %50 kare dalga", "50% square wave on GPIO10"),
  "sk.cal_uretiyor": S("kart {hz} Hz üretiyor", "the board outputs {hz} Hz"),
  "sk.cal_bit": S("({n} bit görev)", "({n}-bit duty)"),
  "sk.cal_1": S("— skop ölçümünü", "— compare the scope reading with"),
  "sk.cal_2": S("bununla", "this"),
  "sk.cal_3": S("karşılaştır", "frequency"),
  "sk.cal_yok": S("GPIO10 → GPIO4 tek tel; skop zincirini bilinen sinyalle sınamak için",
    "GPIO10 → GPIO4 with one wire; tests the scope chain with a known signal"),
  // ── hizli olcum (B8)
  "sk.hizli_baslik": S("Hızlı ölçüm — gerçek güç ve güç faktörü", "Fast measurement — real power and power factor"),
  "sk.hizli_1": S("ESP32'nin dahili ADC'si iki kanalı", "The ESP32's internal ADC reads both channels at"),
  "sk.hizli_2": S("ile okuyup", "and computes"),
  "sk.hizli_3": S("hesaplıyor. Akım örnekleri yarım örnek geç alındığı için Lagrange hizalayıcıyla geri kaydırılıyor — reaktif yükte düzeltmesiz sonuç %78'e varan hata veriyor.",
    "from them. Current samples are taken half a sample late, so a Lagrange aligner shifts them back — on a reactive load the uncorrected result is off by up to 78%."),
  "sk.ort_vi": S("ort(V×I)", "mean(V×I)"),
  "sk.hizli_yap": S("Hızlı ölçüm yap", "Run fast measurement"),
  "sk.gercek_guc": S("Gerçek güç", "Real power"),
  "sk.guc_faktoru": S("Güç faktörü", "Power factor"),
  "sk.gorunur": S("görünür {s} VA", "apparent {s} VA"),
  "sk.ma_ornek": S("{ma} mA · {n} örnek", "{ma} mA · {n} samples"),
  "sk.olcek_kalibre": S("ölçekleme kalibre", "scaling calibrated"),
  "sk.olcek_kalibre_ipucu": S("Ham kodlar çipin eFuse eğrisiyle mV'a çevrildi", "Raw codes were converted to mV with the chip's eFuse curve"),
  "sk.olcek_ham": S("ölçekleme HAM", "scaling RAW"),
  "sk.olcek_ham_ipucu": S("Kart kalibrasyon tablosu kuramadı", "The board could not build a calibration table"),
  "sk.olcek_yok": S("ölçekleme bilinmiyor", "scaling unknown"),
  "sk.olcek_yok_ipucu": S("Eski firmware bu bilgiyi göndermiyor", "Older firmware does not send this"),
  "sk.ofset_1": S("— doğrusal ADC modeli sıfır girişte", "— the linear ADC model gives an offset of"),
  "sk.ofset_2": S("ofset veriyor; P, Vrms ve PF buna göre", "at zero input; P, Vrms and PF are therefore"),
  "sk.ofset_3": S("yanlış", "wrong"),
  "sk.sifir_1": S("⚠️ Kalibrasyonla bile ön uç kurulunca bir", "⚠️ Even with calibration, once the front end is built a"),
  "sk.sifir_2": S("sıfır kalibrasyonu", "zero calibration"),
  "sk.sifir_3": S("gerekecek: kalan belirsizlik girişte ~0.8 V / ~47 mA. Mutlak watt değeri için yukarıdaki",
    "will be needed: the remaining uncertainty is ~0.8 V / ~47 mA at the input. For absolute watts the"),
  "sk.sifir_4": S("D satırı", "D line"),
  "sk.sifir_5": S("(ADS1115) geçerli; burası", "(ADS1115) above is authoritative; this section is for"),
  "sk.sifir_6": S("güç faktörü ve dalga şekli", "power factor and waveform shape"),
  "sk.sifir_7": S("için.", "only."),
  "sk.hizalama_yok": S("hizalama farkı yok (dirençsel)", "no alignment difference (resistive)"),
  "sk.hizalama": S("hizalama {y}% düzeltti", "alignment corrected {y}%"),
  // ── hatalar (app.js; kartin / koprunun sebebi OLDUGU GIBI eklenir)
  "sk.ikili_yok": S("İkili skop dökümü alınamadı", "Could not fetch the binary scope dump"),
  "sk.bin_kisa": S("skop.bin çok kısa", "skop.bin is too short"),
  "sk.bin_imza": S("skop.bin imzası yanlış", "skop.bin has a wrong signature"),
  "sk.bin_eksik": S("skop.bin eksik ({bayt} B, {adet} örnek)", "skop.bin is incomplete ({bayt} B, {adet} samples)"),
  "sk.ct_yok": S("Kalibrasyon tablosu okunamadı", "Could not read the calibration table"),
  "sk.liste_yok": S("Kayıt listesi alınamadı: {mesaj}", "Could not get the capture list: {mesaj}"),
  "sk.acilamadi_kod": S("Kayıt açılamadı ({kod})", "Could not open the capture ({kod})"),
  "sk.acilamadi": S("Kayıt açılamadı: {mesaj}", "Could not open the capture: {mesaj}"),
});

/** Osiloskop kabugunun metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriOsilo(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_OSILO, anahtar, dil, degiskenler);
}
