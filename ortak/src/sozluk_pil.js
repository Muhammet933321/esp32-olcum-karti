// PT7 (2026-10-07) — PIL TESTI IYILESTIRMESI'nin metinleri + hesabi (tasarim/2026-10-07-pil-iyilestirme.md, PT2–PT7):
// kayit hizi secici + tahmini sure, ic direnc (DCIR) ac/kapa, OCV on evresi seridi + egri lejanti, DCIR kapali metni,
// kart istenenden farkli ayarla calisiyor uyarisi. Gosteren bilesen ekran/pil.js PilPt (sablonu telefon paketinde
// derlenir); bu dosyayi YALNIZ o bilesen DINAMIK indirir (Pil sekmesinde). NEDEN AYRI: acilis kumesi (EU31 / #/skop),
// Karsilastirma (KU1: pil.js'i statik indirir) ve #/pil acilisi (13 dosya) butcelerinin dibinde.
// app.js yalniz durumu tutar (pilKayitHz, pilDcirAcik, pilEvre, pilKart*, pilPtDestek, pilIstenen), Pr -> Pd -> P -> p1
// sirasini gonderir ve `/pil` PT alanlarini okur. Inmezse: DURDUR, okumalar, kesme formu calisir (PU1); baslatma
// varsayilani (1/s, DCIR KAPALI) gonderir. Kurallar sozluk.js'inkiyle AYNI (test/sozluk_pil.test.js).

import { sozluktenCeviri } from "./sozluk.js";

const S = (tr, en) => Object.freeze({ tr, en });

export const SOZLUK_PIL = Object.freeze({
  // ── form: kayit hizi (PT3 `Pr<hz>`)
  "pt.kayit_hizi": S("Kayıt hızı", "Recording rate"),
  "pt.her_ornek": S("Her örnek (~{n}/s)", "Every sample (~{n}/s)"),
  "pt.sure": S("Bu hızda en çok ~{sure} kayıt ({kaynak}).", "At this rate up to ~{sure} of recording ({kaynak})."),
  "pt.saat": S("{n} sa", "{n} h"),
  "pt.dakika": S("{n} dk", "{n} min"),
  "pt.kaynak_kart": S("kartın boş kayıt yeri ~{mb} MB", "board's free recording space ~{mb} MB"),
  "pt.kaynak_bolum": S("{mb} MB kayıt bölümüne göre; kartın boş yeri bilinmiyor",
    "based on the {mb} MB recording partition; the board's free space is unknown"),
  "pt.uyari_her": S("Her örnek kaydı belleği yaklaşık 1 saatte doldurur. Daha uzun testte 1/s … 50/s seçin; 1/s noktalar her kipte sürer.",
    "Every-sample recording fills the memory in about 1 hour. For longer tests pick 1/s … 50/s; 1/s points continue in every mode."),
  // ── form: DCIR ac/kapa (PT5 `Pd1` / `Pd0`)
  "pt.dcir": S("İç direnç ölçümü (DCIR)", "Internal-resistance measurement (DCIR)"),
  "pt.dcir_ipucu": S("Açıkken yük her 5 dakikada 200 ms kesilir; kapalıyken (varsayılan) hiç kesilmez.",
    "When on, the load is cut for 200 ms every 5 minutes; when off (default) it is never cut."),
  "pt.kapali": S("kapalı", "off"),
  "pt.acik": S("açık", "on"),
  "pt.dcir_kapali": S("Bu testte iç direnç ölçümü kapalı — yük hiç kesilmiyor.",
    "Internal-resistance measurement is off in this test — the load is never cut."),
  // ── OCV on evresi (PT2)
  "pt.evre_ocv": S("OCV ölçülüyor (yük kapalı) — ilk {s} s", "Measuring OCV (load off) — first {s} s"),
  "pt.lejant_ocv": S("OCV · yük kapalı ilk {s} s", "OCV · load off for the first {s} s"),
  // ── kartin cevabi
  "pt.desteklenmiyor": S("Kartın firmware'i kayıt hızı ve DCIR seçimini bilmiyor (A3-PT1 gerekir): test kartın kendi ayarıyla başlar.",
    "The board firmware does not know the rate and DCIR options (needs A3-PT1): the test starts with the board's own settings."),
  "pt.farkli": S("Kart testi istenenden farklı ayarla sürdürüyor: kayıt {kart} (istenen {istenen}).",
    "The board runs the test with other settings than requested: recording {kart} (requested {istenen})."),
  "pt.farkli_dcir": S("Kart testi istenenden farklı ayarla sürdürüyor: DCIR {kart} (istenen {istenen}).",
    "The board runs the test with other settings than requested: DCIR {kart} (requested {istenen})."),
});

/** Pil testi iyilestirmesinin metni (yalniz bu sozluk). ATMAZ; bilinmeyen anahtar kendisi. */
export function ceviriPil(anahtar, dil = "tr", degiskenler = null) {
  return sozluktenCeviri(SOZLUK_PIL, anahtar, dil, degiskenler);
}

// ── hesap (saf) ────────────────────────────────────────────────────────────────────────────────────────
/** PT3: izinli kayit hizlari (pil_test.h pil_hz_izinli; B7 karsilastiriyor); 0 = her ornek. */
export const PIL_KAYIT_HIZLARI = Object.freeze([1, 5, 20, 50, 0]);
/** "Her ornek" kipinin yaklasik ornek hizi (sure tahmini; kart ~400…500/s olcer). */
export const PIL_HER_ORNEK_HZ = 400;
/** PT2: OCV evresi (pil_test.h PIL_OCV_MS). */
export const PIL_OCV_MS = 5000;
// Kayit yeri: bolum 0xB60000 B (partitions.csv `kayit`). NOKTA kaydi 16 B baslik + 4 + 28 x 36 B (kayit_oturum.h
// KAYIT_AZAMI_YUK 1012); AYRINTI kaydi 16 B baslik + 16 + 166 x 6 B. B7 firmware kaynagindan sinar. Her ornek
// kipinde 1/s noktalar da surer (PT4).
export const KAYIT_BOLUM_BAYT = 0xB60000;
export const PIL_NOKTA_BAYT = 1028 / 28;
export const PIL_AYRINTI_BAYT = 1028 / 166;

/** PT3: tercih -> izinli hiz; bos / tip disi / listede olmayan -> 1/s ("" ve null "her ornek" DEGIL). */
export function kayitHizNormal(x) {
  if ((typeof x !== "number" && typeof x !== "string") || String(x).trim() === "") return 1;
  const n = Number(x);
  return PIL_KAYIT_HIZLARI.includes(n) ? n : 1;
}

/** PT7: secilen hizda tahmini azami kayit suresi (s); bosBayt kartin bos kayit yeri. */
export function kayitSuresiS(hz, bosBayt) {
  const h = kayitHizNormal(hz);
  const bps = h > 0 ? h * PIL_NOKTA_BAYT : PIL_NOKTA_BAYT + PIL_HER_ORNEK_HZ * PIL_AYRINTI_BAYT;
  return Number.isFinite(bosBayt) && bosBayt > 0 ? bosBayt / bps : 0;
}

/** PT7: kartin bos kayit yeri (B) G satirindan — onaylanmamis veri yer tutar (kayit_yonet.h KDR_DOLU); G yoksa null. */
export function bosKayitBayt(g) {
  if (!g || !Number.isFinite(g.onaysiz)) return null;
  return KAYIT_BOLUM_BAYT * (1000 - Math.min(1000, Math.max(0, g.onaysiz))) / 1000;
}

/** PT7: sure (s) -> {anahtar: 'pt.saat' | 'pt.dakika', n}; 10 sa altinda bir ondalik. */
export function sureKisa(s) {
  if (!(s >= 60)) return { anahtar: "pt.dakika", n: s > 0 ? "1" : "0" };
  if (s < 3600) return { anahtar: "pt.dakika", n: String(Math.round(s / 60)) };
  const sa = s / 3600;
  return { anahtar: "pt.saat", n: sa < 10 ? sa.toFixed(1) : String(Math.round(sa)) };
}

/** PT7: kart istenenden farkli hiz / DCIR'la mi calisiyor: null | {tur: 'hz' | 'dcir', kart, istenen}. */
export function ayarFarki(istenen, kartHz, kartDcir) {
  if (!istenen) return null;
  if (Number.isFinite(kartHz) && Math.abs(kartHz - istenen.hz) > 1e-6) return { tur: "hz", kart: kartHz, istenen: istenen.hz };
  const d = istenen.dcir ? 1 : 0;
  return (kartDcir === 0 || kartDcir === 1) && kartDcir !== d ? { tur: "dcir", kart: kartDcir, istenen: d } : null;
}

// Tercih app.js ayarOku/ayarYaz ile ayni anahtarlarda (`olcum.<ad>`, JSON); depo yoksa (ozel kip) yalniz bu oturum.
function tercihOku(ad) {
  try { const v = globalThis.localStorage.getItem("olcum." + ad); return v === null ? undefined : JSON.parse(v); } catch (h) { return undefined; }
}

/** PT7: formun secimini tarayicida sakla; degeri dondurur (bilesen app.js'e olayla verir). */
export function tercih(ad, v) {
  try { globalThis.localStorage.setItem("olcum." + ad, JSON.stringify(v)); } catch (h) { /* ozel kip */ }
  return v;
}

/** PT7: form kurulunca kayitli tercih — app.js'teki degerden farkliysa ver(ad, deger) ('hz' / 'dcir'); bozuk hiz 1/s. */
export function tercihVer(d, ver) {
  const h = tercihOku("pilKayitHz");
  if (h !== undefined && kayitHizNormal(h) !== d.pilKayitHz) ver("hz", kayitHizNormal(h));
  const dc = tercihOku("pilDcir") === true;
  if (dc !== d.pilDcirAcik) ver("dcir", dc);
}

/**
 * PT7: ekran/pil.js PilPt'nin gosterdigi her metin (sablon yalniz bunlari basar). d: app.js'in $data'si
 * (pilKayitHz, pilDcirAcik, pilPtDestek, pilIstenen, pilKartHz, pilKartDcir, pilDurum, pilKayitOzet, pilNokta,
 * kayit.g, dil). Bos dizgi = o oge cizilmez (uyariHer, desteklenmiyor, fark, lejant).
 */
export function ptGorunum(d) {
  const t = (k, v = null) => ceviriPil(k, d.dil, v);
  const hizAd = (h) => (h > 0 ? h + "/s" : t("pt.her_ornek", { n: PIL_HER_ORNEK_HZ }));
  const bos = bosKayitBayt(d.kayit && d.kayit.g);
  const bayt = bos === null ? KAYIT_BOLUM_BAYT : bos;
  const s = sureKisa(kayitSuresiS(d.pilKayitHz, bayt));
  const f = d.pilDurum === "CALISIYOR" ? ayarFarki(d.pilIstenen, d.pilKartHz, d.pilKartDcir) : null;
  const acik = (x) => t(x ? "pt.acik" : "pt.kapali");
  const bant = d.pilKayitOzet ? !!d.pilKayitOzet.ocv : d.pilPtDestek === true && d.pilNokta.length > 0;
  const ocvS = PIL_OCV_MS / 1000;
  return {
    hizlar: PIL_KAYIT_HIZLARI.map((h) => ({ v: h, ad: hizAd(h) })),
    hizEtiket: t("pt.kayit_hizi"),
    sure: t("pt.sure", { sure: t(s.anahtar, { n: s.n }),
      kaynak: t(bos === null ? "pt.kaynak_bolum" : "pt.kaynak_kart", { mb: (bayt / 1e6).toFixed(1) }) }),
    uyariHer: d.pilKayitHz === 0 ? t("pt.uyari_her") : "",
    dcirEtiket: t("pt.dcir"),
    dcirIpucu: t("pt.dcir_ipucu"),
    desteklenmiyor: d.pilPtDestek === false ? t("pt.desteklenmiyor") : "",
    evre: t("pt.evre_ocv", { s: ocvS }),
    fark: !f ? "" : f.tur === "hz" ? t("pt.farkli", { kart: hizAd(f.kart), istenen: hizAd(f.istenen) })
      : t("pt.farkli_dcir", { kart: acik(f.kart), istenen: acik(f.istenen) }),
    lejant: bant ? t("pt.lejant_ocv", { s: ocvS }) : "",
    dcirKapali: t("pt.dcir_kapali"),
    kapali: t("pt.kapali"),
  };
}
