/* ═══════════════════════════════════════════════════════════════════════
   3C — KAYIT DEPOSU: IndexedDB                      (ekran/depo_idb.js)

   `ortak/src/esitle.js` DEPO arayuzunun TARAYICI uygulamasi (karar C2).
   Esitleyici olduğu gibi kullaniliyor; disk yerine IndexedDB.

   AKIS = kartin kayit akisi, KIMLIGI `X-Kayit-Kimlik` (`/kayit/liste`'de
   `kimlik`). Kimlik basina BIR akis kaydi; kart bicimlenip kimlik
   degisirse yeni akis acilir, ESKISI SILINMEZ (listede "eski kart
   kopyasi"). Akis bayt bayt kartin baytlari (§5 "aynen saklar"); ham
   `.kyt` disa aktarimi bu baytlardan.

   VERITABANI `olcum-kayit` (surum 1), uc depo:
     akis   anahtar kimlik:  {kimlik, durum, bayt, sonrakiNo, kal, olusma, guncelleme}
     parca  anahtar [kimlik, no]: {kimlik, no, bas, veri: Uint8Array}
     arsiv  anahtar [kimlik, ad]: {kimlik, ad, veri, zaman}   (kalArsivle)
   Buyuk akis (MB'larca) PARCA PARCA: her `veriEkle` bir ya da birkac
   parca (en cok PARCA_AZAMI), `bas` = parcanin akistaki ofseti.
   `akis.bayt` parcalarla AYNI islemde guncelleniyor — ikisi ayrisamaz.

   SOZLESME (esitle.js basindaki DEPO yorumu):
     * butun yazmalar `durability: 'strict'` islemde; Promise islem
       TAMAMLANINCA (oncomplete) cozuluyor: `veriEkle` donunce baytlar
       kalici, onay ANCAK ondan sonra gidebilir.
     * durumYaz ATOMIK: tek islemde tek kayit.
     * veriKirp(n): n'den sonrasi silinir; n akistan uzunsa SIFIRLA uzar
       (Python truncate / bellekDepo ile ayni).
     * kilitAl: Web Locks (`navigator.locks`, yalniz guvenli baglamda) —
       iki SEKME ayni akisa yazmasin; yoksa (kartin http:// koken'i guvenli
       baglam DEGIL) sekme ici kilit. Kilit doluysa CalismaHatasi (esitle.js).
   ⚠ Bu dosyada Vue YOK: B7 (node) saf parca hesaplarini dogrudan sinar,
     gercek IndexedDB'yi `tarayici_kayitlar.py` (T3C) tarayicida sinar.
   ═══════════════════════════════════════════════════════════════════════ */

import { CalismaHatasi } from '/ortak/imza.js';

export const VT_AD = 'olcum-kayit';
export const VT_SURUM = 1;
/** Tek parcanin en buyuk boyu. Esitleme 8 KB'lik yanitlar ekliyor; tek seferde
 *  daha buyuk ekleme (testler, ileride toplu ice aktarma) bolunur. */
export const PARCA_AZAMI = 64 * 1024;
const SON = Number.MAX_SAFE_INTEGER;

/* ── SAF parca hesaplari (B7 bunlari node'da sinar) ──────────────────── */

/** `b`'yi en cok `azami` baytlik KOPYALARA bol (bos girdi -> bos liste). */
export function parcala(b, azami = PARCA_AZAMI) {
  if (!(azami > 0)) throw new RangeError('parca boyu > 0 olmali');
  const cikti = [];
  for (let a = 0; a < b.length; a += azami) cikti.push(b.slice(a, Math.min(b.length, a + azami)));
  return cikti;
}

/** Parcalari (no sirasinda, bitisik) `bas`tan sona birlestir. toplam = akis boyu. */
export function parcalardanOku(parcalar, bas, toplam) {
  const n = Math.max(0, toplam - Math.max(0, bas));
  const cikti = new Uint8Array(n);
  for (const p of parcalar) {
    const pSon = p.bas + p.veri.length;
    if (pSon <= bas || p.bas >= toplam) continue;
    const a = Math.max(bas, p.bas);
    const b = Math.min(pSon, toplam);
    cikti.set(p.veri.subarray(a - p.bas, b - p.bas), a - bas);
  }
  return cikti;
}

/** Kirpma plani: hangi parca silinir, hangisi kisalir, kac sifir eklenir. */
export function kirpPlani(parcalar, n, toplam) {
  const sil = [];
  let kes = null;
  for (const p of parcalar) {
    if (p.bas >= n) sil.push(p.no);
    else if (p.bas + p.veri.length > n) kes = { no: p.no, boy: n - p.bas };
  }
  return { sil, kes, uzat: Math.max(0, n - toplam) };
}

/** Kalibrasyon arsivinin adi (bellekDepo ile ayni bicim; ayni saniyede -1, -2 ...). */
export function arsivAdi(t, var_) {
  const iki = (x) => String(x).padStart(2, '0');
  const kok = `kalibrasyon-${t.getFullYear()}${iki(t.getMonth() + 1)}${iki(t.getDate())}`
    + `-${iki(t.getHours())}${iki(t.getMinutes())}${iki(t.getSeconds())}`;
  let ad = `${kok}.json`;
  for (let k = 1; var_(ad); k++) ad = `${kok}-${k}.json`;
  return ad;
}

/* ── IndexedDB yardimcilari ─────────────────────────────────────────── */

function istekBekle(r) {
  return new Promise((coz, red) => {
    r.onsuccess = () => coz(r.result);
    r.onerror = () => red(r.error);
  });
}

/** Yazma islemi: `durability: 'strict'` (eski tarayici ucuncu argumani yok sayar). */
function islem(vt, depolar, yaz) {
  return yaz ? vt.transaction(depolar, 'readwrite', { durability: 'strict' })
    : vt.transaction(depolar, 'readonly');
}

/** Islem TAMAMLANINCA (kalici) cozulur; hata / iptal reddeder. */
function bitince(tx) {
  return new Promise((coz, red) => {
    tx.oncomplete = () => coz();
    tx.onerror = () => red(tx.error || new Error('IndexedDB islem hatasi'));
    tx.onabort = () => red(tx.error || new Error('IndexedDB islemi iptal edildi'));
  });
}

let vtSoz = null;

/** Veritabanini ac (sayfa basina bir kez). `idb` testte verilebilir. */
export function vtAc(idb = globalThis.indexedDB) {
  if (vtSoz) return vtSoz;
  if (!idb) return Promise.reject(new Error('Bu tarayıcıda IndexedDB yok'));
  vtSoz = new Promise((coz, red) => {
    const r = idb.open(VT_AD, VT_SURUM);
    r.onupgradeneeded = () => {
      const vt = r.result;
      if (!vt.objectStoreNames.contains('akis')) vt.createObjectStore('akis', { keyPath: 'kimlik' });
      if (!vt.objectStoreNames.contains('parca')) vt.createObjectStore('parca', { keyPath: ['kimlik', 'no'] });
      if (!vt.objectStoreNames.contains('arsiv')) vt.createObjectStore('arsiv', { keyPath: ['kimlik', 'ad'] });
    };
    r.onsuccess = () => {
      const vt = r.result;
      /* Baska sekme surum yukseltirse bu baglanti onu tikamasin. */
      vt.onversionchange = () => { vt.close(); vtSoz = null; };
      coz(vt);
    };
    r.onerror = () => { vtSoz = null; red(r.error); };
    r.onblocked = () => { vtSoz = null; red(new Error('IndexedDB baska bir sekmede açık (sürüm bekliyor)')); };
  });
  return vtSoz;
}

const aralik = (kimlik) => IDBKeyRange.bound([kimlik, 0], [kimlik, SON]);
const aralikAd = (kimlik) => IDBKeyRange.bound([kimlik, ''], [kimlik, '\uffff']);

function yeniAkis(kimlik, ek = {}) {
  const simdi = Date.now();
  return { kimlik, durum: null, bayt: 0, sonrakiNo: 0, kal: null, olusma: simdi, guncelleme: simdi, ...ek };
}

/** Akisi yoksa ac. Durum KIMLIKLE ONCEDEN tohumlanir: liste ile ilk veri yaniti
 *  arasinda kart bicimlenirse Esitleyici "kimlik degisti" der, yanlis akisa YAZMAZ. */
export async function akisHazirla(vt, kimlik, ek = {}) {
  const tx = islem(vt, ['akis'], true);
  const s = tx.objectStore('akis');
  const var_ = await istekBekle(s.get(kimlik));
  if (!var_) {
    s.put(yeniAkis(kimlik, { durum: { son_sira: 0, bayt: 0, onaylanan: 0, kimlik }, ...ek }));
  }
  await bitince(tx);
  return !var_;
}

/** Bu tarayicidaki akislar (parca verisi YOK): [{kimlik, bayt, durum, olusma, guncelleme}]. */
export async function akislar(vt) {
  const tx = islem(vt, ['akis'], false);
  const hepsi = await istekBekle(tx.objectStore('akis').getAll());
  return hepsi.map((a) => ({ kimlik: a.kimlik, bayt: a.bayt, durum: a.durum, olusma: a.olusma,
    guncelleme: a.guncelleme, kalVar: !!a.kal }))
    .sort((x, y) => (y.olusma || 0) - (x.olusma || 0));
}

/** Bir akisin butun izlerini sil (akis + parcalar + kalibrasyon arsivleri). */
export async function akisSil(vt, kimlik) {
  const tx = islem(vt, ['akis', 'parca', 'arsiv'], true);
  tx.objectStore('akis').delete(kimlik);
  tx.objectStore('parca').delete(aralik(kimlik));
  tx.objectStore('arsiv').delete(aralikAd(kimlik));
  await bitince(tx);
}

/* ── kilit ──────────────────────────────────────────────────────────── */
const SEKME_KILIT = new Set();

/** Web Locks varsa onunla (sekmeler arasi), yoksa sekme ici. Dolu -> CalismaHatasi. */
export async function kilitAl(ad, kilitler) {
  if (kilitler && typeof kilitler.request === 'function') {
    let birak = null;
    const tutuldu = new Promise((coz) => { birak = coz; });
    const alindi = await new Promise((coz, red) => {
      kilitler.request(ad, { ifAvailable: true }, (kilit) => {
        if (!kilit) { coz(false); return undefined; }
        coz(true);
        return tutuldu;                 // kilit bu soz cozulene dek tutulur
      }).catch(red);
    });
    if (!alindi) throw new CalismaHatasi('bu kayıt akışını başka bir sekme eşitliyor');
    return async () => { birak(); };
  }
  if (SEKME_KILIT.has(ad)) throw new CalismaHatasi('bu kayıt akışı zaten eşitleniyor');
  SEKME_KILIT.add(ad);
  return async () => { SEKME_KILIT.delete(ad); };
}

/* ── DEPO ───────────────────────────────────────────────────────────── */

/**
 * esitle.js DEPO arayuzu, `kimlik` akisi icin. secenek: { kilitler (navigator.locks),
 * simdi () => Date } — ikisi de testte degistirilebilir.
 */
export function idbDepo(vt, kimlik, { kilitler = globalThis.navigator && globalThis.navigator.locks,
  simdi = () => new Date() } = {}) {
  /** Akis kaydini oku-degistir-yaz; yoksa olusturur. Tek islem. */
  async function guncelle(depolar, fn) {
    const tx = islem(vt, depolar, true);
    const s = tx.objectStore('akis');
    const rec = (await istekBekle(s.get(kimlik))) || yeniAkis(kimlik);
    await fn(rec, tx);
    rec.guncelleme = Date.now();
    s.put(rec);
    await bitince(tx);
  }

  async function oku() {
    const tx = islem(vt, ['akis'], false);
    return istekBekle(tx.objectStore('akis').get(kimlik));
  }

  async function parcalar(tx) {
    return istekBekle(tx.objectStore('parca').getAll(aralik(kimlik)));
  }

  return {
    kimlik,
    kilitAl() {
      return kilitAl(`olcum-kayit:${kimlik}`, kilitler);
    },
    async durumOku() {
      const r = await oku();
      return r && r.durum ? JSON.parse(JSON.stringify(r.durum)) : null;
    },
    async durumYaz(d) {
      const kopya = JSON.parse(JSON.stringify(d));
      await guncelle(['akis'], (rec) => { rec.durum = kopya; });
    },
    async veriBoyu() {
      const r = await oku();
      return r ? r.bayt : 0;
    },
    async veriOku(bas = 0) {
      const tx = islem(vt, ['akis', 'parca'], false);
      const rec = await istekBekle(tx.objectStore('akis').get(kimlik));
      const p = await parcalar(tx);
      return parcalardanOku(p, bas, rec ? rec.bayt : 0);
    },
    async veriEkle(b) {
      const veri = b instanceof Uint8Array ? b : new Uint8Array(b);
      await guncelle(['akis', 'parca'], (rec, tx) => {
        const ps = tx.objectStore('parca');
        for (const p of parcala(veri)) {
          ps.put({ kimlik, no: rec.sonrakiNo, bas: rec.bayt, veri: p });
          rec.sonrakiNo += 1;
          rec.bayt += p.length;
        }
      });
    },
    async veriKirp(n) {
      if (!Number.isInteger(n) || n < 0) throw new RangeError('kirpma boyu gecersiz');
      await guncelle(['akis', 'parca'], async (rec, tx) => {
        const ps = tx.objectStore('parca');
        const p = await parcalar(tx);
        const plan = kirpPlani(p, n, rec.bayt);
        for (const no of plan.sil) ps.delete([kimlik, no]);
        if (plan.kes) {
          const eski = p.find((x) => x.no === plan.kes.no);
          ps.put({ ...eski, veri: eski.veri.slice(0, plan.kes.boy) });
        }
        if (plan.uzat) {
          let bas = rec.bayt;
          for (const z of parcala(new Uint8Array(plan.uzat))) {
            ps.put({ kimlik, no: rec.sonrakiNo, bas, veri: z });
            rec.sonrakiNo += 1;
            bas += z.length;
          }
        }
        rec.bayt = n;
      });
    },
    async kalOku() {
      const r = await oku();
      return r && r.kal ? r.kal.slice() : null;
    },
    async kalYaz(b) {
      const kopya = Uint8Array.from(b);
      await guncelle(['akis'], (rec) => { rec.kal = kopya; });
    },
    async kalArsivle(b) {
      const tx = islem(vt, ['arsiv'], true);
      const s = tx.objectStore('arsiv');
      const varolan = new Set((await istekBekle(s.getAllKeys(aralikAd(kimlik)))).map((k) => k[1]));
      const ad = arsivAdi(simdi(), (x) => varolan.has(x));
      s.put({ kimlik, ad, veri: Uint8Array.from(b), zaman: Date.now() });
      await bitince(tx);
      return ad;
    },
  };
}
