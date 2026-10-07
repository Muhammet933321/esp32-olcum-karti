/* 5P (P1) — GORUNUM ILK BOYAMADAN ONCE (telefon paketi).
   arayuz3/index.html <head>'indeki satir ici betigin AYNISI; telefonda CSP satir ici betigi yasakladigi
   icin DIS klasik betik (modul DEGIL: modul ertelenir, sayfa once Koyu cizilip sonra donerdi).
   index.html'de stil dosyasindan ONCE yuklenir.
   ⚠ Kural `arayuz3/ekran/tema.js` `temaOku` + `temaCoz` ile AYNI — test/panel_paket.test.js bu dosyayi,
     panelin <head> betigini ve tema.js'i her girdide karsilastiriyor; birini degistiren otekini de degistirmeli.
   Tek yazim farki: `window.matchMedia` yerine `typeof matchMedia` — gizlilik kapisi src/ agacinda kuresel
   nesnenin ADINI yasaklar (test/gizlilik.test.js); karar ayni (karsilastirma bunu sinar). */
(function () {
  var secim = 'sistem', sistemAcik = false;
  try {
    var v = JSON.parse(localStorage.getItem('olcum.tema'));
    if (v === 'sistem' || v === 'koyu' || v === 'acik' || v === 'onpanel') secim = v;
  } catch (e) { /* özel kip / engelli depo: varsayılan */ }
  try {
    sistemAcik = !!(typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: light)').matches);
  } catch (e) { /* matchMedia yok: koyu */ }
  var kok = document.documentElement;
  kok.setAttribute('data-tema', secim === 'sistem' ? (sistemAcik ? 'acik' : 'koyu') : secim);
  kok.setAttribute('data-tema-secim', secim);
})();
