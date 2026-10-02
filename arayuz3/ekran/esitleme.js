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
 *  yaniti; bu yalniz ON kosul. neden: 'taban' | 'usb' | 'demo' | null. */
export function esitlemeUygunlugu({ kartTaban = '', tasiyici = 'akis' } = {}) {
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

/* ── denetci ────────────────────────────────────────────────────────── */

export class EsitlemeDenetcisi {
  /** kartAdres: app.js kartAdres (taban oneki); zamanAsimiMs: istek basina. */
  constructor({ kartAdres, zamanAsimiMs = 10000, bekle = uyu } = {}) {
    if (typeof kartAdres !== 'function') throw new TypeError('kartAdres islevi gerekli');
    this.kartAdres = kartAdres;
    this.zamanAsimiMs = zamanAsimiMs;
    this._bekle = bekle;
    this._onbellek = new Map();          // kimlik -> {bayt, kayitlar, oturumlar, sonSira, kal}
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
        y = await fetch(this.kartAdres('/kayit/liste'), { cache: 'no-store', ...this._sinyal() });
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
    const getir = () => fetch(this.kartAdres(yol + (q ? '?' + q : '')), { cache: 'no-store', ...this._sinyal() });
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

  /** Bu tarayicidaki akislarin ozetleri (veri yok). */
  async akislar() {
    return akislar(await vtAc());
  }

  /** Akisi coz (onbellekli; akisin boyu degisince yeniden). Gecerli ON EK
   *  (akisOnek): yarim kuyruk (cokme) okumayi bozmaz, sonraki esitleme kirpar. */
  async akisVerisi(kimlik) {
    const vt = await vtAc();
    const depo = idbDepo(vt, kimlik);
    const boy = await depo.veriBoyu();
    const eski = this._onbellek.get(kimlik);
    if (eski && eski.bayt === boy) return eski;
    const veri = await depo.veriOku(0);
    const [kayitlar, gecerli] = akisOnek(veri);
    const oturumlar = oturumlariKur(kayitlar);
    const c = { kimlik, bayt: veri.length, gecerli, kayitlar, oturumlar,
      sonSira: oturumSonSiralari(kayitlar), kal: kalJsonCoz(await depo.kalOku()),
      durum: await depo.durumOku() };
    this._onbellek.set(kimlik, c);
    return c;
  }

  /** Akisin ham baytlari (dogrulama / ham disa aktarma icin). */
  async akisBaytlari(kimlik) {
    return idbDepo(await vtAc(), kimlik).veriOku(0);
  }

  async akisSil(kimlik) {
    this._onbellek.delete(kimlik);
    await akisSil(await vtAc(), kimlik);
  }
}
