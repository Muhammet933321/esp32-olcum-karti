// Kabugun ortak durumu: kart baglantisi + canli akis (A6, A39, A40). App.vue BIR kez kurar ve
// ekranlara `provide("kabuk", ...)` ile verir; ekranlar kart / canli nesnesini kendileri KURMAZ.
//
//   const k = kabukDurumu({ kartAl, canliAl, belge: document });
//   k.ac();                      // uygulama acildi / one geldi: karti bul, eslesmisse akisi ac
//   k.kapat();                   // arka plana gecti: akis HEMEN kapanir (kartta 4 akis yuvasi var)
//   k.birak();                   // dinleyiciler ve zamanlayici kalkar
//   k.baglanti, k.araniyor, k.akis, k.sonGorulme, k.simdi, k.izleme, k.cizim   (ref)
//   k.kayitBaslat(hizMs) / k.kayitDurdur()  -> Promise (reddederse hata turuyle)
//   k.seri()                     // canli.seri() | null
//
// ACIL DURDUR buradan GECMEZ (kendi yolu: cekirdek/uygulama.js acilDurdur).

import { ref, shallowRef } from "vue";
import { DURDUR_KOMUTU, hizKomutu } from "./canli_gorunum.js";
import { kayitIzle } from "./durum_gorunum.js";

const AKIS_YOK = Object.freeze({ hazir: null, hal: "kapali", bagli: false, son: null, kayit: null });
// Akis bu kadar suredir "hata"daysa kart yeniden ARANIR (adresi degismis olabilir).
export const YENIDEN_ARA_MS = 30000;
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

export function kabukDurumu({
  kartAl, canliAl, belge = null, simdiMs = Date.now,
  araliKur = (fn, ms) => setInterval(fn, ms), araliSil = (no) => clearInterval(no),
}) {
  const baglanti = shallowRef(null);
  const araniyor = ref(false);
  const akis = shallowRef(AKIS_YOK);
  const sonGorulme = ref(null);
  const simdi = ref(simdiMs());
  const izleme = shallowRef(null);
  const cizim = ref(0);                 // her yeni olcumde artar: grafikler bunu izler

  let gorunur = false;
  let canli = null;
  let dinlemeBirak = null;
  let sonOlcum = null;
  let bekleyenHiz = null;               // bu telefonun gonderdigi son Gb'nin araligi (ms)
  let sonDeneme = 0;
  let hataBasi = null;
  let zamanlayici = null;

  const ozet = (b) => (b ? { durum: b.durum, adres: b.adres || null, kimlik: b.kimlik || null } : null);

  function guncelle() {
    if (!canli) return;
    let d = null;
    try { d = canli.durum(); } catch { d = null; }
    if (!d) return;
    const t = simdiMs();
    akis.value = { hazir: true, hal: d.hal, bagli: d.bagli === true, son: d.son || null, kayit: d.kayit || null };
    if (d.son && d.son !== sonOlcum) {
      sonOlcum = d.son;
      sonGorulme.value = t;
      cizim.value += 1;
    }
    if (d.hal === "acik") { sonGorulme.value = t; hataBasi = null; }
    if (d.hal === "hata" && hataBasi === null) hataBasi = t;
    if (d.kayit) {
      const onceki = izleme.value;
      izleme.value = kayitIzle(onceki, d.kayit, t, bekleyenHiz);
      if (izleme.value && izleme.value.oturum !== null && (!onceki || onceki.oturum !== izleme.value.oturum)) bekleyenHiz = null;
    }
  }

  async function ara(elle = null) {
    if (araniyor.value) return;
    araniyor.value = true;
    sonDeneme = simdiMs();
    try {
      const kart = await kartAl();
      const d = kart.durum();
      baglanti.value = ozet(d.durum === "bagli-degil" || elle !== null ? await kart.baglan({ elle }) : d);
    } catch (e) {
      baglanti.value = { durum: e && e.tur === "kasa" ? "kasa-bozuk" : "bulunamadi", adres: null, kimlik: null };
    } finally {
      araniyor.value = false;
    }
  }

  async function akisAc() {
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
    canli.baslat();
    guncelle();
  }

  function akisKapat() {
    if (canli) { try { canli.durdur(); } catch { /* kapanamadiysa da ekran kapali der */ } }
    akis.value = { ...akis.value, hal: "kapali", bagli: false };
  }

  async function ac() {
    gorunur = true;
    if (!zamanlayici) zamanlayici = araliKur(tik, TIK_MS);
    if (!baglanti.value || baglanti.value.durum === "bulunamadi") await ara();
    await akisAc();
  }

  function kapat() {
    gorunur = false;
    if (zamanlayici) { araliSil(zamanlayici); zamanlayici = null; }
    akisKapat();
  }

  function tik() {
    const t = simdiMs();
    simdi.value = t;
    if (!gorunur || araniyor.value) return;
    const b = baglanti.value;
    if ((!b || b.durum === "bulunamadi") && t - sonDeneme >= YENIDEN_DENE_MS) { yenidenBaglan(); return; }
    if (b && b.durum === "bagli" && hataBasi !== null && t - hataBasi >= YENIDEN_ARA_MS) {
      hataBasi = null;
      akisKapat();
      baglanti.value = null;
      yenidenBaglan();
    }
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
    bekleyenHiz = hizMs;
    return komut(k);
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
    baglanti, araniyor, akis, sonGorulme, simdi, izleme, cizim,
    ac, kapat, birak, yenidenBaglan, baglantiDegisti, kayitBaslat, kayitDurdur, seri, gorunurlukDegisti,
  };
}
