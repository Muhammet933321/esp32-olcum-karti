// Kabugun ortak durumu: kart baglantisi + canli akis (A6, A39, A40). App.vue BIR kez kurar ve
// ekranlara `provide("kabuk", ...)` ile verir; ekranlar kart / canli nesnesini kendileri KURMAZ.
//
//   const k = kabukDurumu({ kartAl, canliAl, esitlemeAl, belge: document });
//   k.ac();                      // uygulama acildi / one geldi: karti bul, eslesmisse akisi ac
//   k.kapat();                   // arka plana gecti: akis HEMEN kapanir (kartta 4 akis yuvasi var)
//   k.birak();                   // dinleyiciler ve zamanlayici kalkar
//   k.baglanti, k.araniyor, k.akis, k.sonGorulme, k.simdi, k.izleme, k.cizim, k.oturumTuru   (ref)
//   k.mesgulYap(true / false)    // suren kullanici islemi (eslestirme): o sirada kart yeniden ARANMAZ
//   k.kayitBaslat(hizMs) / k.kayitDurdur()  -> Promise (reddederse hata turuyle)
//   k.seri()                     // canli.seri() | null
//   k.esitleme (ref)             // kayit esitlemesinin durumu (A20–A23): uygulama ondeyken, baglaninca,
//                                // kayit bitince ve 60 s'de bir kendiliginden; k.simdiEsitle() elle
//   k.kopyaSifirla()             // telefondaki kopyayi siler (A23)
//
// ACIL DURDUR buradan GECMEZ (kendi yolu: cekirdek/uygulama.js acilDurdur).

import { ref, shallowRef } from "vue";
import { DURDUR_KOMUTU, hizKomutu } from "./canli_gorunum.js";
import { KDR, gAlan, gorunenOlcum, kayitIzle, oturumTuruBul } from "./durum_gorunum.js";

const AKIS_YOK = Object.freeze({ hazir: null, hal: "kapali", bagli: false, son: null, kayit: null });
// Akis bu kadar suredir "hata"daysa kart KOSULSUZ yeniden ARANIR (adresi degismis olabilir; kart.js ag
// hatasinda "bagli" demeye devam eder). Hata surdukce her YENIDEN_ARA_MS'de bir.
export const YENIDEN_ARA_MS = 30000;
// Bu telefonun gonderdigi `Gb<ms>`in hizi ancak bu sure icinde gorulen BOS -> KAYIT gecisine yazilir.
export const HIZ_OMRU_MS = 10000;
// Kart bulunamadiysa bu aralikla yeniden denenir (uygulama ondeyken).
export const YENIDEN_DENE_MS = 15000;
const TIK_MS = 1000;

export class KabukHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KabukHatasi";
    this.tur = tur;
  }
}

export const ESITLEME_YOK = Object.freeze({ hazir: null, hal: "bos", sonMs: null, yeni: 0, sonSira: null, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false });

export function kabukDurumu({
  kartAl, canliAl, esitlemeAl = null, bildirimIzle = null, belge = null, simdiMs = Date.now,
  araliKur = (fn, ms) => setInterval(fn, ms), araliSil = (no) => clearInterval(no),
}) {
  const baglanti = shallowRef(null);
  const araniyor = ref(false);
  const akis = shallowRef(AKIS_YOK);
  const sonGorulme = ref(null);
  const simdi = ref(simdiMs());
  const izleme = shallowRef(null);
  const cizim = ref(0);                 // her yeni olcumde artar: grafikler bunu izler
  const oturumTuru = ref(null);         // etkin kaydin turu (1 olcum, 2 pil, 3 skop) | null = bilinmiyor
  const esitleme = shallowRef(ESITLEME_YOK);   // kayit esitlemesinin durumu (5D); hazir: null bilinmiyor / false yok / true

  let gorunur = false;
  let canli = null;
  let dinlemeBirak = null;
  let sonOlcum = null;
  let bekleyenHiz = null;               // bu telefonun gonderdigi son Gb: { ms, t } (HIZ_OMRU_MS gecerli)
  let turSorulan = null;                // turu sorulmus (sorulmakta olan) oturum numarasi
  let mesgul = 0;
  let sonDeneme = 0;
  let hataBasi = null;
  let zamanlayici = null;
  let esit = null;                      // esitleme dongusu (tembel kurulur)
  let esitKuruluyor = false;
  let oncekiBagli = false;

  const ozet = (b) => (b ? { durum: b.durum, adres: b.adres || null, kimlik: b.kimlik || null } : null);

  function guncelle() {
    if (!canli) return;
    let d = null;
    try { d = canli.durum(); } catch { d = null; }
    if (!d) return;
    const t = simdiMs();
    akis.value = { hazir: true, hal: d.hal, bagli: d.bagli === true, son: gorunenOlcum(d.hal, d.son), kayit: d.kayit || null };
    if (d.son && d.son !== sonOlcum) {
      sonOlcum = d.son;
      sonGorulme.value = t;
      cizim.value += 1;
    }
    if (d.hal === "acik") { sonGorulme.value = t; hataBasi = null; }
    if (d.hal === "hata" && hataBasi === null) hataBasi = t;
    if (d.kayit) {
      const onceki = izleme.value;
      // Bekleyen hiz yalniz TAZE ise ve kaydin basladigini GORDUYSEK (BOS -> KAYIT) o kayda aittir.
      const bizim = bekleyenHiz !== null && t - bekleyenHiz.t <= HIZ_OMRU_MS && onceki !== null && onceki.durum === KDR.BOS;
      izleme.value = kayitIzle(onceki, d.kayit, t, bizim ? bekleyenHiz.ms : null);
      // Kayit BITTI (KAYIT -> baska hal): son kayitlar hemen telefona alinir (A22).
      if (esit && onceki && onceki.durum === KDR.KAYIT && izleme.value && izleme.value.durum !== KDR.KAYIT) esit.kayitBitti();
      if (izleme.value && izleme.value.durum === KDR.KAYIT) bekleyenHiz = null;
      turIzle(d.kayit);
    }
  }

  // Kayit surerken oturum numarasi degisince BIR kez: etkin oturumun turu (pil testi mi?) sorulur.
  function turIzle(g) {
    const oturum = gAlan(g, "oturum");
    if (gAlan(g, "durum") !== KDR.KAYIT || oturum === null) {
      turSorulan = null;
      oturumTuru.value = null;
      return;
    }
    if (oturum === turSorulan) return;
    turSorulan = oturum;
    oturumTuru.value = null;
    turSor(oturum);
  }

  async function turSor(oturum) {
    let tur = null;
    try {
      const kart = await kartAl();
      const y = await kart.istek("GET", "/kayit/liste");
      tur = oturumTuruBul(await y.json(), oturum);
    } catch {
      tur = null;                       // okunamadi: BILINMIYOR (dugmeler acik kalir; kart zaten reddeder)
    }
    if (turSorulan === oturum) oturumTuru.value = tur;
  }

  // zorla: kart "bagli" gorunse de kesif yeniden kosar (adres degismis olabilir).
  async function ara({ elle = null, zorla = false } = {}) {
    if (araniyor.value) return;
    araniyor.value = true;
    sonDeneme = simdiMs();
    try {
      const kart = await kartAl();
      const d = kart.durum();
      baglanti.value = ozet(zorla || d.durum === "bagli-degil" || elle !== null ? await kart.baglan({ elle }) : d);
    } catch (e) {
      baglanti.value = { durum: e && e.tur === "kasa" ? "kasa-bozuk" : "bulunamadi", adres: null, kimlik: null };
    } finally {
      araniyor.value = false;
    }
  }

  // koru: canli'nin geri cekilme sayaci SIFIRLANMAZ (kabugun kendi yeniden aramasi firtina cikarmasin).
  async function akisAc({ koru = false } = {}) {
    if (!gorunur || !baglanti.value || baglanti.value.durum !== "bagli") return;
    if (!canli) {
      try {
        canli = await canliAl();
      } catch {
        canli = null;
        akis.value = { ...AKIS_YOK, hazir: false };
        return;
      }
    }
    if (!gorunur) return;                                   // beklerken arka plana gecti: ACMA
    if (!dinlemeBirak) dinlemeBirak = canli.dinle(guncelle);
    hataBasi = null;
    canli.baslat({ koru });
    guncelle();
  }

  function akisKapat() {
    if (canli) { try { canli.durdur(); } catch { /* kapanamadiysa da ekran kapali der */ } }
    akis.value = { ...akis.value, hal: "kapali", bagli: false };
  }

  async function ac() {
    gorunur = true;
    if (esit && typeof esit.gorunurluk === "function") esit.gorunurluk(true);
    if (!zamanlayici) zamanlayici = araliKur(tik, TIK_MS);
    if (!baglanti.value || baglanti.value.durum === "bulunamadi") await ara();
    await akisAc();
  }

  function kapat() {
    gorunur = false;
    // A22: arka planda yeni esitleme turu baslamaz (bekleyen "kayit bitti" turu dahil).
    if (esit && typeof esit.gorunurluk === "function") esit.gorunurluk(false);
    if (zamanlayici) { araliSil(zamanlayici); zamanlayici = null; }
    akisKapat();
  }

  // Esitleme dongusu ilk gerektiginde kurulur; modul yoksa / yuklenemezse `hazir: false`.
  async function esitlemeKur() {
    if (esit || esitKuruluyor || typeof esitlemeAl !== "function") return;
    esitKuruluyor = true;
    try {
      const e = await esitlemeAl();
      e.dinle((d) => { esitleme.value = { hazir: true, ...d }; });
      esitleme.value = { hazir: true, ...e.durum() };
      esit = e;
      if (typeof e.gorunurluk === "function") e.gorunurluk(gorunur);
    } catch {
      esitleme.value = { ...ESITLEME_YOK, hazir: false };
    } finally {
      esitKuruluyor = false;
    }
  }

  // Saniyede bir: uygulama ondeyken ve kart BAGLI (eslesmis) iken. Yeni baglantida hemen, sonra 60 s'de bir.
  function esitlemeTik() {
    const b = baglanti.value;
    const bagli = Boolean(b) && b.durum === "bagli";
    if (!esit) {
      if (gorunur && bagli) esitlemeKur();
      oncekiBagli = false;               // kurulunca "yeni baglanti" sayilsin
      return;
    }
    if (gorunur && bagli && !oncekiBagli) esit.baglandi();
    else esit.tik({ gorunur, bagli });
    oncekiBagli = gorunur && bagli;
  }

  // Bildirim (5E-4): yeni baglantida zarf yenilenir, kayit durumu degisince servise iletilir. Bildirim
  // kusuru kabugu ASLA bozmaz.
  function bildirimTik() {
    if (!bildirimIzle) return;
    const b = baglanti.value;
    try {
      bildirimIzle.tik({ gorunur, bagli: Boolean(b) && b.durum === "bagli", kimlik: b ? b.kimlik : null, kayit: akis.value.kayit });
    } catch { /* bildirim yok sayilir */ }
  }

  // "Simdi esitle": ASLA atmaz; esitleme yoksa null.
  async function simdiEsitle() {
    if (!esit) await esitlemeKur();
    return esit ? esit.simdi() : null;
  }

  // "Kopyayi sifirla" (A23). Hata TUR olarak atilir.
  async function kopyaSifirla() {
    if (!esit) await esitlemeKur();
    if (!esit) throw new KabukHatasi("esitleme-yok");
    try {
      await esit.sifirla();
    } catch (e) {
      throw new KabukHatasi(e && typeof e.tur === "string" ? e.tur : "?");
    }
  }

  function tik() {
    const t = simdiMs();
    simdi.value = t;
    esitlemeTik();
    bildirimTik();
    if (!gorunur || araniyor.value || mesgul > 0) return;
    const b = baglanti.value;
    if ((!b || b.durum === "bulunamadi") && t - sonDeneme >= YENIDEN_DENE_MS) { yenidenBaglan(); return; }
    if (b && b.durum === "bagli" && hataBasi !== null && t - hataBasi >= YENIDEN_ARA_MS) {
      hataBasi = t;                     // hata surerse YENIDEN_ARA_MS sonra bir daha
      yenidenAra().catch(() => {});
    }
  }

  // Akis uzun suredir hatada: kart KOSULSUZ yeniden aranir. Akisin kendi yeniden baglanma dongusune
  // (ve geri cekilmesine) DOKUNULMAZ; yalniz adres degistiyse akis yeni adresle — sayac korunarak — acilir.
  async function yenidenAra() {
    const onceki = baglanti.value;
    await ara({ zorla: true });
    const yeni = baglanti.value;
    if (!yeni || yeni.durum !== "bagli") { akisKapat(); return; }
    if (!onceki || onceki.adres !== yeni.adres) {
      akisKapat();
      await akisAc({ koru: true });
    }
  }

  function mesgulYap(v) {
    mesgul = Math.max(0, mesgul + (v ? 1 : -1));
  }

  // Kullanici "yeniden dene" dedi ya da zamanlayici: karti yeniden ara, bulunduysa akisi ac.
  async function yenidenBaglan() {
    if (araniyor.value) return;
    if (baglanti.value && baglanti.value.durum !== "bagli") baglanti.value = null;
    await ara();
    await akisAc();
  }

  // Ayarlar'daki baglanti / eslestirme / kaldirma islemi bitti: yeni sonuca gore akis yeniden kurulur.
  async function baglantiDegisti(b) {
    akisKapat();
    izleme.value = null;
    turSorulan = null;
    oturumTuru.value = null;
    baglanti.value = ozet(b);
    await akisAc();
  }

  async function komut(metin) {
    if (!canli) throw new KabukHatasi("akis-yok");
    try {
      return await canli.komut(metin);
    } catch (e) {
      throw new KabukHatasi(e && typeof e.tur === "string" ? e.tur : "?");
    }
  }

  function kayitBaslat(hizMs) {
    const k = hizKomutu(hizMs);
    if (k === null) return Promise.reject(new KabukHatasi("hiz-gecersiz"));
    const bekleyen = { ms: hizMs, t: simdiMs() };
    bekleyenHiz = bekleyen;
    // Komut gitmediyse / reddedildiyse hiz UNUTULUR: baskasinin baslattigi kayda yapismaz.
    return komut(k).catch((e) => { if (bekleyenHiz === bekleyen) bekleyenHiz = null; throw e; });
  }

  const kayitDurdur = () => komut(DURDUR_KOMUTU);

  function seri() {
    if (!canli) return null;
    try { return canli.seri(); } catch { return null; }
  }

  // Uygulama one / arkaya gecince (Capacitor App eklentisi kurulu degil: belge gorunurlugu).
  function gorunurlukDegisti() {
    if (belge && belge.visibilityState === "hidden") kapat();
    else ac().catch(() => {});
  }
  if (belge && typeof belge.addEventListener === "function") belge.addEventListener("visibilitychange", gorunurlukDegisti);

  function birak() {
    kapat();
    if (dinlemeBirak) { dinlemeBirak(); dinlemeBirak = null; }
    if (belge && typeof belge.removeEventListener === "function") belge.removeEventListener("visibilitychange", gorunurlukDegisti);
  }

  return {
    baglanti, araniyor, akis, sonGorulme, simdi, izleme, cizim, oturumTuru, esitleme,
    ac, kapat, birak, yenidenBaglan, baglantiDegisti, kayitBaslat, kayitDurdur, seri, gorunurlukDegisti, mesgulYap,
    simdiEsitle, kopyaSifirla,
  };
}
