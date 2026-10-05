// Bildirim ayari ve anlik izlemenin WebView yarisi (5E-4; tasarim A29, A31, A35, A37, A42).
// Kripto YOK, ag YOK: zarf karttan IMZALI istekle (kart.istek — tek sayac, S1) alinir ve ACILMADAN
// eklentiye verilir; eklenti K ile acip denetler, oldugu gibi saklar (A31). Cozulmus araci bilgisi
// WebView'e HIC gelmez; bu modulun hicbir donusu adres / kullanici / konu tasimaz.
//
//   const b = bildirimKur({ kartAl, eklenti });
//   await b.yenile()      -> "yazildi" | "kartta-ayarsiz"     (hata: BildirimHatasi(tur))
//   await b.durum(kimlik) -> { zarf, izin, izinGerekli, pilMuaf, calisiyor, izleme, anlik, kapali[], dil }
//   await b.ayarYaz({ anlik?, kapali?, dil? })
//   const i = bildirimIzleyici({ bildirim: b });  i.tik({ gorunur, bagli, kimlik, kayit })   // kabuk, saniyede bir

export const BILGI_YOLU = "/bildirim/bilgi";
// kopru/pc_bildirim.py SINIFLAR ve Kotlin BildirimAyar.SINIFLAR ile AYNI sira.
export const SINIFLAR = Object.freeze(["kopuk", "bitti", "dolu", "esik", "yeniden_basladi", "kacirilan", "deneme"]);
export const DILLER = Object.freeze(["tr", "en"]);
// Zarf: "OKB1" + nonce + sifreli metin + etiket (Kotlin Zarf.EN_AZ / BildirimDeposu.ZARF_AZAMI).
export const ZARF_EN_AZ = 32;
export const ZARF_AZAMI = 2048;
// Kartin G satirindaki `durum`: kayit SURUYOR sayilan kodlar (KDR.KAYIT, KDR.BEKLIYOR — pc_bildirim.py ile ayni).
export const KAYITTA = Object.freeze([2, 4]);

const KIMLIK = /^[0-9a-f]{16}$/;
const TUR = /^[a-z][a-z-]{0,23}$/;
const IZLEME_DURUMLARI = new Set(["baglaniyor", "izleniyor", "internet", "guven", "araci", "kayit-bitti", "ayar", "durduruldu", "ic-hata"]);

export class BildirimHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "BildirimHatasi";
    this.tur = tur;
  }
}

function base64Kodla(b) {
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

export function bildirimKur({ kartAl, eklenti }) {
  if (typeof kartAl !== "function") throw new TypeError("kartAl gerekli");
  if (!eklenti) throw new TypeError("eklenti gerekli");

  async function cagir(ad, veri = {}) {
    if (typeof eklenti[ad] !== "function") throw new BildirimHatasi("ic-hata");
    try {
      return (await eklenti[ad](veri)) || {};
    } catch (e) {
      // Eklenti TUR adiyla reddeder; baska hicbir metin yukari cikmaz.
      throw new BildirimHatasi(e && typeof e.code === "string" && TUR.test(e.code) ? e.code : "ic-hata");
    }
  }

  const kimlikli = (kimlik) => {
    if (typeof kimlik !== "string" || !KIMLIK.test(kimlik)) throw new BildirimHatasi("bicim");
    return kimlik;
  };

  // Karttan zarfi al ve sakla. Yalniz BAGLI (kimligi dogrulanmis, eslesmis) karta imzali istek gider.
  async function yenile() {
    let kart;
    try { kart = await kartAl(); } catch { throw new BildirimHatasi("bagli-degil"); }
    const d = kart.durum();
    if (!d || d.durum !== "bagli" || typeof d.kimlik !== "string" || !KIMLIK.test(d.kimlik)) throw new BildirimHatasi("bagli-degil");
    let yanit;
    try {
      yanit = await kart.istek("GET", BILGI_YOLU);
    } catch (e) {
      const tur = e && typeof e.tur === "string" ? e.tur : "";
      if (tur === "http" && e.durum === 404) {
        // Kartta MQTT bildirimi ayarli degil: eldeki zarf artik gecersiz (eski araci bilgisiyle baglanilmasin).
        await cagir("zarfSil", { kimlik: d.kimlik });
        return "kartta-ayarsiz";
      }
      throw new BildirimHatasi(tur === "ag" || tur === "cihaz-silinmis" || tur === "bagli-degil" || tur === "eslesmemis" ? tur : "kart");
    }
    let govde;
    try { govde = new Uint8Array(await yanit.arrayBuffer()); } catch { throw new BildirimHatasi("kart"); }
    if (govde.length < ZARF_EN_AZ || govde.length > ZARF_AZAMI) throw new BildirimHatasi("bicim");
    await cagir("zarfYaz", { kimlik: d.kimlik, zarf: base64Kodla(govde) });
    return "yazildi";
  }

  // Eklentinin durumu; alanlar TEK TEK denetlenir (beklenmeyen alan yukari cikmaz).
  async function durum(kimlik = null) {
    const y = await cagir("durum", typeof kimlik === "string" && KIMLIK.test(kimlik) ? { kimlik } : {});
    return {
      zarf: y.zarf === true,
      izin: y.izin === true,
      izinGerekli: y.izinGerekli === true,
      pilMuaf: y.pilMuaf === true,
      calisiyor: y.calisiyor === true,
      izleme: IZLEME_DURUMLARI.has(y.izleme) ? y.izleme : "durduruldu",
      anlik: y.anlik === true,
      kapali: SINIFLAR.filter((s) => Array.isArray(y.kapali) && y.kapali.includes(s)),
      dil: DILLER.includes(y.dil) ? y.dil : "tr",
    };
  }

  async function ayarYaz({ anlik, kapali, dil } = {}) {
    const veri = {};
    if (typeof anlik === "boolean") veri.anlik = anlik;
    if (Array.isArray(kapali)) veri.kapali = SINIFLAR.filter((s) => kapali.includes(s));
    if (DILLER.includes(dil)) veri.dil = dil;
    await cagir("ayarYaz", veri);
  }

  return {
    yenile, durum, ayarYaz,
    izinIste: async () => (await cagir("izinIste")).izin === true,
    pilMuafiyetiIste: async () => (await cagir("pilMuafiyetiIste")).pilMuaf === true,
    deneme: async () => (await cagir("deneme")).izin === true,
    // { basladi, neden }: neden "" | "kapali" (anlik izleme kapali) | "zarf-yok" | "calisiyor"
    izlemeBaslat: async (kimlik) => {
      const y = await cagir("izlemeBaslat", { kimlik: kimlikli(kimlik) });
      return { basladi: y.basladi === true, neden: typeof y.neden === "string" && TUR.test(y.neden) ? y.neden : "" };
    },
    izlemeDurdur: async () => { await cagir("izlemeDurdur"); },
    yerel: async (kimlik, kod, oturum) => {
      if (!Number.isInteger(kod) || !Number.isInteger(oturum) || kod < 0 || oturum < 0) throw new BildirimHatasi("bicim");
      return (await cagir("yerel", { kimlik: kimlikli(kimlik), durum: kod, oturum })).iletildi === true;
    },
  };
}

// Kabugun saniyelik tikinden beslenir (uygulama ONDEYKEN ve kart BAGLIYKEN):
//   * her YENI baglantida zarf bir kez yenilenir (A31: "uygulamayi kartin aginda ac" bunu yapar)
//   * kartin kayit durumu DEGISINCE servise iletilir (A35) ve kayit suruyorsa anlik izleme baslatilir
//     (A29 a, b — ayar kapaliysa / zarf yoksa eklenti baslatmaz)
// Isler SIRAYLA kosar (zarf yazilmadan izleme baslatilmaz); hicbir hata yukari cikmaz — bildirim kusuru
// olcum ekranini bozmaz. `son()` son yenilemenin sonucunu verir (Ayarlar gosterir).
export function bildirimIzleyici({ bildirim }) {
  let oncekiBagli = false;
  let sonG = null;
  let kuyruk = Promise.resolve();
  let sonuc = null;                    // null | "yazildi" | "kartta-ayarsiz" | hata turu

  const sirayla = (is) => { kuyruk = kuyruk.then(is).catch(() => {}); };

  function tik({ gorunur, bagli, kimlik, kayit }) {
    if (!gorunur || !bagli || typeof kimlik !== "string" || !KIMLIK.test(kimlik)) {
      oncekiBagli = false;
      sonG = null;
      return;
    }
    if (!oncekiBagli) {
      oncekiBagli = true;
      sirayla(async () => {
        try { sonuc = await bildirim.yenile(); } catch (e) { sonuc = e && typeof e.tur === "string" ? e.tur : "ic-hata"; }
      });
    }
    if (!kayit || !Number.isInteger(kayit.durum) || !Number.isInteger(kayit.oturum) || kayit.durum < 0 || kayit.oturum < 0) return;
    const g = `${kayit.durum}:${kayit.oturum}`;
    if (g === sonG) return;
    sonG = g;
    const { durum, oturum } = kayit;
    sirayla(async () => {
      if (KAYITTA.includes(durum)) await bildirim.izlemeBaslat(kimlik).catch(() => {});
      await bildirim.yerel(kimlik, durum, oturum);
    });
  }

  return { tik, son: () => sonuc, bosalt: () => kuyruk };
}
