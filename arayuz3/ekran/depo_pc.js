/* ═══════════════════════════════════════════════════════════════════════
   4D — PC ARSIVI: SALT OKUNUR DEPO                     (ekran/depo_pc.js)

   Panel PC koprusunden (http://olcum.localhost:8770) acildiginda kayitlar
   bu tarayicinin IndexedDB'sinden DEGIL, koprunun diske yazdigi arsivden
   okunur (karar PC10, tasarim/2026-10-03-alt-proje-4-pc.md "4D uygulama
   kararlari"):
     GET /arsiv/liste                          akislar + oturum ozeti
     GET /arsiv/veri?kart=&akis=&ofset=&bayt=  kayitlar.kyt bayt araligi
     GET /arsiv/kal?kart=&akis=                kalibrasyon.json
   `ortak/src/esitle.js` DEPO arayuzunun YALNIZ OKUMA tarafi (durumOku,
   veriBoyu, veriOku, kalOku). Yazan her yontem (kilitAl, durumYaz,
   veriEkle, veriKirp, kalYaz, kalArsivle) CalismaHatasi ile REDDEDER:
   tek yazar Python (kopru/arka_esitle.py) — iki yazar / iki kopya yok,
   `esitle.kilit`'in onledigi yaris dogmaz. Esitleyici bu depoyla calisirsa
   ilk adimda (kilitAl) durur, aga hicbir istek gitmez.
   Ag `getir(yol)` ile ENJEKTE (esitleme.js: fetch(kartAdres(yol))) — bu
   dosyada fetch yok; kopru uclari imza katmanina girmez (EU8').
   Bu modul YALNIZ kopru kokeninde `import()` ile iner (esitleme.js
   `kaynak()`); kartin sundugu panel onu hic istemez.
   ═══════════════════════════════════════════════════════════════════════ */

import { CalismaHatasi } from '/ortak/imza.js';

/** Tek /arsiv/veri isteginin boyu (kopru tavani 4 MB; dolu 11.4 MB bolum ~6 istek). */
export const PC_PARCA = 2 * 1024 * 1024;
export const SALT_OKUMA = 'PC arsivi salt okuma: tek yazar kopru (kopru/pc.py)';
const KART = /^[0-9a-f]{16}$/;

const tamsayi = (x) => Number.isSafeInteger(x) && x >= 0;

/** /arsiv/liste JSON'u -> akislar (EN YENI ONCE, kopru sirasi). Bicim disi girdi atilir; liste degilse null. */
export function pcListeCoz(v) {
  if (!v || typeof v !== 'object' || !Array.isArray(v.arsivler)) return null;
  const cikti = [];
  for (const a of v.arsivler) {
    if (!a || typeof a !== 'object' || !KART.test(a.kart) || !tamsayi(a.akis) || !tamsayi(a.bayt)) continue;
    const d = a.durum && typeof a.durum === 'object' ? a.durum : {};
    const durum = {};
    for (const k of ['son_sira', 'bayt', 'onaylanan', 'kimlik']) if (tamsayi(d[k])) durum[k] = d[k];
    cikti.push({ kart: a.kart, akis: a.akis, bayt: a.bayt, durum: Object.keys(durum).length ? durum : null,
      degisim: typeof a.degisim === 'number' && a.degisim > 0 ? a.degisim : 0, kal: a.kal === true,
      oturum: tamsayi(a.oturum) ? a.oturum : null });
  }
  return cikti;
}

/** Kopruden akis listesi. Ag / HTTP / bicim hatasi ATAR (cagiran sebebi soyler). */
export async function pcAkislar(getir) {
  const y = await getir('/arsiv/liste');
  if (!y.ok) throw new Error(`/arsiv/liste HTTP ${y.status}`);
  const l = pcListeCoz(await y.json().catch(() => null));
  if (!l) throw new Error('/arsiv/liste bicimsiz');
  return l;
}

function birlestir(parcalar, n) {
  const c = new Uint8Array(n);
  let a = 0;
  for (const p of parcalar) { c.set(p, a); a += p.length; }
  return c;
}

/**
 * esitle.js DEPO arayuzunun OKUMA tarafi, bir PC akisi icin (`a`: pcListeCoz ogesi). `kimlik` =
 * kartin kayit akis kimligi (rota / karsilastirma anahtari tarayici kopyasiyla AYNI bicim).
 */
export function pcDepo(getir, a) {
  const q = `kart=${a.kart}&akis=${a.akis}`;
  const ret = async () => { throw new CalismaHatasi(SALT_OKUMA); };
  return {
    kimlik: a.akis,
    kart: a.kart,
    salt: true,
    kilitAl: ret,
    durumYaz: ret,
    veriEkle: ret,
    veriKirp: ret,
    kalYaz: ret,
    kalArsivle: ret,
    async durumOku() { return a.durum ? { ...a.durum } : null; },
    async veriBoyu() { return a.bayt; },
    /** bas'tan kalici onekin sonuna (X-Arsiv-Boy) — PC_PARCA'lik araliklarla. */
    async veriOku(bas = 0) {
      const parcalar = [];
      let ofset = Number.isSafeInteger(bas) && bas > 0 ? bas : 0;
      let boy = null;
      let n = 0;
      for (let tur = 0; tur < 4096; tur++) {
        const y = await getir(`/arsiv/veri?${q}&ofset=${ofset}&bayt=${PC_PARCA}`);
        if (!y.ok) throw new Error(`/arsiv/veri HTTP ${y.status}`);
        const b = new Uint8Array(await y.arrayBuffer());
        if (boy === null) {
          const h = Number(y.headers.get('X-Arsiv-Boy'));
          boy = Number.isSafeInteger(h) && h >= 0 ? h : ofset + b.length;
        }
        if (b.length) { parcalar.push(b); n += b.length; ofset += b.length; }
        if (!b.length || ofset >= boy) break;
      }
      return birlestir(parcalar, n);
    },
    async kalOku() {
      if (!a.kal) return null;
      const y = await getir(`/arsiv/kal?${q}`);
      if (y.status === 404) return null;
      if (!y.ok) throw new Error(`/arsiv/kal HTTP ${y.status}`);
      return new Uint8Array(await y.arrayBuffer());
    },
  };
}
