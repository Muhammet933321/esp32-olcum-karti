// B73 / 2F — TR/EN SOZLUK (ust tasarim §9 "Dil": metinler sozlukte, ekrana gomulu metin yok).
//
// SOZLUK[anahtar] = { tr, en }. Anahtarlar ASCII nokta ayrimli aileler:
//   sebep.<kod>  oturum.tur.<kod>  olay.<kod>  pil.durum.<kod>  pil.hata.<kod>
//   kal.tur.<kod>  kal.kaynak.<kod>  kal.durum.<ad>   (+ her ailede <onek>bilinmeyen: {kod})
//   bayrak.<ad>  csv.<sutun>  csv.kayit.<tur>  rapor.<alan>  alan.<olay alani>  uyari.<kod>
// Birimler SI ve dile gore DEGISMEZ (V, A, W, ohm, mAh, Wh, s, ms). CSV basliklari iki dilde
// de kucuk ASCII snake_case + birim soneki (kopru/arsiv.py D_BASLIK uslubu; Excel/pandas dostu).
//
// ceviri(anahtar, dil, degiskenler) HICBIR ZAMAN ATMAZ:
//   * bilinmeyen anahtar -> ANAHTARIN KENDISI (eksik ceviri ekranda gorunur, uygulama cokmez)
//   * dil 'tr' / 'en' disi -> 'tr'; o dilde metin yoksa (bos) obur dil, o da yoksa anahtar
//   * {ad} yer tutucusu degiskenler[ad] ile (String); verilmeyen yer tutucu oldugu gibi kalir
// ceviriKod(onek, kod, dil): onek+kod varsa onu, yoksa onek+"bilinmeyen" ({kod} ile).
// Kapsam (her SEBEP/OLAY/oturum turu/CSV basligi/rapor alani icin bos olmayan tr VE en; hic
// kullanilmayan anahtar yok) test/sozluk.test.js'te kaynaktan ve firmware basliklarindan olculur.

const S = (tr, en) => Object.freeze({ tr, en });

export const DILLER = Object.freeze(["tr", "en"]);

export const SOZLUK = Object.freeze({
  // ── BITIR sebepleri (kayit_bicim.h KB_SEBEP_*)
  "sebep.1": S("kullanıcı durdurdu", "stopped by user"),
  "sebep.2": S("bellek doldu", "storage full"),
  "sebep.3": S("hata", "error"),
  "sebep.4": S("pil testi bitti", "battery test finished"),
  "sebep.5": S("kart yeniden başladı", "board restarted"),
  "sebep.6": S("başka oturum başladı", "another session started"),
  "sebep.7": S("planlı süre doldu", "scheduled duration elapsed"),
  "sebep.bilinmeyen": S("bilinmeyen sebep ({kod})", "unknown reason ({kod})"),
  "sebep.acik": S("bitmedi (kayıt sürüyor ya da bitişi henüz eşitlenmedi)",
    "not finished (still recording or the end is not synced yet)"),

  // ── oturum turleri (kayit_bicim.h KAYIT_OTURUM_*)
  "oturum.tur.1": S("Ölçüm kaydı", "Measurement recording"),
  "oturum.tur.2": S("Pil testi", "Battery test"),
  "oturum.tur.3": S("Osiloskop günlüğü", "Oscilloscope log"),
  "oturum.tur.bilinmeyen": S("Bilinmeyen oturum türü ({kod})", "Unknown session type ({kod})"),

  // ── OLAY turleri (kayit_bicim.h KO_*)
  "olay.1": S("Pil testi ayarı", "Battery test settings"),
  "olay.2": S("DCIR ölçümü", "DCIR measurement"),
  "olay.3": S("Pil testi sonucu", "Battery test result"),
  "olay.4": S("Osiloskop kalibrasyon eğrisi", "Oscilloscope calibration curve"),
  "olay.5": S("Zamanlanmış kayıt", "Scheduled recording"),
  "olay.bilinmeyen": S("Bilinmeyen olay ({kod})", "Unknown event ({kod})"),

  // ── pil testi durum / hata (pil_test.h PilDurum / PilHata)
  "pil.durum.0": S("beklemede", "idle"),
  "pil.durum.1": S("çalışıyor", "running"),
  "pil.durum.2": S("bitti (kesme gerilimine ulaşıldı)", "finished (cut-off voltage reached)"),
  "pil.durum.3": S("kullanıcı durdurdu", "stopped by user"),
  "pil.durum.4": S("hata", "error"),
  "pil.durum.bilinmeyen": S("bilinmeyen durum ({kod})", "unknown state ({kod})"),
  "pil.hata.0": S("yok", "none"),
  "pil.hata.1": S("gerilim zaten kesme geriliminin altında", "voltage already below cut-off"),
  "pil.hata.2": S("gerilim 38.5 V üstünde (MOSFET Vdss sınırı)", "voltage above 38.5 V (MOSFET Vdss limit)"),
  "pil.hata.3": S("ters polarite", "reverse polarity"),
  "pil.hata.4": S("MOSFET kapalıyken akım var (yük J3'te)", "current flows with the MOSFET off (load on J3)"),
  "pil.hata.5": S("azami süre aşıldı", "maximum duration exceeded"),
  "pil.hata.6": S("yük bağlanmadı (akım akmadı)", "no load connected (no current)"),
  "pil.hata.bilinmeyen": S("bilinmeyen hata ({kod})", "unknown error ({kod})"),

  // ── kalibrasyon gecmisi (kalgec.h KGT_* / KGK_*) ve rapor durumu
  "kal.tur.0": S("belirsiz", "unspecified"),
  "kal.tur.1": S("donanım değişti", "hardware changed"),
  "kal.tur.2": S("ince ayar", "fine tuning"),
  "kal.tur.bilinmeyen": S("bilinmeyen tür ({kod})", "unknown type ({kod})"),
  "kal.kaynak.0": S("elle", "manual"),
  "kal.kaynak.1": S("otomatik (kayıt başlarken)", "automatic (at recording start)"),
  "kal.kaynak.2": S("ilk kayıt (1B öncesi kalibrasyon)", "initial entry (pre-1B calibration)"),
  "kal.kaynak.bilinmeyen": S("bilinmeyen kaynak ({kod})", "unknown source ({kod})"),
  "kal.durum.bulundu": S("geçmişte bulundu", "found in history"),
  "kal.durum.numarasiz": S("numarasız (geçmiş doluydu ya da eski biçim); değerler oturumun kopyasından",
    "unnumbered (history was full or old format); values from the session copy"),
  "kal.durum.gecmis_yok": S("kalibrasyon geçmişi verilmedi", "calibration history not provided"),
  "kal.durum.yok": S("bu numara geçmişte yok", "this number is not in the history"),
  "kal.durum.bozuk": S("kart bu kaydı okuyamadı (bozuk)", "the board could not read this entry (corrupt)"),
  "kal.durum.kopya_yok": S("oturum başlığı yok: kalibrasyon kopyası yok", "no session header: no calibration copy"),

  // ── bayrak adlari (CSV `bayraklar`; KN_* / KAO_* / KA_*)
  "bayrak.yuksek": S("YUKSEK", "HIGH_RANGE"),
  "bayrak.v_hata": S("V_HATA", "V_ERROR"),
  "bayrak.i_hata": S("I_HATA", "I_ERROR"),
  "bayrak.v_doydu": S("V_DOYDU", "V_SATURATED"),
  "bayrak.duraklama": S("DURAKLAMA", "PAUSE"),
  "bayrak.kayip_once": S("KAYIP_ONCE", "LOSS_BEFORE"),
  "bayrak.dcir": S("DCIR", "DCIR"),
  "bayrak.silme": S("SILME", "FLASH_ERASE"),

  // ── CSV basliklari (ASCII snake_case + SI birim soneki)
  "csv.kayit": S("kayit", "row_type"),
  "csv.kayit.nokta": S("nokta", "point"),
  "csv.kayit.dcir": S("dcir", "dcir"),
  "csv.sira": S("sira", "seq"),
  "csv.acilis": S("acilis", "boot"),
  "csv.devam": S("devam", "resumed"),
  "csv.kart_ms": S("kart_ms", "board_ms"),
  "csv.kart_us": S("kart_us", "board_us"),
  "csv.gecen_ms": S("gecen_ms", "elapsed_ms"),
  "csv.unix_s": S("unix_s", "unix_s"),
  "csv.zaman_utc": S("zaman_utc", "time_utc"),
  "csv.n": S("n", "n"),
  "csv.v_ort": S("v_ort_V", "v_avg_V"),
  "csv.v_min": S("v_min_V", "v_min_V"),
  "csv.v_maks": S("v_maks_V", "v_max_V"),
  "csv.i_ort": S("i_ort_A", "i_avg_A"),
  "csv.i_min": S("i_min_A", "i_min_A"),
  "csv.i_maks": S("i_maks_A", "i_max_A"),
  "csv.w_ort": S("w_ort_W", "p_avg_W"),
  "csv.w_min": S("w_min_W", "p_min_W"),
  "csv.w_maks": S("w_maks_W", "p_max_W"),
  "csv.v": S("v_V", "v_V"),
  "csv.i": S("i_A", "i_A"),
  "csv.w": S("w_W", "p_W"),
  "csv.bayrak": S("bayrak", "flags"),
  "csv.ornek_bayrak": S("ornek_bayrak", "sample_flags"),
  "csv.kayit_bayrak": S("kayit_bayrak", "record_flags"),
  "csv.bayraklar": S("bayraklar", "flag_names"),
  "csv.not": S("not", "note"),
  "csv.mah": S("yuk_mAh", "charge_mAh"),
  "csv.wh": S("enerji_Wh", "energy_Wh"),
  "csv.dcir_no": S("dcir_no", "dcir_no"),
  "csv.dcir_v_once": S("dcir_v_once_V", "dcir_v_before_V"),
  "csv.dcir_i_once": S("dcir_i_once_A", "dcir_i_before_A"),
  "csv.dcir_v_ani": S("dcir_v_ani_V", "dcir_v_instant_V"),
  "csv.dcir_v_oturmus": S("dcir_v_oturmus_V", "dcir_v_settled_V"),
  "csv.dcir_r_ani": S("dcir_r_ani_ohm", "dcir_r_instant_ohm"),
  "csv.dcir_r_oturmus": S("dcir_r_oturmus_ohm", "dcir_r_settled_ohm"),
  "csv.dcir_mah": S("dcir_yuk_mAh", "dcir_charge_mAh"),
  "csv.dcir_wh": S("dcir_enerji_Wh", "dcir_energy_Wh"),
  "csv.skop_ornek": S("ornek", "sample"),
  "csv.skop_t": S("t_s", "t_s"),
  "csv.skop_kod": S("kod", "code"),
  "csv.skop_v": S("v_V", "v_V"),

  // ── rapor alan etiketleri (rapor.js RAPOR_ETIKET)
  "rapor.kimlik": S("Kimlik", "Identity"),
  "rapor.oturum_no": S("Oturum no", "Session no"),
  "rapor.tur": S("Tür", "Type"),
  "rapor.ad": S("Ad", "Name"),
  "rapor.etiketler": S("Etiketler", "Tags"),
  "rapor.notlar": S("Notlar", "Notes"),
  "rapor.firmware": S("Firmware", "Firmware"),
  "rapor.hiz": S("Kayıt aralığı (ms; 0 = her örnek)", "Recording interval (ms; 0 = every sample)"),
  "rapor.ayrintili": S("Ayrıntılı kip (her örnek)", "Detailed mode (every sample)"),
  "rapor.basi_eksik": S("Başlık kopyadan (TEKRAR)", "Header from copy (TEKRAR)"),
  "rapor.zaman": S("Zaman", "Time"),
  "rapor.baslangic": S("Başlangıç", "Start"),
  "rapor.bitis": S("Bitiş", "End"),
  "rapor.toplam_sure": S("Toplam süre (boşluklar dahil, ms)", "Total duration (gaps included, ms)"),
  "rapor.olculen_sure": S("Ölçülen süre (ms)", "Measured duration (ms)"),
  "rapor.bosluk_sure": S("Boşluk süresi (ms)", "Gap duration (ms)"),
  "rapor.bosluk_adet": S("Boşluk sayısı", "Gap count"),
  "rapor.sayac": S("Sayılar", "Counts"),
  "rapor.nokta_adet": S("Nokta", "Points"),
  "rapor.ayrinti_adet": S("Örnek (ayrıntılı)", "Samples (detailed)"),
  "rapor.devam_adet": S("Yeniden başlayıp süren (DEVAM)", "Resumed after restart (DEVAM)"),
  "rapor.olay_adet": S("Olay", "Events"),
  "rapor.not_adet": S("Not", "Notes"),
  "rapor.skop_adet": S("Osiloskop yakalaması", "Oscilloscope captures"),
  "rapor.sebep": S("Bitiş sebebi", "Stop reason"),
  "rapor.bitir_nokta": S("Kartın saydığı nokta", "Points counted by the board"),
  "rapor.istatistik": S("İstatistik (ham veriden)", "Statistics (from raw data)"),
  "rapor.gerilim": S("Gerilim (V)", "Voltage (V)"),
  "rapor.akim": S("Akım (A)", "Current (A)"),
  "rapor.guc": S("Güç (W)", "Power (W)"),
  "rapor.adet": S("Adet", "Count"),
  "rapor.min": S("En düşük", "Minimum"),
  "rapor.maks": S("En yüksek", "Maximum"),
  "rapor.ort": S("Ortalama", "Mean"),
  "rapor.rms": S("RMS", "RMS"),
  "rapor.tepe_tepe": S("Tepeden tepeye", "Peak to peak"),
  "rapor.min_sira": S("En düşüğün sırası", "Sequence of minimum"),
  "rapor.maks_sira": S("En yükseğin sırası", "Sequence of maximum"),
  "rapor.min_zaman": S("En düşüğün zamanı (ms)", "Time of minimum (ms)"),
  "rapor.maks_zaman": S("En yükseğin zamanı (ms)", "Time of maximum (ms)"),
  "rapor.enerji": S("Enerji (boşluklar hariç)", "Energy (gaps excluded)"),
  "rapor.wh": S("Enerji (Wh)", "Energy (Wh)"),
  "rapor.mah": S("Yük (mAh)", "Charge (mAh)"),
  "rapor.pil": S("Pil testi", "Battery test"),
  "rapor.pil_ayar": S("Pil testi ayarı", "Battery test settings"),
  "rapor.pil_sonuc": S("Pil testi sonucu", "Battery test result"),
  "rapor.dcir": S("DCIR ölçümleri", "DCIR measurements"),
  "rapor.kalibrasyon": S("Kalibrasyon", "Calibration"),
  "rapor.kal_no": S("Kalibrasyon no", "Calibration no"),
  "rapor.kal_durum": S("Geçmişteki durumu", "Status in history"),
  "rapor.kal_kayit": S("Geçmiş kaydı", "History entry"),
  "rapor.kal_kopya": S("Oturumun kopyası (çevrimde kullanılan)", "Session copy (used for conversion)"),
  "rapor.olaylar": S("Olaylar", "Events"),
  "rapor.skop": S("Osiloskop", "Oscilloscope"),
  "rapor.yakalamalar": S("Yakalamalar", "Captures"),
  "rapor.skop_tam": S("Tam yakalama", "Complete captures"),
  "rapor.skop_eksik": S("Eksik yakalama", "Incomplete captures"),
  "rapor.uyarilar": S("Uyarılar", "Warnings"),
  "rapor.gecen": S("Başlangıçtan beri (ms)", "Since start (ms)"),
  "rapor.unix": S("Unix zamanı (s)", "Unix time (s)"),
  "rapor.iso": S("Tarih-saat (UTC)", "Date-time (UTC)"),
  "rapor.acilis": S("Açılış (0 = başlangıç)", "Boot (0 = start)"),

  // ── olay / pil alanlari (rapor.js ALAN_ETIKET)
  "alan.kesme_v": S("Kesme gerilimi (V)", "Cut-off voltage (V)"),
  "alan.ocv": S("Açık devre gerilimi (V)", "Open-circuit voltage (V)"),
  "alan.azami_s": S("Azami süre (s)", "Maximum duration (s)"),
  "alan.dcir_aralik_ms": S("DCIR aralığı (ms)", "DCIR interval (ms)"),
  "alan.dcir_ms": S("DCIR darbesi (ms)", "DCIR pulse (ms)"),
  "alan.kayit_hz": S("Kayıt hızı (Hz)", "Recording rate (Hz)"),
  "alan.no": S("No", "No"),
  "alan.v_once": S("Darbeden önce gerilim (V)", "Voltage before pulse (V)"),
  "alan.i_once": S("Darbeden önce akım (A)", "Current before pulse (A)"),
  "alan.v_ani": S("Anlık gerilim (V)", "Instant voltage (V)"),
  "alan.v_oturmus": S("Oturmuş gerilim (V)", "Settled voltage (V)"),
  "alan.r_ani": S("Anlık iç direnç (Ω)", "Instant internal resistance (Ω)"),
  "alan.r_oturmus": S("Oturmuş iç direnç (Ω)", "Settled internal resistance (Ω)"),
  "alan.mah": S("Yük (mAh)", "Charge (mAh)"),
  "alan.wh": S("Enerji (Wh)", "Energy (Wh)"),
  "alan.durum": S("Durum", "State"),
  "alan.hata": S("Hata", "Error"),
  "alan.v_son": S("Son gerilim (V)", "Final voltage (V)"),
  "alan.sure_ms": S("Süre (ms)", "Duration (ms)"),
  "alan.dcir_sayisi": S("DCIR sayısı", "DCIR count"),
  "alan.mv": S("Eğri (mV)", "Curve (mV)"),
  "alan.bas_unix": S("Başlangıç (unix s)", "Start (unix s)"),
  "alan.sure_s": S("Süre (s; 0 = durdurulana dek)", "Duration (s; 0 = until stopped)"),
  "alan.hiz_ms": S("Kayıt aralığı (ms)", "Recording interval (ms)"),
  "alan.plan_no": S("Plan no", "Plan no"),
  "alan.ham": S("Ham yük (hex)", "Raw payload (hex)"),

  // ── rapor uyarilari ({sayi}: adet)
  "uyari.baslik_yok": S("Oturum başlığı yok: kalibrasyon bilinmiyor, V ve A hesaplanamadı.",
    "No session header: calibration unknown, V and A could not be computed."),
  "uyari.basi_eksik": S("Başlık temizlikte silinmiş; sektör başı kopyasından (TEKRAR) okundu.",
    "Header was cleaned up; read from the sector copy (TEKRAR)."),
  "uyari.acik": S("Oturumun bitişi yok: kayıt sürüyor ya da sonu eşitlenmedi.",
    "Session has no end: still recording or the end is not synced."),
  "uyari.devam": S("Kart {sayi} kez yeniden başladı, kayıt sürdü (araya boşluk girdi).",
    "The board restarted {sayi} time(s) and recording resumed (gaps in between)."),
  "uyari.nokta_eksik": S("{sayi} nokta eksik (eşitlenmemiş ya da temizlenmiş).",
    "{sayi} point(s) missing (not synced or cleaned up)."),
  "uyari.bos_nokta": S("{sayi} noktada geçerli örnek yok (değerler boş).",
    "{sayi} point(s) have no valid sample (values empty)."),
  "uyari.kayip_once": S("{sayi} yerde kartın kuyruğu taştı, öncesinde veri düştü.",
    "Board queue overflowed at {sayi} place(s); data was dropped before them."),
  "uyari.duraklama": S("{sayi} noktada ölçüm durdu (ör. osiloskop yakalaması).",
    "Measurement paused at {sayi} point(s) (e.g. oscilloscope capture)."),
  "uyari.silme": S("{sayi} kez flaş silmesi ölçümü ~25 ms durdurdu.",
    "Flash erase paused measurement for ~25 ms {sayi} time(s)."),
  "uyari.v_hata": S("{sayi} kayıtta gerilim ADC'si okunamadı.", "Voltage ADC read failed in {sayi} record(s)."),
  "uyari.i_hata": S("{sayi} kayıtta akım ADC'si okunamadı.", "Current ADC read failed in {sayi} record(s)."),
  "uyari.v_doydu": S("{sayi} kayıtta gerilim girişi doydu.", "Voltage input saturated in {sayi} record(s)."),
  "uyari.saat_yok": S("Kartın saati bilinmiyordu: mutlak tarih-saat yok.",
    "Board clock was unknown: no absolute date-time."),
  "uyari.gecen_bilinmiyor": S("{sayi} satırda başlangıçtan beri geçen süre bilinmiyor (yeniden başlama sırasında saat yoktu).",
    "Elapsed time unknown for {sayi} row(s) (no clock across a restart)."),
  "uyari.zaman_belirsiz": S("{sayi} olayın hangi açılışa ait olduğu belirlenemedi (ham kayıtlar verilmedi).",
    "Boot of {sayi} event(s) could not be determined (raw records not provided)."),
  "uyari.not_belirsiz": S("{sayi} notun grafikteki yeri belirsiz (kart_ms birden fazla açılışa uyuyor ya da hiçbirine).",
    "Position of {sayi} note(s) is ambiguous (board_ms fits several boots or none)."),
  "uyari.olay_bilinmeyen": S("{sayi} olayın türü bu sürümde bilinmiyor.", "{sayi} event(s) of a type unknown to this version."),
  "uyari.skop_eksik": S("{sayi} osiloskop yakalaması eksik (parça eşitlenmemiş).",
    "{sayi} oscilloscope capture(s) incomplete (part not synced)."),
  "uyari.kal_farkli": S("Geçmişteki {no} numaralı kalibrasyon oturumun kopyasından farklı; çevrimde kopya kullanıldı.",
    "Calibration no {no} in history differs from the session copy; the copy was used."),
  "uyari.kal_gecersiz": S("Kalibrasyonda şönt direnci 0: akım hesaplanamadı.",
    "Shunt resistance is 0 in the calibration: current could not be computed."),
});

/** Sozlukten metin; ATMAZ (dosya basindaki kurallar). */
export function ceviri(anahtar, dil = "tr", degiskenler = null) {
  const a = typeof anahtar === "string" ? anahtar : String(anahtar);
  const g = Object.prototype.hasOwnProperty.call(SOZLUK, a) ? SOZLUK[a] : null;
  if (!g) return a;
  const d = dil === "en" ? "en" : "tr";
  const obur = d === "en" ? "tr" : "en";
  let m = g[d] || g[obur] || a;
  if (degiskenler && typeof degiskenler === "object") {
    m = m.replace(/\{([A-Za-z0-9_]+)\}/g, (tam, ad) => (
      Object.prototype.hasOwnProperty.call(degiskenler, ad) ? String(degiskenler[ad]) : tam));
  }
  return m;
}

/** Kod ailesinden metin: onek+kod varsa o, yoksa onek+"bilinmeyen" ({kod}). ATMAZ. */
export function ceviriKod(onek, kod, dil = "tr") {
  const a = `${onek}${kod}`;
  if (Object.prototype.hasOwnProperty.call(SOZLUK, a)) return ceviri(a, dil);
  return ceviri(`${onek}bilinmeyen`, dil, { kod });
}
