/* ═══════════════════════════════════════════════════════════════════════
   3H-2 — TARAYICIDAN ESLESTIRME: ISTEMCI               (ekran/eslesme.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H-2 kararlari"
   (ES1-ES10, EU1-EU30). Kart protokolu tasarim/2026-10-01-1d-eslestirme.md
   (K5 eslestirme, K9 imza, K10 acilis + kayan pencere, K11, K12 /saat).
   Kriptografi ortak/src/imza.js'te (kopru/imza.py ile bayt bayt ayni).

   ACILISTA INMEZ: app.js yalniz bu tarayicida cihaz kaydi varsa dinamik
   ister — eslesmis tarayicinin acilisi bunu indirir (EU30: 3D siniri).
   Ayarlar > Eslestirme EKRANI ve metinleri ayri modulde (eslesme_ekran.js +
   ortak/sozluk_es.js), yalniz o bolum acilinca iner. Parcalar:
     * CIHAZ DEPOSU (ES2): IndexedDB `olcum-cihaz` / `cihaz`, anahtar kart
       kimligi; K ACIK (http:// -> guvenli baglam yok). Yazim TEKDUZE.
     * ISTEMCI (ES4/ES5): app.js kartIstek'in imzali yolu (`imza.ac`,
       credentials:'omit'); 401 -> yeni sayacla tek deneme -> "kart tanimiyor"
       (bildirilir, imzasiz yol). Eslestirme / liste / silme / saat (ES3/ES7/ES8).
     * AKIS (ES6/EU4): /akis fetch ile (EventSource yuzeyi); her baglanti
       YENI imzali URL, artan bekleme.
   `p0` (pil DURDUR) BU MODULE HIC UGRAMAZ (app.js dogrudan, K11).
   ⚠ Parola HICBIR yere yazilmaz; `N?` gonderilmez (B7 + T3H2 tarar).
   ═══════════════════════════════════════════════════════════════════════ */

import {
  ac, akisUrl, esles, HttpHatasi,
} from '/ortak/imza.js';

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
