/* ═══════════════════════════════════════════════════════════════════════
   4F (PC17) — PC KABUGUNUN SERVICE WORKER'I

   Yalniz PC koprusunun kokeninde (`http://olcum.localhost:8770`, guvenli
   baglam) kaydolur — karar `app.js` `swKaydiUygun`. Kartin kendi kokeni
   (`http://olcum.local`, IP) guvenli baglam DEGIL; tarayici orada service
   worker'a hic izin vermez. Bu dosya karta GIRMEZ (arayuz-uret.py `PC_KABUGU`).

   STRATEJI — AG ONCE, ONBELLEK YEDEK (PC17, sentez 4F S1 (b)):
   Derleme adimi yok; kabuk karttaki panelle ayni kaynaktan. Once onbellek
   (stale-while-revalidate) kullanilsaydi kart guncellenince PC'deki kabuk bir
   acilis geride kalir, kunye/komut surumleri ayrisirdi. Ag her zaman once;
   onbellek yalniz kopru bir an yokken (yeniden baslarken) ilk kez acilan bir
   ekranin modulu inebilsin diye.

   ⚠ IZIN LISTESI, YASAK LISTESI DEGIL. Onbellege yalniz `onbellekIzinli()`'nin
     tanidigi DURAGAN kabuk dosyalari girer (bkz. KABUK / KABUK_DESEN). Geri
     kalan her istek (/akis, /komut, /arsiv, /kayit, /skop*, /pil, /kal,
     /eslestir, /cihaz, /saat, /bildirim, /kunye.json, /durum, sorgulu her adres,
     GET olmayan her istek) service worker'a HIC dokunmadan aga gider:
     `respondWith` cagrilmaz, onbellege yazilmaz. Yeni bir API ucu eklendiginde
     burada bir sey unutulursa sonuc "onbelleklenmez" olur, tersi degil.

   GEZINME: aga gider; ag yoksa (kopru kapali -> baglanti reddi) `cevrimdisi.html`
   ("Kopru calismiyor"). Gezinme yaniti onbellege ALINMAZ — eski bir index.html
   yeni modullerle karisamaz.

   SURUM: `SURUM` satirini `uretim/arayuz-uret.py` yazar (kabuk_surumu: panelin
   kaynak ozetleri + PC kabugunun dosyalari, bu dosya haric). Panel degisince bu
   dosyanin baytlari degisir -> tarayici yeni service worker'i kurar ->
   `activate` eski `olcum-kabuk-*` onbelleklerini siler. `sim3_web.py` satirin
   kaynaktan hesaplananla AYNI oldugunu sinar. ELLE DEGISTIRME.
   ═══════════════════════════════════════════════════════════════════════ */
'use strict';

const SURUM = '1e0ca6e95185';
const ONEK = 'olcum-kabuk-';
const ONBELLEK = ONEK + SURUM;
const CEVRIMDISI = '/cevrimdisi.html';

/* Duragan kabuk: sayfanin istedigi varliklar + manifest. Ekran modulleri ve
   `/ortak/` hesap modulleri dizinden okundugu icin DESENLE (arayuz-uret.py'nin
   goruntu kurali: `ekran/*.js`, `ortak/*.js`). Ikonlar `ikon-*.png`. */
const KABUK = Object.freeze([
  '/app.js',
  '/style.css',
  '/vendor/vue.global.prod.js',
  '/manifest.json',
  CEVRIMDISI,
]);
const KABUK_DESEN = /^\/(?:ekran|ortak)\/[a-z0-9_-]+\.js$|^\/ikon-[a-z0-9-]+\.png$/;

function onbellekIzinli(yol) {
  return KABUK.includes(yol) || KABUK_DESEN.test(yol);
}

/* Bir istege ne yapilacagi: 'gec' (dokunma, dogrudan ag), 'sayfa' (gezinme:
   ag, yoksa cevrimdisi sayfa), 'kabuk' (ag once, onbellek yedek). */
function istekKarari(istek, koken) {
  if (istek.method !== 'GET') return 'gec';
  const u = new URL(istek.url);
  if (u.origin !== koken) return 'gec';
  if (istek.mode === 'navigate') return 'sayfa';
  if (u.search !== '' || !onbellekIzinli(u.pathname)) return 'gec';
  return 'kabuk';
}

/* Onbellek de bossa (temizlenmis) son care: dis kaynaksiz kisa sayfa. */
const YEDEK_SAYFA = '<!doctype html><meta charset="utf-8"><title>Köprü çalışmıyor</title>'
  + '<p>Köprü çalışmıyor — kopru\\PC Baslat.bat ile başlatıp sayfayı yenileyin.</p>'
  + '<p lang="en">Bridge not running — start it and reload.</p>';

async function sayfa(istek) {
  try {
    return await fetch(istek);
  } catch (e) {
    const c = await caches.open(ONBELLEK);
    return (await c.match(CEVRIMDISI))
      || new Response(YEDEK_SAYFA, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  }
}

/* Ag once: HTTP onbellegi de atlanmasin diye `no-cache` (kopru Last-Modified
   veriyor; kosullu istek 304 ile ucuz). Yalniz 200 + ayni koken yaniti yazilir. */
async function agOnce(istek, bekle) {
  const c = await caches.open(ONBELLEK);
  try {
    const y = await fetch(istek, { cache: 'no-cache' });
    if (y.ok && y.type === 'basic') bekle(c.put(istek, y.clone()).catch(() => { /* kota: yedek yok, yanit yine gider */ }));
    return y;
  } catch (e) {
    const o = await c.match(istek);
    if (o) return o;
    throw e;
  }
}

self.addEventListener('install', (olay) => {
  olay.waitUntil(caches.open(ONBELLEK)
    .then((c) => c.add(new Request(CEVRIMDISI, { cache: 'reload' })))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', (olay) => {
  olay.waitUntil(caches.keys()
    .then((adlar) => Promise.all(adlar
      .filter((ad) => ad.startsWith(ONEK) && ad !== ONBELLEK)
      .map((ad) => caches.delete(ad))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (olay) => {
  const karar = istekKarari(olay.request, self.location.origin);
  if (karar === 'sayfa') olay.respondWith(sayfa(olay.request));
  else if (karar === 'kabuk') olay.respondWith(agOnce(olay.request, (s) => { try { olay.waitUntil(s); } catch (e) { /* olay bitti: yazim yine surer */ } }));
  /* 'gec': respondWith YOK — tarayici istegi service worker'siz yapar */
});
