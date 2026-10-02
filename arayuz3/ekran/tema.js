/* ═══════════════════════════════════════════════════════════════════════
   3A — GÖRÜNÜM (P1): Koyu · Açık · Ön panel        (ekran/tema.js)

   `ekran/` YENİ EKRANLARIN yeri (P4: kademeli bölme). Bu, oraya giren
   İLK modül: tarayıcının ES modülü, derleme yok. `app.js` bunu
   `import` ile alıyor; node testleri (B7) aynı dosyayı `require` ile.

   ⚠ ADLANDIRMA: kodda "tema", ekranda "Görünüm". `app.js`te `gorunum`
     zaten SEKME demek (#/olcum, `GORUNUMLER`, `.gorunum` sınıfı) ve B7
     o adlara bakıyor; aynı sözcüğü iki anlamda kullanmak okuyanı
     yanıltırdı. Seçilen maket de `data-tema` kullanıyor.

   SEÇİM ≠ ETKİN TEMA:
     secim  'sistem' | 'koyu' | 'acik' | 'onpanel'   — kullanıcının dediği
     etkin  'koyu' | 'acik' | 'onpanel'              — CSS'in uyguladığı
   `<html data-tema="<etkin>" data-tema-secim="<secim>">`. CSS YALNIZCA
   `data-tema`ya bakıyor; üç blok, her belirtecin her temada TEK tanımı.

   🔴 prefers-color-scheme ARTIK CSS'TE DEĞİL. 3A öncesi açık tema bir
      `@media (prefers-color-scheme: light)` bloğuydu ve kullanıcı onu
      seçemiyordu. Şimdi: AÇIK SEÇİM HER ZAMAN KAZANIR; 'sistem' (hiç
      seçim yapılmamışsa varsayılan) işletim sisteminin tercihine göre
      Koyu ya da Açık'a çözülür ve tercih değişince CANLI izlenir. Yani
      seçim yapmayan kullanıcı için davranış 3A öncesiyle AYNI (koyu
      sistem → Koyu, açık sistem → Açık); Koyu tabandır (data-tema yoksa).

   ⚠ İLK BOYAMA bu modülü BEKLEMİYOR: modüller ertelenir, sayfa önce
     varsayılanla çizilip sonra renk değiştirirdi (yanıp sönme).
     `index.html` <head>'indeki küçük betik aynı kararı boyamadan ÖNCE
     veriyor; B7 ikisinin her girdide AYNI sonucu verdiğini sınıyor.
     Kural değişirse İKİ yer değişmeli — o iddia bunu yakalar.

   Saklama: `localStorage['olcum.tema']`, JSON — öbür tercihlerle
   (`app.js` `ayarYaz`, önek `olcum.`) aynı biçim. Cihaz başına (P1).
   ⚠ HER ERİŞİM try/catch: özel kipte ve kota dolunca `localStorage`a
     ERİŞMEK bile atıyor (app.js `ayarOku` ile aynı ders).

   Tuval rengi ÖNBELLEKTE DEĞİL: `app.js` `renk('--volt')` her çizimde
   CSS'ten okuyor. Ama tuval bir bit eşlem — renk değişince YENİDEN
   ÇİZİLMELİ; `degisti` geri çağrısı bunun için.
   ═══════════════════════════════════════════════════════════════════════ */

export const TEMALAR = Object.freeze([
  Object.freeze({ id: 'sistem',  ad: 'Sistem',   alt: 'işletim sisteminin açık/koyu tercihine uyar' }),
  Object.freeze({ id: 'koyu',    ad: 'Koyu',     alt: 'varsayılan — tezgah aleti' }),
  Object.freeze({ id: 'acik',    ad: 'Açık',     alt: 'aydınlık ortam' }),
  Object.freeze({ id: 'onpanel', ad: 'Ön panel', alt: 'grafit + turuncu, cihaz ön paneli' }),
]);

export const TEMA_ANAHTAR = 'olcum.tema';
export const TEMA_VARSAYILAN = 'sistem';
/* Sistem 'sistem' seçiminde AÇIK mı istiyor. */
export const TEMA_SORGU = '(prefers-color-scheme: light)';

export function temaGecerli(secim) {
  return TEMALAR.some((t) => t.id === secim);
}

/* Seçimden CSS'in uygulayacağı temaya. Geçersiz seçim → Koyu (taban). */
export function temaCoz(secim, sistemAcik) {
  if (secim === 'sistem') return sistemAcik ? 'acik' : 'koyu';
  return temaGecerli(secim) ? secim : 'koyu';
}

export function temaOku(pencere) {
  try {
    const v = JSON.parse(pencere.localStorage.getItem(TEMA_ANAHTAR));
    return temaGecerli(v) ? v : TEMA_VARSAYILAN;
  } catch (e) {
    return TEMA_VARSAYILAN;
  }
}

export function temaYaz(pencere, secim) {
  try {
    pencere.localStorage.setItem(TEMA_ANAHTAR, JSON.stringify(secim));
    return true;
  } catch (e) {
    return false;            // tercih saklanamadı — görünüm yine değişir
  }
}

function sistemSorgusu(pencere) {
  try {
    return typeof pencere.matchMedia === 'function' ? pencere.matchMedia(TEMA_SORGU) : null;
  } catch (e) {
    return null;
  }
}

export function temaUygula(belge, secim, sistemAcik) {
  const etkin = temaCoz(secim, sistemAcik);
  const kok = belge.documentElement;
  kok.setAttribute('data-tema', etkin);
  kok.setAttribute('data-tema-secim', secim);
  return etkin;
}

/* Kur: kayıtlı seçimi uygula, 'sistem'deyken işletim sistemini izle.
   `degisti(etkin)` YALNIZCA etkin tema gerçekten değişince çağrılıyor
   (Sistem → Koyu, sistem zaten koyuyken, yeniden çizim gerektirmez). */
export function temaKur({ pencere, belge, degisti } = {}) {
  const sorgu = sistemSorgusu(pencere);
  const sistemAcik = () => !!(sorgu && sorgu.matches);
  let secim = temaOku(pencere);
  let etkin = temaUygula(belge, secim, sistemAcik());

  const bildir = (yeni) => {
    if (yeni === etkin) return;
    etkin = yeni;
    if (typeof degisti === 'function') degisti(etkin);
  };
  const sistemDegisti = () => {
    if (secim === 'sistem') bildir(temaUygula(belge, secim, sistemAcik()));
  };
  /* Eski Safari (< 14) `addEventListener` değil `addListener` tanıyor. */
  if (sorgu) {
    if (typeof sorgu.addEventListener === 'function') sorgu.addEventListener('change', sistemDegisti);
    else if (typeof sorgu.addListener === 'function') sorgu.addListener(sistemDegisti);
  }

  return {
    get secim() { return secim; },
    get etkin() { return etkin; },
    sec(yeni) {
      if (!temaGecerli(yeni) || yeni === secim) return false;
      secim = yeni;
      temaYaz(pencere, secim);
      bildir(temaUygula(belge, secim, sistemAcik()));
      return true;
    },
    birak() {
      if (!sorgu) return;
      if (typeof sorgu.removeEventListener === 'function') sorgu.removeEventListener('change', sistemDegisti);
      else if (typeof sorgu.removeListener === 'function') sorgu.removeListener(sistemDegisti);
    },
  };
}
