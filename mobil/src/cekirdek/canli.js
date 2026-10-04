// Canli akis (5C-1; tasarim A6, A7, A40): kartin SSE akisini uygulama ONDEYKEN acik tutar, satirlari
// ayristirir, son 5 dakikayi halka tamponda saklar ve kayit komutlarini (beyaz liste) imzali yollar.
//
//   const canli = canliKur({ kart, ag, eklenti, simdiMs });
//   canli.baslat();  canli.durdur();            // one gelince / arka plana gecince (cagiran: kabuk)
//   canli.durum()   -> { bagli, hal, sebep, kod, son, kayit, yas_ms, ayrinti }
//        hal: "kapali" | "baglaniyor" | "acik" | "dolu" | "hata";  bagli = (hal === "acik")
//        sebep (yalniz hal "hata"): TUR adi — bagli-degil | eslesmemis | baglanti | zaman-asimi | http |
//        kapandi | sessiz | wifi-yok | cihaz-silinmis | ic-hata …;  kod: http ise durum kodu
//        son: son D satiri | null;  kayit: son G satiri | null;  yas_ms: son D'den beri gecen sure | null
//        ayrinti: { K, GA, GT, GP, A } — gorulen son satirlar
//   canli.dinle(fn) -> birak()                  // fn(durum()): her D / G satirinda ve hal degisiminde
//   canli.seri()    -> { t, v, a, w, n }        // Float64Array; t = telefon saati (ms), eskiden yeniye
//   await canli.komut("Gb1000")                 // yalniz Gb<0|50…60000>, Gd, G?, ? — baskasi CanliHatasi("komut-yasak")
//
// Akis EventSource ile DEGIL: KartAg eklentisi kendi baglantisiyla okur, satirlar "akis", durum
// "akisDurum" olayiyla gelir. Her (yeniden) baglanmada adres YENIDEN imzalanir (tek kullanimlik sayac).
// Imzali adresi `kart.akisUrl()` verir; kart.js'te o yontem yoksa `akisUrlAl` enjekte edilir.
// Adres (imza tasir) hicbir duruma, hataya, dinleyiciye GIRMEZ; sebep yalniz TUR adidir (A45).
// `p0` buradan GECMEZ (kendi yolu: durdur.js).

import { satirAyir } from "./akis_ayir.js";

export const YENIDEN_MS = Object.freeze([1000, 2000, 4000, 8000, 16000, 30000]);
export const DOLU_BEKLE_MS = 10000;
export const SESSIZ_MS = 45000;                 // kart 15 s'de bir kalp atar; eklentinin okuma suresi 40 s
export const SERI_SURE_MS = 300000;
export const SERI_KAPASITE = 16384;             // 5 dk x en hizli rapor (20 ms) = 15000 nokta
export const OLAY_SATIR_AZAMI = 256;
export const YENIDEN_BUL_HER = 3;
// Kartin kabul ettigi en hizli ozetli kayit 50/s = 20 ms (kaynak: kayit hizlari 0, 20, 100, 200, 1000, …).
export const GB_EN_AZ_MS = 20;
export const GB_EN_COK_MS = 60000;

const BEKLEYEN_AZAMI = 64;
const TUR_DESENI = /^[a-z][a-z0-9-]{0,31}$/;
const GB_DESENI = /^Gb(0|[1-9][0-9]{1,4})$/;

export class CanliHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "CanliHatasi";
    this.tur = tur;
  }
}

// Karta giden komutlarin TAMAMI. Tam esleme: bosluk, satir sonu, ek karakter REDDEDILIR.
export function komutGecerli(metin) {
  if (metin === "Gd" || metin === "G?" || metin === "?") return true;
  const m = typeof metin === "string" ? GB_DESENI.exec(metin) : null;
  if (!m) return false;
  const ms = Number(m[1]);
  return ms === 0 || (ms >= GB_EN_AZ_MS && ms <= GB_EN_COK_MS);
}

function turAl(e) {
  const t = e && typeof e.tur === "string" ? e.tur : "";
  return TUR_DESENI.test(t) ? t : "ic-hata";
}

const kodAl = (k) => (Number.isInteger(k) && k >= 100 && k <= 599 ? k : null);
const kodla = (metin) => new TextEncoder().encode(metin);

export function canliKur({
  kart, ag, eklenti, simdiMs = Date.now, akisUrlAl = null, yenidenBul = false, seriKapasite = SERI_KAPASITE,
  zamanla = (fn, ms) => setTimeout(fn, ms), zamaniBirak = (z) => clearTimeout(z),
} = {}) {
  if (!kart || typeof kart.durum !== "function" || typeof kart.istek !== "function") throw new TypeError("kart.durum ve kart.istek gerekli");
  if (!ag || typeof ag.akisAc !== "function" || typeof ag.akisKapat !== "function") throw new TypeError("ag.akisAc ve ag.akisKapat gerekli");
  if (!eklenti || typeof eklenti.addListener !== "function") throw new TypeError("eklenti.addListener gerekli");

  let istenen = false, hal = "kapali", sebep = null, kod = null;
  let nesil = 0;                       // her baglanma denemesi / durdurma bir nesil: eski isler kendini tanir
  let akisKimlik = null;               // acik (ya da acilmakta olan) akisin eklentideki kimligi
  let bekleyen = null;                 // akisAc donene kadar gelen olaylar
  let deneme = 0, ardisik = 0;
  let yenidenZ = null, bekciZ = null, dinleniyor = false;
  let son = null, sonMs = 0, kayit = null;
  const ayrinti = {};
  const dinleyiciler = new Set();

  const kap = Math.max(1, Math.floor(seriKapasite));
  const hT = new Float64Array(kap), hV = new Float64Array(kap), hA = new Float64Array(kap), hW = new Float64Array(kap);
  let yaz = 0, adet = 0;

  function durum() {
    return {
      bagli: hal === "acik", hal, sebep, kod, son, kayit,
      yas_ms: son ? simdiMs() - sonMs : null, ayrinti: { ...ayrinti },
    };
  }

  function bildir() {
    for (const fn of [...dinleyiciler]) {
      try { fn(durum()); } catch { /* arayuz hatasi akisi etkilemez */ }
    }
  }

  function halYap(yeni, yeniSebep = null, yeniKod = null) {
    if (hal === yeni && sebep === yeniSebep && kod === yeniKod) return;
    hal = yeni;
    sebep = yeniSebep;
    kod = yeniKod;
    bildir();
  }

  function dinle(fn) {
    if (typeof fn !== "function") throw new TypeError("dinleyici islev olmali");
    dinleyiciler.add(fn);
    return () => { dinleyiciler.delete(fn); };
  }

  // ── halka tampon ───────────────────────────────────────────────────────
  function seriEkle(d) {
    hT[yaz] = simdiMs();
    hV[yaz] = d.v;
    hA[yaz] = d.a;
    hW[yaz] = d.w;
    yaz = (yaz + 1) % kap;
    if (adet < kap) adet += 1;
  }

  function seri() {
    const esik = simdiMs() - SERI_SURE_MS;
    const ilk = (yaz - adet + kap) % kap;
    let atla = 0;
    while (atla < adet && hT[(ilk + atla) % kap] <= esik) atla += 1;
    const n = adet - atla;
    const t = new Float64Array(n), v = new Float64Array(n), a = new Float64Array(n), w = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const k = (ilk + atla + i) % kap;
      t[i] = hT[k];
      v[i] = hV[k];
      a[i] = hA[k];
      w[i] = hW[k];
    }
    return { t, v, a, w, n };
  }

  // ── zamanlayicilar ─────────────────────────────────────────────────────
  function bekciBirak() {
    if (bekciZ !== null) zamaniBirak(bekciZ);
    bekciZ = null;
  }

  function kapatSessiz(kimlik) {
    try {
      const p = ag.akisKapat(kimlik);
      if (p && typeof p.catch === "function") p.catch(() => {});
    } catch { /* kapatma bir temizliktir */ }
  }

  // Eklenti hic olay vermezse (baglanti asili, kalp gelmiyor) akis burada da dusurulur.
  function bekciKur() {
    bekciBirak();
    const n = nesil;
    bekciZ = zamanla(() => {
      bekciZ = null;
      if (n !== nesil || !istenen) return;
      const k = akisKimlik;
      nesil += 1;                      // acilmakta olan akis varsa donunce kendini kapatir
      akisKimlik = null;
      bekleyen = null;
      if (k !== null) kapatSessiz(k);
      dustu("sessiz");
    }, SESSIZ_MS);
  }

  function yenidenKur(ms, tazele) {
    if (yenidenZ !== null) zamaniBirak(yenidenZ);
    const n = nesil;
    yenidenZ = zamanla(() => {
      yenidenZ = null;
      if (n !== nesil || !istenen) return;
      baglan(tazele);
    }, ms);
  }

  function dustu(yeniSebep, yeniKod = null) {
    bekciBirak();
    halYap("hata", yeniSebep, yeniKod);
    const ms = YENIDEN_MS[Math.min(deneme, YENIDEN_MS.length - 1)];
    deneme += 1;
    ardisik += 1;
    // 401: kart yeniden baslamis olabilir (acilis degisti). Akis adresi eski acilisla imzalanir; siradan
    // imzali bir istek acilisi tazeler (kart.js kimligi yeniden dogrular) — sonra yeniden baglanilir.
    yenidenKur(ms, yeniSebep === "http" && yeniKod === 401);
  }

  // ── olaylar ────────────────────────────────────────────────────────────
  function satirIsle(metin) {
    const s = satirAyir(metin);
    if (s.tur === "D") {
      son = s;
      sonMs = simdiMs();
      seriEkle(s);
      bildir();
    } else if (s.tur === "G") {
      kayit = s;
      bildir();
    } else if (s.tur !== "diger") {
      ayrinti[s.tur] = s;
    }
  }

  function bizimMi(ad, veri) {
    if (!veri || typeof veri !== "object" || typeof veri.kimlik !== "string") return false;
    if (bekleyen !== null) {
      if (bekleyen.length < BEKLEYEN_AZAMI) bekleyen.push({ ad, veri });
      return false;
    }
    return akisKimlik !== null && veri.kimlik === akisKimlik;
  }

  function olayAkis(veri) {
    if (!bizimMi("akis", veri) || !Array.isArray(veri.satirlar)) return;
    bekciKur();
    deneme = 0;                        // veri geldi: sonraki kopmada 1 s'den baslanir
    ardisik = 0;
    const n = Math.min(veri.satirlar.length, OLAY_SATIR_AZAMI);
    for (let i = 0; i < n; i++) satirIsle(veri.satirlar[i]);
  }

  function olayDurum(veri) {
    if (!bizimMi("akisDurum", veri)) return;
    if (veri.hal === "acik") {
      if (hal === "acik") return;
      bekciKur();
      halYap("acik");
      // Kart G satirini yalniz degisince / kayitta basar: guncel kayit durumu bir kez sorulur.
      Promise.resolve().then(() => kart.istek("POST", "/komut", [], kodla("G?"))).catch(() => {});
    } else if (veri.hal === "dolu") {
      akisKimlik = null;
      bekciBirak();
      halYap("dolu");
      yenidenKur(DOLU_BEKLE_MS, false);
    } else if (veri.hal === "hata") {
      akisKimlik = null;
      dustu(turAl(veri), kodAl(veri.kod));
    } else if (veri.hal === "kapandi") {
      akisKimlik = null;
      dustu("kapandi");
    }
  }

  function dinlemeyiKur() {
    if (dinleniyor) return;
    dinleniyor = true;
    for (const [ad, fn] of [["akis", olayAkis], ["akisDurum", olayDurum]]) {
      try {
        const s = eklenti.addListener(ad, fn);
        if (s && typeof s.catch === "function") s.catch(() => {});
      } catch { /* eklenti yok: akis acilamaz, hal "hata" olur */ }
    }
  }

  // ── baglanma ───────────────────────────────────────────────────────────
  function urlAl() {
    if (typeof kart.akisUrl === "function") return kart.akisUrl();
    if (typeof akisUrlAl === "function") return akisUrlAl();
    throw new CanliHatasi("ic-hata");
  }

  async function baglan(tazele) {
    nesil += 1;
    const n = nesil;
    akisKimlik = null;
    bekleyen = [];
    halYap("baglaniyor");
    bekciKur();
    let url, s;
    try {
      if (tazele) await kart.istek("POST", "/komut", [], kodla("G?"));
      if (n !== nesil) return;
      let d = kart.durum();
      if (yenidenBul && typeof kart.baglan === "function"
        && (d.durum === "bagli-degil" || (ardisik > 0 && ardisik % YENIDEN_BUL_HER === 0))) {
        try { await kart.baglan(); } catch { /* bulunamadi: asagida soylenir */ }
        if (n !== nesil) return;
        d = kart.durum();
      }
      if (d.durum !== "bagli") throw new CanliHatasi(d.durum === "eslesmemis" ? "eslesmemis" : "bagli-degil");
      url = await urlAl();
      if (n !== nesil) return;
      s = await ag.akisAc(url);
    } catch (e) {
      if (n !== nesil) return;
      bekleyen = null;
      dustu(turAl(e));
      return;
    }
    if (n !== nesil) {                 // bu arada durduruldu / yeniden baslandi: akis sahipsiz kalmasin
      kapatSessiz(s.kimlik);
      return;
    }
    akisKimlik = s.kimlik;
    const saklanan = bekleyen;
    bekleyen = null;
    for (const o of saklanan) (o.ad === "akis" ? olayAkis : olayDurum)(o.veri);
  }

  function baslat() {
    if (istenen) return;
    istenen = true;
    deneme = 0;
    ardisik = 0;
    dinlemeyiKur();
    baglan(false);
  }

  function durdur() {
    istenen = false;
    nesil += 1;
    if (yenidenZ !== null) zamaniBirak(yenidenZ);
    yenidenZ = null;
    bekciBirak();
    const k = akisKimlik;
    akisKimlik = null;
    bekleyen = null;
    if (k !== null) kapatSessiz(k);
    halYap("kapali");
  }

  async function komut(metin) {
    if (!komutGecerli(metin)) throw new CanliHatasi("komut-yasak");
    await kart.istek("POST", "/komut", [], kodla(metin));
    return true;
  }

  return { baslat, durdur, durum, dinle, seri, komut };
}
