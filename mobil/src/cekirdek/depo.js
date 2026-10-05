// Kartin kayitlarinin telefondaki kopyasi (tasarim §2.2, A20, A23): `ortak/src/esitle.js` DEPO
// arayuzunun KartDepo eklentisi uzerindeki uygulamasi. Dosyalar PC ile AYNI (kayitlar.kyt, durum.json,
// kalibrasyon.json) ve uygulamanin ozel dizininde: `files/kart/<kimlik>/`.
//
//   const depo = depoKur(KartDepo, kimlik);          // kimlik: 16 kucuk onaltilik hane
//   new Esitleyici({ ..., depo });                   // esitle.js sozlesmesi (hepsi async)
//   await depo.sifirla();                            // "kopyayi sifirla" (A23)
//   await depo.boyutlar();                           // { veri, toplam, arsiv } — Ayarlar'in depolama satiri
//
// Sozlesme eklentide (KartDepo.kt): veriEkle fsync'ten SONRA doner; durumYaz / kalYaz atomik. Burada:
//   * bayt dizileri kopruden base64 gecer, parca parca (OKUMA_PARCA / YAZMA_PARCA). Cok parcali bir
//     ekleme yarida kalirsa dosyada on ek kalir — esitleyici onu acilista ileri sarar / kirpar.
//   * kilitAl surec ici: iki esitleme ayni depoya AYNI ANDA yazamaz (CalismaHatasi). Kilit kimlige
//     baglidir (ayni kimlikle kurulan iki depo nesnesi AYNI kilidi gorur).
//   * durum.json okunamiyorsa (bozuk JSON / nesne degil) DepoHatasi("bozuk"): sessizce "bos depo"
//     sayilmaz — esitleyici bastan yazip eldeki kopyanin ustune binerdi.
//   * hata: DepoHatasi(tur) — tur eklentinin TUR adi (bicim, okunamadi, yazilamadi, bozuk, ic-hata).
//     Eklentinin mesaji / yolu disari cikmaz.
import { CalismaHatasi } from "@ortak/imza.js";

export const OKUMA_PARCA = 256 * 1024;
export const YAZMA_PARCA = 256 * 1024;
const KIMLIK = /^[0-9a-f]{16}$/;
const TURLER = new Set(["bicim", "okunamadi", "yazilamadi", "bozuk", "ic-hata"]);

export class DepoHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "DepoHatasi";
    this.tur = tur;
  }
}

function base64Kodla(b) {
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

function base64Coz(s) {
  const ham = atob(s);
  const b = new Uint8Array(ham.length);
  for (let i = 0; i < ham.length; i++) b[i] = ham.charCodeAt(i);
  return b;
}

function baytlar(b) {
  if (b instanceof Uint8Array) return b;
  if (b instanceof ArrayBuffer) return new Uint8Array(b);
  if (ArrayBuffer.isView(b)) return new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
  throw new DepoHatasi("bicim");
}

const kilitler = new Set();           // kilitli kimlikler (surec ici)

export function depoKur(eklenti, kimlik, { okumaParca = OKUMA_PARCA, yazmaParca = YAZMA_PARCA } = {}) {
  if (!eklenti || typeof eklenti !== "object") throw new TypeError("eklenti gerekli");
  if (typeof kimlik !== "string" || !KIMLIK.test(kimlik)) throw new DepoHatasi("bicim");

  async function cagir(ad, veri = {}) {
    if (typeof eklenti[ad] !== "function") throw new DepoHatasi("ic-hata");
    try {
      return (await eklenti[ad]({ kimlik, ...veri })) || {};
    } catch (e) {
      const tur = e && typeof e.code === "string" && TURLER.has(e.code) ? e.code : "ic-hata";
      throw new DepoHatasi(tur);
    }
  }

  function coz(y) {
    if (!y || y.var !== true) return null;
    if (typeof y.veri !== "string") throw new DepoHatasi("ic-hata");
    try { return base64Coz(y.veri); } catch { throw new DepoHatasi("ic-hata"); }
  }

  return {
    async kilitAl() {
      if (kilitler.has(kimlik)) throw new CalismaHatasi("depo: baska bir esitleme suruyor");
      kilitler.add(kimlik);
      let birakildi = false;
      return async () => {
        if (birakildi) return;
        birakildi = true;
        kilitler.delete(kimlik);
      };
    },
    async durumOku() {
      const b = coz(await cagir("durumOku"));
      if (b === null) return null;
      let d;
      try { d = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(b)); } catch { throw new DepoHatasi("bozuk"); }
      if (d === null || typeof d !== "object" || Array.isArray(d)) throw new DepoHatasi("bozuk");
      return d;
    },
    async durumYaz(d) {
      if (d === null || typeof d !== "object" || Array.isArray(d)) throw new DepoHatasi("bicim");
      await cagir("durumYaz", { veri: base64Kodla(new TextEncoder().encode(JSON.stringify(d))) });
    },
    async veriBoyu() {
      const y = await cagir("veriBoyu");
      if (!Number.isSafeInteger(y.boy) || y.boy < 0) throw new DepoHatasi("ic-hata");
      return y.boy;
    },
    async veriOku(bas = 0) {
      if (!Number.isSafeInteger(bas) || bas < 0) throw new DepoHatasi("bicim");
      const parcalar = [];
      let toplam = 0;
      for (let konum = bas; ;) {
        const b = coz(await cagir("veriOku", { bas: konum, azami: okumaParca }));
        if (b === null || b.length === 0) break;
        if (b.length > okumaParca) throw new DepoHatasi("ic-hata");
        parcalar.push(b);
        toplam += b.length;
        konum += b.length;
      }
      const cikti = new Uint8Array(toplam);
      let a = 0;
      for (const p of parcalar) { cikti.set(p, a); a += p.length; }
      return cikti;
    },
    async veriEkle(b) {
      const v = baytlar(b);
      for (let a = 0; a < v.length; a += yazmaParca) {
        await cagir("veriEkle", { veri: base64Kodla(v.subarray(a, a + yazmaParca)) });
      }
    },
    async veriKirp(n) {
      if (!Number.isSafeInteger(n) || n < 0) throw new RangeError("kirpma boyu gecersiz");
      await cagir("veriKirp", { boy: n });
    },
    async kalOku() {
      return coz(await cagir("kalOku"));
    },
    async kalYaz(b) {
      await cagir("kalYaz", { veri: base64Kodla(baytlar(b)) });
    },
    async kalArsivle(b) {
      const y = await cagir("kalArsivle", { veri: base64Kodla(baytlar(b)) });
      if (typeof y.ad !== "string") throw new DepoHatasi("ic-hata");
      return y.ad;
    },
    // ── esitle.js arayuzunun DISINDA ──
    async sifirla() {
      if (kilitler.has(kimlik)) throw new CalismaHatasi("depo: esitleme surerken sifirlanamaz");
      await cagir("sifirla");
    },
    async boyutlar() {
      const y = await cagir("boyutlar");
      const sayi = (v) => (Number.isSafeInteger(v) && v >= 0 ? v : 0);
      return { veri: sayi(y.veri), toplam: sayi(y.toplam), arsiv: sayi(y.arsiv) };
    },
  };
}
