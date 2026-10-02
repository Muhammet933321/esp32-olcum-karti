/* ═══════════════════════════════════════════════════════════════════════
   3H-2 — TARAYICIDAN ESLESTIRME                      (ekran/eslesme.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H-2 kararlari"
   (ES1-ES10) ve "3H-2 uygulama kararlari". Kart tarafi protokolu
   tasarim/2026-10-01-1d-eslestirme.md (K5 eslestirme, K6 anahtar, K8 liste,
   K9 imza, K10 acilis + kayan pencere, K11 istisnalar, K12 /saat).
   Kriptografi ortak/src/imza.js'te (kopru/imza.py ile bayt bayt ayni);
   burada YENIDEN YAZILMAZ.

   Bu modul ACILISTA INMEZ (app.js dinamik `import()`): yalniz bu tarayicida
   bir cihaz kaydi varsa (app.js cihazKaydiVar) ya da Ayarlar > Eslestirme
   acilinca. Uc parcasi:
     * CIHAZ DEPOSU (ES2): IndexedDB `olcum-cihaz` / depo `cihaz`, anahtar kart
       kimligi. K ACIK saklanir (kart http:// -> guvenli baglam yok). Kayit
       yazimi TEKDUZE (kayitBirlestir): iki sekme sayaci geri goturemez.
     * ISTEMCI (ES4/ES5/ES7/ES8): app.js'in TEK istek katmani (kartIstek) bu
       sinifa sorar. Bu kartin kimligiyle kayit varsa istek `imza.ac` ile
       imzali, credentials:'omit' (tarayicinin onbellekteki Basic-Auth'u
       GITMEZ); yoksa cagiranin bugunku yolu (duz). Ayni acilisla 401 ->
       YENI sayacla tek yeniden deneme (ES5); yine 401 -> "kart tanimiyor":
       kayit isaretlenir, kullaniciya bildirilir, imzasiz yola dusulur.
     * AKIS (ES6): /akis fetch ile okunur (ImzaliAkis, EventSource yuzeyi).
       EventSource kendiliginden yeniden baglanirken AYNI (tek kullanimlik)
       imzali URL'yi yollar ve onbellekteki Basic-Auth'u tasir; burada her
       baglanti YENI imzali URL, artan bekleme.
   `p0` (pil DURDUR) BU MODULE HIC UGRAMAZ: app.js onu dogrudan yollar (K11).
   ⚠ Parola HICBIR yere yazilmaz (alan gonderimde bosaltilir; depo, URL,
     govde, baslik — B7 + T3H2 tarar). `N?` gonderilmez.
   ═══════════════════════════════════════════════════════════════════════ */

import {
  ac, akisUrl, adGecerli, esles, HttpHatasi, PAROLA_EN_AZ,
} from '/ortak/imza.js';
import { utf8Kodla } from '/ortak/kripto.js';
import { ceviri } from '/ortak/sozluk.js';

/* ── sabitler ───────────────────────────────────────────────────────── */

/** ES2: cihaz anahtarlarinin veritabani (kayit kopyalarinin `olcum-kayit`inden AYRI). */
export const CIHAZ_VT = 'olcum-cihaz';
export const CIHAZ_VT_SURUM = 1;
export const CIHAZ_DEPO = 'cihaz';
/** ES6: yeniden baglanma beklemesi (ms): 1, 2, 4, 8, 16, 30, 30 ... */
export const AKIS_BEKLE_ILK_MS = 1000;
export const AKIS_BEKLE_AZAMI_MS = 30000;
/** EU24: /eslestir/bilgi zaman asimi (ms) — kart TCP'yi kabul edip susarsa baglanti / esitleme asili kalmasin. */
export const BILGI_SURE_MS = 5000;

/* ── metinler (sozluk anahtarlari; ES10) ────────────────────────────── */
export const ES_METIN = Object.freeze({
  baslik: 'es.baslik', aciklama: 'es.aciklama', bKimlik: 'es.b_kimlik', bZorunlu: 'es.b_zorunlu', bMisafir: 'es.b_misafir',
  bSaat: 'es.b_saat', acik: 'es.acik', kapali: 'es.kapali', denetleniyor: 'es.d_denetleniyor',
  ad: 'es.ad', adIpucu: 'es.ad_ipucu', parola: 'es.parola', parolaIpucu: 'es.parola_ipucu', eslestir: 'es.eslestir',
  eslesiyor: 'es.eslesiyor', unut: 'es.unut', unutEminim: 'es.unut_eminim', unutUyari: 'es.unut_uyari',
  listeBaslik: 'es.liste_baslik', listeTablo: 'es.liste_tablo', lN: 'es.l_n', lAd: 'es.l_ad', lEklenme: 'es.l_eklenme',
  lSon: 'es.l_son', lIslem: 'es.l_islem', buTarayici: 'es.bu_tarayici', kaldir: 'es.kaldir', kaldirEminim: 'es.kaldir_eminim',
  kaldirUyari: 'es.kaldir_uyari', saatBaslik: 'es.saat_baslik', saatAyarla: 'es.saat_ayarla', saatIpucu: 'es.saat_ipucu',
  saatNtpVar: 'es.saat_ntp_var', saatEslesmeli: 'es.saat_eslesmeli', guvBaslik: 'es.guv_baslik', guvAciklama: 'es.guv_aciklama',
  anahtarBaslik: 'es.anahtar_baslik', anahtarAciklama: 'es.anahtar_aciklama', bildirimBaslik: 'es.bildirim_baslik',
  bildirimAciklama: 'es.bildirim_aciklama', yenile: 'ay.yenile', vazgec: 'kl.vazgec',
  yabanciBaslik: 'es.yabanci_baslik', yabanciAciklama: 'es.yabanci_aciklama', yabanciSil: 'es.yabanci_sil', silEminim: 'es.sil_eminim',
});
/** /eslestir/bilgi `saat`: 0 yok, 1 NTP, 2 cihazdan (guvenlik_esp.h guv_saat_kaynak). */
export const SAAT_METIN = Object.freeze(['es.saat_yok', 'es.saat_ntp', 'es.saat_cihaz']);
const DURUM_METIN = Object.freeze({ yok: 'es.d_yok', hazir: 'es.d_hazir', tanimiyor: 'es.d_tanimiyor', ag: 'es.d_ag',
  kartYok: 'es.d_kart_yok' });
const UYGUN_METIN = Object.freeze({ usb: 'es.uygun_usb', demo: 'es.uygun_demo', taban: 'es.uygun_taban' });
const UNUT_METIN = Object.freeze({ silindi: 'es.unutuldu', ulasilamadi: 'es.unutuldu_ulasilamadi',
  tanimiyordu: 'es.unutuldu_tanimiyor', hata: 'es.unutuldu_hata', yok: 'es.unutuldu_yok' });
const SONUC_METIN = Object.freeze({ eslesti: 'es.eslesti', kaldirildi: 'es.kaldirildi', kaldirHata: 'es.kaldir_hata',
  listeHata: 'es.liste_hata', saatTamam: 'es.saat_tamam', saatHata: 'es.saat_hata' });

export function metinler(harita, dil) {
  const m = {};
  for (const [a, k] of Object.entries(harita)) m[a] = ceviri(k, dil);
  return m;
}

/* ── SAF fonksiyonlar (B7 node'da sinar) ────────────────────────────── */

/** ES6: n. ardisik basarisizliktan sonra bekleme (ms). */
export function akisBekleme(n) {
  const k = Math.max(1, Math.floor(n)) - 1;
  return Math.min(AKIS_BEKLE_AZAMI_MS, AKIS_BEKLE_ILK_MS * 2 ** Math.min(k, 16));
}

/** `/yol?a=1&b=2` -> {yol, argumanlar: [[a, d], ...]} (gelis sirasi, URL-cozulmus: kartin kanonik kurali K9). */
export function yolAyir(yol) {
  const s = String(yol);
  const i = s.indexOf('?');
  if (i < 0) return { yol: s, argumanlar: [] };
  return { yol: s.slice(0, i), argumanlar: [...new URLSearchParams(s.slice(i + 1)).entries()] };
}

/** ES1: eslestirme yalniz panel kartin KENDI adresinden (akis kipi, bos taban; 3C C1 ile ayni kural). */
export function eslesmeUygunlugu({ kartTaban = '', tasiyici = 'akis' } = {}) {
  if (tasiyici === 'seri') return { uygun: false, neden: 'usb' };
  if (tasiyici === 'demo') return { uygun: false, neden: 'demo' };
  if (String(kartTaban || '').trim()) return { uygun: false, neden: 'taban' };
  return { uygun: true, neden: null };
}

/** ES7: varsayilan cihaz adi — tarayici/isletim sistemi (listede ayirt edilsin). ASCII, <= 24 bayt. */
export function varsayilanAd(ua) {
  const s = String(ua || '');
  const t = /Edg\//.test(s) ? 'Edge' : /Firefox\//.test(s) ? 'Firefox' : /(Chrome|CriOS)\//.test(s) ? 'Chrome'
    : /Safari\//.test(s) ? 'Safari' : '';
  const i = /iPhone|iPad|iPod/.test(s) ? 'iOS' : /Android/.test(s) ? 'Android' : /Windows/.test(s) ? 'Windows'
    : /Mac OS X|Macintosh/.test(s) ? 'macOS' : /Linux|X11/.test(s) ? 'Linux' : '';
  return t ? (i ? `${t}/${i}` : t) : 'Tarayici';
}

/**
 * ES5/ES2: depodaki kayit (eski) + yazilmak istenen (yeni) -> yazilacak kayit; null = YAZMA.
 * Ayni eslestirme (n + eklenme ayni): sayac max (iki sekme geri goturemez), "tanimiyor" yapiskan,
 * acilis yeni yazandan. Farkli eslestirme: yalniz daha YENI (eklenme) olan yazilir.
 * EU22: kayit YOKSA yalniz eslestirme (`olustur`) yazar — sayac / acilis / "tanimiyor" yazmalari
 * silinmis kaydi (K ile) geri getiremez ("unut" ile yarisan imzali istek).
 */
export function kayitBirlestir(eski, yeni, { olustur = false } = {}) {
  if (!yeni) return null;
  if (!eski) return olustur ? { ...yeni } : null;
  if (eski.n !== yeni.n || (eski.eklenme || 0) !== (yeni.eklenme || 0)) {
    return (yeni.eklenme || 0) >= (eski.eklenme || 0) ? { ...yeni } : null;
  }
  return { ...yeni, sayac: Math.max(eski.sayac || 0, yeni.sayac || 0), tanimiyor: !!(eski.tanimiyor || yeni.tanimiyor),
    tanimiyorMesaj: yeni.tanimiyorMesaj || eski.tanimiyorMesaj || '' };
}

/**
 * ES5: sayaci TEK islemde ayir (cihazDeposu.ayir bunu readwrite islemde cagirir — IndexedDB ayni
 * kapsamli yazma islemlerini sekmeler arasinda SIRAYA koyar: iki sekme ayni sayaci alamaz).
 * s = max(depo + 1, bellek + 1, simdi_ms). Kayit yoksa / baska eslestirmeyse null.
 */
export function sayacAyir(kayit, c, simdiMs) {
  if (!kayit || kayit.n !== c.n || (kayit.eklenme || 0) !== (c.eklenme || 0)) return null;
  const s = Math.max((kayit.sayac || 0) + 1, (c.sayac || 0) + 1, Math.floor(simdiMs) || 0);
  return { kayit: { ...kayit, sayac: s }, s, tanimiyor: !!kayit.tanimiyor };
}

const KART_RET = /^\/eslestir\/(baslat|kanit): (\d+) ([\s\S]*)$/;

/**
 * ES3: eslestirme hatasi -> {anahtar, d} (sozluk). Kartin metni `kart`ta, 429'da Retry-After
 * saniyesi `sn`de (istemci son yanittan yakalar).
 */
export function retSebebi(h, { retry = null } = {}) {
  const ad = h && h.name;
  const mesaj = String((h && h.message) || h || '');
  if (ad === 'TypeError' || ad === 'AbortError' || ad === 'TimeoutError') return { anahtar: 'es.ret_ag', d: { mesaj } };
  if (ad === 'DegerHatasi') {
    if (/parola en az/.test(mesaj)) return { anahtar: 'es.ret_kisa', d: { en_az: PAROLA_EN_AZ } };
    if (/^ad /.test(mesaj)) return { anahtar: 'es.ret_ad', d: {} };
    return { anahtar: 'es.ret_bilgi', d: { mesaj } };
  }
  if (ad === 'CalismaHatasi') {
    const m = KART_RET.exec(mesaj);
    if (m) {
      const kod = m[2];
      const kart = m[3].trim();
      if (kod === '403') return { anahtar: m[1] === 'kanit' ? 'es.ret_parola' : 'es.ret_kart_parola', d: { kart } };
      if (kod === '429') return { anahtar: 'es.ret_bekle', d: { kart, sn: retry === null || retry === undefined ? '?' : String(retry) } };
      if (kod === '409') return { anahtar: 'es.ret_dolu', d: { kart } };
      if (kod === '410') return { anahtar: 'es.ret_sure', d: { kart } };
      return { anahtar: 'es.ret_http', d: { kod, kart } };
    }
    if (/kart kaniti YANLIS/.test(mesaj)) return { anahtar: 'es.ret_sahte', d: {} };
  }
  if (ad === 'HttpHatasi') return { anahtar: 'es.ret_http', d: { kod: String(h.durum), kart: '' } };
  return { anahtar: 'es.ret_diger', d: { mesaj } };
}

/**
 * ES6: text/event-stream cozucu (EventSource'un ayristirma kurali): parca parca gelen metin,
 * CRLF / LF, `:` yorum, cok satirli `data`, `event`, `id`, `retry`. Verisiz blok olay degil.
 */
export class SseCozucu {
  constructor() {
    this._t = '';
    this._cr = false;             // EU18: onceki parca '\r' ile bitti — bu parcanin basindaki '\n' ayni satir sonu
    this._olay = '';
    this._veri = [];
    this.id = '';
    this.retry = null;
  }

  ekle(metin) {
    const cikti = [];
    metin = String(metin);
    if (this._cr && metin) {
      if (metin[0] === '\n') metin = metin.slice(1);
      this._cr = false;
    }
    this._t += metin;
    let n;
    while ((n = this._t.search(/\r\n|\r|\n/)) >= 0) {
      const sat = this._t.slice(0, n);
      /* tamponun SONUNDAKI '\r': CRLF'nin '\n'i sonraki parcada olabilir (WHATWG: '\r'den sonraki ilk '\n' yutulur) */
      if (this._t[n] === '\r' && n === this._t.length - 1) this._cr = true;
      this._t = this._t.slice(n + (this._t.startsWith('\r\n', n) ? 2 : 1));
      if (sat === '') {
        if (this._veri.length) cikti.push({ olay: this._olay || 'message', veri: this._veri.join('\n'), id: this.id });
        this._olay = '';
        this._veri = [];
        continue;
      }
      if (sat[0] === ':') continue;
      const i = sat.indexOf(':');
      const alan = i < 0 ? sat : sat.slice(0, i);
      let deger = i < 0 ? '' : sat.slice(i + 1);
      if (deger[0] === ' ') deger = deger.slice(1);
      if (alan === 'data') this._veri.push(deger);
      else if (alan === 'event') this._olay = deger;
      else if (alan === 'id') this.id = deger;
      else if (alan === 'retry' && /^\d+$/.test(deger)) this.retry = Number(deger);
    }
    return cikti;
  }
}

/* ── ES2: cihaz deposu (IndexedDB) ──────────────────────────────────── */

/* Veritabani depo OLMADAN varsa (baska bir arac surumsuz acip yarattiysa) bir ust surumle depo kurulur. */
function vtAc(idb, surum = null) {
  return new Promise((coz, red) => {
    /* surumsuz: yoksa CIHAZ_VT_SURUM (1) ile yaratilir; varsa (onarilmis, ust surum) oldugu gibi acilir */
    const r = surum === null ? idb.open(CIHAZ_VT) : idb.open(CIHAZ_VT, surum);
    r.onupgradeneeded = () => {
      const vt = r.result;
      if (!vt.objectStoreNames.contains(CIHAZ_DEPO)) vt.createObjectStore(CIHAZ_DEPO, { keyPath: 'kimlik' });
    };
    r.onsuccess = () => {
      const vt = r.result;
      if (!vt.objectStoreNames.contains(CIHAZ_DEPO)) {
        const v = vt.version;
        vt.close();
        vtAc(idb, v + 1).then(coz, red);
        return;
      }
      vt.onversionchange = () => vt.close();
      coz(vt);
    };
    r.onerror = () => red(r.error || new Error('IndexedDB acilamadi'));
    r.onblocked = () => red(new Error('IndexedDB engellendi'));
  });
}

/** {oku, yaz, ayir, sil, hepsi} — her yazma `durability: 'strict'` ve TEKDUZE (kayitBirlestir, tek islemde oku+yaz).
    yaz(c) yalniz VAR OLAN kaydi gunceller; yeni kayit yalniz yaz(c, {olustur: true}) (eslestirme, EU22). */
export function cihazDeposu(idb = globalThis.indexedDB) {
  let vtSoz = null;
  const vt = () => {
    if (!idb) return Promise.reject(new Error('IndexedDB yok'));
    if (!vtSoz) vtSoz = vtAc(idb).catch((h) => { vtSoz = null; throw h; });
    return vtSoz;
  };
  const islem = async (yaz, f) => {
    const v = await vt();
    return new Promise((coz, red) => {
      const t = yaz ? v.transaction(CIHAZ_DEPO, 'readwrite', { durability: 'strict' }) : v.transaction(CIHAZ_DEPO, 'readonly');
      let sonuc;
      f(t.objectStore(CIHAZ_DEPO), (x) => { sonuc = x; });
      t.oncomplete = () => coz(sonuc);
      t.onerror = () => red(t.error || new Error('IndexedDB islem hatasi'));
      t.onabort = () => red(t.error || new Error('IndexedDB islemi iptal edildi'));
    });
  };
  return {
    oku: (kimlik) => islem(false, (d, ver) => { const r = d.get(kimlik); r.onsuccess = () => ver(r.result || null); }),
    yaz: (c, secenek = {}) => islem(true, (d, ver) => {
      const r = d.get(c.kimlik);
      r.onsuccess = () => {
        const y = kayitBirlestir(r.result || null, c, secenek);
        if (y) d.put(y);
        ver(y);
      };
    }),
    ayir: (c, simdiMs) => islem(true, (d, ver) => {
      const r = d.get(c.kimlik);
      r.onsuccess = () => {
        const a = sayacAyir(r.result || null, c, simdiMs);
        if (a) d.put(a.kayit);
        ver(a ? { s: a.s, tanimiyor: a.tanimiyor } : null);
      };
    }),
    sil: (kimlik) => islem(true, (d) => { d.delete(kimlik); }),
    hepsi: () => islem(false, (d, ver) => { const r = d.getAll(); r.onsuccess = () => ver(r.result || []); }),
  };
}

/* ── ES4/ES5/ES7/ES8: istemci ───────────────────────────────────────── */

const ozet = (c) => (c ? { n: c.n, ad: c.ad, kimlik: c.kimlik } : null);

export class EslesmeIstemcisi {
  /**
   * kartAdres: app.js kartAdres (taban oneki); bildir({durum, ...}): 'tanimiyor' | 'eslesti' |
   * 'unutuldu' (app serit uyarisi ve akis); depo: cihazDeposu arayuzu (testte bellek).
   */
  constructor({ kartAdres, bildir = () => {}, depo = null, simdiMs = () => Date.now(), bilgiSureMs = BILGI_SURE_MS } = {}) {
    if (typeof kartAdres !== 'function') throw new TypeError('kartAdres islevi gerekli');
    this.kartAdres = kartAdres;
    this.bilgiSureMs = bilgiSureMs;
    this.bildir = bildir;
    this.depo = depo || cihazDeposu();
    this.simdiMs = simdiMs;
    this.durum = 'bilinmiyor';       // 'bilinmiyor' | 'yok' | 'hazir' | 'tanimiyor'
    this.bilgi = null;               // /eslestir/bilgi (kimlik, acilis, zorunlu, misafir, saat ...)
    this.bilgiKod = null;            // /eslestir/bilgi HTTP kodu (200 degilse: kart degil / eski firmware)
    this.cihaz = null;
    this.sonRetry = null;            // son yanitin Retry-After'i (429)
    this._taban = null;
    this._cozSoz = null;
  }

  /** Tek ag kapisi: HER istek kartAdres'ten (B7 kurali). */
  _getir(yol, secenekler) {
    return fetch(this.kartAdres(yol), secenekler);
  }

  /** imza.js ortami: imzali istekler tarayicinin Basic-Auth onbellegini TASIMAZ (credentials:'omit').
      `olustur` yalniz eslestirmede: kaydi o yaratir (EU22). */
  _ortam(signal = null, { olustur = false } = {}) {
    return {
      fetch: async (url, o) => {
        const y = await this._getir(url, { ...o, cache: 'no-store', credentials: 'omit', ...(signal ? { signal } : {}) });
        this.sonRetry = y.headers.get('Retry-After');
        return y;
      },
      kaydet: (c) => this._kaydet(c, { olustur }),
      /* sayac _sayacAyir'da AYRILDI (c.sayac = ayrilan - 1): imza.js sonrakiSayac = max(c.sayac + 1, 0)
         tam olarak ayrilani kullanir. Eslestirmede (sayac 0) etkisiz. */
      simdiMs: () => 0,
    };
  }

  /** ES5: sayac (ve acilis) istekten ONCE depoya; depo TEKDUZE birlestirir. Donus: yazilan kayit ya da null
      (EU22: kayit artik yok — baska sekme "unut" dedi; geri YARATILMAZ). */
  async _kaydet(c, { olustur = false } = {}) {
    if (!c.eklenme) c.eklenme = Date.now();
    return this.depo.yaz(c, { olustur });
  }

  /** Kayit bu sekmenin elinden gitti (silindi / yeniden eslestirildi): istemci onu birakir, sonraki istek yeniden cozer. */
  _birak(c) {
    if (this.cihaz === c || this.cihaz === null) {
      this.cihaz = null;
      this.durum = 'bilinmiyor';
    }
  }

  /** ES5: bu istegin sayacini depoda ATOMIK ayir (istekten ONCE yazilir). Kayit gittiyse false. */
  async _sayacAyir(c) {
    const a = await this.depo.ayir(c, this.simdiMs());
    if (!a) { this._birak(c); return false; }
    c.sayac = a.s - 1;
    if (a.tanimiyor) {                    // baska sekme "kart tanimiyor" buldu: bu sekme de imzasiz yola
      c.tanimiyor = true;
      if (this.cihaz === c) this.durum = 'tanimiyor';
    }
    return true;
  }

  /**
   * Kartin kimligini ve bu tarayicinin o karttaki kaydini coz. Karta ulasilamazsa ATAR (sonuc
   * ezberlenmez); 200 disi yanit (kopru, eski firmware) -> 'yok'.
   */
  async coz(zorla = false) {
    const taban = this.kartAdres('');
    if (!zorla && this._taban === taban && (this.durum === 'yok' || this.durum === 'hazir' || this.durum === 'tanimiyor')) {
      return this.durum;
    }
    if (!this._cozSoz) this._cozSoz = this._coz(taban).finally(() => { this._cozSoz = null; });
    return this._cozSoz;
  }

  async _coz(taban) {
    const sure = typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function' && this.bilgiSureMs > 0
      ? { signal: AbortSignal.timeout(this.bilgiSureMs) } : {};
    const y = await this._getir('/eslestir/bilgi', { cache: 'no-store', credentials: 'omit', ...sure });
    this.bilgiKod = y.status;
    let b = null;
    if (y.status === 200) b = await y.json().catch(() => null);
    if (!b || !/^[0-9a-f]{16}$/.test(b.kimlik) || !/^[0-9a-f]{32}$/.test(b.acilis)) {
      this.bilgi = null;
      this.cihaz = null;
      this.durum = 'yok';
      if (y.status < 500) this._taban = taban;          // 5xx (mesgul) ezberlenmez
      return this.durum;
    }
    this.bilgi = b;
    const c = await this.depo.oku(b.kimlik);
    this._taban = taban;
    if (!c) {
      this.cihaz = null;
      this.durum = 'yok';
      return this.durum;
    }
    if (c.acilis !== b.acilis) {
      c.acilis = b.acilis;
      await this._kaydet(c);
    }
    this.cihaz = c;
    this.durum = c.tanimiyor ? 'tanimiyor' : 'hazir';
    if (c.tanimiyor) this.bildir({ durum: 'tanimiyor', ...ozet(c), mesaj: c.tanimiyorMesaj || '' });
    return this.durum;
  }

  async _tanimiyor(c, metin, sessiz) {
    c.tanimiyor = true;
    c.tanimiyorMesaj = String(metin || '').slice(0, 160);
    const y = await this._kaydet(c).catch(() => undefined);
    if (y === null) { this._birak(c); return; }    // EU22: kayit bu arada silindi — geri yazilmadi, bildirim yok
    if (this.cihaz === c) this.durum = 'tanimiyor';
    if (!sessiz) this.bildir({ durum: 'tanimiyor', ...ozet(c), mesaj: c.tanimiyorMesaj });
  }

  /**
   * ES4/ES5: imzali istek. Donus: Response (2xx ya da 401 disi hata — cagiran isler) ya da null
   * (kart bu cihazi TANIMIYOR; cagiran imzasiz yola duser). Ag hatasi atar.
   */
  async _imzali(yol, sec = {}, { sessiz = false } = {}) {
    const c = this.cihaz;
    if (!c || c.tanimiyor) return null;
    const { yol: y, argumanlar } = yolAyir(yol);
    const yontem = String(sec.method || 'GET').toUpperCase();
    const govde = sec.body === undefined || sec.body === null ? new Uint8Array(0) : sec.body;
    let son = null;
    for (let deneme = 0; deneme < 2; deneme++) {
      if (!(await this._sayacAyir(c))) return null;    // kayit baska sekmede silinmis / yenilenmis (_birak): yeniden coz
      if (c.tanimiyor) return null;
      try {
        return await ac(c, '', yontem, y, argumanlar, govde, this._ortam(sec.signal || null));
      } catch (h) {
        if (!(h instanceof HttpHatasi)) throw h;
        if (h.durum !== 401) return h.yanit;
        son = h.yanit;
        const a = son.headers.get('X-Acilis');
        if (a && a !== c.acilis) {          // arada yeniden basladi: acilis guncelle, kalan hakla dene
          c.acilis = a;
          await this._kaydet(c);
        }
      }
    }
    await this._tanimiyor(c, await son.text().catch(() => ''), sessiz);
    return null;
  }

  /** ES4: app.js kartIstek'in kapisi. `duz()` = bugunku (imzasiz) yol. */
  async istek(yol, sec = {}, duz) {
    const d = await this.coz();
    if (d !== 'hazir') return duz();
    const y = await this._imzali(yol, sec);
    return y === null ? duz() : y;
  }

  /** ES6: eslesmis ya da cozulemeyen kart -> ImzaliAkis; bu kartta kayit yok -> null (EventSource). */
  async akisAc() {
    let d;
    try { d = await this.coz(); } catch (h) { d = 'ag'; }
    return d === 'yok' ? null : new ImzaliAkis(this);
  }

  /** ES3: parolali eslestirme (imza.js esles). Parola SAKLANMAZ; kisa parola aga cikmaz. */
  async esles(ad, parola) {
    this.sonRetry = null;
    const c = await esles('', ad, parola, this._ortam(null, { olustur: true }));
    this.cihaz = c;
    this.durum = 'hazir';
    this._taban = this.kartAdres('');
    if (this.bilgi === null || this.bilgi.kimlik !== c.kimlik) await this.coz(true).catch(() => {});
    this.bildir({ durum: 'eslesti', ...ozet(c) });
    return c;
  }

  /** ES7: kartin cihaz listesi (imzali). Donus [{n, ad, eklenme, son}]; tanimiyorsa null. */
  async cihazListe() {
    const y = await this._imzali('/cihaz/liste', {});
    if (y === null) return null;
    if (!y.ok) throw new Error('HTTP ' + y.status);
    const j = await y.json();
    return Array.isArray(j && j.cihazlar) ? j.cihazlar : [];
  }

  /** ES7: baska bir cihazi kartta sil (imzali POST /cihaz/sil?n=). */
  async cihazSil(n) {
    const y = await this._imzali('/cihaz/sil?n=' + Number(n), { method: 'POST' });
    if (y === null) return { tamam: false, mesaj: 'imza' };
    return { tamam: y.ok, mesaj: y.ok ? '' : 'HTTP ' + y.status };
  }

  /**
   * ES7: "bu tarayiciyi unut" — ONCE kartta kendini sil, SONRA yerel kayit. Kart ulasilamazsa da
   * yerel kayit silinir; sonuc kartin durumunu soyler: silindi | ulasilamadi | tanimiyordu | hata | yok.
   * EU21: `yok` = bu sekmenin bildigi kayit artik depoda yok (baska sekmede silindi ya da YENIDEN
   * eslestirildi): hicbir sey silinmez — yeni eslestirmenin kaydi bayat ekrandan silinmesin.
   */
  async unut() {
    const c = this.cihaz;
    if (!c) return { kart: 'yok', n: null, kod: null };
    let kart = 'silindi';
    let kod = null;
    if (c.tanimiyor) {
      kart = 'tanimiyordu';
    } else {
      try {
        const y = await this._imzali('/cihaz/sil?n=' + c.n, { method: 'POST' }, { sessiz: true });
        if (y === null) kart = c.tanimiyor ? 'tanimiyordu' : 'yok';
        else if (!y.ok && y.status !== 404) { kart = 'hata'; kod = y.status; }
      } catch (h) {
        kart = 'ulasilamadi';
      }
    }
    if (kart === 'yok') {
      this._birak(c);
      return { kart, n: c.n, kod };
    }
    await this.depo.sil(c.kimlik);
    this.cihaz = null;
    this.durum = 'yok';
    this.bildir({ durum: 'unutuldu', ...ozet(c) });
    return { kart, n: c.n, kod };
  }

  /** ES8: kartin saatini bu cihazdan (imzali POST /saat?unix=). Yalniz cagrilinca. */
  async saatAyarla() {
    const unix = Math.floor(this.simdiMs() / 1000);
    const y = await this._imzali('/saat?unix=' + unix, { method: 'POST' });
    if (y === null) return { tamam: false, mesaj: 'imza', unix };
    const metin = y.ok ? '' : await y.text().catch(() => '');
    if (y.ok) await this.coz(true).catch(() => {});
    return { tamam: y.ok, mesaj: y.ok ? '' : `HTTP ${y.status} ${metin}`.trim(), unix };
  }

  /** EU26: bu tarayicida BASKA kart kimligine ait kayitlar (eski kart, NVS'i sifirlanan kart) — K disari verilmez. */
  async yabancilar() {
    const k = this.bilgi ? this.bilgi.kimlik : null;
    const l = await this.depo.hepsi();
    return l.filter((r) => r && r.kimlik !== k)
      .map((r) => ({ kimlik: r.kimlik, n: r.n, ad: r.ad, eklenme: r.eklenme || 0 }));
  }

  /** EU26: baska kartin kaydini YALNIZ bu tarayicidan sil. Bu kartin kaydi bu yoldan silinmez ("unut": once kart). */
  async yerelSil(kimlik) {
    if (!kimlik || (this.bilgi && kimlik === this.bilgi.kimlik)) return false;
    await this.depo.sil(kimlik);
    return true;
  }
}

/* ── ES6: imzali akis (EventSource yuzeyi) ──────────────────────────── */

function olay(tur, veri, id) {
  if (typeof MessageEvent === 'function') return new MessageEvent(tur, { data: veri, lastEventId: id || '' });
  const e = new Event(tur);
  e.data = veri;
  return e;
}

/**
 * /akis'i fetch ile okur; app.js TasiyiciAkis'in kullandigi yuzey: onmessage, onerror,
 * addEventListener('kimlik' | 'kopru' | 'error' ...), close(), readyState.
 * Her baglanti YENI imzali URL (tek kullanimlik sayac); koptugunda artan bekleme (akisBekleme).
 * 401 + yeni acilis -> hemen yeni acilisla; ayni acilisla iki 401 -> "kart tanimiyor" + imzasiz /akis.
 */
export class ImzaliAkis extends EventTarget {
  constructor(istemci, { bekle = (ms) => new Promise((r) => setTimeout(r, ms)) } = {}) {
    super();
    this.ist = istemci;
    this._bekle = bekle;
    this.onmessage = null;
    this.onerror = null;
    this.onopen = null;
    this.readyState = 0;           // 0 baglaniyor, 1 acik, 2 kapali (EventSource ile ayni)
    this.url = '';
    this.basarisiz = 0;
    this._kapali = false;
    this._iptal = null;
    this._ret = 0;                 // EU17: AYNI acilisla ard arda 401 (yeni acilisli 401 SAYILMAZ)
    this._acilisYeni = 0;          // ard arda yeni acilisli 401 (sinirli: kart her seferinde yeni acilis derse)
    this._dongu();
  }

  close() {
    this._kapali = true;
    this.readyState = 2;
    if (this._iptal) this._iptal.abort();
  }

  _yay(tur, veri, id) {
    const e = olay(tur, veri, id);
    this.dispatchEvent(e);
    /* EU19: EventSource gibi — isleyicinin istisnasi raporlanir, akisi KOPARMAZ */
    if (tur === 'message' && typeof this.onmessage === 'function') {
      try { this.onmessage(e); } catch (h) { if (typeof globalThis.reportError === 'function') globalThis.reportError(h); }
    }
  }

  _hata() {
    const e = new Event('error');
    this.dispatchEvent(e);
    if (typeof this.onerror === 'function') this.onerror(e);
  }

  async _dongu() {
    let hemen = 0;
    while (!this._kapali) {
      let y = null;
      try { y = await this._ac(); } catch (h) { y = null; }
      if (y === null) this._ret = 0;                     // EU17: ag hatasi araya girdiyse 401'ler ard arda degil
      if (this._kapali) return;
      if (y === 'yeniden' && ++hemen <= 4) continue;     // yeni acilis / ES5: beklemeden (sinirli)
      hemen = 0;
      if (y === 'yeniden') y = null;
      if (y && y.ok && y.body) {
        try { await this._oku(y); } catch (h) { /* kopma: asagida bekle + yeni URL */ }
      }
      if (this._kapali) return;
      this.readyState = 0;
      this._hata();
      this.basarisiz++;
      await this._bekle(akisBekleme(this.basarisiz));
    }
  }

  /** Bir baglanti: Response | 'yeniden' (hemen tekrar) | null (bekle). */
  async _ac() {
    let d;
    try { d = await this.ist.coz(); } catch (h) { return null; }
    if (this._kapali) return null;
    if (this._iptal) this._iptal.abort();            // EU19: onceki baglanti kesin kapansin
    this._iptal = new AbortController();
    const sec = { cache: 'no-store', headers: { Accept: 'text/event-stream' }, signal: this._iptal.signal };
    if (d !== 'hazir') {
      /* eslesme yok / kart tanimiyor: bugunku EventSource yolu (ayni kimlik bilgisi kipi) */
      this.url = '/akis';
      return this.ist._getir('/akis', { ...sec, credentials: 'same-origin' });
    }
    const c = this.ist.cihaz;
    if (!(await this.ist._sayacAyir(c))) {
      this.ist.durum = 'bilinmiyor';
      this.ist.cihaz = null;
      return 'yeniden';
    }
    if (c.tanimiyor) return 'yeniden';
    this.url = await akisUrl(c, '', this.ist._ortam());
    const y = await this.ist._getir(this.url, { ...sec, credentials: 'omit' });
    if (y.status !== 401) {
      this._ret = 0;
      this._acilisYeni = 0;
      return y;
    }
    const a = y.headers.get('X-Acilis');
    /* EU17: kart yeniden basladi (yeni acilis) -> acilis guncellenir, bu 401 ayni-acilis sayacina GIRMEZ;
       boylece ardindan gelen tek ayni-acilisli 401 de ES5'in yeni sayacli denemesini alir */
    if (a && a !== c.acilis && this._acilisYeni < 3) {
      this._acilisYeni++;
      this._ret = 0;
      c.acilis = a;
      await this.ist._kaydet(c);
      return 'yeniden';
    }
    this._acilisYeni = 0;
    if (++this._ret < 2) return 'yeniden';         // ES5: yeni sayacla tek yeniden deneme
    this._ret = 0;
    await this.ist._tanimiyor(c, await y.text().catch(() => ''), false);
    return 'yeniden';
  }

  async _oku(y) {
    const okuyucu = y.body.getReader();
    const iptal = this._iptal;
    const cozucu = new TextDecoder('utf-8');
    const sse = new SseCozucu();
    let ilk = true;
    try {
      for (;;) {
        const { value, done } = await okuyucu.read();
        if (done || this._kapali) break;
        if (ilk) {
          ilk = false;
          this.readyState = 1;
          this.dispatchEvent(new Event('open'));
          if (typeof this.onopen === 'function') this.onopen();
        }
        for (const o of sse.ekle(cozucu.decode(value, { stream: true }))) {
          /* EU20: bekleme sayacini GERCEK olay sifirlar (ilk bayt degil): kart 'dolu' / 'kopru' yazip kapatirsa
             bekleme artmaya devam eder */
          if (o.olay === 'message' || o.olay === 'kimlik') this.basarisiz = 0;
          this._yay(o.olay, o.veri, o.id);
        }
      }
    } finally {
      /* EU19: kopma / hata / bitis — eski baglanti bekleme BASLAMADAN kapanir (kartin akis yuvasini tutmasin) */
      try { okuyucu.cancel().catch(() => {}); } catch (h) { /* zaten kapali */ }
      if (iptal) iptal.abort();
    }
  }
}

/* ── Vue bileseni (Ayarlar > Eslestirme) ────────────────────────────── */

const SABLON = `
<div class="es-mod">
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.baslik }}</h2>
    <p class="ipucu">{{ m.aciklama }}</p>
    <div class="ay-ust">
      <p class="ay-ozet" data-es-durum tabindex="-1" aria-live="polite">{{ durumYazi }}</p>
      <button type="button" @click="yenile" :disabled="calisiyor" :aria-busy="calisiyor ? 'true' : 'false'">{{ m.yenile }}</button>
    </div>
    <dl class="ay-bilgi" v-if="bilgi" data-es-bilgi>
      <dt>{{ m.bKimlik }}</dt><dd><code>{{ bilgi.kimlik }}</code></dd>
      <dt>{{ m.bZorunlu }}</dt><dd data-es-zorunlu>{{ bilgi.zorunlu ? m.acik : m.kapali }}</dd>
      <dt>{{ m.bMisafir }}</dt><dd data-es-misafir>{{ bilgi.misafir ? m.acik : m.kapali }}</dd>
      <dt>{{ m.bSaat }}</dt><dd data-es-saat>{{ saatYazi }}</dd>
    </dl>
    <p v-if="uygunluk.neden" class="ipucu" data-es-uygun>{{ uygunYazi }}</p>
    <form v-else-if="!cihaz && bilgi" class="es-form" data-es-form @submit.prevent="eslestir">
      <div class="alan">
        <label for="es-ad">{{ m.ad }}</label>
        <input id="es-ad" type="text" name="cihaz-adi" v-model="ad" autocomplete="off" autocapitalize="off" spellcheck="false"
               maxlength="24" :aria-invalid="retAlan === 'ad' ? 'true' : null"
               :aria-describedby="retAlan === 'ad' ? 'es-ad-ipucu es-ret' : 'es-ad-ipucu'" required>
        <span class="ipucu" id="es-ad-ipucu">{{ m.adIpucu }}</span>
      </div>
      <div class="alan">
        <label for="es-parola">{{ m.parola }}</label>
        <input id="es-parola" ref="parola" type="password" name="parola" autocomplete="current-password"
               :aria-invalid="retAlan === 'parola' ? 'true' : null"
               :aria-describedby="retAlan === 'parola' ? 'es-parola-ipucu es-ret' : 'es-parola-ipucu'" required>
        <span class="ipucu" id="es-parola-ipucu">{{ m.parolaIpucu }}</span>
      </div>
      <button type="submit" class="birincil" data-es-eslestir :disabled="calisiyor" :aria-busy="calisiyor ? 'true' : 'false'">{{ calisiyor ? m.eslesiyor : m.eslestir }}</button>
    </form>
    <div class="ay-duyuru" aria-live="polite"><p v-if="sonuc" class="ipucu" data-es-sonuc>{{ sonuc }}</p></div>
    <p v-if="ret" id="es-ret" class="hata" role="alert" data-es-ret>{{ ret }}</p>
    <div v-if="cihaz" class="dugme-grup">
      <template v-if="unutOnay">
        <button type="button" class="tehlike" data-es-unut-eminim @click="unut">{{ m.unutEminim }}</button>
        <button type="button" data-es-unut-vazgec @click="unutVazgec">{{ m.vazgec }}</button>
      </template>
      <button v-else type="button" data-es-unut @click="unutBasla" :disabled="calisiyor">{{ m.unut }}</button>
    </div>
    <p v-if="unutOnay" class="uyari" role="alert">{{ m.unutUyari }}</p>
  </section>

  <section class="kart" v-if="hazir" data-ay-bolum="eslestirme">
    <h2 id="es-liste-baslik" tabindex="-1">{{ m.listeBaslik }}</h2>
    <p v-if="listeHata" class="hata" role="alert" data-es-liste-hata>{{ listeHata }}</p>
    <div v-if="liste.length" class="ay-tablo-sarmal">
      <table class="ay-tablo" data-es-liste>
        <caption class="gorunmez">{{ m.listeTablo }}</caption>
        <thead><tr>
          <th scope="col">{{ m.lN }}</th><th scope="col">{{ m.lAd }}</th><th scope="col">{{ m.lEklenme }}</th>
          <th scope="col">{{ m.lSon }}</th><th scope="col">{{ m.lIslem }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="c in liste" :key="c.n" :data-es-cihaz="c.n" :class="{ 'ay-etkin': c.n === kendiN }">
            <th scope="row">{{ c.n }}</th>
            <td class="ay-metin">{{ c.ad }} <span v-if="c.n === kendiN" class="kl-rozet kl-nerede-ikisi">{{ c.n === kendiN ? m.buTarayici : '' }}</span></td>
            <td>{{ zaman(c.eklenme) }}</td><td>{{ zaman(c.son) }}</td>
            <td class="ay-islem">
              <button v-if="c.n === kendiN" type="button" :data-es-kendi="c.n" @click="unutBasla">{{ m.unut }}</button>
              <template v-else-if="kaldirOnay === c.n">
                <button type="button" class="tehlike" :data-es-kaldir-eminim="c.n" @click="kaldir(c.n)">{{ m.kaldirEminim }}</button>
                <button type="button" @click="kaldirVazgec(c.n)">{{ m.vazgec }}</button>
              </template>
              <button v-else type="button" :data-es-kaldir="c.n" @click="kaldirBasla(c.n)" :disabled="calisiyor">{{ m.kaldir }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="kaldirOnay !== null" class="uyari" role="alert">{{ m.kaldirUyari }}</p>
  </section>

  <section class="kart" v-if="yabanci.length" data-ay-bolum="eslestirme" data-es-yabanci>
    <h2 id="es-yabanci-baslik" tabindex="-1">{{ m.yabanciBaslik }}</h2>
    <p class="ipucu">{{ m.yabanciAciklama }}</p>
    <ul class="es-yabanci">
      <li v-for="y in yabanci" :key="y.kimlik" :data-es-yabanci-kayit="y.kimlik">
        <span class="ay-metin"><code>{{ y.kimlik }}</code> · {{ y.ad }} ({{ m.lN }} {{ y.n }})</span>
        <span class="dugme-grup">
          <template v-if="yabanciOnay === y.kimlik">
            <button type="button" class="tehlike" :data-es-yabanci-eminim="y.kimlik" @click="yabanciSil(y.kimlik)">{{ m.silEminim }}</button>
            <button type="button" @click="yabanciVazgec(y.kimlik)">{{ m.vazgec }}</button>
          </template>
          <button v-else type="button" :data-es-yabanci-sil="y.kimlik" @click="yabanciBasla(y.kimlik)">{{ m.yabanciSil }}</button>
        </span>
      </li>
    </ul>
  </section>

  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.saatBaslik }}</h2>
    <p class="ipucu">{{ m.saatIpucu }}</p>
    <button v-if="hazir && bilgi && bilgi.saat !== 1" type="button" data-es-saat-ayarla @click="saatAyarla" :disabled="calisiyor">{{ m.saatAyarla }}</button>
    <p v-else-if="bilgi && bilgi.saat === 1" class="ipucu" data-es-ntp>{{ m.saatNtpVar }}</p>
    <p v-else class="ipucu">{{ m.saatEslesmeli }}</p>
  </section>

  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.guvBaslik }}</h2>
    <p class="ipucu" data-es-guv>{{ m.guvAciklama }}</p>
  </section>
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.anahtarBaslik }}</h2>
    <p class="ipucu" data-es-anahtar>{{ m.anahtarAciklama }}</p>
  </section>
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.bildirimBaslik }}</h2>
    <p class="ipucu" data-es-bildirim>{{ m.bildirimAciklama }}</p>
  </section>
</div>`;

function zamanYaz(s) {
  if (!(s > 0)) return '—';
  const d = new Date(s * 1000);
  const i = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}`;
}

export const EslestirmeEkrani = {
  name: 'EslestirmeEkrani',
  props: {
    istemciAl: { type: Function, required: true },     // app.js eslesmeIstemcisi (TEK istemci)
    kartTaban: { type: String, default: '' },
    tasiyici: { type: String, default: 'akis' },
    bagli: { type: Boolean, default: false },
    dilSecim: { type: String, default: 'tr' },
    etkin: { type: Boolean, default: true },
  },
  template: SABLON,
  data() {
    return {
      ad: varsayilanAd(globalThis.navigator ? globalThis.navigator.userAgent : ''),
      durum: 'bilinmiyor', bilgi: null, bilgiKod: null, cihaz: null, agMesaj: '',
      calisiyor: false, ret: '', retAlan: null, sonuc: '', liste: [], listeHata: '', kaldirOnay: null, unutOnay: false,
      yabanci: [], yabanciOnay: null,
    };
  },
  computed: {
    dil() { return this.dilSecim === 'en' ? 'en' : 'tr'; },
    m() { return metinler(ES_METIN, this.dil); },
    uygunluk() { return eslesmeUygunlugu({ kartTaban: this.kartTaban, tasiyici: this.tasiyici }); },
    uygunYazi() { return this.uygunluk.neden ? ceviri(UYGUN_METIN[this.uygunluk.neden], this.dil) : ''; },
    hazir() { return this.durum === 'hazir' && !!this.cihaz; },
    kendiN() { return this.cihaz ? this.cihaz.n : null; },
    saatYazi() { return this.bilgi ? ceviri(SAAT_METIN[this.bilgi.saat] || SAAT_METIN[0], this.dil) : '—'; },
    durumYazi() {
      const c = this.cihaz || {};
      if (this.durum === 'bilinmiyor') return this.m.denetleniyor;
      if (this.durum === 'ag') return ceviri(DURUM_METIN.ag, this.dil, { mesaj: this.agMesaj || '—' });
      if (this.durum === 'yok' && !this.bilgi) return ceviri(DURUM_METIN.kartYok, this.dil, { kod: this.bilgiKod === null ? '?' : this.bilgiKod });
      if (this.durum === 'tanimiyor') {
        return ceviri(DURUM_METIN.tanimiyor, this.dil, { n: c.n, ad: c.ad, mesaj: c.tanimiyorMesaj || '—' });
      }
      return ceviri(DURUM_METIN[this.durum] || DURUM_METIN.yok, this.dil, { n: c.n, ad: c.ad });
    },
  },
  watch: {
    etkin(v) { if (v) this.yenile(); else { this.kaldirOnay = null; this.unutOnay = false; this.yabanciOnay = null; } },
  },
  mounted() {
    if (this.etkin) this.yenile();
  },
  methods: {
    zaman(s) { return zamanYaz(s); },
    _odakla(secici) {
      this.$nextTick(() => {
        if (typeof document === 'undefined') return;
        const e = document.querySelector(secici);
        if (e && typeof e.focus === 'function') e.focus();
      });
    },
    _al(ist) {
      this.durum = ist.durum;
      this.bilgi = ist.bilgi ? { ...ist.bilgi } : null;
      this.bilgiKod = ist.bilgiKod;
      this.cihaz = ist.cihaz ? { n: ist.cihaz.n, ad: ist.cihaz.ad, tanimiyorMesaj: ist.cihaz.tanimiyorMesaj || '' } : null;
    },
    /** Kartin bilgisi + bu tarayicinin kaydi (+ eslesmisse cihaz listesi). */
    async yenile() {
      this.kaldirOnay = null;
      this.unutOnay = false;
      this.yabanciOnay = null;
      if (this.uygunluk.neden) { this.durum = 'yok'; return; }
      let ist;
      try {
        ist = await this.istemciAl();
        await ist.coz(true);
        this._al(ist);
      } catch (h) {
        this.durum = 'ag';
        this.agMesaj = (h && h.message) || String(h);
        return;
      }
      await this.yabanciYukle(ist);
      if (this.hazir) await this.listeYukle(ist);
    },
    /** EU26: bu tarayicida baska kart kimligine ait kayitlar (yalniz yerel silinebilir). */
    async yabanciYukle(ist) {
      try {
        const i = ist || await this.istemciAl();
        this.yabanci = typeof i.yabancilar === 'function' ? await i.yabancilar() : [];
      } catch (h) {
        this.yabanci = [];
      }
    },
    yabanciBasla(k) {
      this.yabanciOnay = k;
      this._odakla('[data-es-yabanci-eminim="' + k + '"]');
    },
    yabanciVazgec(k) {
      this.yabanciOnay = null;
      this._odakla('[data-es-yabanci-sil="' + k + '"]');
    },
    /** EU26: ikinci asama — YALNIZ silahli satirin kaydi, YALNIZ bu tarayicidan. */
    async yabanciSil(k) {
      if (this.yabanciOnay !== k) return;
      this.yabanciOnay = null;
      try {
        const ist = await this.istemciAl();
        await ist.yerelSil(k);
        await this.yabanciYukle(ist);
      } catch (h) {
        this.sonuc = ceviri('es.ret_diger', this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this._odakla(this.yabanci.length ? '#es-yabanci-baslik' : '[data-es-durum]');
    },
    async listeYukle(ist) {
      this.listeHata = '';
      try {
        const l = await (ist || await this.istemciAl()).cihazListe();
        if (l === null) { this._al(ist || await this.istemciAl()); this.liste = []; return; }
        this.liste = l;
      } catch (h) {
        this.liste = [];
        this.listeHata = ceviri(SONUC_METIN.listeHata, this.dil, { mesaj: (h && h.message) || String(h) });
      }
    },
    /** ES3: parola alandan okunur ve esles cagrilmadan ONCE bosaltilir; Vue durumuna girmez. */
    async eslestir() {
      const alan = this.$refs.parola;
      const parola = alan ? alan.value : '';
      if (alan) alan.value = '';
      this.ret = '';
      this.retAlan = null;
      this.sonuc = '';
      if (!adGecerli(this.ad)) {
        this.ret = ceviri('es.ret_ad', this.dil);
        this.retAlan = 'ad';
        this._odakla('#es-ad');
        return;
      }
      if (utf8Kodla(parola).length < PAROLA_EN_AZ) {
        this.ret = ceviri('es.ret_kisa', this.dil, { en_az: PAROLA_EN_AZ });
        this.retAlan = 'parola';
        this._odakla('#es-parola');
        return;
      }
      this.calisiyor = true;
      let ist = null;
      try {
        ist = await this.istemciAl();
        const c = await ist.esles(this.ad, parola);
        this._al(ist);
        this.sonuc = ceviri(SONUC_METIN.eslesti, this.dil, { n: c.n });
        await this.listeYukle(ist);
        this._odakla('[data-es-durum]');              // EU27: form kalkti — odak durum satirina
      } catch (h) {
        const r = retSebebi(h, { retry: ist ? ist.sonRetry : null });
        this.ret = ceviri(r.anahtar, this.dil, r.d);
        this.retAlan = r.anahtar === 'es.ret_ad' ? 'ad' : 'parola';
        this._odakla(this.retAlan === 'ad' ? '#es-ad' : '#es-parola');
      }
      this.calisiyor = false;
    },
    unutBasla() {
      this.unutOnay = true;
      this._odakla('[data-es-unut-eminim]');
    },
    unutVazgec() {
      this.unutOnay = false;
      this._odakla('[data-es-unut]');
    },
    async unut() {
      if (!this.unutOnay) return;
      this.unutOnay = false;
      this.calisiyor = true;
      this.ret = '';
      try {
        const ist = await this.istemciAl();
        const r = await ist.unut();
        this._al(ist);
        this.liste = [];
        this.sonuc = ceviri(UNUT_METIN[r.kart] || UNUT_METIN.hata, this.dil, { n: r.n, kod: r.kod === null || r.kod === undefined ? '?' : r.kod });
        if (r.kart === 'yok') await this.yenile();   // EU21: ekran bayatti — gercek durumu goster
      } catch (h) {
        this.ret = ceviri('es.ret_diger', this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
      this._odakla(!this.cihaz && this.bilgi ? '#es-ad' : '[data-es-durum]');   // EU27: tiklanan dugme DOM'dan kalkti
    },
    kaldirBasla(n) {
      this.kaldirOnay = n;
      this._odakla('[data-es-kaldir-eminim="' + n + '"]');
    },
    kaldirVazgec(n) {
      this.kaldirOnay = null;
      this._odakla('[data-es-kaldir="' + n + '"]');
    },
    /** ES7: ikinci asama — YALNIZ silahli satirin cihazi kaldirilir. */
    async kaldir(n) {
      if (this.kaldirOnay !== n) return;
      this.kaldirOnay = null;
      this.calisiyor = true;
      try {
        const ist = await this.istemciAl();
        const r = await ist.cihazSil(n);
        this.sonuc = r.tamam ? ceviri(SONUC_METIN.kaldirildi, this.dil, { n })
          : ceviri(SONUC_METIN.kaldirHata, this.dil, { n, mesaj: r.mesaj || '—' });
        await this.listeYukle(ist);
      } catch (h) {
        this.sonuc = ceviri(SONUC_METIN.kaldirHata, this.dil, { n, mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
      this._odakla('#es-liste-baslik');              // EU27: "Eminim, kaldir" DOM'dan kalkti
    },
    /** ES8: yalniz dugmeyle (otomatik degil). */
    async saatAyarla() {
      this.calisiyor = true;
      try {
        const ist = await this.istemciAl();
        const r = await ist.saatAyarla();
        this._al(ist);
        this.sonuc = r.tamam ? ceviri(SONUC_METIN.saatTamam, this.dil, { zaman: zamanYaz(r.unix) })
          : ceviri(SONUC_METIN.saatHata, this.dil, { mesaj: r.mesaj || '—' });
      } catch (h) {
        this.sonuc = ceviri(SONUC_METIN.saatHata, this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
    },
  },
};
