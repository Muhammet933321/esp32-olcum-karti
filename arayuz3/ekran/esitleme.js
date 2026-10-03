/* ═══════════════════════════════════════════════════════════════════════
   3C — PANELIN ESITLEME DENETCISI                   (ekran/esitleme.js)

   Kart asil kaydi tutar (§5); panel `ortak/src/esitle.js` Esitleyici'siyle
   eksik kayitlari `/kayit/veri`den ceker ve `ekran/depo_idb.js`
   (IndexedDB) deposuna AYNEN ekler. Kararlar (tasarim/2026-10-02-alt-
   proje-3-panel.md):
     C1  Esitleme YALNIZ panel kartin KENDI adresinden acildiginda: kart
         CORS'u `X-Kayit-*` basliklarini baska kokene acmiyor, `/kayit/veri`
         seri yolda yok. `kartTaban` doluysa, tasiyici USB ya da demo ise
         ya da ayni kokendeki `/kayit/liste` kart degilse (kopru /
         gelistirme sunucusu 404) esitleme YOK, sebep yazilir; liste yine
         bu tarayicidaki kopyayi gosterir.
     C2  Kart kimligi basina bir akis; kimlik degisirse YENI akis.
     C3  VARSAYILAN: karta "aldim" onayi GONDERILMEZ. "Bu tarayici
         arsivdir" kart (kimlik) basina localStorage'da; aciksa onay
         panelin komut yolundan `Go<sira>` (app.js gonder).
   Her uzak istek app.js `kartAdres()`ten geciyor (B7 kurali); C1 geregi
   taban bos oldugu icin ayni koken.
   4D (PC10) — PANEL PC KOPRUSUNDE: kopru kokeninde (`*.localhost`,
   dongu adresi) `/durum` `pc_arsiv: true` derse denetcinin KAYNAGI
   'pc': akislar / akisVerisi / akisBaytlari / kalBaytlari koprunun disk
   arsivinden (ekran/depo_pc.js, salt okuma — tek yazar Python), esitleme
   ve kopya silme YOK (C1 sebebi 'pc'). Kart kokeninde (olcum.local, IP)
   bu karar ICIN hicbir istek gitmez; kaynak 'tarayici' (IndexedDB) —
   kartin sundugu panelin davranisi degismedi.
   ⚠ Bu dosyada Vue YOK. Agir veri (kayitlar, oturumlar) bilesene markRaw
     ile gider — reaktif vekil yuz binlerce noktada paneli kilitlerdi.
   ═══════════════════════════════════════════════════════════════════════ */

import { Esitleyici, EsitlemeHatasi } from '/ortak/esitle.js';
import { HttpHatasi, CalismaHatasi } from '/ortak/imza.js';
import { akisOnek, oturumlariKur, KayitHatasi, T_NOT } from '/ortak/kayit.js';
import { vtAc, idbDepo, akisHazirla, akislar, akisSil } from './depo_idb.js';

export const ARSIV_ONEK = 'olcum.arsiv.';
export const DIL_ANAHTAR = 'olcum.dil';
/** Esitlemede tek yanitin tavani (kart KAYIT_VERI_AZAMI = 8192 ile ayni). */
export const PARCA_BAYT = 8192;

/* ── SAF karar fonksiyonlari (B7 node'da sinar) ─────────────────────── */

/** C1: bu panel esitleyebilir mi? Kanit (ayni kokende kart mi) `/kayit/liste`
 *  yaniti; bu yalniz ON kosul. neden: 'pc' | 'taban' | 'usb' | 'demo' | null.
 *  4D: `pc` (kayitlar PC arsivinden) -> esitleme YOK: kartin kayitlarini kopru esitler. */
export function esitlemeUygunlugu({ kartTaban = '', tasiyici = 'akis', pc = false } = {}) {
  if (pc === true) return { uygun: false, neden: 'pc' };
  if (String(kartTaban || '').trim()) return { uygun: false, neden: 'taban' };
  if (tasiyici === 'seri') return { uygun: false, neden: 'usb' };
  if (tasiyici === 'demo') return { uygun: false, neden: 'demo' };
  return { uygun: true, neden: null };
}

/** `/kayit/liste` yanitini siniflandir. 200 + kart bicimi -> tamam; 401 imza;
 *  404 kart degil (kopru / gelistirme sunucusu); 403 Host; 503 mesgul. */
export function listeYanitiCoz(durum, metin) {
  if (durum === 200) {
    let l = null;
    try { l = JSON.parse(metin); } catch (e) { l = null; }
    const kart = l && typeof l === 'object' && Array.isArray(l.oturumlar)
      && Number.isInteger(l.kimlik) && l.kimlik >= 0;
    return kart ? { durum: 'tamam', liste: l } : { durum: 'bozuk', mesaj: String(metin).slice(0, 120) };
  }
  if (durum === 401) return { durum: 'imza', mesaj: metin };
  if (durum === 404) return { durum: 'yok', mesaj: metin };
  if (durum === 403) return { durum: 'host', mesaj: metin };
  if (durum === 503) return { durum: 'mesgul', mesaj: metin };
  return { durum: 'hata', mesaj: `HTTP ${durum}${metin ? ': ' + String(metin).slice(0, 120) : ''}` };
}

/** Esitleme hatasini kullaniciya soylenecek sinifa cevir. */
export function hataSinifla(h) {
  if (h instanceof HttpHatasi) return { durum: h.durum === 401 ? 'imza' : 'hata', mesaj: `HTTP ${h.durum}` };
  if (h instanceof EsitlemeHatasi) return { durum: 'akis', mesaj: h.message };
  if (h instanceof KayitHatasi) return { durum: 'bozuk', mesaj: h.message };
  if (h instanceof CalismaHatasi) return { durum: 'kilit', mesaj: h.message };
  return { durum: 'ag', mesaj: (h && h.message) || String(h) };
}

/* Ag hatasinda yeniden deneme. Gercek kartta (2026-10-02) tarayici esitlemesi bir /kayit/veri
   isteginde ERR_CONNECTION_TIMED_OUT aldi ve DURDU (44 oturumdan 1'i geldi); ayni kart ham
   ardisik cekimde 1.27 MB'i hatasiz verdi. ESP32'nin soket havuzu tarayicinin paralel
   baglantilarinda (SSE + moduller + esitleme) ara sira reddediyor. Esitleme depodaki durumdan
   KALDIGI YERDEN surer — yeniden denemek ne veri kaybettirir ne cift kayit yazar. */
export const AG_DENEME = 4;          // ag hatasinda toplam deneme
export const AG_BEKLE_MS = 1500;     // n. yeniden denemeden once n x bu kadar

const uyu = (ms) => new Promise((r) => setTimeout(r, ms));

/** islev() -> {durum, ...}. durum 'ag' ise artan beklemeyle en fazla `deneme` kez dener;
 *  baska her sonuc HEMEN doner. Donus sonucun kendisi + `deneme` (kac kez denendi). */
export async function agYenidenDene(islev, { deneme = AG_DENEME, bekleMs = AG_BEKLE_MS, bekle = uyu } = {}) {
  let r = null;
  for (let n = 0; n < deneme; n++) {
    if (n) await bekle(bekleMs * n);
    r = await islev(n);
    if (!r || r.durum !== 'ag') return { ...r, deneme: n + 1 };
  }
  return { ...r, deneme };
}

/** C3: onay islevi. Arsiv secili DEGILSE ya da panel karta bagli degilse null
 *  (Esitleyici onaysiz calisir; kart bu tarayicinin kopyasini "arsiv" saymaz). */
export function onayIslevi({ arsiv, bagli, gonder }) {
  if (!arsiv || !bagli || typeof gonder !== 'function') return null;
  return async (sira) => { await gonder('Go' + sira); };
}

function depoOku(depo, anahtar) {
  try { return depo ? depo.getItem(anahtar) : null; } catch (e) { return null; }
}

function depoYaz(depo, anahtar, deger) {
  try {
    if (!depo) return false;
    if (deger === null) depo.removeItem(anahtar); else depo.setItem(anahtar, deger);
    return true;
  } catch (e) { return false; }
}

/** "Bu tarayici arsivdir" secimi, kart (akis kimligi) basina. */
export function arsivOku(kimlik, depo = globalThis.localStorage) {
  return depoOku(depo, ARSIV_ONEK + kimlik) === 'true';
}

export function arsivYaz(kimlik, acik, depo = globalThis.localStorage) {
  return depoYaz(depo, ARSIV_ONEK + kimlik, acik ? 'true' : null);
}

/** Dil tercihi (3H secici gelene dek elle: localStorage['olcum.dil'] = '"en"'). */
export function dilOku(depo = globalThis.localStorage) {
  let v = null;
  try { v = JSON.parse(depoOku(depo, DIL_ANAHTAR)); } catch (e) { v = null; }
  return v === 'en' ? 'en' : 'tr';
}

/** Akistaki her oturumun en buyuk kayit sirasi (NOT kayitlari hedef oturumuna sayilir). */
export function oturumSonSiralari(kayitlar) {
  const m = new Map();
  for (const k of kayitlar) {
    let ot = k.oturum;
    if (!ot && k.tur === T_NOT && k.yuk.length >= 4) {
      ot = new DataView(k.yuk.buffer, k.yuk.byteOffset, 4).getUint32(0, true);
    }
    if (!ot) continue;
    if (!(m.get(ot) >= k.sira)) m.set(ot, k.sira);
  }
  return m;
}

/** kalibrasyon.json baytlari -> nesne (okunamazsa null). */
export function kalJsonCoz(b) {
  if (!b) return null;
  try { return JSON.parse(new TextDecoder('utf-8').decode(b)); } catch (e) { return null; }
}

/** 4D: sayfa kopru kokeninden mi acilmis olabilir (dongu adi / adresi)? Yalniz o zaman `/durum`
 *  sorulur. Kart (olcum.local, IP) ASLA — kartin sundugu panel bu karar icin istek atmaz. */
export function kokenSinama(konum) {
  if (!konum || (konum.protocol !== 'http:' && konum.protocol !== 'https:')) return false;
  const h = String(konum.hostname || '').toLowerCase();
  return h === 'localhost' || h.endsWith('.localhost') || /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)
    || h === '[::1]' || h === '::1';
}

/** 4D: kaynak karari — `/durum` yaniti kopru mu ve BU istemci PC arsivini okuyabilir mi. */
export function kaynakCoz(durum, metin) {
  if (durum !== 200) return 'tarayici';
  let d = null;
  try { d = JSON.parse(metin); } catch (e) { d = null; }
  return d && typeof d === 'object' && d.pc_arsiv === true && 'kart' in d ? 'pc' : 'tarayici';
}

/* ── denetci ────────────────────────────────────────────────────────── */

export class EsitlemeDenetcisi {
  /** kartAdres: app.js kartAdres (taban oneki); istek: app.js kartIstek (3H-2 ES4 — TEK istek
   *  katmani: eslesmisse imzali; verilmezse bugunku yol fetch(kartAdres)); zamanAsimiMs: istek basina.
   *  4D: kaynak ('pc' | 'tarayici'; verilmezse kendisi bulur), konum (location) ve pcYukle (depo_pc
   *  modulu) testte verilir. */
  constructor({ kartAdres, istek = null, zamanAsimiMs = 10000, bekle = uyu, kaynak = null,
    konum = globalThis.location, pcYukle = () => import('./depo_pc.js') } = {}) {
    if (typeof kartAdres !== 'function') throw new TypeError('kartAdres islevi gerekli');
    this.kartAdres = kartAdres;
    this._katman = typeof istek === 'function' ? istek : null;
    this.zamanAsimiMs = zamanAsimiMs;
    this._bekle = bekle;
    this._onbellek = new Map();          // kimlik -> {bayt, kayitlar, oturumlar, sonSira, kal}
    this._kaynakSoz = kaynak === 'pc' || kaynak === 'tarayici' ? Promise.resolve(kaynak) : null;
    this._konum = konum;
    this._pcYukle = pcYukle;
    this._pc = new Map();                // 4D: akis kimligi -> /arsiv/liste ogesi
  }

  /* ── 4D (PC10): kaynak — PC arsivi mi, bu tarayici mi ── */

  /** 'pc' (kopru, bu istemci PC arsivini okuyabilir) | 'tarayici'. Kart kokeninde ISTEK YOK. */
  kaynak() {
    if (!this._kaynakSoz) {
      const soz = this._kaynakBul().then(([k, ezber]) => {
        if (!ezber && this._kaynakSoz === soz) this._kaynakSoz = null;   // ag hatasi ezberlenmez
        return k;
      });
      this._kaynakSoz = soz;
    }
    return this._kaynakSoz;
  }

  /** [kaynak, ezberlenir mi]. Kart kokeninde istek YOK. */
  async _kaynakBul() {
    if (!kokenSinama(this._konum)) return ['tarayici', true];
    try {
      const y = await this._kopruGetir('/durum');
      return [kaynakCoz(y.status, await y.text().catch(() => '')), true];
    } catch (h) {
      return ['tarayici', false];
    }
  }

  /** Kopru uclari (/durum, /arsiv/*, /esitleme/durum) imza katmanina GIRMEZ (EU8'): duz fetch. */
  _kopruGetir(yol) {
    return fetch(this.kartAdres(yol), { cache: 'no-store', credentials: 'omit', ...this._sinyal() });
  }

  async _pcListe() {
    const m = await this._pcYukle();
    const l = await m.pcAkislar((y) => this._kopruGetir(y));
    /* ayni akis kimligi iki kartta (olasilik ~2^-32): kopru sirasinda ilki (EN YENI) kalir */
    const tekil = new Map();
    for (const a of l) if (!tekil.has(a.akis)) tekil.set(a.akis, a);
    this._pc = tekil;
    return tekil;
  }

  /** Akisin deposu: kopruda PC arsivi (salt okuma), degilse bu tarayicinin IndexedDB'si. */
  async _depo(kimlik) {
    if (await this.kaynak() !== 'pc') return idbDepo(await vtAc(), kimlik);
    if (!this._pc.has(kimlik)) await this._pcListe();
    const a = this._pc.get(kimlik);
    if (!a) throw new Error(`PC arsivinde akis yok: ${kimlik}`);
    return (await this._pcYukle()).pcDepo((y) => this._kopruGetir(y), a);
  }

  /** 4D: koprunun arka plan esitlemesinin durumu (`/esitleme/durum`); kopru degilse null. */
  async esitlemeDurumu() {
    if (await this.kaynak() !== 'pc') return null;
    try {
      const y = await this._kopruGetir('/esitleme/durum');
      if (!y.ok) return { hata: `HTTP ${y.status}` };
      const d = await y.json();
      return d && typeof d === 'object' ? d : { hata: 'JSON' };
    } catch (h) {
      return { hata: (h && h.message) || String(h) };
    }
  }

  /** Tek ag kapisi: istek katmani (varsa) ya da bugunku yol. */
  _getir(yol, secenekler) {
    return this._katman ? this._katman(yol, secenekler) : fetch(this.kartAdres(yol), secenekler);
  }

  _sinyal() {
    return typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
      ? { signal: AbortSignal.timeout(this.zamanAsimiMs) } : {};
  }

  /** Kartin oturum dizini (ayni koken). Ag hatasi -> {durum: 'ag'}. */
  async kartListesi() {
    return agYenidenDene(async () => {
      let y;
      try {
        y = await this._getir('/kayit/liste', { cache: 'no-store', ...this._sinyal() });
      } catch (h) {
        return { durum: 'ag', mesaj: (h && h.message) || String(h) };
      }
      const metin = await y.text().catch(() => '');
      return listeYanitiCoz(y.status, metin);
    }, { bekle: this._bekle });
  }

  /** Esitleyici'nin `istek`i: /kayit/veri ve /kal/liste, kartAdres uzerinden.
   *  /kal/liste ag hatasinda burada yeniden denenir: Esitleyici o hatayi kalibrasyon_hata'ya
   *  cevirip "tamam" dondugunden ust katmanin agYenidenDene'si onu hic gormez (gercek kartta
   *  2026-10-02, TimeoutError). /kayit/veri'yi ust katman kaldigi yerden yeniden kuruyor. */
  async _istek(yol, argumanlar) {
    const q = argumanlar.map(([a, d]) => `${a}=${d}`).join('&');
    const getir = () => this._getir(yol + (q ? '?' + q : ''), { cache: 'no-store', ...this._sinyal() });
    if (yol !== '/kal/liste') return getir();
    for (let n = 1; ; n++) {
      try {
        return await getir();
      } catch (h) {
        if (n >= AG_DENEME) throw h;
        await this._bekle(n * AG_BEKLE_MS);
      }
    }
  }

  /**
   * `kimlik` akisini esitle. onay: onayIslevi() sonucu (null = onaysiz).
   * ilerleme(bayt): her depoya eklemeden sonra (toplam yeni bayt).
   * Donus: {durum: 'tamam', sonuc} | {durum, mesaj} (hataSinifla).
   */
  async esitle({ kimlik, onay = null, ilerleme = null } = {}) {
    /* 4D: PC arsivi SALT OKUMA — tek yazar kopru; panel hicbir sey yazmaz, karta onay yollamaz */
    if (await this.kaynak() === 'pc') return { durum: 'pc', mesaj: 'PC arsivini kopru esitler' };
    let vt;
    try {
      vt = await vtAc();
      await akisHazirla(vt, kimlik);
    } catch (h) {
      return { durum: 'depo', mesaj: (h && h.message) || String(h) };
    }
    const depo = idbDepo(vt, kimlik);
    let yeni = 0;
    let yeniKayit = 0;     // BUTUN denemeler boyunca (Esitleyici yalniz kendi denemesininkini sayar)
    const izleyen = { ...depo, async veriEkle(b) {
      await depo.veriEkle(b);
      yeni += b.length;
      yeniKayit += akisOnek(b)[0].length;     // eklenen parca butun, CRC'si dogrulanmis kayitlar
      if (ilerleme) ilerleme(yeni);
    } };
    try {
      /* Her deneme YENI Esitleyici: depodaki durumdan (son sira) kaldigi yerden surer. */
      return await agYenidenDene(async () => {
        const e = new Esitleyici({ tabanUrl: '', depo: izleyen, onay, bayt: PARCA_BAYT,
          istek: (taban, yol, argumanlar) => this._istek(yol, argumanlar) });
        try {
          const sonuc = await e.esitle();
          /* Ag hatasindan sonra yeniden denendiyse Esitleyici'nin sayisi yalniz SON denemeninki:
             gercek kartta 1846 kayit alindigi halde "150 yeni kayit" yaziyordu. */
          return { durum: 'tamam', sonuc: { ...sonuc, yeni_kayit: yeniKayit }, bayt: yeni };
        } catch (h) {
          return { ...hataSinifla(h), bayt: yeni };
        }
      }, { bekle: this._bekle });
    } finally {
      this._onbellek.delete(kimlik);
    }
  }

  /** Bu tarayicidaki akislarin ozetleri (veri yok). 4D: kopruda PC arsivinin akislari (pc: true). */
  async akislar() {
    if (await this.kaynak() === 'pc') {
      return [...(await this._pcListe()).values()].map((a) => ({ kimlik: a.akis, kart: a.kart, bayt: a.bayt,
        durum: a.durum, olusma: a.degisim * 1000, guncelleme: a.degisim * 1000, kalVar: a.kal, pc: true,
        oturum: a.oturum }));
    }
    return akislar(await vtAc());
  }

  /** Akisi coz (onbellekli; akisin boyu degisince yeniden). Gecerli ON EK
   *  (akisOnek): yarim kuyruk (cokme) okumayi bozmaz, sonraki esitleme kirpar. */
  async akisVerisi(kimlik) {
    const depo = await this._depo(kimlik);
    const boy = await depo.veriBoyu();
    const eski = this._onbellek.get(kimlik);
    if (eski && eski.boy === boy) return eski;
    const veri = await depo.veriOku(0);
    const [kayitlar, gecerli] = akisOnek(veri);
    const oturumlar = oturumlariKur(kayitlar);
    const c = { kimlik, bayt: veri.length, boy, gecerli, kayitlar, oturumlar,
      sonSira: oturumSonSiralari(kayitlar), kal: kalJsonCoz(await depo.kalOku()),
      durum: await depo.durumOku(), kart: depo.kart || null };
    this._onbellek.set(kimlik, c);
    return c;
  }

  /** Akisin ham baytlari (dogrulama / ham disa aktarma icin). */
  async akisBaytlari(kimlik) {
    return (await this._depo(kimlik)).veriOku(0);
  }

  /** Akisin kalibrasyon.json kopyasinin HAM baytlari (yoksa null). */
  async kalBaytlari(kimlik) {
    return (await this._depo(kimlik)).kalOku();
  }

  async akisSil(kimlik) {
    if (await this.kaynak() === 'pc') throw new CalismaHatasi('PC arsivi salt okuma: kopyayi kopru tutar');
    this._onbellek.delete(kimlik);
    await akisSil(await vtAc(), kimlik);
  }
}
