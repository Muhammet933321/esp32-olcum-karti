// Telefon ortaminin ARKA PLANI (5P K17): eski kabugun (src/ekran/kabuk_durum.js + App.vue) uygulama
// acilisinda kurdugu her sey, panelden BAGIMSIZ ve Vue'suz:
//   * kartin bulunmasi / baglanmasi (kart.baglan; bulunamazsa 15 s'de bir, akis 30 s hatadaysa yeniden arama)
//   * canli akis (cekirdek/canli.js): YALNIZ uygulama ondeyken VE panel tasiyiciya bagliyken acik (A22, A6);
//     arka plana gecince HEMEN kapanir, one donunce yeniden acilir — panel satirlarin yeniden geldigini gorur
//   * kayit esitlemesi (cekirdek/esitleme.js): baglaninca, kayit bitince ve 60 s'de bir, yalniz ondeyken (A22)
//   * bildirim izleyicisi (cekirdek/bildirim.js bildirimIzleyici): saniyede bir tik (A29, A31, A35)
//   * pil testi durumu (`GET /pil`, 30 s'de bir + kayit durumu degisince): ACIL DURDUR seridi (K9, pil_durum.js)
//   * bildirim dili = panelin dili (eski App.vue: bildirimAl().ayarYaz({ dil }))
//   * "anlik izleme" sorusunun kayit-bitti kapanisi (eski KayitDugmesi.vue)
//
//   const a = arkaPlanKur({ kartAl, canliAl, esitlemeAl, bildirimIzle, pilOku, izlemeSorusu, ... });
//   a.baslat();                 // belge gorunurlugunu dinler; gorunurse hemen ac()
//   a.akisIste(true / false);   // panel tasiyiciya baglandi / koptu
//   await a.baglan();           // kart bulunur (suren aramaya baglanir) -> { durum, adres, kimlik }
//   a.hamDinle(fn);  a.dinle(fn);   // ham akis satirlari / durum degisimi
//   a.seritGorunur();           // pil testinin SURMEDIGI kesin degilse true
//   a.baglantiDegisti(b);       // "Bu telefon" bolumunde baglan / esles / kaldir bitti
//   a.birak();
//
// ACIL DURDUR buradan GECMEZ (kendi yolu: cekirdek/uygulama.js acilDurdur). Hicbir hata disari cikmaz.

import { PIL_BILINMIYOR, PIL_YOKLAMA_MS, akisHali, durdurGorunur } from "../cekirdek/pil_durum.js";
import { kayitBittiMi } from "../cekirdek/bildirim.js";

export const TIK_MS = 1000;
// Akis bu kadar suredir hatadaysa kart KOSULSUZ yeniden aranir (adresi degismis olabilir).
export const YENIDEN_ARA_MS = 30000;
// Kart bulunamadiysa bu aralikla yeniden denenir (uygulama ondeyken).
export const YENIDEN_DENE_MS = 15000;

const KDR_KAYIT = 2;                    // akis_ayir.js KDR.KAYIT
const KIMLIK = /^[0-9a-f]{16}$/;

const ozet = (b) => (b ? { durum: b.durum, adres: b.adres || null, kimlik: b.kimlik || null } : null);
const tamsayi = (g, ad) => (g && Number.isInteger(g[ad]) ? g[ad] : null);

// /kayit/liste govdesi + oturum no -> tur | null.
export function oturumTuruBul(liste, oturum) {
  if (!liste || typeof liste !== "object" || !Array.isArray(liste.oturumlar) || !Number.isInteger(oturum)) return null;
  const k = liste.oturumlar.find((o) => o && typeof o === "object" && o.id === oturum);
  return k && Number.isInteger(k.tur) ? k.tur : null;
}

export function arkaPlanKur({
  kartAl, canliAl, esitlemeAl = null, bildirimIzle = null, pilOku = null, izlemeSorusu = null,
  bildirimDil = null, dilOku = null, mesgulMu = () => false,
  belge = null, simdiMs = Date.now,
  araliKur = (fn, ms) => setInterval(fn, ms), araliSil = (no) => clearInterval(no),
}) {
  if (typeof kartAl !== "function" || typeof canliAl !== "function") throw new TypeError("kartAl ve canliAl gerekli");

  let gorunur = false;
  let panelIster = false;
  let baglanti = null;                  // { durum, adres, kimlik } — son arama / baglanti sonucu
  let araSoz = null;
  let canli = null;
  let canliSoz = null;
  const canliBirak = [];
  let akis = { hal: "kapali", sebep: null, kod: null };
  let sonOlcum = null;
  let sonGorulme = null;
  let hataBasi = null;
  let sonDeneme = 0;
  let zamanlayici = null;
  let esit = null;
  let esitKuruluyor = false;
  let oncekiBagli = false;
  let pil = PIL_BILINMIYOR;
  let pilSonIstek = null;
  let pilSuruyor = false;
  let pilKusak = 0;
  let sonKayitIzi = null;
  let oncekiKod = null;
  let kayit = null;
  let oturumTuru = null;
  let turSorulan = null;
  let sonDil = null;
  let dinleniyor = false;
  const hamlar = new Set();
  const dinleyenler = new Set();

  const mesgul = () => { try { return mesgulMu() === true; } catch { return false; } };

  function durum() {
    return {
      gorunur, panelIster, baglanti: baglanti ? { ...baglanti } : null, akis: { ...akis },
      sonGorulme, oturumTuru, pil, kayit, araniyor: araSoz !== null,
    };
  }

  function yay() {
    const d = durum();
    for (const fn of [...dinleyenler]) { try { fn(d); } catch { /* dinleyicinin hatasi arka plani etkilemez */ } }
  }

  function hamYay(satir) {
    for (const fn of [...hamlar]) { try { fn(satir); } catch { /* panelin hatasi akisi etkilemez */ } }
  }

  // ── canli akistan gelen durum ─────────────────────────────────────────
  function guncelle() {
    if (!canli) return;
    let d = null;
    try { d = canli.durum(); } catch { d = null; }
    if (!d) return;
    const t = simdiMs();
    const degisti = d.hal !== akis.hal || (d.sebep ?? null) !== akis.sebep || (d.kod ?? null) !== akis.kod;
    akis = { hal: d.hal, sebep: d.sebep ?? null, kod: d.kod ?? null };
    if (d.son && d.son !== sonOlcum) { sonOlcum = d.son; sonGorulme = t; }
    if (d.hal === "acik") { sonGorulme = t; hataBasi = null; }
    if (d.hal === "hata" && hataBasi === null) hataBasi = t;
    if (d.kayit) kayitGuncelle(d.kayit);
    if (degisti) yay();
  }

  function kayitGuncelle(g) {
    kayit = g;
    const kod = tamsayi(g, "durum");
    const oturum = tamsayi(g, "oturum");
    // Kayit durumu DEGISTI: pil testi baslamis / bitmis olabilir -> yeni okuma gelene dek BILINMIYOR.
    const iz = `${kod}:${oturum}`;
    if (iz !== sonKayitIzi) { sonKayitIzi = iz; pilGecersiz(); }
    if (kod !== null && kod !== oncekiKod) {
      // Kayit BITTI (KAYIT -> baska hal): son kayitlar hemen telefona alinir (A22; eski kabuk).
      if (oncekiKod === KDR_KAYIT && kod !== KDR_KAYIT && esit) { try { esit.kayitBitti(); } catch { /* yok say */ } }
      // Anlik izleme sorusu kayit bitince kapanir (eski KayitDugmesi.vue; KAYIT -> BEKLIYOR bitti DEGIL).
      if (izlemeSorusu && kayitBittiMi(oncekiKod, kod)) { try { izlemeSorusu.kayitBitti(); } catch { /* yok say */ } }
      oncekiKod = kod;
    }
    turIzle(kod, oturum);
  }

  // Kayit surerken oturum numarasi degisince BIR kez: etkin oturumun turu (pil testi mi?) sorulur.
  function turIzle(kod, oturum) {
    if (kod !== KDR_KAYIT || oturum === null) {
      turSorulan = null;
      oturumTuru = null;
      return;
    }
    if (oturum === turSorulan) return;
    turSorulan = oturum;
    oturumTuru = null;
    turSor(oturum);
  }

  async function turSor(oturum) {
    let tur = null;
    try {
      const y = await (await kartAl()).istek("GET", "/kayit/liste");
      tur = oturumTuruBul(await y.json(), oturum);
    } catch {
      tur = null;                       // okunamadi: BILINMIYOR (serit gorunur kalir)
    }
    if (turSorulan === oturum) oturumTuru = tur;
  }

  // ── pil durumu (ACIL DURDUR seridi) ──────────────────────────────────
  function pilGecersiz() {
    pilKusak += 1;
    pilSonIstek = null;
    pil = PIL_BILINMIYOR;
  }

  function pilTik(t) {
    if (typeof pilOku !== "function") return;
    const b = baglanti;
    if (!gorunur || !b || b.durum !== "bagli") { if (pilSonIstek !== null || pil !== PIL_BILINMIYOR) pilGecersiz(); return; }
    if (pilSuruyor || (pilSonIstek !== null && t - pilSonIstek < PIL_YOKLAMA_MS)) return;
    pilSonIstek = t;
    pilSuruyor = true;
    const kusak = pilKusak;
    Promise.resolve().then(pilOku).then(
      (d) => { if (kusak === pilKusak) pil = typeof d === "string" ? { durum: d, okunduMs: simdiMs() } : PIL_BILINMIYOR; },
      () => { if (kusak === pilKusak) pil = PIL_BILINMIYOR; },
    ).finally(() => { pilSuruyor = false; });
  }

  function seritGorunur() {
    const t = simdiMs();
    return durdurGorunur({
      bagli: Boolean(baglanti) && baglanti.durum === "bagli",
      akisHal: akisHali(akis.hal, sonGorulme, t),
      veriYasMs: sonGorulme === null ? null : t - sonGorulme,
      pil, oturumTuru, simdiMs: t,
    });
  }

  // ── kart arama ────────────────────────────────────────────────────────
  // zorla: kart "bagli" gorunse de kesif yeniden kosar (adres degismis olabilir). Suren aramaya baglanir.
  function ara({ zorla = false } = {}) {
    if (araSoz) return araSoz;
    // "Bu telefon"da eslestirme suruyor: kart.baglan() o eslestirmenin baglantisini sifirlardi -> ARANMAZ,
    // eldeki durum doner (eski kabugun mesgulYap'i).
    if (mesgul()) return Promise.resolve(baglanti ? { ...baglanti } : { durum: "bulunamadi", adres: null, kimlik: null });
    sonDeneme = simdiMs();
    const soz = (async () => {
      try {
        const kart = await kartAl();
        const d = kart.durum();
        baglanti = ozet(zorla || !d || d.durum === "bagli-degil" ? await kart.baglan() : d);
      } catch (e) {
        baglanti = { durum: e && e.tur === "kasa" ? "kasa-bozuk" : "bulunamadi", adres: null, kimlik: null };
      }
      return baglanti;
    })();
    araSoz = soz;
    soz.finally(() => { if (araSoz === soz) araSoz = null; yay(); }).catch(() => {});
    return soz;
  }

  // Panelin tasiyicisi / istekleri icin: kart bu baglantida dogrulanmissa aga cikmadan, degilse aranir.
  async function baglan() {
    if (araSoz) return araSoz;
    try {
      const d = (await kartAl()).durum();
      if (d && d.durum !== "bagli-degil") {
        baglanti = ozet(d);
        return { ...baglanti };
      }
    } catch { /* aranir */ }
    return ara();
  }

  // ── canli akis ────────────────────────────────────────────────────────
  function canliHazirla() {
    if (canli) return Promise.resolve(canli);
    if (!canliSoz) {
      canliSoz = (async () => {
        const c = await canliAl();
        if (!canli) {
          canli = c;
          canliBirak.push(c.dinle(guncelle));
          if (typeof c.hamDinle === "function") canliBirak.push(c.hamDinle(hamYay));
        }
        return canli;
      })();
      canliSoz.catch(() => {}).finally(() => { canliSoz = null; });
    }
    return canliSoz;
  }

  // koru: canli'nin geri cekilme sayaci SIFIRLANMAZ (kendi yeniden aramamiz firtina cikarmasin).
  async function akisAc({ koru = false } = {}) {
    if (!gorunur || !panelIster || !baglanti || baglanti.durum !== "bagli") return;
    try {
      await canliHazirla();
    } catch {
      akis = { hal: "hata", sebep: "canli-yok", kod: null };
      yay();
      return;
    }
    if (!gorunur || !panelIster || !baglanti || baglanti.durum !== "bagli") return;   // beklerken degisti
    hataBasi = null;
    try { canli.baslat({ koru }); } catch { /* canli kendi halini bildirir */ }
    guncelle();
  }

  function akisKapat() {
    if (canli) { try { canli.durdur(); } catch { /* kapanamadiysa da kapali sayilir */ } }
    if (akis.hal !== "kapali") {
      akis = { hal: "kapali", sebep: null, kod: null };
      yay();
    }
  }

  // ── on / arka plan ────────────────────────────────────────────────────
  async function ac() {
    gorunur = true;
    if (esit && typeof esit.gorunurluk === "function") esit.gorunurluk(true);
    if (!zamanlayici) zamanlayici = araliKur(tik, TIK_MS);
    if (!baglanti || baglanti.durum === "bulunamadi") await ara();
    await akisAc();
  }

  function kapat() {
    gorunur = false;
    // A22: arka planda yeni esitleme turu baslamaz (bekleyen "kayit bitti" turu dahil).
    if (esit && typeof esit.gorunurluk === "function") esit.gorunurluk(false);
    if (zamanlayici) { araliSil(zamanlayici); zamanlayici = null; }
    pilGecersiz();
    akisKapat();
    yay();
  }

  function gorunurlukDegisti() {
    if (belge && belge.visibilityState === "hidden") kapat();
    else ac().catch(() => {});
  }

  // ── esitleme (A20–A23) ────────────────────────────────────────────────
  async function esitlemeKur() {
    if (esit || esitKuruluyor || typeof esitlemeAl !== "function") return;
    esitKuruluyor = true;
    try {
      const e = await esitlemeAl();
      esit = e;
      if (typeof e.gorunurluk === "function") e.gorunurluk(gorunur);
    } catch {
      esit = null;                      // sonraki tikte yeniden denenir
    } finally {
      esitKuruluyor = false;
    }
  }

  // Saniyede bir: ondeyken ve kart BAGLI (eslesmis) iken. Yeni baglantida hemen, sonra 60 s'de bir.
  function esitlemeTik() {
    const bagli = Boolean(baglanti) && baglanti.durum === "bagli";
    if (!esit) {
      if (gorunur && bagli) esitlemeKur();
      oncekiBagli = false;               // kurulunca "yeni baglanti" sayilsin
      return;
    }
    try {
      if (gorunur && bagli && !oncekiBagli) esit.baglandi();
      else esit.tik({ gorunur, bagli });
    } catch { /* esitleme kusuru arka plani bozmaz */ }
    oncekiBagli = gorunur && bagli;
  }

  function bildirimTik() {
    if (!bildirimIzle) return;
    const b = baglanti;
    try {
      bildirimIzle.tik({ gorunur, bagli: Boolean(b) && b.durum === "bagli", kimlik: b ? b.kimlik : null, adres: b ? b.adres : null, kayit });
    } catch { /* bildirim yok sayilir */ }
  }

  function dilTik() {
    if (typeof dilOku !== "function" || typeof bildirimDil !== "function") return;
    let d = null;
    try { d = dilOku(); } catch { d = null; }
    if ((d !== "tr" && d !== "en") || d === sonDil) return;
    sonDil = d;
    try { Promise.resolve(bildirimDil(d)).catch(() => {}); } catch { /* yok say */ }
  }

  function tik() {
    const t = simdiMs();
    // Akis "acik" gorunse de veri gelmiyorsa yeniden arama saati baslar (eski kabuk: hal "eski").
    if (akisHali(akis.hal, sonGorulme, t) === "eski" && hataBasi === null) hataBasi = t;
    esitlemeTik();
    bildirimTik();
    pilTik(t);
    dilTik();
    if (!gorunur || araSoz || mesgul()) return;
    const b = baglanti;
    if ((!b || b.durum === "bulunamadi") && t - sonDeneme >= YENIDEN_DENE_MS) { yenidenBaglan().catch(() => {}); return; }
    if (b && b.durum === "bagli" && hataBasi !== null && t - hataBasi >= YENIDEN_ARA_MS) {
      hataBasi = t;                     // hata surerse YENIDEN_ARA_MS sonra bir daha
      yenidenAra().catch(() => {});
    }
  }

  // Akis uzun suredir hatada: kart KOSULSUZ yeniden aranir. Akisin kendi geri cekilmesine DOKUNULMAZ;
  // yalniz adres degistiyse akis yeni adresle (sayac korunarak) acilir.
  async function yenidenAra() {
    const onceki = baglanti;
    await ara({ zorla: true });
    const yeni = baglanti;
    if (!yeni || yeni.durum !== "bagli") { akisKapat(); return; }
    if (!onceki || onceki.adres !== yeni.adres) {
      akisKapat();
      await akisAc({ koru: true });
    }
  }

  async function yenidenBaglan() {
    if (araSoz) return;
    if (baglanti && baglanti.durum !== "bagli") baglanti = null;
    await ara();
    await akisAc();
  }

  // "Bu telefon" bolumunde baglanti / eslestirme / kaldirma bitti: akis yeni duruma gore yeniden kurulur.
  async function baglantiDegisti(b) {
    akisKapat();
    turSorulan = null;
    oturumTuru = null;
    oncekiBagli = false;
    baglanti = ozet(b);
    yay();
    await akisAc();
  }

  function akisIste(v) {
    panelIster = v === true;
    if (panelIster) akisAc().catch(() => {});
    else akisKapat();
  }

  function baslat() {
    if (!dinleniyor && belge && typeof belge.addEventListener === "function") {
      belge.addEventListener("visibilitychange", gorunurlukDegisti);
      dinleniyor = true;
    }
    dilTik();
    gorunurlukDegisti();
  }

  function birak() {
    kapat();
    for (const fn of canliBirak.splice(0)) { try { fn(); } catch { /* yok say */ } }
    if (dinleniyor && belge && typeof belge.removeEventListener === "function") belge.removeEventListener("visibilitychange", gorunurlukDegisti);
    dinleniyor = false;
  }

  return {
    baslat, birak, ac, kapat, gorunurlukDegisti, tik,
    baglan, ara, akisIste, baglantiDegisti, yenidenBaglan,
    seritGorunur, durum,
    hamDinle(fn) { hamlar.add(fn); return () => { hamlar.delete(fn); }; },
    dinle(fn) { dinleyenler.add(fn); return () => { dinleyenler.delete(fn); }; },
    kartKimligi: () => (baglanti && typeof baglanti.kimlik === "string" && KIMLIK.test(baglanti.kimlik) ? baglanti.kimlik : null),
  };
}
