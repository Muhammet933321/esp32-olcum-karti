/* 5P (P1) — ACILMAMA DURUMU GORUNUR OLMALI (telefon paketi).
   arayuz3/index.html'in govde sonundaki satir ici bekcisinin karsiligi; CSP satir ici betigi ve
   `onerror`/`onclick` ozniteliklerini yasakladigi icin DIS klasik betik + dinleyiciler:
     - #acilmadi kutusunun "Yenile" dugmesi (panel_paketle.mjs `onclick`'i `data-yenile`ye cevirir),
     - bir betik dosyasi hic gelmezse: belgede YAKALAMA asamasinda `error` (betik ogesinin hatasi
       kabarmaz ama yakalamada belgeden gecer),
     - src/giris.js'in `arayuz-hata` olayi (ortam ya da panel modulu inmedi; ayrinti olayin detail'i),
     - 6 sn sonra #uyg hala `v-cloak` tasiyorsa (Vue mount edemedi).
   PC'deki `file:` dali yok: uygulama her zaman paketten (https://localhost) acilir.
   Gizlilik kapisi (test/gizlilik.test.js) src/ agacinda kuresel nesnenin ADINI yasaklar: dinleyiciler
   `document` uzerinde. index.html'de kutudan SONRA, modul betiklerinden ONCE kosar (moduller ertelenir). */
(function () {
  var kutu = document.getElementById('acilmadi');
  var neden = document.getElementById('acilmadi-neden');
  if (!kutu || !neden) return;
  function arayuzHata(ne) {
    neden.textContent = ne + ' yüklenemedi.';
    kutu.hidden = false;
  }
  var dugme = kutu.querySelector('[data-yenile]');
  if (dugme) dugme.addEventListener('click', function () { location.reload(); });
  document.addEventListener('arayuz-hata', function (o) { arayuzHata(String(o.detail)); });
  document.addEventListener('error', function (o) {
    var h = o.target;
    if (h && h.tagName === 'SCRIPT' && h.src) arayuzHata(h.src.split('/').pop() || 'betik');
  }, true);
  setTimeout(function () {
    var u = document.getElementById('uyg');
    if (u && u.hasAttribute('v-cloak')) {
      neden.textContent = neden.textContent
        || 'Betikler indi ama arayüz başlamadı (' +
           (typeof Vue === 'undefined' ? 'Vue yok' : 'Vue var') + ').';
      kutu.hidden = false;
    }
  }, 6000);
})();
