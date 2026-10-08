// HT5 (2026-10-08) — HAT DIRENCI DUZELTICISI: metinler + saf hesap + gonderim akisi (tasarim/2026-10-07-pil-iyilestirme.md
// HT1–HT5). Kart pil testinin gerilimini V_pil = V + I x R ile duzeltir; D satiri (Canli), olcum oturumlari, skop ve akim
// HAM kalir. Pil sekmesindeki ozet ("Hat direnci: n mΩ" + V kartindaki "ham") ortak/sozluk_pil.js'te; bu dosyayi YALNIZ
// ekran/pil_hat.js (duzeltici bileseni) indirir — o da kullanici "Ayarla…"ya basinca DINAMIK iner (#/pil acilisi ve
// acilis butceleri degismez). Gonderim app.js pilAyarGonder ile (Pr / Pd'nin onay bekleyisi): kartin onayi
// `* pil hat direnci <n> mOhm`, reddi `! Ph: 0..1000 mOhm`. Kurallar sozluk.js'inkiyle AYNI (test/sozluk_hat.test.js).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_HAT = Object.freeze({
  "ht.giris": S("Elle (mΩ, 0…1000)", "Manual (mΩ, 0…1000)"),
  "ht.yaz": S("Ayarla", "Set"),
  "ht.ipucu": S("Pil testinde gerilim pil kutuplarına göre düzeltilir: V + I × R (kablo ve temas direnci). Canlı ekran, ölçüm kayıtları, osiloskop ve akım ham kalır. Kart değeri saklar; 0 = telafi yok.",
    "In the battery test the voltage is corrected to the cell terminals: V + I × R (lead and contact resistance). The live screen, measurement recordings, oscilloscope and current stay raw. The board stores the value; 0 = no compensation."),
  "ht.mm": S("Multimetre (V, pil kutuplarında)", "Multimeter (V, at the cell terminals)"),
  "ht.duzelt": S("Multimetreyle düzelt", "Correct with multimeter"),
  "ht.kosul": S("Multimetreyle düzeltme yalnız test sürerken ve akım ≥ 0,1 A iken.",
    "Multimeter correction only while the test runs and the current is ≥ 0.1 A."),
  "ht.mm_ipucu": S("Multimetreyi doğrudan pilin kutuplarına tutun, okuduğunuz gerilimi yazın.",
    "Hold the multimeter directly on the cell terminals and type the voltage you read."),
  "ht.oneri": S("Yeni hat direnci {yeni} mΩ (şimdi {eski} mΩ): gösterilen {v} V, multimetre {mm} V, akım {i} A.{kirp} Karta gönderilsin mi?",
    "New lead resistance {yeni} mΩ (now {eski} mΩ): shown {v} V, multimeter {mm} V, current {i} A.{kirp} Send it to the board?"),
  "ht.kirp": S(" Hesap {ham} mΩ çıktı, 0…1000 sınırına kırpıldı.", " The result was {ham} mΩ, clipped to 0…1000."),
  "ht.gonder": S("Gönder", "Send"),
  "ht.vazgec": S("Vazgeç", "Cancel"),
  "ht.onay": S("Kart onayladı: hat direnci {n} mΩ.", "The board confirmed: lead resistance {n} mΩ."),
  "ht.ret": S("Kart reddetti: {satir}", "The board rejected: {satir}"),
  "ht.yanitsiz": S("Kart yanıt vermedi — değer kartın bir sonraki durumunda görünür.",
    "No answer from the board — the value shows with the board's next status."),
  "ht.hata_giris": S("Hat direnci 0 ile 1000 arasında tam sayı (mΩ) olmalı.", "The lead resistance must be a whole number 0 to 1000 (mΩ)."),
  "ht.hata_mm": S("Multimetre değerini volt olarak yazın (ör. 3,966).", "Type the multimeter value in volts (e.g. 3.966)."),
  "ht.bagli_degil": S("Kart bağlı değil.", "The board is not connected."),
});

/** Hat duzelticisinin metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriHat(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_HAT, anahtar, dil, degiskenler);
}

// ── hesap (saf) ────────────────────────────────────────────────────────────────────────────────────────
/** HT1: pil_test.h PIL_HAT_AZAMI_MOHM (B7 karsilastiriyor). */
export const PIL_HAT_AZAMI_MOHM = 1000;
/** HT5: multimetre duzeltmesi en az bu akimda (A) — kucuk akimda (V_mm − V) / I olcum gurultusunu buyutur. */
export const PIL_HAT_ENAZ_A = 0.1;

/** HT2: pil kutuplarindaki gerilim (kartin pil_v_duzelt'i): R <= 0 iken HAM AYNEN (I NaN olsa bile). */
export function hatDuzelt(v, i, mohm) {
  return mohm > 0 ? v + i * (mohm / 1000) : v;
}

/** HT1: elle giris -> {mohm} | {hata}; kartin pil_ph_ayir kurali (yalniz rakam, bastaki sifir yok, <= 1000). */
export function hatGiris(x) {
  const s = typeof x === "number" || typeof x === "string" ? String(x).trim() : "";
  const n = Number(s);
  return /^(0|[1-9]\d{0,3})$/.test(s) && n <= PIL_HAT_AZAMI_MOHM ? { mohm: n } : { hata: "ht.hata_giris" };
}

/** HT5: multimetre girisi (V; virgul ondalik) -> sayi | null; 0 < V <= 38.5 (pil_test.h PIL_AZAMI_V). */
export function mmGiris(x) {
  const s = typeof x === "number" || typeof x === "string" ? String(x).trim().replace(",", ".") : "";
  const v = Number(s);
  return /^\d{1,2}(\.\d{1,4})?$/.test(s) && v > 0 && v <= 38.5 ? v : null;
}

/**
 * HT5: R_yeni = R_eski + (V_multimetre − V_gosterilen) / I  (mΩ; V_gosterilen = hatDuzelt(V, I, R_eski) — Pil sekmesinin
 * V kartindaki sayi). En yakin mΩ'a yuvarlanir, 0…1000'e KIRPILIR. I < PIL_HAT_ENAZ_A ya da sayi olmayan girdi -> null.
 */
export function hatOneri(eskiMohm, vMm, vGos, i) {
  if (![eskiMohm, vMm, vGos, i].every(Number.isFinite) || !(i >= PIL_HAT_ENAZ_A)) return null;
  const ham = Math.round(eskiMohm + (vMm - vGos) / i * 1000);
  const yeni = Math.min(PIL_HAT_AZAMI_MOHM, Math.max(0, ham));
  return { yeni, ham, kirpildi: yeni !== ham };
}

/** Canli V/I (D satiri) gecerli ve test suruyor mu; u: app ($root). */
function canli(u) {
  return u.pilDurum === "CALISIYOR" && !u.voltGecersiz && !u.amperGecersiz && !u.veriYok
    && Number.isFinite(u.volt) && Number.isFinite(u.amper);
}

/** Multimetre duzeltmesi su an yapilabilir mi (test suruyor, I >= 0.1 A). */
export function mmAcikMi(u) {
  return canli(u) && u.amper >= PIL_HAT_ENAZ_A;
}

/**
 * ekran/pil_hat.js PilHat'in gosterdigi her metin. u: app ($root: pilDurum, volt, amper, voltGecersiz, amperGecersiz,
 * veriYok, pilBaslatiliyor, dil); y: bilesenin durumu (hatGiris, mmGiris, oneri, mesgul, sonuc).
 */
export function hatGorunum(u, y) {
  const t = (k, v = null) => ceviriHat(k, u.dil, v);
  const mmAcik = mmAcikMi(u);
  const o = y.oneri;
  const s = y.sonuc;
  return {
    giris: t("ht.giris"), yaz: t("ht.yaz"), ipucu: t("ht.ipucu"), mm: t("ht.mm"), duzelt: t("ht.duzelt"),
    mmIpucu: t(mmAcik ? "ht.mm_ipucu" : "ht.kosul"), mmAcik, mesgul: !!y.mesgul || !!u.pilBaslatiliyor,
    oneri: o ? t("ht.oneri", { yeni: o.yeni, eski: o.eski, v: o.v.toFixed(3), mm: o.mm.toFixed(3), i: o.i.toFixed(3),
      kirp: o.kirpildi ? t("ht.kirp", { ham: o.ham }) : "" }) : "",
    gonder: t("ht.gonder"), vazgec: t("ht.vazgec"),
    sonuc: s ? t(s.a, s.d || null) : "", sonucHata: !!s && s.a !== "ht.onay",
  };
}

/** `Ph<n>` -> kartin onayi (u.pilAyarGonder). Onayda app'in `pilHat`i hemen guncellenir (sonraki /pil dogrular). */
async function gonder(u, y, n) {
  if (!u.bagli) { y.sonuc = { a: "ht.bagli_degil" }; return false; }
  y.mesgul = true;
  y.sonuc = null;
  let r = {};
  try {
    r = (await u.pilAyarGonder("Ph" + n)) || {};
  } catch (h) {
    r = { tur: "ret", s: String((h && h.message) || h) };
  } finally {
    y.mesgul = false;
  }
  const m = r.tur === "ayar" ? /^\* pil hat direnci (\d+) mOhm/.exec(r.s || "") : null;
  if (m && Number(m[1]) === n) {
    y.sonuc = { a: "ht.onay", d: { n } };
    u.pilHat = String(n);
    return true;
  }
  y.sonuc = r.tur === "ret" ? { a: "ht.ret", d: { satir: r.s || "" } } : { a: "ht.yanitsiz" };
  return false;
}

/**
 * PilHat dugmeleri. a: 'yaz' (elle `Ph<n>`), 'oner' (multimetre -> oneri; tek onay ister), 'gonder' (oneriyi gonder),
 * 'vazgec'. r: kartin su anki R'si (mΩ, /pil hat_mohm). Gecersiz giris karta GITMEZ (sebep sonuc satirinda).
 * Donus Promise<bool>: gitti ve kart onayladi.
 */
export async function hatIslem(u, y, a, r) {
  if (y.mesgul) return false;
  if (a === "yaz") {
    const g = hatGiris(y.hatGiris);
    if (g.hata) { y.sonuc = { a: g.hata }; return false; }
    const ok = await gonder(u, y, g.mohm);
    if (ok) y.hatGiris = "";
    return ok;
  }
  if (a === "oner") {
    y.oneri = null;
    if (!Number.isFinite(r) || !mmAcikMi(u)) { y.sonuc = { a: "ht.kosul" }; return false; }
    const mm = mmGiris(y.mmGiris);
    if (mm === null) { y.sonuc = { a: "ht.hata_mm" }; return false; }
    const v = hatDuzelt(u.volt, u.amper, r);
    y.sonuc = null;
    y.oneri = { ...hatOneri(r, mm, v, u.amper), eski: r, v, mm, i: u.amper };
    return false;
  }
  if (a === "gonder" && y.oneri) {
    const n = y.oneri.yeni;
    y.oneri = null;
    const ok = await gonder(u, y, n);
    if (ok) y.mmGiris = "";
    return ok;
  }
  if (a === "vazgec") y.oneri = null;
  return false;
}
