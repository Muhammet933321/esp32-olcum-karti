// Kasa sarmalayicisi (tasarim A14, A16, S1): Kotlin `Kasa` eklentisinin ustunde cihaz nesnesi ve
// blok ayirmali kalici sayac. Kripto YOK — K yalnizca tasinir (Keystore sarmasi Kotlin'de).
//
//   const kasa = kasaKur(Kasa, { simdiMs, blok });
//   const cihaz = await kasa.cihazYukle(kimlik);     // { kimlik, n, K, ad, sayac, acilis: null } | null
//   await kasa.cihazSakla(cihaz);                    // eslestirmeden sonra: anahtar + ilk isaret
//   ortam.kaydet = kasa.kaydet                       // imza.js ac() her istekten ONCE bekler
//
// Sayac kurali (A16). Diskte tek bir ISARET durur; kullanilan her sayac <= isaret olmak ZORUNDADIR:
//   * yuklemede sayac = isaret  -> sonraki deger isareti gecer -> ilk istek isareti yazar
//   * kaydet: sayac isareti geciyorsa isaret = sayac + blok olarak, istek gitmeden once yazilir
//   * gecmiyorsa diske dokunulmaz (blok basina bir yazim)
// Boylece uygulama hangi anda cokerse coksun ve saat ne kadar geri alinirsa alinsin, yeniden
// yuklenen sayac daha once kullanilmis hicbir degerin altina inmez.
//
// Kayit ya TAMDIR ya YOKTUR: cihazSakla yarida kalirsa (anahtar yazildi, ilk isaret yazilamadi) disk
// kaydini ve bellekteki nesneyi siler. Silme de olmazsa geriye "anahtar var, isaret 0" kalir — tam bir
// kaydin isareti hic 0 olamayacagi icin (ilk isaret >= blok) cihazYukle bunu tanir, siler, null doner.
// Sifirlanmis (32 sifir bayt) K ile imza atilmaz: kaydet 'kayitsiz' der.
// TEK kasa nesnesi (S1): uygulamada kasaKur bir kez cagrilir (cekirdek/uygulama.js). Ikinci bir yazar
// olursa eklenti, diskteki isarete ESIT ya da kucuk yazimi 'geri' ile reddeder.
//
// Kimlik basina TEK cihaz nesnesi (A15): cihazYukle ayni nesneyi doner, kaydet baska nesneyi reddeder
// (iki nesne ayni milisaniyede ayni sayaci secerdi).
// Hata: KasaHatasi(tur) — yalniz tur; eklentinin mesaji, kimlik, anahtar tasinmaz (A45).
//   yok | bozuk | bicim | geri | ic-hata (eklentiden)   kayitsiz | sayac-geride (buradan)

import { adGecerli } from "@ortak/imza.js";

const KIMLIK = /^[0-9a-f]{16}$/;
const ISARET = /^(0|[1-9][0-9]{0,15})$/;
const ANAHTAR_BOYU = 32;
const EKLENTI_TURLERI = Object.freeze(["yok", "bozuk", "bicim", "geri"]);

export class KasaHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KasaHatasi";
    this.tur = tur;
  }
}

function base64Kodla(b) {
  let s = "";
  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
  return btoa(s);
}

function base64Coz(s) {
  const ham = atob(s);
  const b = new Uint8Array(ham.length);
  for (let i = 0; i < ham.length; i++) b[i] = ham.charCodeAt(i);
  return b;
}

function sifirMi(K) {
  for (let i = 0; i < K.length; i++) if (K[i] !== 0) return false;
  return true;
}

function sayacGecerli(s) {
  return Number.isSafeInteger(s) && s >= 0;
}

export function kasaKur(eklenti, { simdiMs = Date.now, blok = 4096 } = {}) {
  if (!eklenti || typeof eklenti.sayacYaz !== "function") throw new TypeError("eklenti.sayacYaz gerekli");
  if (!Number.isSafeInteger(blok) || blok < 1) throw new TypeError("blok pozitif tamsayi olmali");

  // kimlik -> { cihaz, isaret, nesil }. isaret: diske yazildigini BILDIGIMIZ deger. nesil: 'geri'
  // her goruldugunde artar; daha once secilmis sayaclar (eski nesil) reddedilir.
  const yuklu = new Map();
  // Disk islemleri TEK kuyruktan gecer: es zamanli kaydet cagrilari sirayla, ust uste binmeden.
  let kuyruk = Promise.resolve();
  function sirayla(is) {
    const soz = kuyruk.then(is);
    kuyruk = soz.catch(() => {});
    return soz;
  }

  async function cagir(ad, veri) {
    try {
      return await eklenti[ad](veri);
    } catch (e) {
      throw new KasaHatasi(e && typeof e.code === "string" && EKLENTI_TURLERI.includes(e.code) ? e.code : "ic-hata");
    }
  }

  async function isaretOku(kimlik) {
    const y = await cagir("sayacOku", { kimlik });
    const metin = y ? y.isaret : null;
    if (typeof metin !== "string" || !ISARET.test(metin)) throw new KasaHatasi("bozuk");
    return Number(metin);
  }

  function birak(kimlik) {
    const k = yuklu.get(kimlik);
    if (k) k.cihaz.K.fill(0);
    yuklu.delete(kimlik);
  }

  function cihazYukle(kimlik) {
    return sirayla(async () => {
      const onceki = yuklu.get(kimlik);
      if (onceki) return onceki.cihaz;
      let kayit;
      try {
        kayit = await cagir("anahtarOku", { kimlik });
      } catch (e) {
        if (e.tur === "yok") return null;
        throw e;
      }
      if (!kayit || kayit.kimlik !== kimlik || !KIMLIK.test(kimlik) || !Number.isSafeInteger(kayit.n) || kayit.n < 1
        || typeof kayit.ad !== "string" || typeof kayit.anahtar !== "string") throw new KasaHatasi("bozuk");
      let K;
      try { K = base64Coz(kayit.anahtar); } catch { throw new KasaHatasi("bozuk"); }
      if (K.length !== ANAHTAR_BOYU) { K.fill(0); throw new KasaHatasi("bozuk"); }
      let isaret;
      try { isaret = await isaretOku(kimlik); } catch (e) { K.fill(0); throw e; }
      // Yarim kayit (cihazSakla yarida kalmis, silinememis): eslesme sayilmaz, temizlenir.
      if (isaret === 0) {
        K.fill(0);
        await cagir("sil", { kimlik });
        return null;
      }
      // A16: acilista son = diskteki isaret.
      const cihaz = { kimlik, n: kayit.n, K, ad: kayit.ad, sayac: isaret, acilis: null };
      yuklu.set(kimlik, { cihaz, isaret, nesil: 0 });
      return cihaz;
    });
  }

  function cihazSakla(cihaz) {
    return sirayla(async () => {
      if (!cihaz || typeof cihaz.kimlik !== "string" || !KIMLIK.test(cihaz.kimlik) || !(cihaz.K instanceof Uint8Array)
        || cihaz.K.length !== ANAHTAR_BOYU || !Number.isInteger(cihaz.n) || cihaz.n < 1 || cihaz.n > 255
        || typeof cihaz.ad !== "string" || !adGecerli(cihaz.ad) || sifirMi(cihaz.K)) throw new KasaHatasi("bicim");
      const { kimlik } = cihaz;
      try {
        await yaz(cihaz, kimlik);
      } catch (e) {
        // Yarim kayit kalmaz: bellekten duser, diskten silinir (silinemezse cihazYukle tanir).
        const kalan = yuklu.get(kimlik);
        if (kalan && kalan.cihaz !== cihaz) kalan.cihaz.K.fill(0);       // eski nesnenin diski de gidiyor
        yuklu.delete(kimlik);
        try { await cagir("sil", { kimlik }); } catch { /* cihazYukle: isaret 0 -> yarim kayit */ }
        throw e;
      }
    });
  }

  async function yaz(cihaz, kimlik) {
    await cagir("anahtarYaz", { kimlik, n: cihaz.n, ad: cihaz.ad, anahtar: base64Kodla(cihaz.K) });
    const onceki = yuklu.get(kimlik);
    if (onceki && onceki.cihaz !== cihaz) birak(kimlik);         // eski K bellekte kalmaz
    // Ilk isaret: ayni kimlikle onceki bir eslesmenin isareti varsa onun ALTINA inilmez.
    const diskte = await isaretOku(kimlik);
    const k = { cihaz, isaret: diskte, nesil: 0 };
    yuklu.set(kimlik, k);
    if (!sayacGecerli(cihaz.sayac) || cihaz.sayac < diskte) cihaz.sayac = diskte;
    const hedef = Math.max(diskte, cihaz.sayac, Math.floor(simdiMs())) + blok;
    if (!Number.isSafeInteger(hedef)) throw new KasaHatasi("bicim");
    try {
      await cagir("sayacYaz", { kimlik, isaret: String(hedef) });
      k.isaret = hedef;
    } catch (e) {
      if (e.tur !== "geri") throw e;
      k.isaret = await isaretOku(kimlik);
      if (cihaz.sayac < k.isaret) cihaz.sayac = k.isaret;
    }
  }

  // imza.js `ortam.kaydet` kancasi. Sayac, cagri ANINDA okunur (es zamanli isteklerde herkes kendi
  // degerini gorur); yazim kuyruktan gecer ve cagiran, isaret diske varana kadar BEKLER.
  function kaydet(cihaz) {
    const s = cihaz ? cihaz.sayac : null;
    const ilk = cihaz ? yuklu.get(cihaz.kimlik) : null;
    const nesil = ilk ? ilk.nesil : 0;
    return sirayla(async () => {
      const k = cihaz ? yuklu.get(cihaz.kimlik) : null;
      if (!k || k.cihaz !== cihaz || sifirMi(cihaz.K)) throw new KasaHatasi("kayitsiz");
      if (!sayacGecerli(s) || !Number.isSafeInteger(s + blok)) throw new KasaHatasi("bicim");
      // 'geri' gorulmeden once secilmis deger: baska bir yazar onu kullanmis olabilir.
      if (nesil !== k.nesil) throw new KasaHatasi("sayac-geride");
      if (s <= k.isaret) return;
      const hedef = s + blok;
      try {
        await cagir("sayacYaz", { kimlik: cihaz.kimlik, isaret: String(hedef) });
      } catch (e) {
        if (e.tur !== "geri") throw e;
        // Disk bizden ileride (ikinci bir yazar — S1'e gore olmamali). Sayac diskteki isarete
        // cekilir; o ana kadar secilmis her deger (eski nesil) reddedilir, cagiran yeniden imzalar.
        k.isaret = await isaretOku(cihaz.kimlik);
        k.nesil += 1;
        if (cihaz.sayac < k.isaret) cihaz.sayac = k.isaret;
        throw new KasaHatasi("sayac-geride");
      }
      k.isaret = hedef;
    });
  }

  function sil(kimlik) {
    return sirayla(async () => {
      await cagir("sil", { kimlik });
      birak(kimlik);
    });
  }

  function liste() {
    return sirayla(async () => {
      const y = await cagir("liste", {});
      if (!y || !Array.isArray(y.kayitlar)) throw new KasaHatasi("bozuk");
      return y.kayitlar.map((k) => {
        // Acilamayan kayit gizlenmez: cagiran silip yeniden eslestirmeyi onerebilsin.
        if (k && typeof k.kimlik === "string" && KIMLIK.test(k.kimlik) && k.bozuk === true) return { kimlik: k.kimlik, bozuk: true };
        if (!k || typeof k.kimlik !== "string" || !KIMLIK.test(k.kimlik) || !Number.isSafeInteger(k.n) || typeof k.ad !== "string") {
          throw new KasaHatasi("bozuk");
        }
        return { kimlik: k.kimlik, n: k.n, ad: k.ad };
      });
    });
  }

  return { cihazYukle, cihazSakla, kaydet, sil, liste };
}
