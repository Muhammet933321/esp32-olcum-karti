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
export const URETICILER = Object.freeze(["honor", "huawei", "xiaomi", "samsung", "diger"]);
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
      uretici: URETICILER.includes(y.uretici) ? y.uretici : "diger",
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
    uygulamaAyarlariAc: async () => { await cagir("uygulamaAyarlariAc"); },
    // { basladi, neden }: neden "" | "kapali" (anlik izleme kapali) | "zarf-yok" | "calisiyor"
    // buKayit: anlik izleme ayari KAPALI olsa da yalniz bu kayit icin baslat (kullanici soruya "ac" dedi).
    izlemeBaslat: async (kimlik, { buKayit = false } = {}) => {
      const y = await cagir("izlemeBaslat", buKayit === true ? { kimlik: kimlikli(kimlik), buKayit: true } : { kimlik: kimlikli(kimlik) });
      return { basladi: y.basladi === true, neden: typeof y.neden === "string" && TUR.test(y.neden) ? y.neden : "" };
    },
    izlemeDurdur: async () => { await cagir("izlemeDurdur"); },
    // Kartin dogrulanmis yerel adresi (A36: servis araci "cevrimdisi" derken bu adresi imzasiz yoklar).
    adresYaz: async (kimlik, adres) => {
      if (typeof adres !== "string" || adres.length === 0 || adres.length > 21) throw new BildirimHatasi("bicim");
      await cagir("adresYaz", { kimlik: kimlikli(kimlik), adres });
    },
    yerel: async (kimlik, kod, oturum) => {
      if (!Number.isInteger(kod) || !Number.isInteger(oturum) || kod < 0 || oturum < 0) throw new BildirimHatasi("bicim");
      return (await cagir("yerel", { kimlik: kimlikli(kimlik), durum: kod, oturum })).iletildi === true;
    },
  };
}

// Kayit BU TELEFONDAN baslatilinca BIR kez sorulan soru (kullanici karari, 2026-10-05): anlik izleme
// varsayilan kapali kalir; "bu kayit icin acilsin mi?" Soru kaydi BEKLETMEZ (kayit coktan basladi).
//   hal: "yok" | "soruluyor" | "aciliyor" | "acildi" | "acilamadi"
// Sorulmaz: anlik izleme zaten acik (izleyici kendisi baslatir), servis calisiyor, bildirim ayari
// (zarf) yok — izlenemeyecek kayit icin soru sorulmaz. Hicbir hata yukari cikmaz.
export function izlemeSorusuKur({ bildirim, kimlikAl }) {
  let hal = "yok";
  let kimlik = null;
  let kusak = 0;                       // kayit bitti / yeni kayit: suren islem sonucunu YAZMASIN
  const dinleyenler = new Set();
  const yay = (yeni) => { if (yeni !== hal) { hal = yeni; for (const fn of dinleyenler) { try { fn(hal); } catch { /* dinleyen */ } } } };

  async function kayitBasladi() {
    const k = ++kusak;
    yay("yok");
    try {
      const id = await kimlikAl();
      if (typeof id !== "string" || !KIMLIK.test(id)) return;
      const d = await bildirim.durum(id);
      if (k !== kusak || d.anlik || d.calisiyor || !d.zarf) return;
      kimlik = id;
      yay("soruluyor");
    } catch { /* soru sorulmaz */ }
  }

  async function evet() {
    if (hal !== "soruluyor") return;
    const k = kusak;
    yay("aciliyor");
    let basladi = false;
    try {
      const d = await bildirim.durum(kimlik);
      if (k !== kusak) return;                                      // kayit bu arada bitti (curutucu 5E B15)
      if (!d.izin && d.izinGerekli) await bildirim.izinIste();      // reddedilse de izleme calisir; bildirim gorunmez
      if (k !== kusak) return;                                      // izin penceresi acikken kayit bitti: BASLATILMAZ
      basladi = (await bildirim.izlemeBaslat(kimlik, { buKayit: true })).basladi === true;
    } catch { basladi = false; }
    if (k === kusak) yay(basladi ? "acildi" : "acilamadi");
  }

  return {
    kayitBasladi, evet,
    hayir: () => { if (hal === "soruluyor") yay("yok"); },
    kayitBitti: () => { kusak += 1; yay("yok"); },
    hal: () => hal,
    dinle(fn) { dinleyenler.add(fn); return () => dinleyenler.delete(fn); },
  };
}

// Kayit durumu (G satirinin `durum` kodu) degisince: kayit BITTI mi? Bilinmeyen (null: akis koptu) "bitti" DEGILDIR;
// BEKLIYOR da kayit sayilir (KAYITTA) — curutucu 5E K-11: KAYIT -> BEKLIYOR gecisinde soru kapaniyordu.
export function kayitBittiMi(onceki, yeni) {
  return KAYITTA.includes(onceki) && Number.isInteger(yeni) && !KAYITTA.includes(yeni);
}

// Basarisiz zarf yenilemesi bu kadar tik (~saniye) sonra yeniden denenir (curutucu 5E B12).
export const YENILE_ARALIK_TIK = 30;
// Servis henuz ayaga kalkmadan iletilen yerel durum en cok bu kadar tik yeniden iletilir (B13).
export const YEREL_DENEME = 5;

// Kabugun saniyelik tikinden beslenir (uygulama ONDEYKEN ve kart BAGLIYKEN):
//   * her YENI baglantida (ve kart DEGISINCE — B14) adres yazilir, zarf yenilenir (A31); yenileme basarisizsa
//     YENILE_ARALIK_TIK sonra yeniden denenir ve basarinca suren kayit icin izleme yeniden baslatilir (B12)
//   * kartin kayit durumu DEGISINCE servise iletilir (A35) ve kayit suruyorsa anlik izleme baslatilir
//     (A29 a, b — ayar kapaliysa / zarf yoksa eklenti baslatmaz); servis henuz hazir degilse durum birkac
//     tik yeniden iletilir (B13)
// Isler SIRAYLA kosar (zarf yazilmadan izleme baslatilmaz); hicbir hata yukari cikmaz — bildirim kusuru
// olcum ekranini bozmaz. `son()` son yenilemenin sonucunu verir (Ayarlar gosterir).
export function bildirimIzleyici({ bildirim }) {
  let bagliKimlik = null;              // durum KIMLIGE bagli: kart degisirse her sey bastan
  let sonG = null;
  let kuyruk = Promise.resolve();
  let sonuc = null;                    // null | "yazildi" | "kartta-ayarsiz" | hata turu
  let yenileBekle = 0;                 // yeniden denemeye kalan tik; 0 = bekleyen yok
  let yenileSuruyor = false;
  let yerelKalan = 0;

  const sirayla = (is) => { kuyruk = kuyruk.then(is).catch(() => {}); };

  function sifirla() {
    sonG = null;
    yenileBekle = 0;
    yerelKalan = 0;
  }

  function yenile(kimlik, yeniden) {
    yenileSuruyor = true;
    sirayla(async () => {
      try { sonuc = await bildirim.yenile(); } catch (e) { sonuc = e && typeof e.tur === "string" ? e.tur : "ic-hata"; }
      yenileSuruyor = false;
      if (bagliKimlik !== kimlik) return;
      if (sonuc === "yazildi" || sonuc === "kartta-ayarsiz") {
        yenileBekle = 0;
        if (yeniden && sonuc === "yazildi") sonG = null;       // zarf SIMDI yazildi: suren kayit icin izleme yeniden denensin
      } else {
        yenileBekle = YENILE_ARALIK_TIK;
      }
    });
  }

  function gonder(kimlik, g, durum, oturum, baslat) {
    sirayla(async () => {
      let basladi = false;
      if (baslat && KAYITTA.includes(durum)) {
        try { basladi = (await bildirim.izlemeBaslat(kimlik)).basladi === true; } catch { basladi = false; }
      }
      const iletildi = (await bildirim.yerel(kimlik, durum, oturum)) === true;
      if (bagliKimlik !== kimlik || sonG !== g) return;
      if (iletildi) yerelKalan = 0;
      else if (basladi) yerelKalan = YEREL_DENEME;             // servis baslatildi ama henuz dinlemiyor
    });
  }

  function tik({ gorunur, bagli, kimlik, kayit, adres = null }) {
    if (!gorunur || !bagli || typeof kimlik !== "string" || !KIMLIK.test(kimlik)) {
      bagliKimlik = null;
      sifirla();
      return;
    }
    if (bagliKimlik !== kimlik) {
      bagliKimlik = kimlik;
      sifirla();
      if (typeof adres === "string" && typeof bildirim.adresYaz === "function") sirayla(() => bildirim.adresYaz(kimlik, adres));
      yenile(kimlik, false);
    } else if (yenileBekle > 0 && !yenileSuruyor) {
      yenileBekle -= 1;
      if (yenileBekle === 0) yenile(kimlik, true);
    }
    if (!kayit || !Number.isInteger(kayit.durum) || !Number.isInteger(kayit.oturum) || kayit.durum < 0 || kayit.oturum < 0) return;
    const g = `${kayit.durum}:${kayit.oturum}`;
    if (g !== sonG) {
      sonG = g;
      yerelKalan = 0;
      gonder(kimlik, g, kayit.durum, kayit.oturum, true);
    } else if (yerelKalan > 0) {
      yerelKalan -= 1;
      gonder(kimlik, g, kayit.durum, kayit.oturum, false);
    }
  }

  return { tik, son: () => sonuc, bosalt: () => kuyruk };
}
