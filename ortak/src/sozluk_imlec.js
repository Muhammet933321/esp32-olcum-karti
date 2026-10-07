// 2026-10-07 — IMLEC OKUMASININ ACIKLAMASI ("ⓘ Bu değerler ne demek?"): Canli (dondurulmus grafik), kayit
// gorunumu ve Karsilastirma'daki A / B okuma izgarasinin her alani bir satir.
//
// ACILIS sozlugunden (sozluk.js) AYRI (EU30/EU32 deseni): yalniz ekran/imlec_aciklama.js bu dosyayi STATIK
// ice aktarir. Canli'da o modul app.js'te defineAsyncComponent ile, grafik DONDURULUNCA iner (okuma izgarasi
// ancak o zaman var); kayit gorunumu ve Karsilastirma onu zaten statik aliyor (Kayitlar zinciri).
// Metinler FORMULLERE gore yazildi (ortak/src/grafik.js imlecOkuma, istatistik.js istatistik / enerji,
// ekran/kayit_gorunum.js aralikEnerji): deger = imlece en yakin HAM ornek; ort = ornek ortalamasi (zaman
// agirlikli DEGIL); mAh = ∫ I dt, Wh = ∫ P dt, yamuk kurali, ISARETLI, bosluk (boslukMs) ustunden integral yok.
// Kurallar sozluk.js'inkiyle AYNI (test/sozluk_imlec.test.js).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_IMLEC = Object.freeze({
  "ia.dugme": S("Bu değerler ne demek?", "What do these values mean?"),
  "ia.baslik": S("İmleç okumasının açıklaması", "Cursor reading explained"),
  // ── terimler (ekrandaki etiketlerle ayni)
  "ia.t_ab": S("A · B", "A · B"),
  "ia.t_dt": S("Δt", "Δt"),
  "ia.t_deger_canli": S("V A/B · I A/B · W A/B", "V A/B · I A/B · W A/B"),
  "ia.t_deger_kayit": S("V (A) · V (B) …", "V (A) · V (B) …"),
  "ia.t_deger_kr": S("A · B sütunları", "A · B columns"),
  "ia.t_dv": S("ΔV", "ΔV"),
  "ia.t_fark": S("Δ (B − A)", "Δ (B − A)"),
  "ia.t_ort_i": S("A ort", "I avg"),
  "ia.t_ort": S("ort", "mean"),
  "ia.t_minmaks": S("en düşük · en yüksek", "min · max"),
  "ia.t_yuk": S("Yük (mAh)", "Charge (mAh)"),
  "ia.t_enerji": S("Enerji (Wh)", "Energy (Wh)"),
  "ia.t_sure": S("Ölçülen süre A–B", "Measured time A–B"),
  "ia.t_bosluk": S("Boşluklar", "Gaps"),
  // ── aciklamalar
  "ia.ab_canli": S("İki imlecin grafikteki zamanı. Çift tıklayın ya da A / B tuşuna basın; sürükleyerek taşıyın.",
    "The time of the two cursors on the chart. Double-click or press A / B; drag to move them."),
  "ia.ab_kayit": S("İki imlecin kaydın başından beri geçen zamanı. Çift tıklayın ya da A / B tuşuna basın; sürükleyerek taşıyın.",
    "The time of the two cursors since the start of the recording. Double-click or press A / B; drag to move them."),
  "ia.ab_kr": S("İki imlecin x eksenindeki yeri (seçili eksene göre: geçen süre, saat ya da mAh). Her kayıt bu aralıkta AYRI okunur.",
    "Where the two cursors sit on the x axis (by the selected axis: elapsed time, clock or mAh). Every recording is read SEPARATELY over this span."),
  "ia.dt": S("B − A: iki imleç arasındaki süre.", "B − A: the time between the two cursors."),
  "ia.deger": S("Kanalın A anındaki ve B anındaki değeri: imlece en yakın gerçek örnek, ara değer üretilmez.",
    "The channel's value at A and at B: the real sample nearest the cursor, nothing is interpolated."),
  "ia.deger_kr": S("Seçili kanalın o kayıttaki A ve B anındaki değeri (en yakın gerçek nokta). İmleç kaydın dışındaysa “—”.",
    "The selected channel's value in that recording at A and at B (nearest real point). “—” if the cursor is outside the recording."),
  "ia.dv": S("B'deki gerilim eksi A'daki gerilim.", "Voltage at B minus voltage at A."),
  "ia.fark": S("B'deki değer eksi A'daki değer.", "Value at B minus value at A."),
  "ia.ort_i": S("A ile B arasındaki akım örneklerinin ortalaması (burada A = amper). Zaman ağırlıklı değil, multimetre gibi.",
    "Mean of the current samples between A and B. Not time-weighted, like a multimeter."),
  "ia.ort": S("A ile B arasındaki noktaların ortalaması. Zaman ağırlıklı değil, multimetre gibi.",
    "Mean of the points between A and B. Not time-weighted, like a multimeter."),
  "ia.minmaks": S("A ile B arasındaki en küçük ve en büyük değer; her noktanın kendi aralığındaki en düşük / en yüksek ölçüm dahil.",
    "The smallest and largest value between A and B, including each point's own lowest / highest reading."),
  "ia.yuk": S("A ile B arasında akımın zamana göre integrali (yamuk kuralı). İşaretli: akım eksiyken (şarj, ters bağlantı) eksi birikir ve toplamdan düşer.",
    "The time integral of the current between A and B (trapezoidal rule). Signed: while the current is negative (charging, reversed) it adds up negative and reduces the total."),
  "ia.enerji": S("A ile B arasında gücün (V × I) zamana göre integrali. İşaret kuralı Yük ile aynı.",
    "The time integral of the power (V × I) between A and B. Same sign rule as Charge."),
  "ia.sure": S("İntegrale giren süre. Δt'den kısaysa aradaki boşluklar sayılmadı.",
    "The time that went into the integral. Shorter than Δt means gaps were left out."),
  "ia.bosluk": S("Verinin kesildiği aralığın (kayıt duraklaması, bağlantı kopması) üstünden integral alınmaz: o süre Yük'e ve Enerji'ye girmez.",
    "No integral is taken across a span where data stopped (recording paused, link lost): that time is not in Charge or Energy."),
});

/** Imlec aciklamasi metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriImlec(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_IMLEC, anahtar, dil, degiskenler);
}
