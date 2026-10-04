// Kotlin `Kasa` eklentisinin Node'daki sahtesi (arayuz: 5B gorev tanimi). "Disk" ayri bir nesnedir:
// ayni diskle yeni bir sahte kurmak = uygulamayi yeniden baslatmak.
//
//   const disk = kasaDiski();
//   const ek = kasaSahtesi(disk, { yazimGecikmeMs: 0 });
//   ek.cagrilar  -> [{ ad, veri }]      ek.sayacYazimi -> basarili sayacYaz sayisi
//   ek.azamiEszamanli -> ayni anda suren sayacYaz sayisinin en buyugu
//   ek.bozYazim = "ic-hata"  -> bir sonraki sayacYaz bu turle reddedilir (bir kez)
// Hata, eklenti gibi `code` = tur ile atilir. Isaretler BigInt tutulur (Kotlin'de Long).
// GERCEK Kotlin KasaKomut ile ayni kurallar (test/curutucu-5b/ayrisma.test.js karsilastirir):
//   ad <= 24 UTF-8 bayt · base64 java.util.Base64 gibi KATI (dolgu ya hic ya tam) · isaret Long sinirinda
//   liste kimlige gore SIRALI · sayacYaz: dosya VARKEN isaret <= eski -> 'geri' (esit yazim = ikinci yazar)

const KIMLIK = /^[0-9a-f]{16}$/;
const ONDALIK = /^[0-9]{1,19}$/;
const BASE64 = /^([A-Za-z0-9+/]*)(={0,2})$/;      // standart alfabe; bosluk yok
const AD_AZAMI_BAYT = 24;
const LONG_AZAMI = 9223372036854775807n;

// java.util.Base64.getDecoder(): dolgu ya HIC yoktur ya da TAM gerektigi kadardir.
function base64Kati(s) {
  const m = BASE64.exec(s);
  if (!m || m[1].length % 4 === 1) return false;
  return m[2].length === 0 || m[2].length === (4 - (m[1].length % 4)) % 4;
}

function hata(tur) {
  const e = new Error(tur);
  e.code = tur;
  return e;
}

export function kasaDiski() {
  return { anahtarlar: new Map(), isaretler: new Map() };
}

export function kasaSahtesi(disk, { yazimGecikmeMs = 0 } = {}) {
  const ek = { cagrilar: [], sayacYazimi: 0, azamiEszamanli: 0, bozYazim: null, yazimGecikmeMs };
  let suren = 0;
  const kayit = (ad, veri) => { ek.cagrilar.push({ ad, veri: { ...veri } }); };
  const kimlikGerek = (v) => { if (!v || typeof v.kimlik !== "string" || !KIMLIK.test(v.kimlik)) throw hata("bicim"); };

  ek.anahtarYaz = async (v) => {
    kayit("anahtarYaz", v);
    kimlikGerek(v);
    if (!Number.isInteger(v.n) || v.n < 1 || v.n > 255 || typeof v.ad !== "string" || typeof v.anahtar !== "string") throw hata("bicim");
    if (!base64Kati(v.anahtar) || Buffer.from(v.anahtar, "base64").length !== 32) throw hata("bicim");
    if (Buffer.byteLength(v.ad, "utf8") > AD_AZAMI_BAYT) throw hata("bicim");
    disk.anahtarlar.set(v.kimlik, { n: v.n, ad: v.ad, anahtar: v.anahtar });
    return {};
  };

  ek.anahtarOku = async (v) => {
    kayit("anahtarOku", v);
    kimlikGerek(v);
    const k = disk.anahtarlar.get(v.kimlik);
    if (!k) throw hata("yok");
    if (k.bozuk) throw hata("bozuk");
    return { kimlik: v.kimlik, n: k.n, ad: k.ad, anahtar: k.anahtar };
  };

  ek.liste = async () => {
    kayit("liste", {});
    // Acilamayan kayit GIZLENMEZ: { kimlik, bozuk: true } (n / ad yok).
    return { kayitlar: [...disk.anahtarlar].sort(([a], [b]) => (a < b ? -1 : 1)).map(([kimlik, k]) => (k.bozuk ? { kimlik, bozuk: true } : { kimlik, n: k.n, ad: k.ad })) };
  };

  ek.sil = async (v) => {
    kayit("sil", v);
    kimlikGerek(v);
    disk.anahtarlar.delete(v.kimlik);
    disk.isaretler.delete(v.kimlik);
    return {};
  };

  ek.sayacOku = async (v) => {
    kayit("sayacOku", v);
    kimlikGerek(v);
    const i = disk.isaretler.get(v.kimlik);
    if (i === "bozuk") throw hata("bozuk");
    return { isaret: (i ?? 0n).toString() };
  };

  ek.sayacYaz = async (v) => {
    kayit("sayacYaz", v);
    kimlikGerek(v);
    if (typeof v.isaret !== "string" || !ONDALIK.test(v.isaret) || BigInt(v.isaret) > LONG_AZAMI) throw hata("bicim");
    suren += 1;
    ek.azamiEszamanli = Math.max(ek.azamiEszamanli, suren);
    try {
      if (ek.yazimGecikmeMs > 0) await new Promise((r) => setTimeout(r, ek.yazimGecikmeMs));
      if (ek.bozYazim) { const t = ek.bozYazim; ek.bozYazim = null; throw hata(t); }
      // Bozuk sayac dosyasinin USTUNE YAZILMAZ: tek kurtarma sil() + yeniden eslestirme.
      if (disk.isaretler.get(v.kimlik) === "bozuk") throw hata("bozuk");
      const yeni = BigInt(v.isaret);
      // Dosya VARKEN esit yazim da 'geri': tek yazar hep buyutur; esit deger ikinci bir yazarin isaretidir.
      if (disk.isaretler.has(v.kimlik) && yeni <= disk.isaretler.get(v.kimlik)) throw hata("geri");
      disk.isaretler.set(v.kimlik, yeni);
      ek.sayacYazimi += 1;
      return { isaret: yeni.toString() };
    } finally {
      suren -= 1;
    }
  };

  return ek;
}
