/* ═══════════════════════════════════════════════════════════════════════
   Ölçüm Kartı — arayüz mantığı

   Karta Web Serial API ile bağlanır. Firmware'in gönderdiği satırlar:
     D <volt> <amper> <watt> <joule> <wh> <ms> <örnek>          ölçüm
     S2 <adet> <Hz> <volt/adım> <tetik> <tdiv_us> <kip> <tetik?> skop başlığı
     M f=.. T=.. Vpp=.. Vmax=.. ... n=..                        skop ölçümleri
     <ham 12-bit ADC kodları>                                   skop verisi
     E                                                          skop sonu
     T tdiv=.. hz=.. adet=..                                    skop ayarları
     S <adet> <hz> <volt/adım>                     Aşama 1 skop başlığı (eski)
   Diğer her satır günlüğe düşer.

   Web Serial güvenli bağlam ister: sayfa http://localhost üzerinden
   açılmalı. file:// ile çalışmaz — sunucu.py bunun için var.

   3A (P4) — BU DOSYA BİR ES MODÜLÜ (`<script type="module">`): strict
   kip, en üst düzey adlar `window`a düşmüyor. Yeni ekranlar `ekran/*.js`
   modülleri, paylaşılan hesap `/ortak/*.js` (kart/köprü/sunucu.py aynı
   yolu sunuyor). Eski ekranlar BURADA kalıyor; ancak yeniden yazılınca
   çıkıyorlar — bir seferde bölmek B7/B22'nin bu dosyanın metnine bakan
   iddialarını ve mutasyon girdilerini boşa düşürürdü.
   ⚠ İçe aktarmalar TEK SATIR `import { … } from '…';` biçiminde: B7 bu
     dosyayı vm'de betik olarak koşuyor ve bu satırları söküp adları
     modülün kendisinden (node `require`) bağlıyor; başka biçim KIRMIZI.

   3D (alt proje 3) — KABUK + CANLI + KAYIT DENETİMİ. Kabuk sol şerit (D1),
   Canlı'nın okuma kartları ve kayıt denetimi BURADA (index.html şablonu +
   bu dosyanın durumu); grafiği `ekran/canli.js` (ekran ilk görünür olunca
   iner). Kayıt durumu YALNIZ pasif dinlemeyle: kartın kendiliğinden bastığı
   `G` / `GP` / `GA` / `GT` satırları `satirIsle`'de (tek ayrıştırıcı, B22.2);
   `G?` yalnız bağlanınca bir kez ve bir kayıt komutundan sonra (D5).
   Yeni metinler `/ortak/sozluk.js`ten (`kb.` kabuk, `cn.` Canlı; D8).
   ═══════════════════════════════════════════════════════════════════════ */

import { TEMALAR, temaKur } from './ekran/tema.js';
import { ceviri, ceviriKod } from '/ortak/sozluk.js';

/* 3C: `defineAsyncComponent` — Kayitlar ekrani (ekran/kayitlar.js ve onun
   /ortak/ modulleri) ancak ekran ILK acilinca iner (dinamik `import()`):
   karttan her dosya istegi olcum dongusunu blokluyor ve acilis istekleri
   (B7 bolum 15: <= 8) buyumesin. */
const { createApp, defineAsyncComponent } = Vue;

/* Zaman tabanı merdiveni — firmware'deki SKOP_TDIV_US ile AYNI olmalı
   (kod/olcum-karti-a2/olcum-karti-a2.ino). Doğrulama zinciri (A5) iki
   listenin ayrışmadığını sınıyor. */
const SKOP_TDIV = [100, 200, 500, 1000, 2000, 5000,
                   10000, 20000, 50000, 100000, 200000, 500000];
/* 3E (OS2): izgara bolmeleri. Yatay = firmware SKOP_BOLME (pencere = bolme x tdiv);
   B7 iki sayiyi karsilastiriyor. Dikey 8 (osiloskop gelenegi). */
const SKOP_BOLME_X = 10;
const SKOP_BOLME_Y = 8;

/* Mühendislik biçimi: 0.000012 -> "12.0 µ" */
function muh(v, birim, hane = 3) {
  if (!isFinite(v) || v === 0) return '0 ' + birim;
  const on = [
    [1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''],
    [1e-3, 'm'], [1e-6, 'µ'], [1e-9, 'n'],
  ];
  const a = Math.abs(v);
  for (const [c, e] of on) {
    if (a >= c) return (v / c).toFixed(hane) + ' ' + e + birim;
  }
  return (v / 1e-9).toFixed(hane) + ' n' + birim;
}

/* ═══════════════════════════════════════════════════════════════════════
   TAŞIYICI KATMANI (B22.2)

   Üç taşıyıcı, TEK arayüz. Hepsi aynı yüzeyi sunuyor ve hepsi aynı
   `satirIsle(string)` ayrıştırıcısını besliyor:

       ad                 kısa kimlik
       destekli()         bu ortamda kullanılabilir mi
       yetenek            arayüzün hangi paneli açacağını söyleyen tablo
       ac(uyg)            bağlan      kapat(uyg)       kapat
       gonder(uyg, s)     komut yolla

   NEDEN BÖYLE: bu proje arayüz↔firmware ayrışmasından ÜÇ kez yandı
   (DEVIR 4.1, 4.15, B17 — sonuncusunda zincir 70/70 yeşilken kullanıcı
   gücü %82 yüksek okuyordu). "Basit sürüm + zengin sürüm" diye iki ayrı
   arayüz yazmak aynı riski dördüncü kez açardı. Onun yerine TEK arayüz,
   üç TAŞIYICI: kart USB'de, kart WiFi'de ya da PC köprüsünde —
   ayrıştırıcı, çizim ve panellerin hiçbiri değişmiyor. Modlar arasındaki
   fark kodda değil `yetenek` tablosunda yaşıyor.

   ⚠ `gonder()` ÇAĞRI YERLERİNİN ŞEKLİ DEĞİŞMİYOR. `test_arayuz3.js`
     `gonder('x')` / `komut('x')` düz metin kalıbını tarıyor; şekil
     korunursa çift yönlü komut denetimi bozulmadan çalışır. Değişen
     yalnızca `gonder()`in GÖVDESİ.

   ⚠ `satirIsle` içinde taşıyıcıya özgü dal AÇILMAYACAK. Hangi taşıyıcının
     beslediğini bilmesi gerekmiyor; bilmesi gerekseydi tel üstündeki
     baytlar ayrışmış demektir.
   ═══════════════════════════════════════════════════════════════════════ */

/* Gelen parçaları satır sınırında böler — seri ve akış aynısını kullanır. */
function satirBol(uyg, parca) {
  uyg._tampon = (uyg._tampon || '') + parca;
  let n;
  while ((n = uyg._tampon.indexOf('\n')) >= 0) {
    uyg.satirIsle(uyg._tampon.slice(0, n).trim());
    uyg._tampon = uyg._tampon.slice(n + 1);
  }
}

/* USB doğrudan: tam yetki. Tarihçe yalnız bu sekmede, ikinci izleyici yok. */
const TasiyiciSeri = {
  ad: 'usb-seri',
  yetenek: {
    ad: 'usb-seri', komut: 'hepsi', skop: 'ascii', skop_azami: 4000,
    gecmis_s: 0, cok_istemci: false, surucu: true,
  },
  destekli() { return typeof navigator !== 'undefined' && !!navigator.serial; },
  async ac(uyg) {
    uyg.port = await navigator.serial.requestPort();
    await uyg.port.open({ baudRate: 115200 });
    uyg.kaydet('— bağlandı, 115200 baud —');
    this.oku(uyg);
  },
  async kapat(uyg) {
    uyg.durduruldu = true;
    try {
      if (uyg.okuyucu) await uyg.okuyucu.cancel().catch(() => {});
      if (uyg.kapanis) await uyg.kapanis.catch(() => {});
      if (uyg.port) await uyg.port.close();
    } catch (e) { /* kapanışta hata önemli değil */ }
    uyg.port = null;
  },
  async gonder(uyg, metin) {
    if (!uyg.port) return;
    const yazici = uyg.port.writable.getWriter();
    try {
      await yazici.write(new TextEncoder().encode(metin + '\n'));
    } finally {
      yazici.releaseLock();
    }
  },
  async oku(uyg) {
    uyg.durduruldu = false;
    const cozucu = new TextDecoderStream();
    uyg.kapanis = uyg.port.readable.pipeTo(cozucu.writable).catch(() => {});
    uyg.okuyucu = cozucu.readable.getReader();
    try {
      while (true) {
        const { value, done } = await uyg.okuyucu.read();
        if (done) break;
        satirBol(uyg, value);
      }
    } catch (e) {
      if (!uyg.durduruldu) uyg.hata = 'Okuma hatası: ' + e.message + ' — kablo çıkmış ya da kart yeniden başlamış olabilir; “Karta bağlan”a yeniden basın.';
    } finally {
      uyg.okuyucu.releaseLock();
    }
  },
};

/* SSE — kart doğrudan (B22.4) ya da PC köprüsü (B22.3) üzerinden.
   Satırlar `data: <satır>` olarak geliyor, yani tel üstündeki baytlar
   seri porttakiyle BİREBİR AYNI. Tek ayrıştırıcı bu yüzden mümkün. */
const TasiyiciAkis = {
  ad: 'akis',
  yetenek: {
    ad: 'akis', komut: 'hepsi', skop: 'ikili', skop_azami: 4000,
    gecmis_s: 86400, cok_istemci: true, surucu: true,
  },
  destekli() { return typeof EventSource !== 'undefined'; },
  async ac(uyg) {
    uyg.akis = new EventSource(uyg.kartAdres('/akis'));
    uyg.akis.onmessage = (e) => uyg.satirIsle(String(e.data).trim());
    uyg.akis.onerror = () => { uyg.hata = 'Akış koptu — yeniden bağlanılıyor'; };
    /* Kart TEK sürücüye hizmet ediyor. Köprü kayıtlıysa ikinci istemci
       reddediliyor ve NEREYE gideceği söyleniyor — sessiz kapanma yok. */
    uyg.akis.addEventListener('kopru', (e) => {
      /* B27 A1: aynı bilgi HEM .hata HEM .uyari kutusunda çıkıyordu —
         iki bildirim, tek olgu. Bağlantılı olan (.uyari, kopruAdresi)
         kaldı; hata satırı düştü. */
      uyg.kopruAdresi = String(e.data).trim();
    });
    /* PC köprüsü N izleyiciye yayın yapıyor ama SÜRÜCÜ bir tane. Jeton
       burada geliyor ve her komutta geri gönderiliyor. Kart doğrudan
       bağlandıysa bu olay hiç gelmez — o zaman hakem yok, sürücü biziz. */
    uyg.akis.addEventListener('kimlik', (e) => {
      try {
        const k = JSON.parse(e.data);
        uyg.jeton = k.jeton || '';
        uyg.surucuyum = !!k.surucu;
      } catch (err) { /* kimlik olayı yoksa varsayılan geçerli */ }
    });
    uyg.kaydet('— akış açıldı: ' + uyg.kartAdres('/akis') + ' —');
    /* 🔴 B27 A2 — `kimlik` GELMEDEN DÖNME. Kart komut ucunda önce jetona
       bakıyor (403), sonra parolaya (401). `ac()` hemen dönünce baglan()
       `?`yi BOŞ jetonla yolluyordu: gerçek kartta CDP ile ölçüldü, her
       açılışta "Komut gönderilemedi (403): gecersiz oturum jetonu" —
       K5 eşitlemesi WiFi yolunda hiç çalışmamış, üstelik her açılış bir
       hata bildirimiyle başlıyordu. `kimlik` olayı jetonu getirince
       dönüyoruz; eski köprü (kimlik yollamayan) ya da hata için 3 s tavan. */
    await new Promise((coz) => {
      const tavan = setTimeout(coz, 3000);
      const bitir = () => { clearTimeout(tavan); coz(); };
      uyg.akis.addEventListener('kimlik', bitir, { once: true });
      uyg.akis.addEventListener('error', bitir, { once: true });
    });
  },
  async kapat(uyg) {
    if (uyg.akis) uyg.akis.close();
    uyg.akis = null;
  },
  async gonder(uyg, metin) {
    /* POST + özel başlık: çapraz kökende preflight'a zorlar ve
       <img>/<form> özel başlık ekleyemez. GET olsaydı CSRF'e açık olurdu
       ve `p1` (pil deşarjını başlat) uzaktan tetiklenebilirdi. */
    const y = await fetch(uyg.kartAdres('/komut'), {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain',
        'X-Olcum': '1',
        'X-Jeton': uyg.jeton || '',
      },
      body: metin,
    }).catch(() => null);
    if (!y || !y.ok) {
      /* Sunucunun SEBEBİNİ göster — "403" tek başına kullanıcıya
         "neden olmadı" sorusunun cevabını vermiyor. */
      const neden = y ? await y.text().catch(() => '') : '';
      uyg.hata = 'Komut gönderilemedi'
               + (y ? ' (' + y.status + ')' : ' — bağlantı yok')
               + (neden ? ': ' + neden : '');
      return;
    }
    /* Köprü 204 + boş gövde döndürüyor: kartın cevabı zaten SSE'den
       geliyor. Kart doğrudan bağlandığında yanıt gövdede gelir; ikisi de
       aynı kodla işleniyor çünkü boş gövde hiçbir satır üretmiyor. */
    for (const sat of (await y.text()).split('\n')) {
      if (sat.trim()) uyg.satirIsle(sat.trim());
    }
  },
};

/* ?demo — donanımsız önizleme. Referans uygulama: firmware'in ürettiği
   satırların AYNISINI üretiyor, yani ayrıştırıcı gerçek yolundan çalışır. */
const TasiyiciSahte = {
  ad: 'demo',
  yetenek: {
    ad: 'demo', komut: 'hepsi', skop: 'ascii', skop_azami: 4000,
    gecmis_s: 0, cok_istemci: false, surucu: true,
  },
  /* B27 A2: HER ZAMAN destekli. Betik aynı kökende ve `demoVeri()`
     indiriyor; "SahteKart tanımlı mı" diye bakmak, menüden demo seçen
     kullanıcıya ÖLÜ BİR DÜĞME gösteriyordu (DEVIR 4.15'in tam kendisi).
     İndirme başarısızsa `demoVeri()` sebebi yazıyor. */
  destekli() { return true; },
  async ac() { /* kurulum demoVeri() içinde */ },
  async kapat(uyg) {
    if (uyg.demoZaman) clearTimeout(uyg.demoZaman);   // B27 A2: setTimeout zinciri
    uyg.demoZaman = null;
    uyg.demoKurulu = false;      // demoya geri dönülürse yeniden kurulabilsin
  },
  async gonder(uyg, metin) {
    for (const sat of SahteKart.komut(metin)) uyg.satirIsle(sat);
  },
};

const TASIYICILAR = {
  seri: TasiyiciSeri,
  akis: TasiyiciAkis,
  demo: TasiyiciSahte,
};

/* ═══ B27 Aşama 1 — GÖRÜNÜMLER ═══════════════════════════════════════
   Tek sayfa, hash yönlendirme (#/olcum …). stok-takip'teki desenle aynı:
   geri tuşu çalışır, adres paylaşılabilir, ESP'ye ek istek yok.
   Görünümler `v-show` ile gizleniyor, `v-if` ile DEĞİL — tuvaller
   (zaman grafiği, skop) canlı kalsın, geçişte yalnızca yeniden çizilsin. */
/* 3D (D1): sol şeridin gezinmesi. Ad ve alt yazı SÖZLÜKTEN (`kb.<id>`,
   `kb.<id>_alt`; D8). Henüz yazılmamış ekran (Karşılaştırma, 3G) BURADA
   YOK — ölü bağlantı kullanıcıyı boş ekrana götürürdü. `ikon` SVG yolu
   (seçilen maketten; çizgi, dolgu yok). */
const GORUNUMLER = [
  { id: 'canli', ad: 'kb.canli', alt: 'kb.canli_alt', ikon: 'M3 12h4l3-8 4 16 3-8h4' },
  { id: 'skop', ad: 'kb.skop', alt: 'kb.skop_alt',
    ikon: 'M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM3 14c3 0 3-6 6-6s3 8 6 8 3-4 6-4' },
  { id: 'pil', ad: 'kb.pil', alt: 'kb.pil_alt',
    ikon: 'M9 4h6a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM10 2h4M10 14h4' },
  { id: 'kayitlar', ad: 'kb.kayitlar', alt: 'kb.kayitlar_alt', ikon: 'M4 6h16M4 12h16M4 18h10' },
  { id: 'ayar', ad: 'kb.ayar', alt: 'kb.ayar_alt',
    ikon: 'M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2' },
  { id: 'konsol', ad: 'kb.konsol', alt: 'kb.konsol_alt', ikon: 'M4 17l6-5-6-5M12 19h8' },
];

/* 3D (D8): kabuk (`kb.`) ve Canli (`cn.`) metinleri — sozluk ANAHTARI duz
   metin sabitiyle (ekran/kayitlar.js KL_METIN deseni): sozluk testi
   "kullanilmayan anahtar yok"u bu dosyayi da tarayarak olcuyor. */
const KB_METIN = Object.freeze({
  ad: 'kb.ad', gezinme: 'kb.gezinme', menuAc: 'kb.menu_ac', menuKapat: 'kb.menu_kapat',
  cevrimdisi: 'kb.cevrimdisi', baglan: 'kb.baglan', kes: 'kb.kes',
  esitlenmemisYok: 'kb.esitlenmemis_yok', surumIpucu: 'kb.surum_ipucu',
  icerigeGec: 'kb.icerige_gec', esitlenmemisBagliDegil: 'kb.esitlenmemis_bagli_degil', pilCalisiyor: 'kb.pil_calisiyor',
});
const CN_METIN = Object.freeze({
  baslik: 'cn.baslik', okumalar: 'cn.okumalar', gerilim: 'cn.gerilim', akim: 'cn.akim', guc: 'cn.guc',
  enerji: 'cn.enerji', enerjiIpucu: 'cn.enerji_ipucu', onSaniyeYok: 'cn.on_saniye_yok',
  grafik: 'cn.grafik', grafikEtiket: 'cn.grafik_etiket', sagEksen: 'cn.sag_eksen', sagAkim: 'cn.sag_akim',
  sagGuc: 'cn.sag_guc', sagYok: 'cn.sag_yok', pencere: 'cn.pencere', yenileme: 'cn.yenileme',
  dondur: 'cn.dondur', canliyaDon: 'cn.canliya_don', donmusIpucu: 'cn.donmus_ipucu', veriYok: 'cn.veri_yok',
  yukleniyor: 'cn.yukleniyor', yuklenemedi: 'cn.yuklenemedi', kanalVeriYok: 'cn.kanal_veri_yok',
  imlecSil: 'cn.imlec_sil', imlecYok: 'cn.imlec_yok', okumaDt: 'cn.okuma_dt', okumaDv: 'cn.okuma_dv',
  okumaOrtI: 'cn.okuma_ort_i', okumaYuk: 'cn.okuma_yuk', okumaEnerji: 'cn.okuma_enerji',
  kayitDenetim: 'cn.kayit_denetim', kayitHiz: 'cn.kayit_hiz', herOrnek: 'cn.her_ornek', baslat: 'cn.baslat',
  durdur: 'cn.durdur', notEkle: 'cn.not_ekle', notMetin: 'cn.not_metin', notGonder: 'cn.not_gonder',
  vazgec: 'cn.vazgec', zamanla: 'cn.zamanla', planBas: 'cn.plan_bas', planSure: 'cn.plan_sure',
  planSureIpucu: 'cn.plan_sure_ipucu', planKur: 'cn.plan_kur', planIptal: 'cn.plan_iptal',
  birimSa: 'cn.birim_sa', birimDk: 'cn.birim_dk', kayitSuruyor: 'cn.kayit_suruyor',
  aktifKayit: 'cn.aktif_kayit', kayitBilinmiyor: 'cn.kayit_bilinmiyor', sure: 'cn.sure', hiz: 'cn.hiz',
  kalanHesap: 'cn.kalan_hesap', planYok: 'cn.plan_yok', planSuresiz: 'cn.plan_suresiz',
  sonOlaylar: 'cn.son_olaylar', olayYok: 'cn.olay_yok',
  /* WIG (2026-10-02): iki asamali onaylar, mesgul not dugmesi, ADC yanit vermiyor */
  durdurEminim: 'cn.durdur_eminim', planIptalKayit: 'cn.plan_iptal_kayit', planIptalEminim: 'cn.plan_iptal_eminim',
  notGonderiliyor: 'cn.not_gonderiliyor', adcYokV: 'cn.adc_yok_v', adcYokI: 'cn.adc_yok_i',
});

/* WIG: iki asamali onayin omru — bayat bir "Eminim" saatler sonra tek tikla calismasin. */
const ONAY_MS = 6000;
/* WIG: pil durumu / hatasi kartta ASCII ad olarak geliyor (`/pil`); ekranda sozlukten.
   Hata metinleri firmware `pil_hata_metni` ile AYNI (B7 her birini ino'dan okuyup sinar). */
const PIL_DURUM_KOD = Object.freeze({ BEKLEMEDE: 0, CALISIYOR: 1, BITTI: 2, DURDURULDU: 3, HATA: 4 });
const PIL_HATA_KOD = Object.freeze([
  ['gerilim zaten kesmenin altinda', 1], ['gerilim 38.5 V ustunde', 2], ['TERS POLARITE', 3],
  ['MOSFET kapali ama AKIM VAR', 4], ['azami sure asildi', 5], ['yuk baglanmadi', 6],
]);
/** WIG: sekme basligi gorunumu soyler ("Pil testi — Olcum Karti"; ekran okuyucu, gecmis). */
function belgeBasligiYaz(id, dil) {
  if (typeof document === 'undefined') return;
  const g = GORUNUMLER.find((x) => x.id === id);
  document.title = (g ? ceviri(g.ad, dil) + ' — ' : '') + ceviri('kb.ad', dil);
}
/** Kart adresi: sema yoksa http:// (yoksa istek sayfanin KENDI sunucusuna goreli gider). */
function tabanTam(taban) {
  const t = String(taban || '').trim().replace(/\/+$/, '');
  if (!t) return '';
  return /^https?:\/\//i.test(t) ? t : 'http://' + t;
}

/** Anahtar haritasi -> metinler (dil). */
function metinHaritasi(harita, dil) {
  const m = {};
  for (const [a, k] of Object.entries(harita)) m[a] = ceviri(k, dil);
  return m;
}

/** D8: dil secimi `localStorage['olcum.dil']` (JSON) — ekran/esitleme.js `dilOku`
 *  ile AYNI kural (B7 iki fonksiyonu her girdide karsilastiriyor). */
function dilSec(depo) {
  let v = null;
  try { v = JSON.parse(depo ? depo.getItem('olcum.dil') : null); } catch (e) { v = null; }
  return v === 'en' ? 'en' : 'tr';
}
/* 3D (D1): ESKİ ADRES `#/olcum` (B27'den beri Ölçüm sekmesi) Canlı'ya düşer:
   bilinmeyen her adres varsayılana gider ve varsayılan Canlı. Ayrı bir takma
   ad tablosu YOK — mutasyon onu ölü kod olarak gösterdi (aynı sonucu
   varsayılan veriyordu). B7 `#/olcum -> canli`yı davranış olarak sınıyor:
   varsayılan değişirse eski adres kırmızıya döner. */
const GORUNUM_VARSAYILAN = 'canli';

/* Akım kanalının ADS kademesi SABIT: ±0.256 V (firmware `PGA_0256`).
   Menzili şönt belirliyor — kademe değil. */
const ADS_PGA_V = 0.256;

/* B27 A2 — RAPOR ARALIGI secenekleri (ms). Kartin `r<ms>` siniri 20..5000;
   menu bilerek daha dar: 50 ms altinda grafik noktasi degil gurultu
   gorunur, 1 s ustunde arayuz "koptu" hissi verir. */
const RAPOR_SECENEKLERI = [
  { ms: 50,   ad: '20 / s' },
  { ms: 100,  ad: '10 / s' },
  { ms: 200,  ad: '5 / s (varsayılan)' },
  { ms: 500,  ad: '2 / s' },
  { ms: 1000, ad: '1 / s' },
];

/* Cizim istekleri bir kareye BIRLESTIRILIYOR. 20 satir/s'de her satirda
   ayri cizim, 60 s pencerede 1200 noktayi saniyede 20 kez yeniden cizmek
   demek; telefonu isitir. requestAnimationFrame yoksa (test sanaligi)
   dogrudan ciziliyor. Bayrak Vue verisi DEGIL: reaktif olmasi gerekmiyor. */
let grafikBekliyor = false;

function hashtenGorunum() {
  const h = (typeof location !== 'undefined' ? location.hash : '').replace(/^#\/?/, '');
  /* 3C: `#/kayit/<oturum>[@kimlik][/rapor]` Kayitlar sekmesinin ICI; hangi
     kaydin acik oldugunu ekran kendisi okuyor (ekran/kayitlar.js rotaCoz). */
  if (/^kayit\//.test(h)) return 'kayitlar';
  /* 3E (OS6): `#/skop/kayit/<oturum>/<sira>[@kimlik]` Osiloskop'un ICI — hangi yakalama
     oldugunu ekran modulu okuyor (ekran/osiloskop.js skopRotaCoz). */
  if (/^skop\/kayit\//.test(h)) return 'skop';
  return GORUNUMLER.some((g) => g.id === h) ? h : GORUNUM_VARSAYILAN;
}

/* ═══ 3D — KAYIT DURUMU: PASİF DİNLEME (D4–D7) ═══════════════════════
   Kartın kendiliğinden bastığı satırlar (olcum-karti-a3.ino):
     G  <durum> <oturum> <nokta> …          kayıtta saniyede bir + değişince
     GA <hazir_sektor> …                    `G?` ile (ayrıntılı kip)
     GT <etkin> …                           `G?` ile (osiloskop günlüğü)
     GP <durum> <bas_unix> …                `G?` ve `Gp?` ile (plan)
   Alan ADLARI firmware'in protokol yorumundaki adlar, SAYISI onun snprintf
   biçiminden — B7 ikisini de firmware kaynağından türetip karşılaştırıyor;
   kart bir alan eklerse burası kırmızıya döner. Ayrıştırıcı KATI: alan
   sayısı tutmayan ya da tamsayı olmayan satır durum SAYILMAZ (konsola düşer).
   ⚠ Bu fonksiyonlar saf ve en üst düzeyde: B7 onları vm bağlamından alıp
     firmware'in biçimiyle sınıyor (Vue'suz). */
const KAYIT_SATIRLARI = Object.freeze({
  G: Object.freeze(['durum', 'oturum', 'nokta', 'sonraki', 'onay', 'doluluk', 'onaysiz', 'dusen',
    'yaz_azami_us', 'sil_azami_us', 'sil_adet', 'tarama_ms', 'son_hata']),
  GA: Object.freeze(['hazir_sektor', 'ayrintili_ornek', 'dusen_ornek', 'kayit_ici_silme']),
  GT: Object.freeze(['etkin', 'aralik_ms', 'yakalama', 'yazilamayan']),
  GP: Object.freeze(['durum', 'bas_unix', 'sure_s', 'hiz_ms', 'oturum']),
});
/* kayit_yonet.h KDR_* ve kayit_plan.h PLAN_* (B7 karşılaştırıyor). */
const KDR = Object.freeze({ TARIYOR: 0, BOS: 1, KAYIT: 2, DOLU: 3, BEKLIYOR: 4, HATA: 5 });
const PLAN = Object.freeze({ YOK: 0, BEKLIYOR: 1, SURUYOR: 2, BITTI: 3, ATLANDI: 4, KACIRILDI: 5,
  SAAT_YOK: 6, BASLATILAMADI: 7 });
/* Kartın kabul ettiği kayıt aralıkları (kayit__hiz_gecerli; 0 = her örnek). */
const KAYIT_HIZLARI = Object.freeze([0, 20, 100, 200, 1000, 10000, 60000]);
/* Komut tavanı BAYT: firmware KOMUT_AZAMI 176 (NUL dahil) ve String::length()
   bayt sayıyor — Türkçe harf UTF-8'de 2 bayt. Not metni: kayit_bicim.h
   KAYIT_NOT_METIN (kart fazlasını SESSİZCE keser; panel reddedip söylüyor). */
const KOMUT_AZAMI_BAYT = 175;
const NOT_METIN_AZAMI_BAYT = 120;
/* kayit_plan.h: PLAN_SURE_AZAMI · PLAN_UNIX_ALT · PLAN_ILERI_AZAMI */
const PLAN_SURE_AZAMI_S = 30 * 86400;
const PLAN_UNIX_ALT = 1700000000;
const PLAN_ILERI_AZAMI_S = 366 * 86400;
/* D6: "~X kaldı" tahmini en az bu kadar gözlemden sonra (öncesi "hesaplanıyor"). */
const KALAN_EN_AZ_MS = 60000;
/* D2: okuma kartlarının altındaki aralık (saniye). */
const ON_SANIYE = 10;
/* D7: son olaylar listesi tavanı (yalnız bu sekmede). */
const OLAY_AZAMI = 20;
/* Kart `! G…` satırı bir kayıt komutundan bu kadar sonra gelirse O KOMUTUN reddi sayılır. */
const RET_PENCERESI_MS = 5000;
/* millis() 32 bit: 49.7 günde sarar (yeniden başlama SAYILMAZ). */
const MILLIS_TUR = 4294967296;

/** `G` / `GA` / `GT` / `GP` satırı -> {tur, <alan>: sayı}; değilse null. */
function kayitSatiriCoz(satir) {
  const p = String(satir === null || satir === undefined ? '' : satir).trim().split(/\s+/);
  const alanlar = Object.prototype.hasOwnProperty.call(KAYIT_SATIRLARI, p[0]) ? KAYIT_SATIRLARI[p[0]] : null;
  if (!alanlar || p.length !== alanlar.length + 1) return null;
  const o = { tur: p[0] };
  for (let k = 0; k < alanlar.length; k++) {
    if (!/^-?\d{1,10}$/.test(p[k + 1])) return null;
    o[alanlar[k]] = Number(p[k + 1]);
  }
  return o;
}

/** Açılış afişi (`Olcum Karti — <aşama>`) -> {surum, fw}; değilse null. `fw`
 *  afişte `A3-xx` biçiminde bir firmware sürümü varsa o (bugün YOK: kayıt
 *  sürümü KAYIT_FW_SURUM afişe basılmıyor), yoksa null. */
function afisCoz(satir) {
  const m = /^Olcum Karti(?:\s*[—–-]\s*(.*))?$/.exec(String(satir || '').trim());
  if (!m) return null;
  const surum = (m[1] || '').trim();
  const fw = /\b(A\d+-[0-9A-Za-z]+)\b/.exec(surum);
  return { surum, fw: fw ? fw[1] : null };
}

/** D satırının `ms`i geri gitti mi: 'yeniden' (kart yeniden başladı), 'sarma'
 *  (millis 32 bit sardı) ya da null (ileri gidiyor). */
function msAtlamasi(onceki, yeni) {
  if (!(onceki > 0) || !Number.isFinite(yeni) || yeni >= onceki) return null;
  return (onceki > MILLIS_TUR - 600000 && yeni < 600000) ? 'sarma' : 'yeniden';
}

/** Son `sureS` saniyedeki (gecmis'in son noktasına göre) geçerli değerlerin
 *  min/maks'ı. NaN (kanal yanıt vermedi) sayılmaz. Yoksa null. */
function sonAralikMinMaks(gecmis, alan, sureS = ON_SANIYE) {
  const n = gecmis ? gecmis.length : 0;
  if (!n) return null;
  const basT = gecmis[n - 1].t - sureS;
  let min = Infinity;
  let maks = -Infinity;
  let say = 0;
  for (let k = n - 1; k >= 0 && gecmis[k].t >= basT; k--) {
    const x = gecmis[k][alan];
    if (typeof x !== 'number' || Number.isNaN(x)) continue;
    say++;
    if (x < min) min = x;
    if (x > maks) maks = x;
  }
  return say ? { min, maks, say } : null;
}

/**
 * D6 — DOLANA KADAR KALAN SÜRE, yalnız ÖLÇÜLENDEN. `gozlem` = [{t (ms), d
 * (onaysız binde)}], azalmayan d (onay gelince düşerse çağıran sıfırlar).
 * Kart onaysız veri yüzünden DOLU'ya düşer (kayit_gunluk.h KG_DOLU: onaysız
 * veri ASLA silinmez) — kalan = (1000 − onaysız) / artış hızı. Binde 1'lik
 * nicemleme yüzünden hız DEĞİŞİM ANLARINDAN ölçülür:
 *   < 60 s gözlem                 -> {durum: 'hesaplaniyor'}
 *   >= 2 değişim                  -> {durum: 'yaklasik', ms}  (ilk–son değişim arası;
 *                                    son değişimden beri artış yavaşladıysa ortalama alt sınır)
 *   0–1 değişim                   -> {durum: 'enaz', ms}  (artış < Δ+1 binde: kalan ALT SINIRI)
 */
function kalanTahmin(gozlem) {
  const n = gozlem ? gozlem.length : 0;
  if (n < 2) return { durum: 'hesaplaniyor', ms: NaN };
  const ilk = gozlem[0];
  const son = gozlem[n - 1];
  const sure = son.t - ilk.t;
  if (!(sure >= KALAN_EN_AZ_MS)) return { durum: 'hesaplaniyor', ms: NaN };
  const bos = Math.max(0, 1000 - son.d);
  const degisim = [];
  for (let k = 1; k < n; k++) if (gozlem[k].d !== gozlem[k - 1].d) degisim.push(gozlem[k]);
  if (degisim.length >= 2) {
    const a = degisim[0];
    const b = degisim[degisim.length - 1];
    let hiz = (b.d - a.d) / (b.t - a.t);
    /* son değişimden beri beklenenin çok ötesinde sessizlik: artış yavaşladı */
    const ust = (son.d + 1 - a.d) / (son.t - a.t);
    if (ust < hiz) hiz = ust;
    if (hiz > 0) return { durum: 'yaklasik', ms: bos / hiz };
  }
  const hizUst = (son.d - ilk.d + 1) / sure;   // artış < Δ + 1 binde (nicemleme)
  return { durum: 'enaz', ms: Math.max(0, bos - 1) / hizUst };
}

/** UTF-8 bayt sayısı (kartın String::length()'i). TextEncoder'sız: B7 vm'inde yok. */
function utf8Bayt(s) {
  let n = 0;
  for (const ch of String(s)) {
    const c = ch.codePointAt(0);
    n += c < 0x80 ? 1 : c < 0x800 ? 2 : c < 0x10000 ? 3 : 4;
  }
  return n;
}

/** Her kayıt komutu buradan geçer: kartın tavanını (bayt) aşan komut GÖNDERİLMEZ. */
function kayitKomutuDenetle(komut) {
  const bayt = utf8Bayt(komut);
  return bayt > KOMUT_AZAMI_BAYT ? { hata: 'cn.hata_komut_uzun', bayt } : { komut };
}

/** Başlat: hız (ms) -> `Gb<ms>`; 0 = her örnek (ayrıntılı kip). */
function kayitBaslatKomutu(hiz) {
  const h = Number(hiz);
  return KAYIT_HIZLARI.includes(h) ? { komut: 'Gb' + h } : { hata: 'cn.hata_hiz' };
}

/** Not: `Gn<oturum>[@<kart_ms>] <metin>`. `kartMs` verilirse not grafikte o anda
 *  durur (kayıt görünümü notListesi). Kartın SESSİZCE attığı karakterler (", \,
 *  denetim) ve 120 baytı aşan metin REDDEDİLİR — yazılan, kaydedilenle aynı olsun. */
function kayitNotKomutu(oturum, metin, kartMs = null) {
  if (!(Number.isInteger(oturum) && oturum > 0)) return { hata: 'cn.hata_oturum' };
  const m = String(metin === null || metin === undefined ? '' : metin).replace(/[\r\n\t]+/g, ' ').trim();
  if (!m) return { hata: 'cn.hata_not_bos' };
  /* \u0022 = cift tirnak, \u005c = ters bolu (regex'te CIPLAK tirnak yok: sozluk
     testinin dizge cozucusu bu dosyayi da tariyor) */
  if (/[\u0022\u005c\u0000-\u001f\u007f]/.test(m)) return { hata: 'cn.hata_not_karakter' };
  const bayt = utf8Bayt(m);
  if (bayt > NOT_METIN_AZAMI_BAYT) return { hata: 'cn.hata_not_uzun', bayt };
  const zaman = Number.isInteger(kartMs) && kartMs >= 0 ? '@' + kartMs : '';
  return kayitKomutuDenetle('Gn' + oturum + zaman + ' ' + m);
}

/** Zamanla: `Gp<unix>,<süre_s>,<hız_ms>` — kartın kayit_plan.h sınırlarıyla aynı
 *  (1.7e9 altı başlangıç, 1 yıldan ileri, 30 günden uzun, penceresi geçmiş -> ret). */
function kayitPlanKomutu({ basUnix, sureS, hizMs, simdiUnix } = {}) {
  if (!Number.isInteger(basUnix)) return { hata: 'cn.hata_plan_bas' };
  if (!Number.isInteger(sureS) || sureS < 0) return { hata: 'cn.hata_plan_sure' };
  if (!KAYIT_HIZLARI.includes(hizMs)) return { hata: 'cn.hata_hiz' };
  if (basUnix < PLAN_UNIX_ALT) return { hata: 'cn.hata_plan_eski' };
  if (Number.isFinite(simdiUnix) && basUnix - simdiUnix > PLAN_ILERI_AZAMI_S) return { hata: 'cn.hata_plan_ileri' };
  if (sureS > PLAN_SURE_AZAMI_S) return { hata: 'cn.hata_plan_sure' };
  if (sureS && Number.isFinite(simdiUnix) && basUnix + sureS <= simdiUnix) return { hata: 'cn.hata_plan_gecmis' };
  return kayitKomutuDenetle(`Gp${basUnix},${sureS},${hizMs}`);
}

/** `<input type="datetime-local">` değeri (YEREL saat) -> unix saniye; geçersizse NaN. */
function yerelSaattenUnix(deger) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(String(deger || ''))) return NaN;
  const ms = new Date(deger).getTime();
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : NaN;
}

/** İki `G` arasındaki değişimden olaylar (D7): [{anahtar, d}]. İlk G (önceki yok) olay DEĞİL. */
function kayitOlaylari(o, y) {
  if (!o || !y) return [];
  const kayitta = (g) => g.durum === KDR.KAYIT;
  const ol = [];
  if (kayitta(y) && (!kayitta(o) || o.oturum !== y.oturum)) {
    ol.push({ anahtar: kayitta(o) ? 'cn.olay_yeni_oturum' : 'cn.olay_basladi', d: { oturum: y.oturum } });
  } else if (kayitta(o) && !kayitta(y)) {
    ol.push({ anahtar: 'cn.olay_durdu', d: { oturum: o.oturum }, durum: y.durum });
  } else if (o.durum !== y.durum) {
    ol.push({ anahtar: 'cn.olay_durum', d: {}, durum: y.durum });
  }
  if (y.dusen > o.dusen) ol.push({ anahtar: 'cn.olay_dusen', d: { n: y.dusen - o.dusen } });
  return ol;
}

/* ═══ 3E — OSILOSKOP (OS1-OS8) ═════════════════════════════════════════
   Dalga tuvali, yakalama ve komutlar BURADA (eski skop kodu; OS2/OS7: kartla
   dogrulanmis cizim ve iddialar korunuyor). Spektrum ve kayitli yakalama
   `ekran/osiloskop.js` (ekran ilk acilinca `import()`; U1/E1 deseni).
   OS5 — yakalama gunlugu `Gt0` (her tetik) / `Gt<ms>` / `Gtd`: aralik kartin
   `kayit__skop_aralik` siniri (0 ya da 1000 … 3 600 000 ms, yalniz rakam);
   B7 bu iki sayiyi firmware kaynagindan okuyup karsilastiriyor. Durum PASIF
   `GT` satirindan (kayitSatiriCoz, D5), kartin `! G:` reddi OLDUGU GIBI (E9). */
const SKOP_GUNLUK_ENAZ_MS = 1000;
const SKOP_GUNLUK_AZAMI_MS = 3600000;
/* Elle yakalamanin reddi bu kadar sonra da gelebilir: NORMAL kipte tetik beklenir (osiloYakala'nin
   20 s / osiloOtomatik'in 30 s tavaniyla ayni) — `! tetiklenemedi` o zaman gelir. */
const SKOP_RET_PENCERESI_MS = 30000;

/** Gunluk komutu: {kip: 'tetik'} -> Gt0; {kip: 'aralik', saniye} -> Gt<ms> (1 s … 1 sa). */
function skopGunlukKomutu({ kip, saniye } = {}) {
  if (kip === 'tetik') return { komut: 'Gt0' };
  if (kip !== 'aralik') return { hata: 'os.hata_kip' };
  const s = typeof saniye === 'string' ? Number(saniye.replace(',', '.')) : Number(saniye);
  if (saniye === '' || saniye === null || !Number.isFinite(s)) return { hata: 'os.hata_aralik' };
  const ms = Math.round(s * 1000);
  if (ms < SKOP_GUNLUK_ENAZ_MS || ms > SKOP_GUNLUK_AZAMI_MS) return { hata: 'os.hata_aralik' };
  return { komut: 'Gt' + ms };
}

/** 3E (OS8): osiloskop ekraninin metinleri (sozluk anahtari duz metin; D8 deseni). */
const OS_METIN = Object.freeze({
  baslik: 'os.baslik', altBaslik: 'os.alt_baslik', denetimler: 'os.denetimler', yakalama: 'os.yakalama',
  yakala: 'os.yakala', yakalaniyor: 'os.yakalaniyor', surekli: 'os.surekli', surekliDur: 'os.surekli_dur',
  surekliIpucu: 'os.surekli_ipucu', otomatik: 'os.otomatik', otomatikIpucu: 'os.otomatik_ipucu',
  zamanTabani: 'os.zaman_tabani', hizlandir: 'os.hizlandir', yavaslat: 'os.yavaslat', tetik: 'os.tetik',
  tetikKip: 'os.tetik_kip', kipOto: 'os.kip_oto', kipNormal: 'os.kip_normal', kipTek: 'os.kip_tek',
  kenar: 'os.kenar', kenarYukselen: 'os.kenar_yukselen', kenarDusen: 'os.kenar_dusen', seviye: 'os.seviye',
  onTetik: 'os.on_tetik', onay: 'os.onay', gunluk: 'os.gunluk', gunlukIpucu: 'os.gunluk_ipucu',
  gunlukHerTetik: 'os.gunluk_her_tetik', gunlukHerN: 'os.gunluk_her_n', gunlukSaniye: 'os.gunluk_saniye',
  gunlukBaslat: 'os.gunluk_baslat', gunlukDurdur: 'os.gunluk_durdur', gunlukElleYok: 'os.gunluk_elle_yok',
  kalCikisi: 'os.kal_cikisi', calKapali: 'os.cal_kapali', gorev: 'os.gorev',
  spektrum: 'os.spektrum', spektrumIpucu: 'os.spektrum_ipucu', pencere: 'os.pencere', pencereHann: 'os.pencere_hann',
  pencereDikdortgen: 'os.pencere_dikdortgen', genlik: 'os.genlik', birimV: 'os.birim_v', birimDbv: 'os.birim_dbv',
  tepeFrekans: 'os.tepe_frekans', harmonik: 'os.harmonik', frekans: 'os.frekans', thd: 'os.thd',
  spektrumYok: 'os.spektrum_yok', tepeYok: 'os.tepe_yok', yukleniyor: 'os.yukleniyor', yuklenemedi: 'os.yuklenemedi',
  arsiv: 'os.arsiv', canliyaDon: 'os.canliya_don', kaydaDon: 'os.kayda_don', kayitliYukleniyor: 'os.kayitli_yukleniyor',
  tuvalEtiket: 'os.tuval_etiket', spektrumEtiket: 'os.spektrum_etiket', tuvalBos: 'os.tuval_bos',
  harmonikTablo: 'os.harmonik_tablo', egriKayitta: 'os.egri_kayitta', egriYokKayitta: 'os.egri_yok_kayitta',
  spektrumKlavye: 'os.spektrum_klavye',
});

/* ═══ 3F — PIL TESTI (PL1-PL7) ═════════════════════════════════════════
   EMNIYET VE DURUM BURADA (PU1): `p0` (acil serit + Pil sekmesi), durum
   makinesi, yoklama, `/pil` ayristirmasi, kartin pil satirlari ve komut
   ureticileri app.js'te — Pil sekmesinin modulu (ekran/pil.js: egri +
   kayit kaynagi) INMESE de DURDUR ve acil serit calisir. Modul ekran ilk
   gorunur olunca `import()` ile iner (U1/E1 deseni).
   PL4 YOKLAMA: `/pil?sira=` SUREKLI yalniz (bagli ∧ Pil sekmesi ∧ belge
   gorunur ∧ test suruyor) — PIL_YOKLAMA_MS'de bir. Tek seferlik: baglaninca
   (acil serit icin durum), Pil sekmesi acilinca (durum bayatsa), test
   bitince (sekme gorunurse; degilse sekme acilinca). Testin basladigi /
   bittigi kartin KENDILIGINDEN bastigi satirlardan (`* pil testi BASLADI …`;
   SSE her istemciye yayar) — yoklamaya gerek yok.
   Sinirlar FIRMWARE'den (B7 karsilastiriyor): `P` komutu 0.5 … PIL_AZAMI_V
   (pil_test.h), DCIR araligi/darbesi pil_test.h derleme sabitleri (komutu
   YOK — PL1 firmware degismez, formda salt-okur; PU5). */
const PIL_KESME_ENAZ_V = 0.5;
const PIL_KESME_AZAMI_V = 38.5;
const PIL_DCIR_ARALIK_MS = 300000;
const PIL_DCIR_DARBE_MS = 200;
/* PL4: test surerken yoklama araligi (kart 1 Hz nokta kaydediyor; ~2 nokta/istek). */
const PIL_YOKLAMA_MS = 2000;
/* PU4: `P<v>`den sonra kartin `* pil kesme gerilimi` onayi bu kadar beklenir; gelmezse p1 GITMEZ. */
const PIL_KESME_ONAY_MS = 3000;
/* PL5: hazir kesme degerleri (hucre basina; kursun-asit 12 V aku). */
const PIL_HAZIR_KESME = Object.freeze([
  Object.freeze({ ad: 'pl.hazir_liion', v: 3.0 }),
  Object.freeze({ ad: 'pl.hazir_kursun', v: 10.5 }),
]);
/* Bir `/pil` yanitinda kalan nokta varsa (yeniden baglanma dolgusu) ayni yoklamada en cok bu kadar istek. */
const PIL_DOLGU_AZAMI = 100;
const PIL_SAKLA = 'olcum.pil.son';

/** PL5: kesme girisi -> `P<v>`; kartin `P` kuraliyla AYNI sinir (0.5 … PIL_AZAMI_V). Virgul ondalik olur. */
function pilKesmeKomutu(giris) {
  const s = String(giris === null || giris === undefined ? '' : giris).trim().replace(',', '.');
  if (!/^\d{1,3}(\.\d{1,4})?$/.test(s)) return { hata: 'pl.hata_kesme' };
  const v = Number(s);
  if (!(v >= PIL_KESME_ENAZ_V) || !(v <= PIL_KESME_AZAMI_V)) return { hata: 'pl.hata_kesme' };
  return { komut: 'P' + v, v };
}

/** PU7: oturuma ad — `Ga<oturum> <ad>`; metin kurali Gn ile ayni (kartin attigi karakter ve
 *  120 bayti asan metin REDDEDILIR; komut <= 175 bayt). */
function pilAdKomutu(oturum, ad) {
  if (!(Number.isInteger(oturum) && oturum > 0)) return { hata: 'pl.hata_ad_oturum' };
  const m = String(ad === null || ad === undefined ? '' : ad).replace(/[\r\n\t]+/g, ' ').trim();
  if (!m) return { hata: 'pl.hata_ad_bos' };
  /* \u0022 cift tirnak, \u005c ters bolu (kayitNotKomutu ile ayni; regex'te ciplak tirnak yok) */
  if (/[\u0022\u005c\u0000-\u001f\u007f]/.test(m)) return { hata: 'pl.hata_ad_karakter' };
  const bayt = utf8Bayt(m);
  if (bayt > NOT_METIN_AZAMI_BAYT) return { hata: 'pl.hata_ad_uzun', bayt };
  return kayitKomutuDenetle('Ga' + oturum + ' ' + m);
}

/** PL4: surekli yoklama kosulu. */
function pilYoklamaKosulu({ bagli = false, gorunum = '', gorunur = true, durum = '' } = {}) {
  return !!bagli && gorunum === 'pil' && gorunur !== false && durum === 'CALISIYOR';
}

/**
 * Kartin pil satirlari (pil_baslat / pil_isle / `p` / `P` komutlari; metinler FIRMWARE'in, B7
 * her birini ino'da arar). Donus {tur, …} ya da null:
 *   basladi {ocv, kesme} · bitti {mah, wh} · durduruldu · calismiyor · sure · reddedildi {hata}
 *   kaydedilmiyor {neden} · kesme {v} · ret (diger `! pil…` / `! P:` reddi) · durum (B satiri)
 */
function pilSatirOlayi(satir) {
  const s = String(satir === null || satir === undefined ? '' : satir).trim();
  let m = /^\* pil testi BASLADI — OCV (-?[\d.]+) V, kesme ([\d.]+) V/.exec(s);
  if (m) return { tur: 'basladi', ocv: Number(m[1]), kesme: Number(m[2]) };
  m = /^\* pil testi BITTI — (-?[\d.]+) mAh, (-?[\d.]+) Wh/.exec(s);
  if (m) return { tur: 'bitti', mah: Number(m[1]), wh: Number(m[2]) };
  if (/^\* pil testi DURDURULDU/.test(s)) return { tur: 'durduruldu' };
  if (/^\* pil testi zaten calismiyor/.test(s)) return { tur: 'calismiyor' };
  if (/^! pil testi: azami sure asildi/.test(s)) return { tur: 'sure' };
  m = /^! pil testi REDDEDILDI: (.*)$/.exec(s);
  if (m) return { tur: 'reddedildi', hata: m[1] };
  m = /^! pil testi KAYDEDILMIYOR — (.*)$/.exec(s);
  if (m) return { tur: 'kaydedilmiyor', neden: m[1] };
  m = /^\* pil kesme gerilimi ([\d.]+) V/.exec(s);
  if (m) return { tur: 'kesme', v: Number(m[1]) };
  if (/^! (pil|P:)/.test(s)) return { tur: 'ret' };
  const b = pilBSatiriCoz(s);
  return b ? { tur: 'durum', ...b } : null;
}

/** `p` komutunun durum satiri (USB / kopru: /pil yok — PU13):
 *  B <durum> <mAh> <Wh> <OCV> <V_son> <kesme> <sure_s> <dcir_ani> <dcir_otr> <dcir_n> <sira> <hata…> */
function pilBSatiriCoz(satir) {
  const p = String(satir === null || satir === undefined ? '' : satir).trim().split(/\s+/);
  if (p[0] !== 'B' || p.length < 13 || !/^[A-Z]+$/.test(p[1])) return null;
  const sayi = p.slice(2, 12).map(Number);
  if (!sayi.every(Number.isFinite)) return null;
  const [mah, wh, ocv, vson, kesme, sureS, dcirAni, dcirOtr, dcirN, sira] = sayi;
  return { durum: p[1], mah, wh, ocv, vson, kesme, sureS, dcirAni, dcirOtr, dcirN, sira, hata: p.slice(12).join(' ') };
}

/** ss:dd:sn (saat 24'u gecebilir); bilinmiyorsa "—". */
function pilSureYaz(ms) {
  if (!Number.isFinite(ms) || ms < 0) return '—';
  const s = Math.floor(ms / 1000);
  const iki = (x) => String(x).padStart(2, '0');
  return `${iki(Math.floor(s / 3600))}:${iki(Math.floor(s / 60) % 60)}:${iki(s % 60)}`;
}

/** PU10: n. DCIR darbesinin testin basindan zamani (ms): kartin kurali — darbe son darbenin
 *  BITISINDEN PIL_DCIR_ARALIK_MS sonra baslar, PIL_DCIR_DARBE_MS surer (± dongu suresi). */
function pilDcirAniMs(no) {
  return Number.isInteger(no) && no > 0 ? no * (PIL_DCIR_ARALIK_MS + PIL_DCIR_DARBE_MS) : NaN;
}

/** PU10: DCIR tablosu satirlari. Girdi [{no, tMs, rAni, rOtr, mah, yaklasik, gorulmedi}] (ohm, mAh).
 *  Gorulmeyen olcumun degerleri "—" (kayitta tam); yoklamadan alinan mAh "≈". */
function pilDcirSatirlari(liste) {
  const mohm = (r) => (Number.isFinite(r) && r !== 0 ? (r * 1000).toFixed(1) + ' mΩ' : '—');
  return (liste || []).slice().sort((a, b) => a.no - b.no).map((d) => ({
    no: d.no,
    zaman: pilSureYaz(Number.isFinite(d.tMs) ? d.tMs : pilDcirAniMs(d.no)),
    rAni: d.gorulmedi ? '—' : mohm(d.rAni),
    rOtr: d.gorulmedi ? '—' : mohm(d.rOtr),
    mah: d.gorulmedi || !Number.isFinite(d.mah) ? '—' : (d.yaklasik ? '≈ ' : '') + d.mah.toFixed(1),
    gorulmedi: !!d.gorulmedi,
  }));
}

/** 3F (PL7): Pil ekraninin metinleri (sozluk anahtari duz metin; D8 deseni). */
const PL_METIN = Object.freeze({
  baslik: 'pl.baslik', durdur: 'pl.durdur', durdurIpucu: 'pl.durdur_ipucu', okumalar: 'pl.okumalar',
  gerilim: 'pl.gerilim', akim: 'pl.akim', kapasite: 'pl.kapasite', enerji: 'pl.enerji', sure: 'pl.sure',
  kesme: 'pl.kesme', kaynakCanli: 'pl.kaynak_canli', kaynakSayac: 'pl.kaynak_sayac', kaynakSaat: 'pl.kaynak_saat',
  kaynakAyar: 'pl.kaynak_ayar', kaynakKayit: 'pl.kaynak_kayit', kaynakSon: 'pl.kaynak_son', yukKesik: 'pl.yuk_kesik',
  bilinmiyor: 'pl.bilinmiyor', grafik: 'pl.grafik', grafikEtiket: 'pl.grafik_etiket', xEksen: 'pl.x_eksen',
  eksenZaman: 'pl.eksen_zaman', eksenMah: 'pl.eksen_mah', grafikKlavye: 'pl.grafik_klavye',
  yukleniyor: 'pl.yukleniyor', yuklenemedi: 'pl.yuklenemedi', egriYok: 'pl.egri_yok', egriSatir: 'pl.egri_satir',
  dcir: 'pl.dcir', dcirNo: 'pl.dcir_no', dcirZaman: 'pl.dcir_zaman', dcirAni: 'pl.dcir_ani', dcirOtr: 'pl.dcir_otr',
  dcirMah: 'pl.dcir_mah', dcirYok: 'pl.dcir_yok', dcirIpucu: 'pl.dcir_ipucu', dcirGorulmedi: 'pl.dcir_gorulmedi',
  parametreler: 'pl.parametreler', ocv: 'pl.ocv', dcirAralik: 'pl.dcir_aralik', dcirSabit: 'pl.dcir_sabit',
  basla: 'pl.basla', kesmeGir: 'pl.kesme_gir', hazir: 'pl.hazir', ad: 'pl.ad', adIpucu: 'pl.ad_ipucu',
  baslat: 'pl.baslat', baslatiliyor: 'pl.baslatiliyor', sonuc: 'pl.sonuc', bitisSebebi: 'pl.bitis_sebebi',
  kayitlardaAc: 'pl.kayitlarda_ac', noktaCsv: 'pl.nokta_csv', pilCsv: 'pl.pil_csv',
  kayitYukleniyor: 'pl.kayit_yukleniyor', kayitEsitleniyor: 'pl.kayit_esitleniyor',
  imlecSil: 'pl.imlec_sil', adGonder: 'pl.ad_gonder',
});

createApp({
  /* 3C (P4): yeni ekran modul olarak; ilk kullanimda iner (yukaridaki not). */
  components: {
    'kayitlar-ekran': defineAsyncComponent({
      loader: () => import('./ekran/kayitlar.js').then((m) => m.KayitlarEkrani),
      /* Modul inmezse (bayat goruntu, kart yeniden basliyor) sekme BOS kalmasin:
         sebep + care (DEVIR 4.15 dersi). Sozluk de o modullerle iniyor — bu
         metin bu yuzden burada. */
      errorComponent: { template: '<p class="hata">Kayıtlar ekranı yüklenemedi (modül inmedi) — kart yeniden başlıyor olabilir; birkaç saniye sonra sayfayı yenileyin.</p>' },
    }),
  },
  data() {
    return {
      /* B22.2: hangi taşıyıcı etkin. `tasiyici` ve `yetenek` bundan
         türetiliyor (computed), böylece kip değişince panel görünürlüğü
         kendiliğinden güncelleniyor. */
      tasiyiciAdi: 'seri',
      kartTaban: '',        // '' = aynı köken; PC'den karta bağlanırken dolu
      kopruAdresi: '',      // kart "köprü şurada" derse
      /* PC köprüsünde N izleyici, BIR sürücü. Kart doğrudan bağlıysa
         hakem yok — o yüzden varsayılan `true`. */
      jeton: '',
      surucuyum: true,
      bagli: false,
      hata: '',
      menzil: null,       // 0 NORMAL, 1 YUKSEK, null bilinmiyor
      gorunum: hashtenGorunum(),   // B27 Aşama 1: #/olcum #/skop #/pil #/ayar #/konsol
      gorunumler: GORUNUMLER,
      /* 3C: Kayitlar ekrani ilk acilista KURULUR (sonra v-show ile canli
         kalir; tuval ve esitleme durumu kaybolmasin). */
      kayitlarAcik: hashtenGorunum() === 'kayitlar',
      /* 3D: Canli'nin grafik modulu (ekran/canli.js) ekran ILK gorunur olunca iner
         (yukaridaki Kayitlar deseni). `canliAcik` o ani isaretler; okuma kartlari
         ve kayit denetimi modulu BEKLEMEZ (app.js'te). */
      canliAcik: hashtenGorunum() === 'canli',
      canliDurum: 'bekliyor',      // 'bekliyor' | 'yukleniyor' | 'hazir' | 'yuklenemedi'
      canliBilgi: null,            // ekran/canli.js: {lejant, pencere, okuma, donmus}
      donmus: false,               // D3: "dondur" — imlec + yakinlastirma
      sagEksen: 'akim',            // K1 (ekran/canli.js): sag eksen tek birim
      /* 3D (D1): sol serit dar ekranda (<= 900 px) cekmece. */
      cekmeceAcik: false,
      /* D8: dil (3H secicisi gelene dek localStorage `olcum.dil`; 3C ile ayni anahtar) */
      dil: 'tr',
      afisSurum: '',               // D1: acilis afisinin asama/surum metni (gorulduyse)
      kopruda: false,              // D1: sayfa PC koprusu uzerinden (kopruYokla /durum)
      /* ── 3D — KAYIT DURUMU (pasif; D4-D7) ── */
      kayit: { g: null, ga: null, gt: null, gp: null },
      kayitGZaman: 0,              // son G satirinin (tarayici) zamani
      kayitBas: null,              // {oturum, zaman}: panelin GORDUGU baslangic
      kayitGozlem: [],             // [{t, d}]: aktif oturumda onaysiz (binde) gozlemleri (D6)
      kayitNoktaGozlem: [],        // [{t, n}]: ilk ve son nokta gozlemi (olculen hiz)
      kayitIstek: null,            // {hiz, zaman}: bu sekmenin son Gb'si
      kayitHizBilgi: null,         // {oturum, hiz, kaynak: 'istek'|'plan'|'ayrinti'}
      kayitUyari: null,            // {tur: 'panel'|'kart', metin}
      kayitKomutZamani: 0,
      yenidenBekleyen: null,       // kart yeniden basladi: onceki G (kayit surdu mu)
      olaylar: [],                 // D7: [{saat, metin, tur}] en yeni basta, <= 20
      baslatHiz: 200,
      kayitHizlari: KAYIT_HIZLARI,
      notAcik: false, notMetni: '', notGonderiliyor: false,
      /* WIG: iki asamali onay — silahli eylemin adi (null = yok); bkz. onayIste */
      onay: null,
      canliDuyuru: '',             // WIG: donmus imlec okumasinin gecikmeli ozeti (aria-live)
      planAcik: false, planBas: '', planSureSa: 1, planSureDk: 0, planHiz: 1000,
      /* 3A (P1): renk takımı SEÇİMİ ('sistem' | 'koyu' | 'acik' | 'onpanel').
         ⚠ `gorunum` (SEKME) ile karıştırma — bkz. ekran/tema.js. Değer
         mounted()'ta kayıtlı seçimden geliyor; uygulama ve saklama
         `ekran/tema.js`te, burada yalnızca düğmelerin durumu. */
      temaSecim: null,
      temaSecenekleri: TEMALAR,
      adsDurum: 0,        // B27/K1: bit0 V okunamadi, bit1 I okunamadi
      kartSont: null,     // B27/K5: kartin `?` ile bildirdigi GERCEK sont (ohm)
      hizliHata: '',      // B27/K3: kart 'giris rayda' derse burada
      hizli: null,        // B8 hizli yol olcumu
      otoMenzil: true,

      // anlık ölçüm
      volt: 0, amper: 0, watt: 0, joule: 0, wh: 0, kartMs: 0,
      ornekAdet: 0, sonAralik: 0,
      /* B30 — kalibrasyon cikisi (CAL). Skopun prob dengeleme
         karsiligi: GPIO10'da %50 kare dalga. `calGercek` KARTIN
         bildirdigi frekans — LEDC istenen degeri kirpiyor (7000 -> 6998)
         ve skop olcumu bununla karsilastirilmali, istenenle DEGIL. */
      calHz: 0,
      calGercek: null,
      /* B33: CAL gorev orani (binde). RC suzgecle birlikte panelden
         ayarlanabilir bir DC kaynagi: %0..%100 -> 0..3.3 V. */
      calGorev: 500,
      calCozunurluk: null,
      raporMs: 200,          // B27 A2: tercih (localStorage); kart `r<ms>` ile uyar
      raporSecenekleri: RAPOR_SECENEKLERI,
      kartRapor: null,       // kartin `A rapor=` / `* rapor araligi` dedigi deger

      // geçmiş: { t (sn), v, i, w, e (Wh) } — 3D: ogeler DONUK (Object.freeze):
      // Vue onlari reaktif vekile sarmaz, 36 000 noktalik pencere ucuz taranir.
      gecmis: [],
      ilkMs: null,
      /* 3D: kart yeniden baslayinca `ms` sifirdan basliyor; t AZALMASIN diye
         kaydirma (grafik.js/ozet.js azalmayan t ister). */
      msKaydir: 0,
      pencere: 60,
      gosterV: true,

      // osiloskop
      osilo: null,
      osiloBekliyor: false,
      /* 3E: spektrum + kayitli yakalama modulu (ekran/osiloskop.js) ekran ILK acilinca iner. */
      skopAcik: hashtenGorunum() === 'skop',
      skopDurum: 'bekliyor',       // 'bekliyor' | 'yukleniyor' | 'hazir' | 'yuklenemedi'
      spektrumBilgi: null,         // SpektrumGrafik.ciz bilgisi (tepe, harmonikler, thd, df …)
      spektrumPencere: 'hann',     // OS3: 'hann' | 'dikdortgen' (tercih)
      spektrumBirim: 'v',          // OS3: 'v' (tepe) | 'dbv' (tercih)
      skopKayitli: null,           // OS6: {oturum, kimlik, no, sira, gecenMs, unixMs, ad, egri}
      skopKayitliHata: '',
      skopKayitliYukleniyor: false,
      gunlukKip: 'tetik',          // OS5: 'tetik' (Gt0) | 'aralik' (Gt<ms>)
      gunlukSaniye: 10,
      skopGunlukUyari: null,       // {tur: 'panel'|'kart', metin}
      skopGunlukZamani: 0,
      skopKomutZamani: 0,          // son elle yakalama komutu (ret penceresi)
      skopYakalamaUyari: '',       // kartin `! skop…` / `! tetiklenemedi` reddi, oldugu gibi
      skopIkiliBekle: false,  // B40: `tB` gönderildi, onay satırı bekleniyor
      skopIkiliOlcum: null,   // B43: ikili yakalamanın `M` satırı (onaydan ÖNCE gelir)
      osiloTopla: null,
      skopAyar: null,        // kartın bildirdiği T satırı
      skopTdiv: 5,           // zaman tabanı indeksi (0..11)
      skopKip: 0,            // 0 oto · 1 normal · 2 tek atış
      skopOnay: 2,           // B47: 1 tek örnek · 2 iki örnek (gürültü reddi); kart varsayılanı 2
      skopKenar: 0,          // 0 yükselen · 1 düşen
      skopEsik: 2048,        // tetik seviyesi, ADC kodu
      skopOn: 25,            // ön-tetik yüzdesi

      // yakınlaştırma — kart değil, GÖRÜNTÜ ayarı (yeniden yakalama gerekmez)
      dikeyOto: true,        // dikey ölçek otomatik mi
      dikeyZoom: 1,          // elle kipte büyütme katsayısı
      dikeyKaydir: 0,        // -1..+1, ekran yüksekliğinin oranı
      yatayZoom: 1,          // kayıt içinde kaç kat yakınlaştırıldı
      yatayKaydir: 0.5,      // görünen pencerenin kayıt içindeki merkezi

      // sürekli yakalama (gerçek osiloskoplardaki RUN/STOP)
      surekli: false,
      surekliZaman: null,
      surekliSayac: 0,       // saniyedeki yakalama sayısı için
      surekliHiz: 0,
      surekliT0: 0,

      /* ── skop arşivi (B35) — GERİYE DÖNÜK KAYIT ───────────────────
         🔴 Kayıt tarayıcıda DEĞİL, PC köprüsünün disk günlüğünde. Pil
            eğrisi IndexedDB'de duruyor ve dosyanın kendi yorumu bunu
            dürüstçe söylüyor: "tarayıcı verilerini temizle" denince
            gider. Bir ölçüm kaydının ömrü tarayıcı tercihine bağlı
            olamaz. Ayrıca kayıt HAM ADC KODU olarak duruyor: B34'te
            bulunan doğrusalsızlığın düzeltmesi ileride karara
            bağlandığında ESKİ kayıtlara da uygulanabilsin.
         ⚠ Yalnızca köprü kipinde var. Kart `/durum` ucunu hiç açmıyor,
           yani o ucun yanıtı zaten köprünün imzası. */
      skopArsivVar: false,
      skopKayitlar: [],
      skopGunler: [],
      skopGun: '',
      skopKayitMesgul: false,
      skopAcikKayit: null,   // {gun, ms} — şu an çizilen arşiv kaydı
      skopArsivtenAciliyor: false,   // osiloBitir() listeyi tazelemesin

      /* ── skop gerilim ekseni kalibrasyonu (B36) ───────────────────
         🔴 Kart ham ADC kodunu SABİT bir çarpanla volta çeviriyordu;
            B34 bu varsayımın ölçüldüğünde tutmadığını gösterdi. Kartın
            `CT` komutu çipin kendi eFuse eğrisini veriyor ve düzeltme
            ÇİZİM ANINDA uygulanıyor.
         ⚠ Tablo KARTTAN geliyor, buraya gömülü DEĞİL: her yonganın
           eğrisi kendisine ait. Gömülseydi başka bir karta yanlış
           düzeltme uygulanırdı.
         ⚠ Kayıtlar ham kod tuttuğu için (B35) düzeltme ESKİ
           yakalamalara da uygulanıyor. */
      skopKal: null,        // {oran, ofset, tavanMv, kod[], mv[]}

      // fare ile kaydırma
      suruk: null,

      // demo kipi
      demoSinyal: 'sinus50',
      demoZaman: null,
      demoKurulu: false,   // B27 A2: demo kurulumu tek sefer (bkz. demoVeri)
      /* 🔴 B27 A2: BAĞLANTIYI HANGİ TAŞIYICI AÇTI. Önce "eski seçim"
         varsayılıyordu ve bu yanlıştı: `demoVeri()` önce `tasiyiciAdi`yi
         'demo' yapıp sonra `bagli`yi açıyor, watch ise ondan SONRA
         koşuyor — yani açılan demo bağlantısını "eski taşıyıcı" sanıp
         kapatıyordu. Demo akışı ilk 300 noktadan sonra susuyordu
         (headless render yakaladı). Bağlı taşıyıcı artık AÇIKÇA tutuluyor. */
      bagliTasiyici: null,
      demoMs: 0,
      demoJ: 0,

      // denetimler
      sontSecim: '10',
      /* B20: sebeke frekansi ve faz kalibrasyonu. B17 bunlari firmware'e
         ekledi ama arayuze koymadi; kullanici yalnizca seri porttan
         ayarlayabiliyordu. Fabrika ayari 50 Hz — DC olcumunde guc %82
         yuksek okunur ve arayuzde bunu duzeltecek bir sey yoktu. */
      sebekeHz: '50',
      fazKal: '',
      fazHata: '',          // WIG: faz hatasi ALANIN yaninda (en ustteki genel kutuda degil)
      sifirlaOnay: false,
      agSsid: '',
      agSifre: '',
      agWebSifre: '',
      kalibV: '', kalibA: '',
      elleKomut: '',

      // günlük
      gunluk: [],

      /* ── B21 PİL KAPASİTE TESTİ ───────────────────────────────────
         Kart son 1.5 saati tutuyor (PSRAM varsa 24 saat); TARAYICI
         IndexedDB'de SINIRSIZ biriktiriyor. Sekme kapanıp açılınca
         "bende N'e kadar var" deyip kalanını istiyoruz. Kartın tuttuğu
         pencereden daha uzun kapalı kalınırsa BOŞLUK olur ve grafikte
         AÇIKÇA işaretlenir — sessizce interpolasyon YAPILMAZ.
         mAh/Wh sayaçları KARTTA biriktiği için boşluk olsa bile
         TOPLAM KAPASİTE doğru kalır. */
      pilDurum: 'BEKLEMEDE',
      pilHata: '-',
      pilZaman: null,      // 3F (PL4): yoklama zamanlayicisi — YALNIZ pilYoklamaAcik iken
      pilMah: 0, pilWh: 0, pilCoulomb: 0,
      pilOcv: 0, pilVson: 0, pilKesme: 3.0,
      pilDcirAni: 0, pilDcirOtr: 0, pilDcirN: 0,
      pilSira: 0,          // kartın ürettiği toplam nokta
      pilYerelSira: 0,     // bizde olan son sıra
      pilNokta: [],        // {sira, ms, v, i} · boşlukta {sira, bosluk:true} — ogeler DONUK (Vue sarmaz)
      pilBosluk: 0,
      pilHataMetni: '',        // kaç nokta kayboldu
      pilKesmeGiris: '',
      /* ── 3F — Pil testi ekrani (PL1-PL7; uygulama kararlari PU1-PU17) ── */
      pilKesmeBilinen: false,      // kartin kesmesi/sayaclari okundu mu (/pil, B satiri, kart satiri)
      pilSonMs: null,              // kartin son noktasinin ms'i (testin basindan) — "gecen sure"
      pilTazeZaman: 0,             // son /pil (ya da B) yanitinin tarayici zamani
      pilBayat: true,              // durum degisti ama son hali alinmadi (PL4: sekme acilinca bir kez)
      sayfaGorunur: true,          // PL4: belge gorunur mu (visibilitychange)
      pilAcik: hashtenGorunum() === 'pil',   // ekran/pil.js ilk gorunurlukte iner
      pilModDurum: 'bekliyor',     // 'bekliyor' | 'yukleniyor' | 'hazir' | 'yuklenemedi'
      pilBilgi: null,              // ekran/pil.js PilGrafik bilgisi {var, okuma, eksenUyari, xSon}
      pilEksen: 'zaman',           // PL3: 'zaman' | 'mah' (tercih)
      pilOturum: null,             // PU6: {no, gorulmedi} — PIL oturumunun numarasi (G satirindan)
      pilOturumBekle: null,        // {onceki, zaman}: BASLADI goruldu, PIL oturumu G'de bekleniyor
      pilKayitYok: '',             // `! pil testi KAYDEDILMIYOR — <neden>`
      pilDcirListe: [],            // PU10: [{no, tMs, rAni, rOtr, mah, yaklasik, gorulmedi}]
      pilAd: '', pilAdBekleyen: '',
      pilUyari: null,              // {tur: 'panel'|'kart', metin} — PL5 ret satiri (E9 deseni)
      pilKomutZamani: 0,
      pilBaslatiliyor: false,
      pilKayitOzet: null,          // PU11: kayit kaynagi ozeti {oturum, kimlik, sonuc, ayar, sebep, dcir}
      pilKayitDurum: '',           // '' | 'yukleniyor' | 'esitleniyor' | 'yok' | 'hata'
      pilKayitMesaj: '',
      pilDuyuru: '',               // PL7: durum degisimi duyurusu (aria-live)
      saatTik: 0,                  // saniyelik saat (acil seritteki degerin yasi); setTimeout zinciri
    };
  },

  computed: {
    /* B22.2 — TAŞIYICI ve YETENEK.
       `yetenek` arayüzün hangi paneli açacağını söyleyen tek kaynak.
       🔴 Kural: yetenek yoksa düğme GÖRÜNMEZ ama NEDENİ görünür. Ölü
       düğme bırakmak DEVIR 4.15'in ta kendisiydi — üç düğme sessizce
       çalışmıyordu ve kullanıcı sebebini hiçbir yerden göremiyordu. */
    tasiyici() { return TASIYICILAR[this.tasiyiciAdi] || TasiyiciSeri; },
    yetenek() { return this.tasiyici.yetenek; },
    destekli() { return this.tasiyici.destekli(); },
    /* Bu kipte neden bağlanılamadığını SÖYLE — boş ekran bırakma. */
    desteksizNeden() {
      if (this.destekli) return '';
      if (this.tasiyiciAdi === 'seri') {
        /* 🔴 B26: SEBEBİ DOĞRU SÖYLE. Chrome/Edge Web Serial'i destekler
           ama YALNIZCA güvenli bağlamda: `navigator.serial` http://<ip>
           ya da http://olcum.local üzerinde TANIMSIZDIR. Eski metin bunu
           "tarayıcın desteklemiyor" diye okutuyordu ve kullanıcı Chrome'da
           olduğu hâlde yanlış yere bakıyordu. */
        if (typeof window !== 'undefined' && window.isSecureContext === false) {
          return 'Bu sayfa güvenli bağlamda değil, o yüzden Web Serial '
               + 'kapalı — tarayıcının suçu değil. Web Serial yalnızca '
               + 'https:// ya da http://localhost üzerinde çalışır. Sayfa '
               + 'kartın kendisinden geldiğine göre doğru kip WiFi (akış); '
               + 'yukarıdan onu seçin.';
        }
        return 'Bu tarayıcı Web Serial desteklemiyor. Chrome veya Edge '
             + 'gerekiyor; telefonda hiçbir tarayıcı desteklemiyor — '
             + 'telefondan bağlanmak için WiFi (akış) kipini seçin.';
      }
      if (this.tasiyiciAdi === 'akis') {
        return 'Bu tarayıcı EventSource desteklemiyor.';
      }
      return 'Demo kartı yüklenmedi — adrese ?demo ekleyin.';
    },
    gecmisAciklama() {
      const s = this.yetenek.gecmis_s;
      if (!s) return 'Geçmiş yalnızca bu sekmede tutuluyor (kart tamponu yok).';
      return 'Kart ' + (s / 3600).toFixed(0) + ' saatlik tamponu tutuyor; '
           + 'tarayıcı kopukluğu sonrası eksikler geri alınıyor.';
    },

    demo() { return this.tasiyiciAdi === 'demo'; },

    /* ═══ 3D — KABUK + CANLI ═══════════════════════════════════════════ */
    /** D8: sozluk metinleri (`kb.` + `cn.`). */
    m() { return { ...metinHaritasi(KB_METIN, this.dil), ...metinHaritasi(CN_METIN, this.dil) }; },
    /** D1: baglanti kipi — taşıyıcıdan; akışta köprü `/durum`la ayrılıyor. */
    baglantiKipi() {
      const a = this.bagliTasiyici || this.tasiyiciAdi;
      if (a === 'demo') return 'demo';
      if (a === 'seri') return 'usb';
      return this.kopruda ? 'kopru' : 'wifi';
    },
    baglantiYazi() {
      if (!this.bagli) return this.m.cevrimdisi;
      const kip = { usb: 'kb.kip_usb', wifi: 'kb.kip_wifi', kopru: 'kb.kip_kopru', demo: 'kb.kip_demo' };
      return ceviri('kb.cevrimici', this.dil, { kip: ceviri(kip[this.baglantiKipi], this.dil) });
    },
    /** D1: şeridin alt satırı: kartın yeri · afişteki sürüm (görüldüyse). */
    seritAlt() {
      let yer = '';
      if (this.baglantiKipi === 'usb') yer = 'USB';
      else if (this.baglantiKipi === 'demo') yer = 'demo';
      else {
        const m = /^https?:\/\/([^/]+)/.exec(tabanTam(this.kartTaban));
        yer = m ? m[1] : (typeof location !== 'undefined' ? location.host : '');
      }
      return [yer, this.afisSurum].filter(Boolean).join(' · ');
    },
    /** D1 alt bilgi: eşitlenmemiş oran — `G` satırının `onaysiz` alanı (binde). */
    esitlenmemisYazi() {
      const g = this.kayit.g;
      if (!g) return this.bagli ? this.m.esitlenmemisYok : this.m.esitlenmemisBagliDegil;
      return ceviri('kb.esitlenmemis', this.dil, { oran: (g.onaysiz / 10).toFixed(1) });
    },
    menzilKisa() {
      if (this.menzil === null) return '';
      return this.menzil === 1 ? '±614 V' : '±32 V';
    },
    /** D2: her okuma kartının altında son 10 s'nin min … maks'ı (canlı örneklerden). */
    onSaniye() {
      const bicimle = {
        v: (x) => this.bicim(x, 3) + ' V',
        i: (x) => this.olcekliYaz(x, this.akimBirim, 'A'),
        w: (x) => this.olcekliYaz(x, this.gucBirim, 'W'),
        e: (x) => this.olcekliYaz(x, this.enerjiBirim, 'Wh'),
      };
      const r = {};
      for (const alan of ['v', 'i', 'w', 'e']) {
        const a = sonAralikMinMaks(this.gecmis, alan, ON_SANIYE);
        r[alan] = a ? ceviri('cn.on_saniye', this.dil, { min: bicimle[alan](a.min), maks: bicimle[alan](a.maks) })
                    : this.m.onSaniyeYok;
      }
      return r;
    },
    enerjiGoster() {
      const e = Math.abs(this.wh);
      if (e >= 1) return this.bicim(this.wh, 4);
      if (e >= 1e-3) return this.bicim(this.wh * 1e3, 3);
      return this.bicim(this.wh * 1e6, 1);
    },
    enerjiBirim() {
      const e = Math.abs(this.wh);
      return e >= 1 ? 'Wh' : e >= 1e-3 ? 'mWh' : 'µWh';
    },
    /* ── 3D kayıt durumu (D6) ── */
    kayitAktif() { return !!(this.kayit.g && this.kayit.g.durum === KDR.KAYIT); },
    /** Kayıt komutları: bağlı VE sürücü (köprüde izleyici komut gönderemez). */
    kayitKomutAcik() { return this.bagli && this.surucuyum; },
    kayitDurumYazi() {
      const g = this.kayit.g;
      return g ? ceviriKod('kayit.durum.', g.durum, this.dil) : this.m.kayitBilinmiyor;
    },
    /** Aralık: bu sekmenin Gb'si / plan / GA (her örnek) — yoksa nokta artışından ÖLÇÜLEN. */
    kayitHiz() {
      const g = this.kayit.g;
      if (!g || g.durum !== KDR.KAYIT) return null;
      const b = this.kayitHizBilgi;
      if (b && b.oturum === g.oturum) return { hiz: b.hiz, kaynak: b.kaynak };
      const n = this.kayitNoktaGozlem;
      if (n.length === 2 && n[1].t - n[0].t >= 10000 && n[1].n > n[0].n) {
        return { hiz: (n[1].t - n[0].t) / (n[1].n - n[0].n), kaynak: 'olculen' };
      }
      return null;
    },
    kayitHizYazi() {
      const h = this.kayitHiz;
      if (!h) return '';
      const y = this.hizYazi(h.hiz);
      return h.kaynak === 'olculen' ? ceviri('cn.hiz_olculen', this.dil, { hiz: y }) : y;
    },
    /** Süre: bilinen aralıkta nokta × aralık; değilse panelin gördüğü başlangıçtan. */
    kayitSureMs() {
      const g = this.kayit.g;
      if (!this.kayitAktif) return null;
      const h = this.kayitHiz;
      if (h && h.hiz > 0 && h.kaynak !== 'olculen') return g.nokta * h.hiz;
      if (this.kayitBas && this.kayitBas.oturum === g.oturum) return this.kayitGZaman - this.kayitBas.zaman;
      if (h && h.hiz > 0) return g.nokta * h.hiz;
      return null;
    },
    kayitSureYazi() {
      const ms = this.kayitSureMs;
      return ms === null ? '—' : this.saatYazi(ms);
    },
    kayitOturumYazi() {
      const g = this.kayit.g;
      return g ? ceviri('cn.oturum', this.dil, { oturum: g.oturum }) : '';
    },
    kayitNoktaYazi() {
      const g = this.kayit.g;
      if (!g) return '';
      const ayrinti = this.kayitHiz && this.kayitHiz.hiz === 0;
      /* WIG: toLocaleString('tr-TR') '.' ile gruplardi ("12.345 nokta" = "12.345 V" gibi
         okunuyordu; panelde '.' ondalik ayraci). Dar bolunmez bosluk (U+202F). */
      const n = String(g.nokta).replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f');
      return ceviri(ayrinti ? 'cn.ornek' : 'cn.nokta', this.dil, { nokta: n });
    },
    kayitDolulukYazi() {
      const g = this.kayit.g;
      if (!g) return '';
      return ceviri('cn.doluluk', this.dil, { doluluk: (g.doluluk / 10).toFixed(1), onaysiz: (g.onaysiz / 10).toFixed(1) });
    },
    kayitKalan() { return kalanTahmin(this.kayitGozlem); },
    kayitKalanYazi() {
      const k = this.kayitKalan;
      if (k.durum === 'hesaplaniyor') return this.m.kalanHesap;
      return ceviri(k.durum === 'yaklasik' ? 'cn.kalan_yaklasik' : 'cn.kalan_enaz', this.dil,
        { sure: this.kalanSureYazi(k.ms) });
    },
    kayitDusenYazi() {
      const g = this.kayit.g;
      return g && g.dusen > 0 ? ceviri('cn.dusen', this.dil, { n: g.dusen }) : '';
    },
    planYazi() {
      const p = this.kayit.gp;
      if (!p || p.durum === PLAN.YOK) return this.m.planYok;
      const durum = ceviri('cn.plan_durum', this.dil, { durum: ceviriKod('plan.durum.', p.durum, this.dil) });
      if (!p.bas_unix) return durum;
      const ayrinti = ceviri('cn.plan_ayrinti', this.dil, {
        bas: this.tarihYazi(p.bas_unix),
        sure: p.sure_s ? this.kalanSureYazi(p.sure_s * 1000) : this.m.planSuresiz,
        hiz: this.hizYazi(p.hiz_ms),
      });
      return durum + ' · ' + ayrinti;
    },
    skopGunlukYazi() {
      const t = this.kayit.gt;
      return t && t.etkin ? ceviri('cn.skop_gunlugu', this.dil, { n: t.yakalama }) : '';
    },
    /* ═══ 3E — OSILOSKOP ═══════════════════════════════════════════════ */
    /** OS8: osiloskop metinleri (sozluk `os.`). */
    os() { return metinHaritasi(OS_METIN, this.dil); },
    /** OS5: gunluk suruyor mu — PASIF `GT` satirindan (kart elle yakalamayi reddeder). */
    skopGunlukAktif() { return !!(this.kayit.gt && this.kayit.gt.etkin); },
    skopGunlukDurumYazi() {
      const t = this.kayit.gt;
      if (!t) return this.metin('os.gunluk_bilinmiyor');
      if (!t.etkin) return this.metin('os.gunluk_kapali');
      const s = t.aralik_ms
        ? this.metin('os.gunluk_aralik_suruyor', { aralik: this.hizYazi(t.aralik_ms), n: t.yakalama })
        : this.metin('os.gunluk_her_tetik_suruyor', { n: t.yakalama });
      return t.yazilamayan > 0 ? s + ' · ' + this.metin('os.gunluk_yazilamayan', { n: t.yazilamayan }) : s;
    },
    /** OS4: olcum kutusunun KAYNAGI — canli `M` satiri / panel (kayitli, skopOlcKart) / kopru arsivi. */
    skopOlcumKaynak() {
      if (this.skopKayitli) return 'panel';
      if (this.skopAcikKayit) return 'arsiv';
      return 'kart';
    },
    skopOlcumKaynakYazi() {
      return this.metin({ kart: 'os.kaynak_kart', panel: 'os.kaynak_panel', arsiv: 'os.kaynak_arsiv' }[this.skopOlcumKaynak]);
    },
    /** OS6: ARSIV seridinin metni. */
    skopKayitliYazi() {
      const k = this.skopKayitli;
      if (!k) return '';
      let zaman = this.metin('os.zaman_yok');
      if (Number.isFinite(k.unixMs)) zaman = this.tarihYazi(Math.floor(k.unixMs / 1000));
      else if (Number.isFinite(k.gecenMs)) zaman = this.metin('os.saatsiz', { sure: this.saatYazi(k.gecenMs) });
      return this.metin('os.kayitli_serit', { oturum: k.oturum, no: k.no, zaman });
    },
    skopKayitAdresi() {
      const k = this.skopKayitli;
      return k ? '#/kayit/' + k.oturum + (k.kimlik === null || k.kimlik === undefined ? '' : '@' + k.kimlik) : '#/kayitlar';
    },
    /** OS3: harmonik tablosu (n, f, genlik V tepe, dBV) — spektrum modulunun bilgisinden. */
    spektrumSatirlari() {
      const b = this.spektrumBilgi;
      if (!b || !b.var) return [];
      /* `taban`: komsulukta yerel tepe yok — sizinti tabani, genlik bir UST SINIR (≤) */
      return b.harmonikler.map((h, j) => (h ? {
        n: h.n, f: muh(h.f, 'Hz', 3), taban: !!h.taban,
        v: (h.taban ? '≤ ' : '') + h.genlik.toFixed(4) + ' V',
        db: (h.taban ? '≤ ' : '') + (20 * Math.log10(Math.max(h.genlik, 1e-6))).toFixed(1) + ' dBV',
      } : { n: j + 1, f: '—', v: '—', db: '—', taban: false }));
    },
    spektrumOzet() {
      const b = this.spektrumBilgi;
      if (!b || !b.var) return null;
      return {
        tepe: b.tepe ? muh(b.tepe.f, 'Hz', 3) : null,
        tepeGenlik: b.tepe ? b.tepe.genlik.toFixed(4) + ' V' : '',
        thd: Number.isFinite(b.thd) ? (100 * b.thd).toFixed(2) + ' %' : '—',
        dc: this.metin('os.dc', { v: Number.isFinite(b.dc) ? b.dc.toFixed(3) + ' V' : '—' }),
        cozunurluk: this.metin('os.cozunurluk', { df: muh(b.df, 'Hz', 2), n: b.n, nfft: b.nfft }),
        /* imlec okumasi (A/B): Hz + secili birimde genlik */
        imlec: (b.imlec || []).map((i) => i.ad + ': ' + muh(i.f, 'Hz', 3) + ' · '
          + (b.birim === 'dbv' ? i.deger.toFixed(1) + ' dBV' : i.deger.toFixed(4) + ' V')).join('   '),
      };
    },
    notBayt() { return utf8Bayt(String(this.notMetni || '').trim()); },
    notBaytYazi() {
      return ceviri('cn.not_bayt', this.dil, { bayt: this.notBayt, azami: NOT_METIN_AZAMI_BAYT });
    },
    /* ── 3D canlı grafik lejantı + dondurulmuş okuma (ekran/canli.js'ten) ── */
    canliLejant() {
      const b = this.canliBilgi;
      if (!b || !b.lejant) return [];
      return b.lejant.map((l) => ({ ad: l.ad, renk: l.renk, birim: l.birim, metin: this.lejantMetni(l) }));
    },
    canliPencereVeri() {
      const b = this.canliBilgi;
      return b ? JSON.stringify({ ...b.pencere, donmus: b.donmus }) : '';
    },
    canliOkuma() {
      const b = this.canliBilgi;
      const o = b && b.okuma;
      if (!o) return null;
      const kn = (ad) => o.kanallar.find((k) => k.ad === ad) || null;
      const deger = (k, uc) => (k && k[uc] ? k[uc].deger : NaN);
      const satir = [];
      const zaman = (t) => (Number.isFinite(t) ? this.zamanFarkYazi(t - b.pencere.koken) : '—');
      satir.push({ ad: 'A', d: zaman(o.tA) }, { ad: 'B', d: zaman(o.tB) });
      if (Number.isFinite(o.dt)) satir.push({ ad: this.m.okumaDt, d: this.zamanFarkYazi(o.dt) });
      for (const [ad, alan, birim] of [['V', 'v', 'V'], ['I', 'i', 'A'], ['W', 'w', 'W']]) {
        const k = kn(ad);
        if (!k || !(Number.isFinite(deger(k, 'a')) || Number.isFinite(deger(k, 'b')))) continue;
        const f = (x) => (Number.isFinite(x) ? x.toFixed(alan === 'v' ? 3 : 4) + ' ' + birim : '—');
        satir.push({ ad: ad + ' A/B', d: f(deger(k, 'a')) + ' → ' + f(deger(k, 'b')), renk: alan });
      }
      if (Number.isFinite(o.dV)) satir.push({ ad: this.m.okumaDv, d: o.dV.toFixed(4) + ' V', renk: 'v' });
      if (Number.isFinite(o.ortI)) satir.push({ ad: this.m.okumaOrtI, d: o.ortI.toFixed(5) + ' A', renk: 'i' });
      if (o.enerji) {
        satir.push({ ad: this.m.okumaYuk, d: o.enerji.mah.toFixed(4) + ' mAh' });
        satir.push({ ad: this.m.okumaEnerji, d: o.enerji.wh.toFixed(6) + ' Wh', renk: 'w' });
      }
      return satir;
    },

    ornekSayisi() { return this.gecmis.length; },

    /* 🔴 B20 — ÖLÇEK DÜZELTMESİNİ GÖRÜNÜR KIL.
       Firmware gücü 1/|H(f)| ile çarpıyor ve bu çarpan 50 Hz'te 1.82.
       Ayar yanlışsa hata sessiz: saf DC'yi 50 Hz ayarıyla ölçen kullanıcı
       gücü %82 yüksek okur ve bunu hiçbir yerden göremezdi. Burası ayarı
       ve çarpanı ekrana yazıyor, ölçülen akıma bakıp tutarsızlık
       şüphesi varsa uyarıyor. */
    sebekeUyari() {
      const f = parseFloat(this.sebekeHz);
      if (!isFinite(f)) return '';
      if (f <= 0) {
        return 'Ölçek düzeltmesi KAPALI (DC). AC ölçerken güç |H|² kadar '
             + 'düşük okunur — 50 Hz\'te yaklaşık %45.';
      }
      /* τ'lar olcum3.h ile aynı (TAU_NORMAL, TAU_AKIM) — bu bir GÖSTERGE,
         ölçüm değil; firmware kendi çarpanını kendisi hesaplıyor. */
      const w = (tau) => Math.sqrt(1 + Math.pow(2 * Math.PI * f * tau, 2));
      const k = w(0.00285957) * w(0.00290400);
      let s = 'Güce uygulanan ölçek çarpanı: ×' + k.toFixed(3)
            + '  (' + f.toFixed(0) + ' Hz ayarıyla)';
      if (f < 40 || f > 70) {
        s += '  ⚠ 40–70 Hz dışında faz kalibrasyonu (F) geçerliliğini yitirir.';
      }
      s += '  ⚠ DC ölçerken DC seçilmezse güç %82 yüksek okunur.';
      return s;
    },

    /* ─────────────────────────────────────────── osiloskop göstergeleri */

    /* Seçili zaman tabanının okunabilir etiketi: "5 ms/böl" */
    tdivEtiket() {
      const us = SKOP_TDIV[this.skopTdiv];
      return us === undefined ? '—' : muh(us * 1e-6, 's', us < 1000 ? 0 : 1) + '/böl';
    },
    demoSinyaller() {
      return typeof SahteKart !== 'undefined' ? SahteKart.sinyaller : {};
    },
    /* Yatay yakınlaştırmadan sonra ekranda görünen örnek aralığı.
       Bu, kartı yeniden tetiklemeden YAKALANMIŞ kaydın içinde gezinmek —
       gerçek osiloskoplardaki "zoom" penceresinin karşılığı. */
    gorunurAralik() {
      if (!this.osilo) return { bas: 0, son: 0 };
      const n = this.osilo.adet;
      const genislik = Math.max(20, Math.round(n / this.yatayZoom));
      let bas = Math.round(this.yatayKaydir * n - genislik / 2);
      bas = Math.max(0, Math.min(n - genislik, bas));
      return { bas, son: bas + genislik };
    },
    yatayZoomEtiket() {
      return this.yatayZoom <= 1 ? 'tam kayıt'
             : '×' + this.yatayZoom.toFixed(this.yatayZoom < 10 ? 1 : 0);
    },
    dikeyZoomEtiket() {
      return this.dikeyOto ? 'oto'
             : '×' + this.dikeyZoom.toFixed(this.dikeyZoom < 10 ? 1 : 0);
    },
    /* Tetik seviyesini ADC kodu yerine VOLT olarak göster — kullanıcı
       prob ucundaki gerilimi düşünüyor, ham kodu değil. */
    esikVolt() {
      /* B19: skop çift yönlü — kod → volt çevirisi ofsetli.
         Yedek katsayılar da yeni bölücüye göre (100k + 2.7k)/2.7k. */
      return this.kodVolt(this.skopEsik);
    },
    /* Tetik seviyesi sinyalin dışındaysa hiç tetiklenemez — söyle. */
    esikMenzilDisi() {
      if (!this.osilo || !this.osilo.veri.length) return false;
      let mn = this.osilo.veri[0], mx = this.osilo.veri[0];
      for (const v of this.osilo.veri) { if (v < mn) mn = v; if (v > mx) mx = v; }
      return this.skopEsik < mn || this.skopEsik > mx;
    },
    tdivEnHizli() { return this.skopTdiv === 0; },
    tdivEnYavas() { return this.skopTdiv === SKOP_TDIV.length - 1; },

    /* Ekranın kapsadığı toplam süre (10 bölme) */
    skopPencere() {
      if (!this.osilo) return '—';
      return muh(this.osilo.adet / this.osilo.hz, 's', 2);
    },

    /* Kartın hesapladığı otomatik ölçümler — gerçek osiloskopların
       ekran altındaki satırı. Değerler firmware'de skop_olc() ile
       hesaplanıyor (olcum2.h), burada sadece biçimleniyor. */
    skopOlcumler() {
      const o = this.osilo && this.osilo.olcum;
      if (!o) return [];
      const l = [];
      if (o.f > 0) {
        l.push({ ad: 'Frekans', d: muh(o.f, 'Hz', 3), vurgu: true });
        if (Number.isFinite(o.T)) l.push({ ad: 'Periyot', d: muh(o.T, 's', 3) });
      } else {
        l.push({ ad: 'Frekans', d: 'periyodik değil', vurgu: false });
      }
      /* B45: gerilimler TEK birimde. `muh` her değeri kendi önekine
         çeviriyordu — aynı satırda "Vmax 348.200 mV" ile "Vmin -4.092 V"
         yan yana duruyordu ve mV'deki üç ondalık (1 µV) kanalın 29 mV'lik
         adımı yanında sahte hassasiyetti. Skop adımı 29 mV: V ve 3 ondalık
         zaten adımın altında. */
      const V = (x) => (isFinite(x) ? x.toFixed(3) : '—') + ' V';
      l.push({ ad: 'Vpp', d: V(o.Vpp), vurgu: true });
      l.push({ ad: 'Vmax', d: V(o.Vmax) });
      l.push({ ad: 'Vmin', d: V(o.Vmin) });
      l.push({ ad: 'Vort', d: V(o.Vort) });
      l.push({ ad: 'Vrms', d: V(o.Vrms) });
      l.push({ ad: 'Vac (RMS)', d: V(o.Vac) });
      /* B45: eksik alan render'ı düşürmesin — arşivdeki kısa bir `M`
         satırında `duty` yoksa `undefined.toFixed` bütün skop görünümünü
         çökertiyordu (tarayıcı testinde yakalandı). */
      if (o.f > 0 && Number.isFinite(o.duty)) l.push({ ad: 'Duty', d: o.duty.toFixed(1) + ' %' });
      if (o.tr > 0) l.push({ ad: 'Yükselme', d: muh(o.tr, 's', 2) });
      if (o.tf > 0) l.push({ ad: 'Düşme', d: muh(o.tf, 's', 2) });
      if (o.n) l.push({ ad: 'Çevrim', d: String(o.n) });
      return l;
    },

    /* Tetiklenmeden gelen iz YALAN olabilir — kullanıcı bilsin. */
    skopUyari() {
      if (!this.osilo) return '';
      if (!this.osilo.tetiklendi) {
        return 'tetiklenemedi — serbest koşu, iz kayabilir';
      }
      const o = this.osilo.olcum;
      if (o && o.f > 0 && this.osilo.adet && this.osilo.hz) {
        const cevrim = (this.osilo.adet / this.osilo.hz) * o.f;
        if (cevrim < 1.5) return 'ekranda bir tam çevrim yok — zaman tabanını yavaşlat';
        if (cevrim > 60) return 'çok fazla çevrim — zaman tabanını hızlandır';
      }
      return '';
    },

    /* Kart her raporda kaç ham örnek ortalamış — gürültü bastırmanın ölçüsü.
       Beyaz gürültü √N kat azalır. */
    /* B27 A2: iki ayri hiz var ve ikisi de OLCULUYOR, iddia edilmiyor.
       orneklemeHizi = ADC'nin pencere icinde aldigi ornek / pencere suresi
       (kartin ici, ~465/s). guncellemeHizi = D satirlarinin ekrana dusme
       sikligi (1000 / olculen aralik). Eski etiket "463 /sn" yalnizca
       ilkini soyluyordu ve kullanici ekranin o hizda guncellenmedigini
       fark edip haklı olarak sordu. */
    orneklemeHizi() {
      if (!this.ornekAdet || !this.sonAralik) return '—';
      const hz = this.ornekAdet / (this.sonAralik / 1000);
      return (hz >= 1000 ? (hz / 1000).toFixed(1) + 'k' : Math.round(hz)) + ' örnek/s';
    },
    guncellemeHizi() {
      if (!this.sonAralik || this.sonAralik <= 0) return '';
      const hz = 1000 / this.sonAralik;
      // 5 -> "5", 0.2 -> "0.2", 4.98 -> "5": tam sayiya yakinsa ondalik yok
      return String(hz >= 10 ? Math.round(hz) : Math.round(hz * 10) / 10) + ' güncelleme/s';
    },
    gurultuBastirma() {
      return this.ornekAdet ? '√' + this.ornekAdet + ' ≈ ' +
             Math.round(Math.sqrt(this.ornekAdet)) + '× bastırma' : '';
    },

    // Akım ve güç mA/µA, mW/µW olarak ölçeklenir — küçük değerler okunsun.
    akimGoster() {
      const a = Math.abs(this.amper);
      if (a >= 1) return this.bicim(this.amper, 4);
      if (a >= 1e-3) return this.bicim(this.amper * 1e3, 2);
      return this.bicim(this.amper * 1e6, 0);
    },
    akimBirim() {
      const a = Math.abs(this.amper);
      return a >= 1 ? 'A' : a >= 1e-3 ? 'mA' : 'µA';
    },
    gucGoster() {
      const w = Math.abs(this.watt);
      if (w >= 1) return this.bicim(this.watt, 4);
      if (w >= 1e-3) return this.bicim(this.watt * 1e3, 2);
      return this.bicim(this.watt * 1e6, 0);
    },
    gucBirim() {
      const w = Math.abs(this.watt);
      return w >= 1 ? 'W' : w >= 1e-3 ? 'mW' : 'µW';
    },

    /* Etkin gerilim KANALI. Asama 3'te iki ayri bolucu var; hangisinin
       okundugunu bilmek onemli cunku cozunurluk 18 kat farkli:
         NORMAL  +-32.44 V  adim 1.042 mV
         YUKSEK  +-613.7 V  adim 18.78 mV */
    menzilAd() {
      if (this.menzil === null) return '—';
      return this.menzil === 1 ? 'YÜKSEK' : 'NORMAL';
    },
    menzilAralik() {
      if (this.menzil === null) return '';
      return this.menzil === 1 ? '±613.7 V · 18.78 mV' : '±32.44 V · 1.042 mV';
    },

    /* 🔴 B27 A2-b — AKIM KANALININ ÇÖZÜNÜRLÜĞÜ GÖRÜNÜR OLMALI.
       Gerilim kartı menzilini ve adımını yazıyordu, akım kartı YAZMIYORDU.
       Sonuç: kullanıcı boştaki girişte "7 µA" görüp gerçek bir akım sandı.
       Gerçek: şönt ADS'in diferansiyel girişine DOĞRUDAN bağlı, kademe
       sabit ±0.256 V. 0.1 Ω şöntte 1 LSB = 78 µA — yani 7 µA tek ölçümde
       OKUNAMAZ; ekrandaki sayı 96 örneğin ortalaması (kartta ölçüldü:
       ham gürültü tam 1 LSB, ortalamanın std'si 7.9 µA).
       Kaynak kart: `A ... sont=`; menü tercihi yalnızca yedek. */
    /* 3F (PL4): SUREKLI yoklama yalniz (bagli ∧ Pil sekmesi ∧ belge gorunur ∧ test suruyor).
       ESKI (B27 A4): bagliyken HER ZAMAN — bosta 10 s, Pil sekmesinde ya da test surerken 2 s
       (1 sa Canli = 360 istek; karttaki ESKI tek cekirdekte her biri ~15 ms olcum kaybiydi). */
    pilYoklamaAcik() {
      return pilYoklamaKosulu({ bagli: this.bagli, gorunum: this.gorunum, gorunur: this.sayfaGorunur, durum: this.pilDurum });
    },
    /** PU13: durum kaynagi — 'http' (/pil, kartin kendi WiFi'si) · 'satir' (USB / kopru: `p` -> B) · 'demo'. */
    pilKaynak() {
      const a = this.bagliTasiyici || this.tasiyiciAdi;
      if (a === 'demo') return 'demo';
      return a === 'akis' && !this.kopruda ? 'http' : 'satir';
    },
    pl() { return metinHaritasi(PL_METIN, this.dil); },
    pilCalisiyor() { return this.pilDurum === 'CALISIYOR'; },
    pilHazirKesme() { return PIL_HAZIR_KESME; },
    /** PL2 okuma kartlari — HER kartin degeri ve KAYNAGI (PU8). mAh / Wh KARTIN sayaclari
     *  (her ornekte birikir, DCIR darbesi haric) — tarayici hesaplamaz. */
    pilOkumalar() {
      const m = this.pl;
      const k = this.pilKayitOzet && this.pilKayitOzet.sonuc;
      const surerken = this.pilCalisiyor;
      const simdi = this.saatTik || Date.now();
      const bayatS = this.pilTazeZaman ? Math.max(0, Math.round((simdi - this.pilTazeZaman) / 1000)) : null;
      const sayac = (k ? m.kaynakKayit : this.pilKesmeBilinen
        ? (surerken && bayatS !== null && bayatS > 10 ? this.metin('pl.kaynak_sayac_bayat', { s: bayatS }) : m.kaynakSayac) : '');
      const v = surerken
        ? { d: this.voltGecersiz || this.veriYok ? '—' : this.bicim(this.volt, 3), k: m.kaynakCanli }
        : k ? { d: this.bicim(k.v_son, 3), k: m.kaynakKayit }
          : this.pilKesmeBilinen && this.pilVson ? { d: this.bicim(this.pilVson, 3), k: m.kaynakSon } : { d: '—', k: '' };
      const i = surerken
        ? { d: this.amperGecersiz || this.veriYok ? '—' : this.bicim(this.amper, 4), k: m.kaynakCanli }
        : { d: '—', k: this.pilKesmeBilinen || k ? m.yukKesik : '' };
      const mah = k ? k.mah : this.pilKesmeBilinen ? this.pilMah : NaN;
      const wh = k ? k.wh : this.pilKesmeBilinen ? this.pilWh : NaN;
      const sure = k ? k.sure_ms : this.pilSonMs;
      const kesme = this.pilKayitOzet && this.pilKayitOzet.ayar ? this.pilKayitOzet.ayar.kesme_v
        : this.pilKesmeBilinen ? this.pilKesme : NaN;
      return [
        { a: 'v', sinif: 'v', ad: m.gerilim, deger: v.d, birim: 'V', kaynak: v.k },
        { a: 'i', sinif: 'i', ad: m.akim, deger: i.d, birim: 'A', kaynak: i.k },
        { a: 'mah', sinif: 'e', ad: m.kapasite, deger: Number.isFinite(mah) ? this.bicim(mah, 1) : '—', birim: 'mAh', kaynak: sayac },
        { a: 'wh', sinif: 'e', ad: m.enerji, deger: Number.isFinite(wh) ? this.bicim(wh, 3) : '—', birim: 'Wh', kaynak: sayac },
        { a: 'sure', sinif: 'e', ad: m.sure, deger: pilSureYaz(sure), birim: '', kaynak: k ? m.kaynakKayit : Number.isFinite(sure) ? m.kaynakSaat : '' },
        { a: 'kesme', sinif: 'e', ad: m.kesme, deger: Number.isFinite(kesme) ? this.bicim(kesme, 2) : '—', birim: 'V',
          kaynak: Number.isFinite(kesme) ? (this.pilKayitOzet && this.pilKayitOzet.ayar ? m.kaynakKayit : m.kaynakAyar) : m.bilinmiyor },
      ];
    },
    /** PU10: DCIR tablosu — kayit yuklendiyse kaydin OLAY'lari, degilse canli gozlemler. */
    pilDcirTablo() {
      return pilDcirSatirlari(this.pilKayitOzet ? this.pilKayitOzet.dcir : this.pilDcirListe);
    },
    pilDcirGorulmeyen() { return !this.pilKayitOzet && this.pilDcirListe.some((d) => d.gorulmedi); },
    pilOturumYazi() {
      if (!this.pilOturum) return '';
      return this.metin(this.pilOturum.gorulmedi ? 'pl.oturum_tahmin' : 'pl.oturum_no', { no: this.pilOturum.no });
    },
    /** PL6: "Kayıtlar'da aç" — kayit yuklendiyse kimlikli adres (eski akista da dogru kayit). */
    pilKayitAdresi() {
      if (!this.pilOturum) return '';
      const o = this.pilKayitOzet;
      return '#/kayit/' + this.pilOturum.no + (o && o.oturum === this.pilOturum.no && Number.isInteger(o.kimlik) ? '@' + o.kimlik : '');
    },
    /** PL6: son testin sonucu (test surmuyorken, bilgi varsa). Bitis sebebi kaydin BITIR'inden,
     *  yoksa kartin durumundan. */
    pilSonucYazi() {
      if (this.pilCalisiyor) return '';
      const k = this.pilKayitOzet;
      if (k && k.sonuc) return k.sonuc.durumMetin + (k.sonuc.hata ? ' — ' + k.sonuc.hataMetin : '');
      if (!this.pilKesmeBilinen || this.pilDurum === 'BEKLEMEDE') return '';
      return this.pilDurumYazi + (this.pilHata && this.pilHata !== '-' ? ' — ' + this.pilHataYazi : '');
    },
    pilEgriKaynakYazi() {
      if (this.pilKayitOzet) return this.metin('pl.egri_kayit', { no: this.pilKayitOzet.oturum });
      if (this.pilKaynak === 'satir') return this.pl.egriSatir;
      return this.metin('pl.egri_tarayici', { n: this.pilNokta.length });
    },
    pilKayitDurumYazi() {
      const d = this.pilKayitDurum;
      if (!d) return '';
      return d === 'yukleniyor' ? this.pl.kayitYukleniyor : d === 'esitleniyor' ? this.pl.kayitEsitleniyor
        : this.metin(d === 'yok' ? 'pl.kayit_bu_tarayicida_yok' : 'pl.kayit_hata', { no: this.pilOturum ? this.pilOturum.no : '?', mesaj: this.pilKayitMesaj });
    },
    /** PU9: mAh ekseni kurulamadiysa sebebi (zaman eksenine dusuldu). */
    pilEksenUyari() {
      const b = this.pilBilgi;
      return this.pilEksen === 'mah' && b && b.eksenUyari ? this.metin(b.eksenUyari) : '';
    },
    /** PU9: mAh ekseni TARAYICI hesabi — sonu kartin sayaciyla yan yana (ayrisirsa gorunsun). */
    pilMahKarsilastirma() {
      const b = this.pilBilgi;
      if (this.pilEksen !== 'mah' || !b || !Number.isFinite(b.xSon)) return '';
      const k = this.pilKayitOzet && this.pilKayitOzet.sonuc ? this.pilKayitOzet.sonuc.mah : this.pilKesmeBilinen ? this.pilMah : NaN;
      return this.metin('pl.mah_karsilastir', { eksen: b.xSon.toFixed(1), kart: Number.isFinite(k) ? k.toFixed(1) : '—' });
    },
    pilOcvYazi() {
      const a = this.pilKayitOzet && this.pilKayitOzet.ayar;
      const v = a ? a.ocv : this.pilKesmeBilinen && this.pilOcv ? this.pilOcv : NaN;
      return Number.isFinite(v) ? this.bicim(v, 3) + ' V' : '—';
    },
    pilKesmeYazi() {
      const a = this.pilKayitOzet && this.pilKayitOzet.ayar;
      const v = a ? a.kesme_v : this.pilKesmeBilinen ? this.pilKesme : NaN;
      return Number.isFinite(v) ? this.bicim(v, 3) + ' V' : '—';
    },
    /** PU5: DCIR araligi kartin DERLEME SABITI (kayit yuklendiyse kaydin PIL_AYAR'i). */
    pilDcirAralikYazi() {
      const a = this.pilKayitOzet && this.pilKayitOzet.ayar;
      const ar = a ? a.dcir_aralik_ms : PIL_DCIR_ARALIK_MS;
      const d = a ? a.dcir_ms : PIL_DCIR_DARBE_MS;
      return this.metin('pl.dcir_aralik_deger', { dk: Math.round(ar / 6000) / 10, ms: d });
    },
    pilKayitYokYazi() { return this.pilKayitYok ? this.metin('pl.kayit_yok_neden', { neden: this.pilKayitYok }) : ''; },
    pilDcirSonYazi() { return this.metin('pl.dcir_son', { n: this.pilDcirN }); },
    pilKesmeYer() {
      return this.pilKesmeBilinen ? this.metin('pl.kesme_yer', { v: this.bicim(this.pilKesme, 3) }) : '3.0';
    },
    /** Acil seritteki mAh: yoklama Pil sekmesi disinda durdugu icin (PL4) degerin yasini soyler. */
    acilMahYazi() {
      if (!this.pilKesmeBilinen || !this.pilTazeZaman) return '— mAh';
      const s = Math.max(0, Math.round(((this.saatTik || Date.now()) - this.pilTazeZaman) / 1000));
      return this.bicim(this.pilMah, 1) + ' mAh' + (s > 10 ? ' (' + this.metin('pl.once', { sure: pilSureYaz(s * 1000) }) + ')' : '');
    },

    akimMenzilAralik() {
      const sont = this.kartSont !== null ? this.kartSont : parseFloat(this.sontSecim);
      if (!isFinite(sont) || sont <= 0) return '';
      const fs = ADS_PGA_V / sont;             // tam ölçek, A
      const adim = ADS_PGA_V / 32768 / sont;   // 1 LSB, A
      const bicimA = (x) => (x >= 1 ? x.toFixed(2) + ' A'
                           : x >= 1e-3 ? (x * 1e3).toFixed(x >= 1e-2 ? 1 : 2) + ' mA'
                           : (x * 1e6).toFixed(x >= 1e-5 ? 1 : 2) + ' µA');
      return '±' + bicimA(fs) + ' · ' + bicimA(adim);
    },
    /* Guc isareti: negatif guc, yukun KAYNAK durumuna gectigi anlamina
       gelir (geri besleme, sarj olan pil, ters donen bobin akimi).
       Asama 2 bunu hic gosteremiyordu — akimi sifira kirpiyordu. */
    /* B27/K1: ADC yanıt vermediyse sayı ANLAMSIZ — kalibrasyon sabitinin
       ters çevrilmiş hâli. Kart bunu `D` satırının `durum` alanında söylüyor. */
    /* B27/K5 */
    kartSontYazi() {
      if (this.kartSont === null) return 'kart: — (bağlanınca okunur)';
      const r = this.kartSont;
      return 'kart: ' + (r < 1 ? (r * 1000).toFixed(r < 0.1 ? 0 : 1) + ' mΩ' : r + ' Ω');
    },
    sontUyumsuz() {
      if (this.kartSont === null) return false;
      return Math.abs(parseFloat(this.sontSecim) - this.kartSont) > 0.01 * this.kartSont;
    },
    voltGecersiz()  { return (this.adsDurum & 1) !== 0; },
    amperGecersiz() { return (this.adsDurum & 2) !== 0; },
    gucGecersiz()   { return this.voltGecersiz || this.amperGecersiz; },
    /* Guc isareti: negatif guc, yukun KAYNAK durumuna gectigi anlamina
       gelir (geri besleme, sarj olan pil, ters donen bobin akimi).
       B27/K2: ÖLÜ BANT. Girişler GND'deyken gürültü ±10 µW'lık işaret
       değiştiren güç üretiyor ve etiket "yük / kaynak" arasında yanıp
       sönüyordu. 1 mW altı bir "geri besleme" ölçüm değil gürültüdür. */
    gucYon() {
      if (this.gucGecersiz) return '';
      if (!isFinite(this.watt) || Math.abs(this.watt) < 1e-3) return '';
      return this.watt > 0 ? 'yük çekiyor' : 'kaynak — geri besleme';
    },

    /* Hizalayicinin ne kadar fark ettigi. Dirençsel yukte ~0, reaktif
       yukte buyuk. Kullanici duzeltmenin ise yaradigini GORMELI. */
    hizalamaFarki() {
      if (!this.hizli || !isFinite(this.hizli.pHam)) return '';
      const d = this.hizli.p - this.hizli.pHam;
      if (Math.abs(this.hizli.p) < 1e-9) return '';
      const y = d / Math.abs(this.hizli.p) * 100;
      return (Math.abs(y) < 0.05) ? 'hizalama farkı yok (dirençsel)'
                                  : `hizalama ${y > 0 ? '+' : ''}${y.toFixed(2)}% düzeltti`;
    },
    /* WIG: saat "sa" — eski "1s 5dk" panelin geri kalaninda 's' = saniye oldugu icin
       "1 saniye 5 dakika" okunuyordu. */
    sureGoster() {
      if (!this.gecmis.length) return '—';
      const s = Math.floor(this.gecmis[this.gecmis.length - 1].t);
      const sa = Math.floor(s / 3600), dk = Math.floor((s % 3600) / 60);
      return sa ? `${sa} sa ${dk} dk` : dk ? `${dk} dk ${s % 60} sn` : `${s} sn`;
    },
    /* ── WIG (2026-10-02) ── */
    /** Baglanti yok ya da ilk D gelmedi: okuma kartlari "0.000 V" degil "—". */
    veriYok() { return !this.bagli || !this.gecmis.length; },
    /** Kalici duyurucu (.icerik disinda): pil testi baslayinca soylenir. */
    kabukDuyuru() { return this.pilDurum === 'CALISIYOR' ? this.m.pilCalisiyor : ''; },
    /** Plan SUREN bir kayda bagli: `Gp-` kaydi da durdurur (1C-4) -> iki asamali iptal. */
    planBagli() { const p = this.kayit.gp; return !!p && p.durum === PLAN.SURUYOR; },
    pilDurumYazi() {
      const k = PIL_DURUM_KOD[this.pilDurum];
      return k === undefined ? ceviriKod('pil.durum.', this.pilDurum, this.dil) : ceviri('pil.durum.' + k, this.dil);
    },
    pilHataYazi() {
      const h = String(this.pilHata || '');
      const e = PIL_HATA_KOD.find(([bas]) => h.startsWith(bas));
      return e ? ceviri('pil.hata.' + e[1], this.dil) : h;
    },
    pilDcirYazi() { return this.pilDcirN > 0 ? this.bicim(this.pilDcirAni * 1000, 1) + ' mΩ' : '—'; },

    osiloTepe() {
      if (!this.osilo) return 0;
      return this.kodVolt(Math.max(...this.osilo.veri));
    },
  },

  watch: {
    /* B27 Aşama 1: gizli (display:none) tuval 0 genişlik okur; görünüme
       dönünce yeniden çizilmeli. Adres çubuğunu da eşitle. */
    gorunum(v) {
      /* 3C: adres ZATEN bu gorunumu gosteriyorsa (#/kayit/12 -> kayitlar)
         dokunma — yoksa acik kaydin adresi #/kayitlar'a ezilirdi. */
      if (typeof location !== 'undefined' && hashtenGorunum() !== v) {
        try { history.replaceState(null, '', '#/' + v); } catch (e) { /* file:// */ }
      }
      if (v === 'kayitlar') this.kayitlarAcik = true;
      if (v === 'canli') this.canliAcik = true;        // 3D: grafik modulu ilk acilista
      /* WIG: silahli onaylar gorunum degisince duser; sekme basligi gorunumu soyler;
         gizliyken birikmis konsol satirlarinin dibine gidilir. */
      this.onay = null;
      this.sifirlaOnay = false;
      belgeBasligiYaz(v, this.dil);
      if (v === 'konsol') this.$nextTick(() => { const k = this.$refs.gunlukKutu; if (k) k.scrollTop = k.scrollHeight; });
      if (v === 'skop') this.skopAcik = true;          // 3E: spektrum modulu ilk acilista
      if (v === 'pil') this.pilGorundu();              // 3F: modul ilk acilista; durum bayatsa BIR /pil
      this.$nextTick(() => { this.grafikCiz(); this.osiloCiz(); this.spektrumCiz(); this.pilCiz(); });
    },
    /* 3F (PL4): SUREKLI yoklama yalniz bu kosul dogruyken; dusunce zamanlayici durur. */
    pilYoklamaAcik(v) { this.pilYoklamaKur(v); },
    /* 3F: Pil sekmesi ilk kez gorunur oldu -> egri modulu (bir kez). */
    pilAcik(v) { if (v) this.pilModYukle(); },
    pilEksen(v) { this.ayarYaz('pilEksen', v); this.pilCiz(); },
    /* WIG: baglanti kopunca silahli onay duser (bagli degilken komut zaten gitmez). */
    bagli(v) { if (!v) this.onay = null; },
    /* WIG: donmus imlec okumasi degisti -> gecikmeli duyuru */
    canliOkuma(v) { this.canliOkumaDegisti(v); },
    /* 3D: Canli ilk kez gorunur oldu -> grafik modulunu indir (bir kez). */
    canliAcik(v) { if (v) this.canliYukle(); },
    /* 3E: Osiloskop ilk kez gorunur oldu -> spektrum modulu (bir kez). */
    skopAcik(v) { if (v) this.skopYukle(); },
    spektrumPencere(v) { this.ayarYaz('spektrumPencere', v); this.spektrumCiz(); },
    spektrumBirim(v) { this.ayarYaz('spektrumBirim', v); this.spektrumCiz(); },
    /* B22.2: cizimi tazele VE tercihi sakla. Bu alanlar her acilista
       yeniden giriliyordu — localStorage hic kullanilmiyordu. */
    pencere(v) { this.grafikCiz(); this.ayarYaz('pencere', v); },
    gosterV(v) { this.grafikCiz(); this.ayarYaz('gosterV', v); },
    /* 3D (ekran/canli.js K1): sag eksen tek birim — Akim YA DA Guc. Eski
       `gosterI` / `gosterW` tercihi ilk acilista buna cevriliyor. */
    sagEksen(v) { this.grafikCiz(); this.ayarYaz('sagEksen', v); },
    sontSecim(v) { this.ayarYaz('sontSecim', v); },
    /* B27 A2: rapor araligi tercihi — sakla ve bagliysa karta uygula.
       Kartin yaniti (`* rapor araligi N ms`) kartRapor'u gunceller. */
    raporMs(v) {
      this.ayarYaz('raporMs', v);
      if (this.bagli && this.surucuyum && v !== this.kartRapor) {
        this.gonder('r' + v).catch(() => {});
      }
    },
    sebekeHz(v) { this.ayarYaz('sebekeHz', v); },
    kartTaban(v) { this.ayarYaz('kartTaban', v); },
    /* 3A: görünüm düğmesi → ekran/tema.js (uygula + sakla). Etkin tema
       gerçekten değişirse `temaDegisti` tuvalleri yeniden çizdiriyor. */
    temaSecim(v) { if (this._tema && v) this._tema.sec(v); },
    /* Tasiyici degisince ONCE mevcut baglantiyi kapat — akis acikken
       seriye gecmek iki kaynagin ayni ayristiriciyi beslemesi demek. */
    async tasiyiciAdi(v, eski) {
      this.ayarYaz('tasiyici', v);
      const acik = this.bagliTasiyici;
      if (this.bagli && acik && acik !== v && TASIYICILAR[acik]) {
        await TASIYICILAR[acik].kapat(this);
        this.bagli = false;
        this.bagliTasiyici = null;
        this.kaydet('— taşıyıcı değişti, bağlantı kesildi —');
      }
      /* B27 A2: demo menüden de seçilebiliyor. Sahte kartın kurulumu
         `demoVeri()` içinde (betik indirme + ilk 300 nokta + akış), o
         yüzden burada çağrılıyor; ötekiler "Karta bağlan"ı bekler. */
      if (v === 'demo' && !this.bagli) this.demoVeri();
    },
  },

  mounted() {
    this.tercihleriYukle();
    /* 3D (D8): dil — 3H secicisi gelene dek localStorage (3C ile ayni anahtar). */
    let depo = null;
    try { depo = window.localStorage; } catch (e) { depo = null; }
    this.dil = dilSec(depo);
    this.baslikGuncelle();
    /* 3D (D1): Esc cekmeceyi kapatir (odak menu dugmesine doner). */
    window.addEventListener('keydown', (e) => this.tusBasildi(e));
    if (this.canliAcik) this.canliYukle();
    if (this.skopAcik) this.skopYukle();               // 3E: #/skop… ile acildi
    /* 3A (P1): görünüm. İlk boyamayı index.html'in <head> betiği zaten
       yaptı; burada aynı seçim yeniden uygulanıyor, 'Sistem'deyken işletim
       sistemi izleniyor ve değişince tuvaller yeniden çiziliyor (renkler
       `renk()` ile her çizimde CSS'ten okunuyor ama tuval bir bit eşlem). */
    this._tema = temaKur({ pencere: window, belge: document,
                           degisti: () => this.temaDegisti() });
    this.temaSecim = this._tema.secim;
    /* B27 A2: sayfayı KART ya da KÖPRÜ sunduysa kendiliğinden bağlan.
       Kullanıcı kartın adresini açmışsa ölçümü görmek istiyor; "Karta
       bağlan"a basmak fazladan bir adımdı ve headless doğrulamada da
       sayfa hep "bağlı değil" halinde kalıyordu. localhost/file:// ve
       ?demo'da DEĞİL — orada taşıyıcı USB ya da sahte kart. */
    this.kopruyuAlgila().then(() => { if (this.otomatikBaglanmali()) this.baglan(); });
    window.addEventListener('resize', () => { this.genislikDegisti(); this.grafikCiz(); this.osiloCiz(); this.pilCiz(); });
    window.addEventListener('hashchange', () => { this.gorunum = hashtenGorunum(); this.skopRotaIsle(); });
    window.addEventListener('mousemove', (e) => this.surukHareket(e));
    window.addEventListener('mouseup', () => this.surukBitir());
    this.grafikCiz();
    this.osiloCiz();
    // ?demo — donanım olmadan arayüzü görmek için sahte veri üretir
    if (location.search.includes('demo')) this.demoVeri();

    /* B21: önce IndexedDB'deki eski testi geri yükle (sekme kapanmış
       olabilir), sonra karttan eksikleri istemeye başla. Yoklama 2 s'de
       bir — kayıt 1 Hz olduğu için her yoklamada ~2 nokta geliyor;
       daha sık yoklamanın faydası yok, kartı meşgul eder.

       🔴 B27 Aşama 4 — YOKLAMA BOŞTA SEYRELİYOR. Kartta ölçüldü: her
       HTTP isteği ölçüm döngüsünü bloklar; küçük bir `/pil` isteği bile
       ~15 ms. Test çalışmıyorken ve pil görünümü kapalıyken 2 s'de bir
       yoklamanın hiçbir karşılığı yok — 10 s'de bir yeterli (bir testin
       başka bir istemciden başlatıldığını yine görüyoruz, 10 s gecikmeyle).
       Test başlarsa ya da kullanıcı pil görünümüne geçerse anında
       sıklaşıyor. */
    /* 🔴 3F (PL4) — YUKARIDAKI B27 A4 KURALI DEGISTI: surekli yoklama yalniz Pil sekmesi
       gorunur VE test surerken (`pilYoklamaAcik` izleyicisi kurar/durdurur). Geri kalan her
       sey kartin kendiliginden bastigi satirlardan (pilSatiri). Burada yalniz yerel kopya
       (IndexedDB noktalari + son testin oturumu / DCIR listesi) geri yukleniyor. */
    this._pilYuklendi = this.pilYukle().catch(() => { /* IndexedDB yok (ozel kip): canli yine calisir */ });
    this.pilSaklananiOku();
    this.pilEksen = this.ayarOku('pilEksen', 'zaman') === 'mah' ? 'mah' : 'zaman';
    if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
      const gor = () => { this.sayfaGorunur = document.visibilityState !== 'hidden'; };
      document.addEventListener('visibilitychange', gor);
      gor();
    }
    /* Acil seritteki "N önce" ve okuma kartlarinin yasi icin saniyelik saat (setInterval YOK — D5) */
    const saat = () => { this.saatTik = Date.now(); this._saatZaman = setTimeout(saat, 1000); };
    saat();
    if (this.pilAcik) this.pilModYukle();
  },

  methods: {
    gorunumeGit(id) { this.gorunum = id; },

    /* ═══ 3D — KABUK (D1) ═══════════════════════════════════════════════ */
    metin(anahtar, degiskenler = null) { return ceviri(anahtar, this.dil, degiskenler); },
    /* Cekmece (<= 900 px). Acilinca odak etkin baglantiya; Esc ya da secim kapatir,
       Esc'te odak menu dugmesine doner (klavye kullanicisi yerini kaybetmesin). */
    cekmeceAc() {
      this.cekmeceAcik = true;
      this.$nextTick(() => {
        const s = typeof document !== 'undefined' && typeof document.getElementById === 'function'
          ? document.getElementById('serit') : null;
        const a = s && (s.querySelector('.gorunum-sekme.etkin') || s.querySelector('.gorunum-sekme'));
        if (a && typeof a.focus === 'function') a.focus();
      });
    },
    cekmeceKapat(odakGeri = false) {
      if (!this.cekmeceAcik) return;
      this.cekmeceAcik = false;
      if (odakGeri) {
        this.$nextTick(() => {
          const d = this.$refs.menuDugme;
          if (d && typeof d.focus === 'function') d.focus();
        });
      }
    },
    cekmeceDegistir() {
      if (this.cekmeceAcik) this.cekmeceKapat(true);
      else this.cekmeceAc();
    },
    /* Seritte bir gorunum secildi: cekmece aciksa kapanir (masaustunde zaten kapali). */
    gorunumSecildi() { this.cekmeceKapat(true); },
    /* WIG: pencere genisledi (> 900 px): cekmece yok — acik kalirsa .icerik INERT kalirdi. */
    genislikDegisti() {
      const w = typeof window !== 'undefined' ? window : null;
      if (this.cekmeceAcik && w && typeof w.matchMedia === 'function' && w.matchMedia('(min-width: 901px)').matches) {
        this.cekmeceKapat(false);
      }
    },
    /* WIG: "Icerige gec" — odagi .icerik'e tasir. Hash DEGISMEZ (#icerik gorunum adresini
       ezerdi); tabindex yalniz bu odak icin, ayrilinca kalkar (fareyle tiklamada kutu odak almasin). */
    icerigeGec() {
      const e = this.$refs.icerik;
      if (!e || typeof e.focus !== 'function') return;
      e.setAttribute('tabindex', '-1');
      e.focus();
      e.addEventListener('blur', () => e.removeAttribute('tabindex'), { once: true });
    },
    /* WIG: sekme basligi gorunumu soyler (ekran okuyucu, tarayici gecmisi). */
    baslikGuncelle(id = this.gorunum) { belgeBasligiYaz(id, this.dil); },
    /* ═══ WIG — IKI ASAMALI ONAY ══════════════════════════════════════════
       Yikici eylem: ilk tik `onay`i silahlar (dugme "Eminim …"e doner, yaninda
       Vazgec), ikinci tik eylemi yapar. Onay ONAY_MS sonra, gorunum degisince,
       baglanti kopunca ve karta HERHANGI bir komut gidince (gonder) duser — bayat bir
       "Eminim" saatler sonra tek tikla calismaz. Odak kaybolmasin: silahlaninca onay
       dugmesine, vazgecince (ya da zaman asiminda) acan dugmeye doner. */
    onayIste(ad) {
      this.onay = ad;
      if (this._onayZaman) clearTimeout(this._onayZaman);
      this._onayZaman = setTimeout(() => {
        if (this.onay !== ad) return;
        const odakta = typeof document !== 'undefined' && document.activeElement
          && document.activeElement.getAttribute && document.activeElement.getAttribute('data-onay') === ad;
        this.onay = null;
        if (odakta) this._odakla('[data-onay-ac="' + ad + '"]');
      }, ONAY_MS);
      this._odakla('[data-onay="' + ad + '"]');
    },
    onayVazgec(ad) {
      this.onay = null;
      this._odakla('[data-onay-ac="' + ad + '"]');
    },
    _odakla(secici) {
      this.$nextTick(() => {
        if (typeof document === 'undefined' || typeof document.querySelector !== 'function') return;
        const e = document.querySelector(secici);
        if (e && typeof e.focus === 'function') e.focus();
      });
    },
    /* WIG: imlec okumasi ~300 ms durulunca TEK satir ozet (her ok tusunda degil). */
    canliOkumaDegisti(v) {
      if (this._duyuruZaman) clearTimeout(this._duyuruZaman);
      this._duyuruZaman = setTimeout(() => {
        this.canliDuyuru = v ? v.slice(0, 5).map((s) => s.ad + ' ' + s.d).join(' · ') : '';
      }, 300);
    },
    tusBasildi(e) {
      if (e && e.key === 'Escape' && this.cekmeceAcik) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        this.cekmeceKapat(true);
      }
    },

    /* ═══ 3D — KAYIT DENETIMI (D4) ═════════════════════════════════════
       Komut panelin MEVCUT yolundan (USB / WiFi / kopru; `gonder`). Kurallar
       KARTTA (pil surerken ret vb.) — panel kopyasini yazmaz; kartin `! G…`
       satiri oldugu gibi gosterilir. Panel YALNIZ kartin sessizce bozacagi
       girdiyi durdurur: tavani asan komut, kartin atacagi karakter, gecersiz
       aralik / plan siniri (kart da reddederdi, sebebi burada daha acik). */
    async kayitKomut(komut) {
      const d = kayitKomutuDenetle(komut);
      if (d.hata) {
        this.kayitUyari = { tur: 'panel', metin: this.metin(d.hata, { bayt: d.bayt, azami: KOMUT_AZAMI_BAYT }) };
        return false;
      }
      if (!this.bagli) {
        this.kayitUyari = { tur: 'panel', metin: this.metin('cn.hata_bagli_degil') };
        return false;
      }
      this.kayitUyari = null;
      this.kayitKomutZamani = Date.now();
      try {
        await this.gonder(d.komut);
        /* D5: durum YALNIZ bir kayit komutundan sonra bir kez sorulur — yoklama yok;
           gerisi kartin kendiliginden bastigi G satirlarindan. */
        await this.gonder('G?');
      } catch (e) {
        this.kayitUyari = { tur: 'panel', metin: String((e && e.message) || e) };
        return false;
      }
      return true;
    },
    kayitHataGoster(k) {
      const azami = k.hata === 'cn.hata_not_uzun' ? NOT_METIN_AZAMI_BAYT : KOMUT_AZAMI_BAYT;
      this.kayitUyari = { tur: 'panel', metin: this.metin(k.hata, { bayt: k.bayt, azami }) };
    },
    kayitBaslat() {
      const k = kayitBaslatKomutu(this.baslatHiz);
      if (k.hata) { this.kayitHataGoster(k); return Promise.resolve(false); }
      this.kayitIstek = { hiz: Number(this.baslatHiz), zaman: Date.now() };
      return this.kayitKomut(k.komut);
    },
    kayitDurdur() { return this.kayitKomut('Gd'); },
    notAcDegistir() { this.notAcik = !this.notAcik; this.planAcik = false; },
    async notEkle() {
      /* WIG: istek surerken ikinci basis/Enter IKINCI bir NOT kaydi yazdirmasin */
      if (this.notGonderiliyor) return false;
      const g = this.kayit.g;
      /* Not grafikte kendi aninda dursun: son D satirinin kart ms'i (taze ise). */
      const kms = this.kartMs && Date.now() - (this._sonDZaman || 0) < 3000 ? this.kartMs : null;
      const k = kayitNotKomutu(g && g.durum === KDR.KAYIT ? g.oturum : 0, this.notMetni, kms);
      if (k.hata) { this.kayitHataGoster(k); return false; }
      this.notGonderiliyor = true;
      try {
        const gitti = await this.kayitKomut(k.komut);
        if (gitti) { this.notMetni = ''; this.notAcik = false; }
        return gitti;
      } finally {
        this.notGonderiliyor = false;
      }
    },
    planAcDegistir() {
      this.planAcik = !this.planAcik;
      this.notAcik = false;
      if (this.planAcik && !this.planBas) this.planBas = this.yerelSaatYaz(new Date(Date.now() + 10 * 60000));
    },
    async planKur() {
      const k = kayitPlanKomutu({
        basUnix: yerelSaattenUnix(this.planBas),
        sureS: Math.round((Number(this.planSureSa) || 0) * 3600 + (Number(this.planSureDk) || 0) * 60),
        hizMs: Number(this.planHiz),
        simdiUnix: Math.floor(Date.now() / 1000),
      });
      if (k.hata) { this.kayitHataGoster(k); return false; }
      const gitti = await this.kayitKomut(k.komut);
      if (gitti) this.planAcik = false;
      return gitti;
    },
    planIptal() { return this.kayitKomut('Gp-'); },

    /* ═══ 3D — KAYIT DURUMU: satir isleme (D5-D7) ═══════════════════════ */
    kayitSatiriIsle(o) {
      const k = this.kayit;
      const simdi = Date.now();
      if (o.tur === 'G') {
        const onceki = k.g;
        this.pilGIsle(o);                    // 3F (PU6): PIL oturumunun numarasi
        for (const ol of kayitOlaylari(onceki, o)) {
          const d = { ...ol.d };
          if (ol.durum !== undefined) d.durum = ceviriKod('kayit.durum.', ol.durum, this.dil);
          this.olayEkle(this.metin(ol.anahtar, d));
        }
        const y = this.yenidenBekleyen;
        if (y) {
          this.yenidenBekleyen = null;
          if (y.durum === KDR.KAYIT && o.durum === KDR.KAYIT && y.oturum === o.oturum) {
            this.olayEkle(this.metin('cn.olay_surdu', { oturum: o.oturum }));
          }
        }
        if (o.durum === KDR.KAYIT) {
          const yeni = !onceki || onceki.durum !== KDR.KAYIT || onceki.oturum !== o.oturum;
          if (yeni) {
            /* ilk G'de kayit zaten suruyordu: baslangici GORMEDIK (sure tahmin edilmez) */
            this.kayitBas = onceki ? { oturum: o.oturum, zaman: simdi } : null;
            this.kayitGozlem = [];
            this.kayitNoktaGozlem = [];
            this.kayitHizBilgi = this.hizKaynagi(o.oturum, simdi);
          }
          this.gozlemEkle(simdi, o);
        } else {
          this.kayitBas = null;
          this.kayitGozlem = [];
          this.kayitNoktaGozlem = [];
        }
        k.g = o;
        this.kayitGZaman = simdi;
      } else if (o.tur === 'GP') {
        if (k.gp && k.gp.durum !== o.durum) {
          this.olayEkle(this.metin('cn.olay_plan', { durum: ceviriKod('plan.durum.', o.durum, this.dil) }));
        }
        k.gp = o;
      } else if (o.tur === 'GT') {
        if (k.gt && k.gt.etkin !== o.etkin) this.olayEkle(this.metin(o.etkin ? 'cn.olay_skop_basladi' : 'cn.olay_skop_durdu'));
        k.gt = o;
      } else if (o.tur === 'GA') {
        k.ga = o;
        const g = k.g;
        if (g && g.durum === KDR.KAYIT && o.ayrintili_ornek > 0 && !(this.kayitHizBilgi && this.kayitHizBilgi.oturum === g.oturum)) {
          this.kayitHizBilgi = { oturum: g.oturum, hiz: 0, kaynak: 'ayrinti' };
        }
      }
    },
    /** Yeni oturumun araligi nereden biliniyor: bu sekmenin Gb'si (15 s icinde) ya da plan. */
    hizKaynagi(oturum, simdi) {
      const ist = this.kayitIstek;
      if (ist && simdi - ist.zaman < 15000) {
        this.kayitIstek = null;
        return { oturum, hiz: ist.hiz, kaynak: 'istek' };
      }
      const p = this.kayit.gp;
      const unix = Math.floor(simdi / 1000);
      if (p && (p.oturum === oturum || (p.durum === PLAN.BEKLIYOR && Math.abs(unix - p.bas_unix) < 120))) {
        return { oturum, hiz: p.hiz_ms, kaynak: 'plan' };
      }
      return null;
    },
    /* D6 gozlemleri. Onaysiz azalirsa (onay geldi) tahmin bastan. Ayni degerin ARDISIK
       tekrarlari tek araliga sikisir (uzun kayitta dizi buyumesin; kalanTahmin icin
       yalniz ilk gozlem, degisim anlari ve son gozlem gerekir). */
    gozlemEkle(simdi, o) {
      let g = this.kayitGozlem;
      const n = g.length;
      if (n && o.onaysiz < g[n - 1].d) g = this.kayitGozlem = [];
      const x = { t: simdi, d: o.onaysiz };
      const m = g.length;
      if (m >= 2 && g[m - 1].d === x.d && g[m - 2].d === x.d) g.splice(m - 1, 1, x);
      else g.push(x);
      const ng = this.kayitNoktaGozlem;
      const nx = { t: simdi, n: o.nokta };
      if (ng.length < 2) ng.push(nx);
      else ng.splice(1, 1, nx);
    },
    olayEkle(metin, tur = 'bilgi') {
      const s = new Date();
      const saat = [s.getHours(), s.getMinutes(), s.getSeconds()].map((x) => String(x).padStart(2, '0')).join(':');
      this._olayNo = (this._olayNo || 0) + 1;
      this.olaylar.unshift({ no: this._olayNo, saat, metin, tur });
      if (this.olaylar.length > OLAY_AZAMI) this.olaylar.splice(OLAY_AZAMI);
    },
    /** `!` satiri (D7: olay). Bir kayit komutundan hemen sonra gelen `! G…` o komutun
     *  REDDI: denetimin yaninda oldugu gibi gosterilir (D4). */
    unlemSatiri(satir) {
      this.olayEkle(satir, 'unlem');
      if (/^! ?G\b/.test(satir) && Date.now() - this.kayitKomutZamani < RET_PENCERESI_MS) {
        this.kayitUyari = { tur: 'kart', metin: this.metin('cn.kart_reddetti', { satir }) };
      }
      /* 3E (OS5): gunluk komutunun reddi osiloskobun gunluk kumesinde (E9 deseni) */
      if (/^! ?G\b/.test(satir) && Date.now() - this.skopGunlukZamani < RET_PENCERESI_MS) {
        this.skopGunlukUyari = { tur: 'kart', metin: this.metin('os.kart_reddetti', { satir }) };
      }
      /* 3E: elle yakalamanin reddi (gunluk suruyor, pil testi, tetik yok…) Yakalama kumesinde */
      if (/^! ?(skop|tetiklenemedi|otomatik)/.test(satir) && Date.now() - this.skopKomutZamani < SKOP_RET_PENCERESI_MS) {
        this.skopYakalamaUyari = this.metin('os.kart_reddetti', { satir });
      }
    },
    /** Kart yeniden basladi (afis ya da D `ms`i geri gitti) — ayni an icin TEK olay. */
    yenidenBasladi() {
      const simdi = Date.now();
      if (simdi - (this._sonYeniden || 0) < 15000) return;
      this._sonYeniden = simdi;
      this.yenidenBekleyen = this.kayit.g;
      this.olayEkle(this.metin('cn.olay_yeniden'));
    },
    afisGoruldu(a) {
      this.afisSurum = a.fw || a.surum;
      this.yenidenBasladi();
    },
    /** D `ms`i geri gitti: t AZALMASIN (grafik.js) — sarmada surekli, yeniden baslamada
     *  3 rapor araligi BOSLUKLA (bosluk esigi 2.5x: cizgi kopar, zaman uydurulmaz). */
    msAtladi(tur, yeniMs) {
      if (tur === 'sarma') { this.msKaydir += MILLIS_TUR; return; }
      const aralik = Math.max(this.sonAralik > 0 ? this.sonAralik : 0, this.raporMs || 200);
      this.msKaydir += this.kartMs - yeniMs + 3 * aralik;
      this.yenidenBasladi();
    },
    hizYazi(ms) {
      if (ms === 0) return this.m.herOrnek;
      if (!Number.isFinite(ms)) return '—';
      if (ms < 1000) return this.metin('cn.hiz_ms', { ms: Math.round(ms) });
      if (ms < 60000) return this.metin('cn.hiz_s', { s: Math.round(ms / 100) / 10 });
      return this.metin('cn.hiz_dk', { dk: Math.round(ms / 6000) / 10 });
    },
    /** ss:dd:sn (saat 24'u gecebilir). */
    saatYazi(ms) {
      const s = Math.max(0, Math.floor(ms / 1000));
      const p = (x) => String(x).padStart(2, '0');
      return `${p(Math.floor(s / 3600))}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)}`;
    },
    /** Imlec zamani (ms, eksi olabilir) -> −ss:dd:sn.s */
    zamanFarkYazi(ms) {
      const a = Math.abs(ms);
      const s = Math.floor(a / 1000);
      const p = (x) => String(x).padStart(2, '0');
      return (ms < 0 ? '−' : '') + `${p(Math.floor(s / 3600))}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)}.${Math.floor(a % 1000 / 100)}`;
    },
    /** Kalan / plan suresi: >= 2 gun gun, >= 1 sa saat, degilse dakika (en az 1). */
    kalanSureYazi(ms) {
      if (!Number.isFinite(ms)) return '∞';
      const sa = ms / 3600000;
      if (sa >= 48) return Math.floor(sa / 24) + ' ' + this.metin('cn.birim_gun');
      if (sa >= 1) return Math.floor(sa) + ' ' + this.m.birimSa;
      return Math.max(1, Math.floor(ms / 60000)) + ' ' + this.m.birimDk;
    },
    /* WIG: ISO-benzeri YYYY-AA-GG (Kayitlar listesi kayit_gorunum tarihYaz ile ayni; siralanabilir). */
    tarihYazi(unix) {
      const d = new Date(unix * 1000);
      const p = (x) => String(x).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    yerelSaatYaz(d) {
      const p = (x) => String(x).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    /** Kartin ana sayisiyla AYNI birimde (A / mA / µA ...). */
    olcekliYaz(x, birim, taban) {
      const k = birim === taban ? 1 : birim === 'm' + taban ? 1e3 : 1e6;
      const hane = k === 1 ? 4 : k === 1e3 ? (taban === 'Wh' ? 3 : 2) : (taban === 'Wh' ? 1 : 0);
      return this.bicim(x * k, hane) + ' ' + birim;
    },
    lejantMetni(l) {
      if (!l.gecerli) return this.m.kanalVeriYok;
      const f = (x) => (l.alan === 'v' ? x.toFixed(2) + ' V' : l.alan === 'i' ? (x * 1e3).toFixed(1) + ' mA'
        : (x * 1e3).toFixed(1) + ' mW');
      return this.metin('cn.tepe', { deger: f(l.tepe) })
        + (l.tabanda ? ' · ' + this.metin('cn.olcek', { deger: f(l.olcek) }) : '');
    },

    /* ═══ 3D — CANLI GRAFIK (ekran/canli.js; D3) ═══════════════════════ */
    async canliYukle() {
      if (this._canli || this.canliDurum === 'yukleniyor') return;
      this.canliDurum = 'yukleniyor';
      try {
        const mod = await import('./ekran/canli.js');
        await this.$nextTick();
        const tuval = this.$refs.grafik;
        if (!tuval) throw new Error('grafik tuvali yok');
        this._canli = new mod.CanliGrafik(tuval, { pencere: window, degisti: (b) => { this.canliBilgi = b; } });
        this.canliDurum = 'hazir';
        this.grafikCiz();
      } catch (e) {
        /* Modul inmedi (kart yeniden basliyor, bayat goruntu): sebep + care ekranda */
        this.canliDurum = 'yuklenemedi';
      }
    },
    canliDurumu() {
      return {
        gecmis: this.gecmis, pencereS: this.pencere, gosterV: this.gosterV, sagEksen: this.sagEksen,
        taban: (veri) => this.olcekTabani(veri), aralikMs: this.sonAralik > 0 ? this.sonAralik : this.raporMs,
        donmus: this.donmus,
      };
    },
    dondurDegistir() {
      this.donmus = !this.donmus;
      this.grafikCiz();
    },
    imlecTemizle() { if (this._canli) this._canli.imlecTemizle(); },

    /* ═══ 3E — OSILOSKOP: spektrum + kayitli yakalama (ekran/osiloskop.js) ═ */
    async skopYukle() {
      if (this._skop || this.skopDurum === 'yukleniyor') return;
      this.skopDurum = 'yukleniyor';
      try {
        const mod = await import('./ekran/osiloskop.js');
        await this.$nextTick();
        const tuval = this.$refs.spektrumTuval;
        if (!tuval) throw new Error('spektrum tuvali yok');
        this._skopMod = mod;
        this._skop = new mod.SpektrumGrafik(tuval, { pencere: window, degisti: (b) => { this.spektrumBilgi = b; } });
        this.skopDurum = 'hazir';
        this.spektrumCiz();
        this.skopRotaIsle();
      } catch (e) {
        /* Modul inmedi (kart yeniden basliyor, bayat goruntu): sebep + care ekranda */
        this.skopDurum = 'yuklenemedi';
      }
    },
    /** OS3: spektrum HER ZAMAN yakalamanin butun ham kodlarindan, eksenle ayni ceviriyle. */
    spektrumCiz() {
      if (!this._skop || this.gorunum !== 'skop') return;
      const o = this.osilo;
      this._skop.ciz({
        veri: o && o.veri && o.veri.length >= 2 ? o.veri : null, hz: o ? o.hz : 0,
        kodVolt: (k) => this.kodVolt(k), pencere: this.spektrumPencere, birim: this.spektrumBirim,
      });
    },
    /** OS6: adres kayitli yakalama rotasiysa onu ac (modul hazir degilse yuklenince). */
    skopRotaIsle() {
      if (!this._skopMod || typeof location === 'undefined') return;
      const r = this._skopMod.skopRotaCoz(location.hash);
      if (!r) return;
      const k = this.skopKayitli;
      if (k && k.oturum === r.oturum && k.sira === r.sira && (r.kimlik === null || r.kimlik === k.kimlik)) return;
      this.skopKayitliAc(r);
    },
    async skopKayitliAc(rota) {
      this.skopKayitliYukleniyor = true;
      this.skopKayitliHata = '';
      let r;
      try {
        r = await this._skopMod.kayitliYakalamaAc(rota, { kartAdres: (y) => this.kartAdres(y) });
      } catch (e) {
        r = { hata: 'os.hata_modul', d: { mesaj: (e && e.message) || String(e) } };
      }
      this.skopKayitliYukleniyor = false;
      if (r.hata) {
        this.skopKayitliHata = this.metin(r.hata, r.d);
        return;
      }
      /* Kayitli yakalama acilinca SUREKLI kip durur (kopru arsivinin B35 kurali): yoksa bir
         sonraki tur kaydin ustune canli dalgayi cizer. */
      if (this.surekli) this.surekliDegis();
      this.skopAcikKayit = null;
      this.osiloTopla = null;
      this.osilo = r.osilo;
      this.skopKayitli = { ...r.bilgi };
      this.yatayZoom = 1;
      this.yatayKaydir = 0.5;
      this.$nextTick(() => { this.osiloCiz(); this.spektrumCiz(); });
    },
    /** OS6: kayitli gorunumden cik — isaret silinir, adres kayit rotasiysa #/skop olur
     *  (adres gosterilenle ayrismasin; geri tusu kayda doner). */
    skopKayitliCik() {
      this.skopKayitli = null;
      this.skopKayitliHata = '';
      if (typeof location !== 'undefined' && /^#\/?skop\/kayit\//.test(location.hash)) {
        try { history.replaceState(null, '', '#/skop'); } catch (e) { /* file:// */ }
      }
    },
    /** OS6 "Canliya don": kayitli gorunumden cik, bagliysa yakala (gunluk surerken kart reddeder). */
    skopCanliyaDon() {
      this.skopKayitliCik();
      if (this.bagli && !this.skopGunlukAktif) {
        this.osiloYakala();
      } else {
        this.osilo = null;
        this.$nextTick(() => { this.osiloCiz(); this.spektrumCiz(); });
      }
    },
    /* OS5 — yakalama gunlugu. Komut panelin MEVCUT yolundan; ardindan `G?` (D5: durum
       yalniz bir kayit komutundan sonra sorulur, gerisi kartin bastigi GT satirlari).
       Kartin `! G:` reddi 5 s icinde gelirse BU denetimin yaninda oldugu gibi (E9). */
    async skopGunlukGonder(komut) {
      if (!this.bagli) {
        this.skopGunlukUyari = { tur: 'panel', metin: this.metin('os.hata_bagli_degil') };
        return false;
      }
      this.skopGunlukUyari = null;
      this.skopGunlukZamani = Date.now();
      try {
        await this.gonder(komut);
        await this.gonder('G?');          // D5: GT satiri (durum) bir kez
      } catch (e) {
        this.skopGunlukUyari = { tur: 'panel', metin: String((e && e.message) || e) };
        return false;
      }
      return true;
    },
    skopGunlukBaslat() {
      const k = skopGunlukKomutu({ kip: this.gunlukKip, saniye: this.gunlukSaniye });
      if (k.hata) {
        this.skopGunlukUyari = { tur: 'panel', metin: this.metin(k.hata) };
        return Promise.resolve(false);
      }
      return this.skopGunlukGonder(k.komut);
    },
    skopGunlukDurdur() { return this.skopGunlukGonder('Gtd'); },
    /* 3A: etkin renk takımı değişti (düğme ya da işletim sistemi). İki
       tuval de bit eşlem: eski renklerle kalırdı — skop bir sonraki
       yakalamaya, grafik bir sonraki `D` satırına (bağlı değilken HİÇ)
       kadar. Gizli sekmedeki tuval 0 genişlik okur ve çizmez; o sekmeye
       dönülünce `gorunum` izleyicisi zaten yeniden çiziyor. */
    temaDegisti() { this.grafikCiz(); this.osiloCiz(); this.spektrumCiz(); this.pilCiz(); },
    calGonder() { this.gonder('X' + this.calHz); },
    calGorevGonder() { this.gonder('x' + this.calGorev); },
    bicim(x, n) {
      if (!isFinite(x)) return '—';
      return x.toFixed(n);
    },

    /* ── B22.2: ADRES ve TERCİH ─────────────────────────────────────
       🔴 Uzak uçlara giden HER istek buradan geçer. Önce `pilYokla`
       göreli `fetch('/pil?…')` yapıyordu; sayfa `localhost:8772`'den
       servis edildiği için istek kartın değil PYTHON SUNUCUSUNUN köküne
       gidiyor ve 404 dönüyordu. `fetch` 404'te reddetmediği için hata
       sayfasının HTML'i `anahtar=değer` sanılıp ayrıştırılıyordu:
       tüm pil KPI'ları SESSİZCE sıfır oluyordu. */
    kartAdres(yol) {
      /* WIG: "192.168.1.50" ya da "olcum.local" yazilirsa istek GORELI olup sayfanin
         kendi sunucusuna gidiyordu ("akis koptu" disinda iz yok) — tabanTam http:// ekler. */
      return tabanTam(this.kartTaban) + yol;
    },

    /* Tercihler tarayıcıda kalsın — kullanıcı her açılışta pencereyi,
       göstergeleri, şöntü ve şebeke frekansını yeniden girmesin.
       ⚠ Her erişim try/catch: özel kipte ve kota dolduğunda localStorage
       ERİŞİMİN KENDİSİ atıyor, okuma/yazma başarısızlığı değil. */
    ayarOku(anahtar, varsayilan) {
      try {
        const v = localStorage.getItem('olcum.' + anahtar);
        return v === null ? varsayilan : JSON.parse(v);
      } catch (e) { return varsayilan; }
    },
    ayarYaz(anahtar, deger) {
      try {
        localStorage.setItem('olcum.' + anahtar, JSON.stringify(deger));
      } catch (e) { /* tercih kaydedilemedi — işlevsel sorun değil */ }
    },
    /* B22.3: sayfa KOPRUDEN geliyorsa tasiyici kendiliginden 'akis'
       olsun — telefonda kullanici acilista dogru kipi secmek zorunda
       kalmasin (Web Serial telefonda hicbir tarayicida yok).
       ⚠ Kullanici bir kez SECMISSE dokunulmuyor: otomatik algilama
       tercihi EZMEZ. */
    otomatikBaglanmali() {
      const k = (typeof location !== 'undefined') ? location : null;
      if (!k || k.protocol === 'file:') return false;
      if (/^(localhost|127\.0\.0\.1|\[::1\])$/i.test(k.hostname)) return false;
      if (/(^|[?&])demo(=|&|$)/.test(k.search)) return false;
      return this.tasiyiciAdi === 'akis' && !this.bagli;
    },

    async kopruyuAlgila() {
      if (this.ayarOku('tasiyici', null) !== null) return;

      /* 🔴 B26: SAYFAYI KART SUNUYORSA DA 'akis' SEÇ.
         Aşağıdaki `/durum` yoklaması B22.3'te KÖPRÜ için yazıldı; o uç
         YALNIZCA köprüde var. B22.4/B22.5 kartı kendi sayfasını sunar
         hale getirdi ama algılama genişletilmedi — kartta `/durum` 404
         dönüyor, algılama sessizce vazgeçiyor, taşıyıcı 'seri'de kalıyor.
         Web Serial de güvenli bağlam olmadığı için çalışmıyor: kullanıcı
         "bağlı değil" görüyor. Telefonda hiç açılmıyordu.

         Doğru ölçüt: sayfayı BİRİ SUNDUYSA ve o biri localhost değilse,
         sunan taraf kart ya da köprüdür — ikisi de `/akis` veriyor.
         localhost ise `arayuz3/sunucu.py` geliştirme sunucusu olabilir ve
         orada USB doğru kiptir; o yüzden `/durum` yoklaması korunuyor. */
      const k = (typeof location !== 'undefined') ? location : null;
      const yerel = !k || k.protocol === 'file:'
                 || /^(localhost|127\.0\.0\.1|\[::1\])$/i.test(k.hostname);
      if (!yerel) {
        this.tasiyiciAdi = 'akis';
        this.kaydet('— sayfa ' + k.host + ' üzerinden geldi: akış kipi —');
        return;
      }

      try {
        const y = await fetch(this.kartAdres('/durum'));
        if (!y.ok) return;
        const d = await y.json();
        if (d && d.kart) {
          this.tasiyiciAdi = 'akis';
          this.kaydet('— köprü algılandı: ' + d.kart + ' —');
        }
      } catch (e) { /* köprü yok — seri kipte kal */ }
    },

    tercihleriYukle() {
      this.tasiyiciAdi = this.ayarOku('tasiyici', this.tasiyiciAdi);
      this.kartTaban = this.ayarOku('kartTaban', this.kartTaban);
      this.pencere = this.ayarOku('pencere', this.pencere);
      this.gosterV = this.ayarOku('gosterV', this.gosterV);
      /* 3D: eski uc kutulu tercih (gosterI / gosterW) sag eksen secimine cevriliyor */
      const eskiI = this.ayarOku('gosterI', true);
      const eskiW = this.ayarOku('gosterW', true);
      const sag = this.ayarOku('sagEksen', eskiI ? 'akim' : eskiW ? 'guc' : 'yok');
      this.sagEksen = ['akim', 'guc', 'yok'].includes(sag) ? sag : 'akim';
      this.sontSecim = this.ayarOku('sontSecim', this.sontSecim);
      this.sebekeHz = this.ayarOku('sebekeHz', this.sebekeHz);
      this.raporMs = this.ayarOku('raporMs', this.raporMs);
      /* 3E (OS3): spektrum penceresi / birimi — bilinmeyen kayitli deger varsayilana dusuyor */
      const sp = this.ayarOku('spektrumPencere', 'hann');
      this.spektrumPencere = ['hann', 'dikdortgen'].includes(sp) ? sp : 'hann';
      const sb = this.ayarOku('spektrumBirim', 'v');
      this.spektrumBirim = ['v', 'dbv'].includes(sb) ? sb : 'v';
    },

    /* Tek seferlik betik yukleyici. `sahte-kart.js` YALNIZCA ?demo kipinde
       gerekiyor; index.html'den kosulsuz yuklenirse 15 936 B her acilista
       bosuna iniyor ve B22.5'te LittleFS goruntusune de girerdi. */
    betikYukle(yol) {
      /* 🔴 B27 A2: AYNI BETIK IKI KEZ INMEMELI. `sahte-kart.js` en üst
         düzeyde `const SahteKart` bildiriyor; ikinci kez inince tarayıcı
         "Identifier 'SahteKart' has already been declared" atıyor ve
         sayfanın O ANDAN SONRAKI betik değerlendirmesi düşüyordu.
         Headless render yakaladı (?demo + menü izi aynı anda). */
      if (document.querySelector('script[src="' + yol + '"]')) return Promise.resolve();
      return new Promise((coz, at) => {
        const v = document.createElement('script');
        v.src = yol;
        v.onload = coz;
        v.onerror = () => at(new Error(yol + ' yuklenemedi'));
        document.head.appendChild(v);
      });
    },

    /* Donanımsız önizleme: gerçek firmware satırlarını taklit eder.
       Adres çubuğuna ?demo eklenince çalışır. */
    /* ?demo — donanim olmadan arayuzu calistirir.
       Seri port yerine SahteKart devreye giriyor (sahte-kart.js, dinamik
       iniyor); ayristirici, cizim ve olcum paneli GERCEK yolundan calisiyor.
       `demo` bayragi ANCAK betik indikten sonra aciliyor: gonder()'in demo
       dali ve demo seridi ona bakiyor, erken acilirsa SahteKart tanimsiz. */
    async demoVeri() {
      /* Kapı `await`ten ÖNCE kapanmalı: ?demo ile açılışta mounted()
         demoVeri()'yi çağırıyor, o `tasiyiciAdi`yi 'demo' yapınca watch
         bir kez daha çağırıyor — ikisi de betiği beklerken geçerdi. */
      if (this.demoKurulu) return;
      this.demoKurulu = true;
      try {
        await this.betikYukle('sahte-kart.js');
      } catch (e) {
        this.hata = 'Demo kipi açılamadı: ' + e.message + ' — sayfayı yenileyip yeniden deneyin.';
        this.demoKurulu = false;
        return;
      }
      // B22.2: `demo` artik tasiyicidan TURETILIYOR (computed).
      // Iki ayri bayrak tutmak bu projenin cezalandirdigi seyin ta
      // kendisi olurdu; gonder() de bu sayede dogru yola gidiyor.
      this.tasiyiciAdi = 'demo';
      this.bagli = true;
      this.bagliTasiyici = 'demo';
      this.kaydet('— DEMO KIPI: karta bagli degil, sahte kart calisiyor —');

      // gecmis grafigi icin birikmis olcum akisi
      let j = 0;
      for (let i = 0; i < 300; i++) {
        const ms = i * 200;
        const d = SahteKart.dSatiri(ms, j);
        j += d.w * 0.2;
        this.satirIsle(d.satir);
      }
      this.demoMs = 300 * 200;
      this.demoJ = j;
      /* 3D (D5): sahte kartin kayit durumu BIR KEZ — baglan() ile ayni kural */
      this.gonder('G?').catch(() => {});
      this.pilTazele();                  // 3F (PL4): sahte kartin pil durumu bir kez

      // canli akis: gercek kart gibi rapor araliginda bir D satiri.
      // B27 A2: aralik sahte karttan okunuyor (`r<ms>` ile degisir),
      // o yuzden setInterval degil kendini yeniden kuran setTimeout.
      const tik = () => {
        const aralik = SahteKart.raporAralik();
        this.demoMs += aralik;
        const d = SahteKart.dSatiri(this.demoMs, this.demoJ);
        this.demoJ += d.w * aralik / 1000;
        this.satirIsle(d.satir);
        /* 3D: sahte kartin kayit motoru da kendiliginden G satiri basar (kayitta saniyede bir) */
        if (typeof SahteKart.kayitTik === 'function') {
          for (const s of SahteKart.kayitTik(this.demoMs)) this.satirIsle(s);
        }
        /* 3F: sahte kartin pil testi (hizlandirilmis) — BITTI satirini kendisi basar */
        if (typeof SahteKart.pilTik === 'function') {
          for (const s of SahteKart.pilTik(this.demoMs)) this.satirIsle(s);
        }
        this.demoZaman = setTimeout(tik, aralik);
      };
      this.demoZaman = setTimeout(tik, SahteKart.raporAralik());

      // acilista bir yakalama yap ki ekran bos kalmasin
      this.$nextTick(() => this.osiloOtomatik());
    },

    demoSinyalDegisti() {
      SahteKart.sinyalSec(this.demoSinyal);
      this.kaydet('— test sinyali: ' +
                  SahteKart.sinyaller[this.demoSinyal].ad + ' —');
      this.osiloOtomatik();
    },

    kaydet(metin, giden = false) {
      /* WIG: yalniz kullanici DIPTEYKEN izle — yukari kaydirip eski bir yaniti okuyan,
         saniyede bir gelen G satiriyla dibe atilmasin. Konsol gizliyken DOM'a dokunulmaz
         (gorunum izleyicisi acilinca dibe goturur). */
      const k = this.gorunum === 'konsol' ? this.$refs.gunlukKutu : null;
      const dipte = !!k && k.scrollHeight - k.scrollTop - k.clientHeight < 8;
      this.gunluk.push({ metin, giden });
      if (this.gunluk.length > 400) this.gunluk.splice(0, this.gunluk.length - 400);
      if (dipte) this.$nextTick(() => { k.scrollTop = k.scrollHeight; });
    },

    // ─────────────────────────────────────────────── seri port
    /* B22.2: bağlantı mantığı TAŞIYICIDA. Buradaki üç metot yalnızca
       yönlendiriyor — hangi taşıyıcının etkin olduğunu bilmeleri yeterli,
       nasıl çalıştığını değil. */
    async baglan() {
      this.hata = '';
      try {
        await this.tasiyici.ac(this);
        this.bagli = true;
        this.bagliTasiyici = this.tasiyiciAdi;
        /* B27/K5: kartın GERÇEK ayarlarını sor. Şönt menüsü daha önce
           yalnızca tarayıcının localStorage tercihini gösteriyordu (menü
           10R derken kart 0.1R çalışıyordu — akım menzili 100 kat yanlış
           sanılırdı). `?` parola isteyebilir; tarayıcı bir kez sorar. */
        try { await this.gonder('?'); } catch (e2) { /* yetkisiz: kartSont null kalır */ }
        /* B35: PC kopruşuna bağlıysak skop arşivi var. Yoklama sessizce
           başarısız olabilir — arşiv bir ek özellik, yokluğu ölçümü
           etkilemiyor, o yüzden bağlanmayı BLOKLAMIYOR. */
        /* B36: skop gerilim ekseninin kalibrasyon tablosu. Kart ham kod
           yolluyor; düzeltme çizim anında burada uygulanıyor. Tablo
           gelmezse eksen ESKİ (düzeltmesiz) yolla çiziliyor ve arayüz
           bunu söylüyor — sessizce "kalibre" görünmüyor. */
        try { await this.gonder('CT'); } catch (e3) { /* tablosuz devam */ }
        /* 3D (D5): kayit durumu BIR KEZ — sonrasi kartin kendiliginden bastigi
           `G` satirlarindan (kayitta saniyede bir + degisince). Yoklama YOK. */
        try { await this.gonder('G?'); } catch (e4) { /* kayit bolumu yoksa kart `! G:` der */ }
        this._kopruBilindi = false;
        this.kopruYokla();
        /* 3F (PL4): pil durumu BIR KEZ (acil serit); surekli yoklama yalniz Pil sekmesinde */
        this.pilIlkTazele();
      } catch (e) {
        // Kullanıcı port seçim kutusunu kapattıysa bu hata değil.
        const metin = this.baglantiHatasiMetni(e);
        if (metin) this.hata = metin;
      }
    },
    /* WIG: hata metni SONRAKI ADIMI soyler. Web Serial'in Ingilizce metni ("Failed to open
       serial port.") tek basina bir sey anlatmiyor; en sik sebep portun baska bir programda
       (Arduino seri monitoru, tezgah betigi) acik olmasi. */
    baglantiHatasiMetni(e) {
      const ad = e && e.name;
      if (ad === 'NotFoundError') return '';
      const mesaj = (e && e.message) || String(e);
      if (ad === 'InvalidStateError' || ad === 'NetworkError') {
        return 'Bağlanamadı: ' + mesaj + ' — port başka bir program (Arduino seri monitör, tezgah betiği) '
          + 'tarafından kullanılıyor olabilir; onu kapatıp yeniden bağlanın.';
      }
      return 'Bağlanamadı: ' + mesaj + ' — kablo ve kartın açık olduğunu denetleyip yeniden deneyin.';
    },

    async kes() {
      await this.tasiyici.kapat(this);
      this.bagli = false;
      this.bagliTasiyici = null;
      this.pilBayat = true;              // 3F: yeniden baglaninca pil durumu yeniden sorulur
      this.kaydet('— bağlantı kesildi —');
    },

    /* ⚠ ÇAĞRI YERLERİ DEĞİŞMEDİ: `gonder('z')`, `gonder('F' + d)` …
       hepsi aynı şekilde duruyor. Değişen yalnızca burası. */
    async gonder(metin) {
      this.onay = null;                  // WIG: baska bir komut silahli onayi dusurur
      this.kaydet(metin, true);
      await this.tasiyici.gonder(this, metin);
    },

    // ─────────────────────────────────────────────── satır ayrıştırma
    satirIsle(satir) {
      if (!satir) return;

      // Osiloskop yakalaması sürüyorsa: önce M (ölçüm) ve E (bitiş)
      // satırlarını ayır, kalanı ham veri olarak topla.
      if (this.osiloTopla) {
        if (satir[0] === 'M' && satir[1] === ' ') {
          this.osiloTopla.olcum = this.skopMCoz(satir);
          return;
        }
        if (satir.trim() === 'E') {
          this.osiloBitir();
          return;
        }
        /* 🔴 B40 — DOKUM ARTIK OLCUMLE IC ICE GELEBILIR. Kart dokumu
           olcum dongusunu bloklamamak icin turlara boluyor; aradaki `D`
           ve `K` satirlari dokumun ICINE dusuyor (kartta goruldu).
           Eskiden BUTUN satirlar ornek sayiliyordu: `D 1.7156 0.00..`
           -> parseInt ile 1, 0, 0 ... dalgaya CÖP ornek olarak giriyor
           ve D satirinin kendisi olcum gostergesine hic ulasmiyordu.
           Artik yalnizca TAMAMI tam sayi olan satir ornek; digerleri
           asagidaki normal ayristirmaya dusuyor. */
        if (/^\d+(\s+\d+)*$/.test(satir.trim())) {
          for (const p of satir.trim().split(/\s+/)) {
            this.osiloTopla.veri.push(parseInt(p, 10));
          }
          if (this.osiloTopla.veri.length >= this.osiloTopla.adet) {
            this.osiloBitir();
          }
          return;
        }
      }

      const p = satir.split(/\s+/);

      /* 3D (D5): KAYIT DURUMU — kartin kendiliginden bastigi G / GA / GT / GP.
         Konsola da dusuyor (konsol "her satir burada" diyor; D/W/skop haric). */
      if (p[0] === 'G' || p[0] === 'GA' || p[0] === 'GT' || p[0] === 'GP') {
        const o = kayitSatiriCoz(satir);
        if (o) this.kayitSatiriIsle(o);
        this.kaydet(satir);
        return;
      }
      /* 3D (D1/D7): acilis afisi — surum + "kart yeniden basladi" olayi */
      const afis = afisCoz(satir);
      if (afis) {
        this.afisGoruldu(afis);
        this.kaydet(satir);
        return;
      }

      // S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
      //    [<volt_ofset>]   ← 9. alan B19'da eklendi (çift yönlü skop).
      //    Yoksa 0 kabul edilir; eski kartlarla geriye uyumlu.
      if (p[0] === 'S2' && p.length >= 8) {
        this.osiloTopla = {
          adet: parseInt(p[1], 10),
          hz: parseFloat(p[2]),
          voltAdim: parseFloat(p[3]),
          voltOfset: p.length >= 9 ? parseFloat(p[8]) : 0,
          tetikIdx: parseInt(p[4], 10),
          tdivUs: parseInt(p[5], 10),
          kip: parseInt(p[6], 10),
          tetiklendi: p[7] === '1',
          olcum: null,
          veri: [],
        };
        return;
      }

      /* CT <n> oran=<f> ofset=<f> tavan_mv=<f> <kod>:<mv> …
         Kalibrasyon tablosu. `CT 0 kaynak=YOK` gelirse tablo kurulmuyor
         ve arayüz bunu SÖYLÜYOR — düzeltmesiz bir eksen "kalibre"
         sanılmamalı. */
      if (p[0] === 'CT') {
        const n = parseInt(p[1], 10);
        if (!n) { this.skopKal = null; return; }
        const kal = { oran: 0, ofset: 0, tavanMv: 0, kod: [], mv: [] };
        for (const alan of p.slice(2)) {
          const e = alan.indexOf('=');
          if (e > 0) {
            const ad = alan.slice(0, e), d = parseFloat(alan.slice(e + 1));
            if (ad === 'oran') kal.oran = d;
            else if (ad === 'ofset') kal.ofset = d;
            else if (ad === 'tavan_mv') kal.tavanMv = d;
            continue;
          }
          const i = alan.indexOf(':');
          if (i > 0) {
            kal.kod.push(parseInt(alan.slice(0, i), 10));
            kal.mv.push(parseFloat(alan.slice(i + 1)));
          }
        }
        /* Eksik ya da bozuk tablo SESSİZCE kullanılmıyor: yarım bir
           tablo düzeltme yapıyormuş gibi görünüp ekseni bozardı. */
        /* ⚠ NaN DENETIMI DE SART. `256:abc` gibi bozuk bir cift
             `parseFloat` ile NaN uretiyor; uzunluklar tutuyor, `oran`
             yerinde, yani onceki denetimlerden GECIYORDU. Sonuc: her
             gerilim NaN olur ve dalga ekrandan SESSIZCE kaybolur —
             "kalibre" rozeti yanarken. */
        const sayiTamam = kal.kod.every(Number.isFinite)
                       && kal.mv.every(Number.isFinite)
                       && Number.isFinite(kal.oran);
        this.skopKal = (kal.oran > 0 && kal.kod.length >= 2
                        && kal.kod.length === kal.mv.length
                        && sayiTamam) ? kal : null;
        if (!this.skopKal) this.hata = 'Kalibrasyon tablosu okunamadı';
        this.$nextTick(() => this.osiloCiz());
        this.kaydet(satir);          // B45: konsol "her satır" diyor
        return;
      }

      // T tdiv=.. (..) hz=.. adet=.. — kartın bildirdiği skop ayarları
      if (p[0] === 'T' && satir.includes('tdiv=')) {
        const a = {};
        for (const alan of satir.slice(2).trim().split(/\s+/)) {
          const e = alan.indexOf('=');
          if (e > 0) a[alan.slice(0, e)] = alan.slice(e + 1);
        }
        this.skopAyar = a;
        /* Kartin bildirdigi ayarlari DENETIMLERE de yansit. Otomatik
           kurulumdan sonra kart tetik seviyesini ve zaman tabanini kendi
           seciyor; kaydiriciler eski degerde kalirsa arayuz yalan soyler
           (or. "tetik menzil disi" uyarisi yanlis cikar). */
        const sayi = (x) => { const n = parseInt(x, 10); return isNaN(n) ? null : n; };
        const td = sayi(a.tdiv);              // "6/11" -> 6
        if (td !== null && td >= 0 && td < SKOP_TDIV.length) this.skopTdiv = td;
        const es = sayi(a.esik);   if (es !== null) this.skopEsik = es;
        const on = sayi(a.on);     if (on !== null) this.skopOn = on;
        const kp = sayi(a.kip);    if (kp !== null) this.skopKip = kp;
        /* B47: eski firmware `onay=` göndermez → menü dokunulmaz, kartın
           davranışı o sürümde zaten tek örnek. */
        const on2 = sayi(a.onay);  if (on2 === 1 || on2 === 2) this.skopOnay = on2;
        if (a.kenar) this.skopKenar = a.kenar.startsWith('dus') ? 1 : 0;
        this.kaydet(satir);
        return;
      }

      /* B27/K5 — `?` yaniti: A menzil=... sont=<ohm> ... Kartin gercek
         ayari. Menu buna UYDURULUYOR; eslesen secenek yoksa menu
         dokunulmaz ama `kartSont` yine gosterilir — gercek her zaman
         gorunur olsun. */
      if (satir.startsWith('A menzil=')) {
        const m = satir.match(/\bsont=([\d.]+)/);
        if (m) {
          this.kartSont = parseFloat(m[1]);
          const secenek = ['10', '1', '0.1', '0.015']
            .find((s) => Math.abs(parseFloat(s) - this.kartSont) <= 0.01 * this.kartSont);
          if (secenek) this.sontSecim = secenek;
        }
        /* B27 A2: rapor araligi. Sont'un TERSI yon: sont fiziksel, kart
           haklidir; rapor araligi bir GORUNTULEME tercihi, tarayici
           haklidir. Kart farkli calisiyorsa ve surucuysek uydururuz.
           Eski firmware `rapor=` gondermez -> dokunulmaz. */
        const r = satir.match(/\brapor=(\d+)/);
        if (r) {
          this.kartRapor = parseInt(r[1], 10);
          if (this.kartRapor !== this.raporMs && this.surucuyum) {
            this.gonder('r' + this.raporMs).catch(() => {});
          }
        }
        /* 🔴 B45 — `A` SATIRI KONSOLA DÜŞMÜYORDU. "Ayarları göster"
           düğmesi `?` gönderiyor ve kullanıcı Konsol'da R/L/K/C/F
           satırlarını görüyordu ama AYARLARIN KENDİSİ (kazanç, sıfır,
           şönt, i_ofset, rapor) olan `A` satırı burada yutuluyordu
           (tarayıcıda görüldü). */
        this.kaydet(satir);
        return;
      }
      /* B30: CAL yaniti — `X cal_hz=6998 istenen=7000 ...` ya da
         `X cal=kapali`. GERCEKLESEN frekans buradan okunuyor. */
      if (satir.startsWith('X ')) {
        const m = satir.match(/cal_hz=(\d+)/);
        this.calGercek = m ? parseInt(m[1], 10) : null;
        const c = satir.match(/cozunurluk=(\d+)/);
        if (c) this.calCozunurluk = parseInt(c[1], 10);
        this.kaydet(satir);
        return;
      }
      /* Kartin `r` yaniti — KIRPILMIS deger buradan geliyor (r5 -> 20). */
      if (satir.startsWith('* rapor araligi ')) {
        const r = satir.match(/(\d+) ms/);
        if (r) {
          this.kartRapor = parseInt(r[1], 10);
          if (this.kartRapor !== this.raporMs) this.raporMs = this.kartRapor;
        }
        this.kaydet(satir);
        return;
      }

      if (p[0] === 'D' && p.length >= 7) {
        this.volt   = parseFloat(p[1]);
        this.amper  = parseFloat(p[2]);
        this.watt   = parseFloat(p[3]);
        this.joule  = parseFloat(p[4]);
        this.wh     = parseFloat(p[5]);
        const yeniMs = parseInt(p[6], 10);
        /* 3D: `ms` geri gittiyse (kart yeniden basladi / millis sardi) gecmisin
           zamani AZALMASIN — ayni sebeple aralik da hesaplanmaz. */
        const atlama = msAtlamasi(this.kartMs, yeniMs);
        if (atlama) this.msAtladi(atlama, yeniMs);
        else if (this.kartMs) this.sonAralik = yeniMs - this.kartMs;
        this.kartMs = yeniMs;
        this._sonDZaman = Date.now();
        this.ornekAdet = p.length >= 8 ? parseInt(p[7], 10) : 0;
        /* 9. alan Asama 3'te eklendi: hangi gerilim KANALI etkin.
           0 = NORMAL (+-32.4 V), 1 = YUKSEK (+-613.7 V).
           Asama 2 firmware'i bu alani gondermiyor; o zaman menzil
           bilinmiyor sayilir ve arayuz "—" gosterir. */
        this.menzil = p.length >= 9 ? parseInt(p[8], 10) : null;
        /* 🔴 B27/K1 — 10. alan `durum`: ADC yanıt verdi mi.
           bit0 = GERİLİM (0x49) okunamadı, bit1 = AKIM (0x48) okunamadı.
           Yokken firmware sessizce 0 dönüyor ve kalibrasyon o sıfıra
           uygulanıp kendinden emin bir "1.716 V" çıkıyordu — ters
           çevrilmiş sıfır-ofset sabiti. Çip bozulduğunda da aynı sahte
           sayı. Bu alan olmadan "veri yok" ile "veri sıfır" ayırt
           edilemiyordu. Eski firmware göndermez → 0 (bilinmiyor = güven). */
        this.adsDurum = p.length >= 10 ? parseInt(p[9], 10) : 0;

        if (this.ilkMs === null) this.ilkMs = this.kartMs + this.msKaydir;   // 3D: ilk nokta t = 0
        /* 🔴 B27 A2 — K1'in GRAFIK yarisi eksikti: kartlar "veri yok"
           derken grafik sahte 1.72 V'u duz cizgi olarak cizmeye, "tepe
           1.72 V" yazmaya devam ediyordu (kullanicinin ekran goruntusu,
           2026-09-12). Gecersiz kanal NaN olarak giriyor: cizgi KOPAR,
           tepe etiketi susar, CSV'de hucre bos kalir. */
        this.gecmis.push(Object.freeze({
          t: (this.kartMs + this.msKaydir - this.ilkMs) / 1000,
          v: this.voltGecersiz  ? NaN : this.volt,
          i: this.amperGecersiz ? NaN : this.amper,
          w: this.gucGecersiz   ? NaN : this.watt,
          e: this.wh,                       // 3D (D2): enerji karti 10 s araligi
        }));
        /* 20 satir/s'de 30 dk = 36 000 nokta; eski 20 000 tavani 30 dk
           penceresini sessizce kirpardi. */
        if (this.gecmis.length > 60000) this.gecmis.splice(0, 10000);
        this.grafikPlanla();
        return;
      }

      /* B8 — hizli yol guc olcumu.
         W <P> <S> <PF> <Vrms> <Irms> <Vort> <Iort> <n> <P_hizalamasiz>
         Son alan BILEREK var: hizalamanin ne kadar fark ettigi gorunsun. */
      if (p[0] === 'W' && p.length >= 10) {
        this.hizliHata = '';
        this.hizli = {
          p: parseFloat(p[1]),   s: parseFloat(p[2]),
          pf: parseFloat(p[3]),  vRms: parseFloat(p[4]),
          iRms: parseFloat(p[5]), vOrt: parseFloat(p[6]),
          iOrt: parseFloat(p[7]), n: parseInt(p[8], 10),
          pHam: parseFloat(p[9]),
          /* B39: 11. alan — olcekleme eFuse tablosuyla mi (1) ESKI
             dogrusal modelle mi (0) yapildi. Eski firmware bu alani
             yollamiyor: `null` = BILINMIYOR, "kalibre" DEGIL. Dogrusal
             model sifir giriste -6.9 V / -397 mA ofset veriyordu; bunu
             bilmeden okunan bir PF sessizce yanlis olur. */
          kal: p.length >= 11 ? p[10] === '1' : null,
        };
        return;
      }

      if (p[0] === 'S' && p.length >= 4) {
        this.osiloTopla = {
          adet: parseInt(p[1], 10),
          hz: parseFloat(p[2]),
          voltAdim: parseFloat(p[3]),
          veri: [],
        };
        return;
      }

      this.kaydet(satir);
      /* 3F (PL4): kartin pil satirlari PASIF — basladi / bitti / durduruldu / ret / B satiri */
      this.pilSatiri(satir);
      /* 3E (OS5): `GT` yalniz `G?` ile basiliyor; gunlugun KENDILIGINDEN durdugunu (Gd, oturum
         kapandi, oturum acilamadi) kartin kendi satiri soyluyor — yoklama yok (D5). */
      const gd = /^\* G osiloskop gunlugu durdu: (\d+) yakalama, (\d+) yazilamayan/.exec(satir);
      if ((gd || /^! G: osiloskop gunlugu oturumu acilamadi/.test(satir)) && this.kayit.gt) {
        if (this.kayit.gt.etkin) this.olayEkle(this.metin('cn.olay_skop_durdu'));
        this.kayit.gt = { ...this.kayit.gt, etkin: 0,
          ...(gd ? { yakalama: Number(gd[1]), yazilamayan: Number(gd[2]) } : {}) };
      }
      if (satir.startsWith('!')) {
        this.osiloBekliyor = false; this.skopIkiliBekle = false; this.skopIkiliOlcum = null;
        this.unlemSatiri(satir);          // 3D: D7 olay + D4 kayit komutunun reddi
      }
      /* 🔴 B43 — İKİLİ YOLDA ÖLÇÜM SATIRI. Kart `M`yi onay satırından hemen
         ÖNCE basıyor (`/skop.bin` başlığında yer yok). Eskiden ikili yolda
         `olcum` hep null'du: WiFi'de frekans/Vpp/duty satırı HİÇ çıkmıyordu.
         Yalnızca bekleme sürerken tutuluyor — başka bir anda gelen `M`
         (örneğin başka istemcinin ASCII dökümü) buraya düşmez: o döküm
         `S2` ile başlar ve yukarıdaki `osiloTopla` dalında tüketilir. */
      if (this.skopIkiliBekle && satir[0] === 'M' && satir[1] === ' ') {
        this.skopIkiliOlcum = this.skopMCoz(satir);
      }
      /* B40: ikili yakalama bitti — gövdeyi ŞİMDİ çek (sabit gecikme yok). */
      if (this.skopIkiliBekle && satir.startsWith('* skop yakalandi (ikili)')) {
        this.skopIkiliBekle = false;
        this.skopIkiliAl();
      }
      /* B27/K3: kart "giris rayda — sinyal yok" derse eski sonucu ekranda
         BIRAKMA. Bos giristen hesaplanan 223 W, kart artik basmiyor; ama
         bir onceki gecerli sonuc panelde kalsaydi kullanici onu yeni
         olcum sanirdi. */
      if (satir.startsWith('! hizli yol:')) {
        this.hizli = null;
        this.hizliHata = satir.slice(2).trim();
      }
    },

    // ─────────────────────────────────────────────── komutlar
    komut(k) { this.gonder(k); },

    /* B22.4 — AG KURULUMU. Akis bilerek boyle: USB ile bagla, WiFi'yi
       kur, sonra kablosuza gec. Kartin WiFi'sini kartin WiFi'si uzerinden
       kurmak tavuk-yumurta olurdu.
       ⚠ Parolalar duz metin gidiyor. USB'de sorun degil; ag uzerinden
         kuruluyorsa sablondaki uyari bunu soyluyor (TLS yok). */
    agSsidGonder() {
      if (!this.agSsid) { this.hata = 'Ağ adı boş olamaz'; return; }
      this.gonder('Na' + this.agSsid);
    },
    /* WIG: bos ag parolasi GITMEZ — kart bir sonraki acilista WPA agina baglanamaz, AP'ye
       duser, geri donmek USB ister. Parolasiz (acik) ag gercekten isteniyorsa Konsol'dan `Np`. */
    agSifreGonder() {
      if (!this.agSifre) { this.hata = 'Parola boş olamaz — parolasız (açık) ağ için Konsol\'dan Np gönderin.'; return; }
      this.gonder('Np' + this.agSifre); this.agSifre = '';
    },
    agWebSifreGonder() {
      /* WIG: bos gondermek parolayi KALDIRIR (firmware HEMEN uygular) — bos alan/Enter bunu
         artik yapmaz; koruma yalniz iki asamali "Korumayi kaldir" (agWebKorumaKaldir) ile kalkar. */
      if (!this.agWebSifre) { this.hata = 'Web parolası boş olamaz — korumayı kaldırmak için “Korumayı kaldır”ı kullanın.'; return; }
      this.gonder('Ns' + this.agWebSifre);
      this.agWebSifre = '';
    },
    agWebKorumaKaldir() { this.gonder('Ns'); },

    /* Köprüden sürücülüğü devral. Yetki sunucuda; arayüz yalnızca
       durumu gösteriyor ve devri istiyor — politikayı İKİ YERDE
       tutmak bu projenin cezalandırdığı ayrışma deseni olurdu. */
    async devral() {
      const y = await fetch(this.kartAdres('/devral'), {
        method: 'POST',
        headers: { 'X-Olcum': '1', 'X-Jeton': this.jeton || '' },
      }).catch(() => null);
      if (y && y.ok) { this.surucuyum = true; this.hata = ''; }
      else if (y && y.status === 409) this.hata = 'Devralınamadı (409): Başka bir sürücü etkin — o sekmeyi kapatıp yeniden deneyin.';
      else this.hata = 'Devralınamadı' + (y ? ' (' + y.status + ')' : '') + ' — köprünün çalıştığını denetleyip yeniden deneyin.';
    },

    /* ASAMA 3 komut kumesi.
       Asama 1: 'r', 'kv', 'ka'  ->  Asama 2: 's', 'v', 'i'
       Asama 3: 's', 'g', 'i' + 'z' 'Z' 'n' 'y' 'a'

       DIKKAT — 'z' ANLAMI DEGISTI: Asama 2'de AKIM sifiriydi, Asama 3'te
       GERILIM sifiri. Akim sifiri artik BUYUK 'Z'. Yanlis gonderilirse
       kart sessizce yanlis kanali sifirlar; DEVIR 4.1'in aynisi olurdu.
       test_arayuz3.js her komutu tek tek siniyor. */
    sontGonder() { this.gonder('s' + this.sontSecim); },
    /* Gerilim SIFIR — giris 0 V'a bagliyken. Cift yonlu olcumde bu,
       Vref'in gercek degerini ogrenmenin yolu. */
    sifirlaV() { this.gonder('z'); },
    /* Akim sifiri — yuk BAGLI DEGILken. */
    sifirlaA() { this.gonder('Z'); },
    kalibreV() {
      const v = parseFloat(this.kalibV.replace(',', '.'));
      /* v > 0 SARTI KALKTI: cift yonlu kartta negatif referansla da
         kalibre edilebilir. Yalnizca sifira yakin deger anlamsiz —
         onu firmware zaten reddediyor (tam olcegin %5'i esigi). */
      if (isFinite(v) && v !== 0) { this.gonder('g' + v); this.kalibV = ''; }
      else this.hata = 'Gerilim kalibrasyonu: sıfırdan farklı bir sayı girin (ör. 12.34 ya da −24).';
    },
    kalibreA() {
      const a = parseFloat(this.kalibA.replace(',', '.'));
      if (isFinite(a) && a !== 0) { this.gonder('i' + a); this.kalibA = ''; }
      else this.hata = 'Akım kalibrasyonu: sıfırdan farklı bir sayı girin, amper (ör. 0.250).';
    },
    menzilSec(m) {
      this.gonder(m === 1 ? 'y' : 'n');
      this.otoMenzil = false;
    },
    otoMenzilDegistir() {
      this.otoMenzil = !this.otoMenzil;
      this.gonder('a' + (this.otoMenzil ? '1' : '0'));
    },
    /* B20 — SEBEKE FREKANSI. Olcek duzeltmesi 1/|H(f)| ile gucu
       carpiyor; f yanlissa hata ONGORULEBILIR ama BUYUK olur.
       DC olcumunde 50 Hz ayari birakilirsa guc %82 yuksek okunur. */
    sebekeGonder() { this.gonder('f' + this.sebekeHz); },
    /* B20 — FAZ KALIBRASYONU. Direncli yukte gercek faz farki sifir
       olmali; okunan fark dogrudan suzgec eslesmezligidir. */
    /* B22.1: birim ORNEK degil MIKROSANIYE. Firmware'de faz_kal_us
       bolmenin icine girdigi icin duzeltme dongu periyodundan bagimsiz;
       sinir da +-2000 us oldu. Eskiden burada +-1 yaziyordu ve arayuz
       sinir disi degeri SESSIZCE yutuyordu — artik sebebini soyluyor. */
    /* WIG: hata ALANIN yaninda (fazHata, role=alert) — en ustteki genel kutu uzun Ayarlar
       sayfasinda gorus alaninin disinda kaliyordu. */
    fazGonder() {
      const d = parseFloat(String(this.fazKal).replace(',', '.'));
      if (!isFinite(d)) { this.fazHata = 'Faz kalibrasyonu: sayı girin (µs), ör. 120'; return; }
      if (d < -2000 || d > 2000) {
        this.fazHata = 'Faz kalibrasyonu −2000 … +2000 µs arası olmalı';
        return;
      }
      this.fazHata = '';
      this.gonder('F' + d);
      this.fazKal = '';
    },

    /* B22.1: FABRIKA SIFIRLAMA. Bozulmus bir NVS kaydindan kurtulmanin
       baska yolu yok. Iki asamali onay — tarayici confirm() kullanilmiyor
       cunku o hem sinanamiyor hem de kip kilitliyor. */
    fabrikaSifirla() {
      if (!this.sifirlaOnay) {
        this.sifirlaOnay = true;
        /* WIG: onay ONAY_MS sonra (ve gorunum degisince) duser — bayat "Eminim, sifirla" yok */
        if (this._sifirlaZaman) clearTimeout(this._sifirlaZaman);
        this._sifirlaZaman = setTimeout(() => { this.sifirlaOnay = false; }, ONAY_MS);
        return;
      }
      this.sifirlaOnay = false;
      this.gonder('R!');
    },
    fabrikaVazgec() {
      this.sifirlaOnay = false;
      this._odakla('[data-onay-ac="fabrika"]');
    },
    /* ── B21 · IndexedDB: sekme kapansa da veri kaybolmasın ─────────
       ⚠ IndexedDB tarayıcının verisidir — "tarayıcı verilerini temizle"
       denince gider. 3F'den beri ASIL KAYIT kartın PİL oturumu (1C-1;
       Kayıtlar, "Kayıtlar'da aç"); buradaki kopya canlı eğri ve kayıt
       açılamayan test için. CSV'si `pilCsvIndir()`. */
    async pilDb() {
      if (this._db) return this._db;
      this._db = await new Promise((coz, red) => {
        const i = indexedDB.open('olcum-pil', 1);
        i.onupgradeneeded = () => {
          i.result.createObjectStore('nokta', { keyPath: 'sira' });
        };
        i.onsuccess = () => coz(i.result);
        i.onerror = () => red(i.error);
      });
      return this._db;
    },
    async pilKaydet(noktalar) {
      try {
        const db = await this.pilDb();
        const iw = db.transaction('nokta', 'readwrite').objectStore('nokta');
        for (const n of noktalar) iw.put({ ...n });
      } catch (e) { /* IndexedDB yok (ozel kip): egri bu sekmede yine cizilir */ }
    },
    async pilYukle() {
      const db = await this.pilDb();
      const hepsi = await new Promise((coz) => {
        const r = db.transaction('nokta').objectStore('nokta').getAll();
        r.onsuccess = () => coz(r.result || []);
        r.onerror = () => coz([]);
      });
      hepsi.sort((a, b) => a.sira - b.sira);
      /* 3F: ogeler DONUK — Vue onlari reaktif vekile sarmaz (24 sa = 86 400 nokta) */
      this.pilNokta = hepsi.map((n) => Object.freeze(n));
      const son = hepsi.filter((n) => !n.bosluk).pop();
      this.pilYerelSira = hepsi.length ? Math.max(hepsi[hepsi.length - 1].sira + (hepsi[hepsi.length - 1].adet || 1), 0) : 0;
      this.pilBosluk = hepsi.reduce((t, n) => t + (n.bosluk ? n.adet || 0 : 0), 0);
      if (son && this.pilSonMs === null) this.pilSonMs = son.ms;
      this.pilCiz();
    },
    async pilTemizle() {
      this.onay = null;                  // WIG: iki asamali onay buradan geldi
      await this.pilYerelSifirla();
    },
    /** PU12: bu tarayicinin nokta kopyasi bastan (yeni test / kartin halkasi sifirlandi). */
    async pilYerelSifirla() {
      this.pilNokta = []; this.pilYerelSira = 0; this.pilBosluk = 0; this.pilSonMs = null;
      try {
        const db = await this.pilDb();
        db.transaction('nokta', 'readwrite').objectStore('nokta').clear();
      } catch (e) { /* IndexedDB yok */ }
      this.pilCiz();
    },
    /* Karttan durumu + eksik noktaları çek. */
    async pilYokla() {
      /* 🔴 B22.2 — ÜÇ KUSUR BİRDEN.
         (1) Adres GÖRELİYDİ: sayfa localhost:8772'den geldiği için istek
             karta değil Python sunucusuna gidiyordu. Artık kartAdres().
         (2) `fetch` 404'te REDDETMEZ. Yanıt gövdesi (Python'un HTML hata
             sayfası) `anahtar=değer` sanılıp ayrıştırılıyor, `a.durum`
             tanımsız kalıyor ve TÜM KPI'lar sessizce 0 oluyordu —
             başlangıçtaki `pilKesme: 3.0` bile eziliyordu.
         (3) Aynı sessiz bozulma KISMİ yanıtta da olur: kartta yığın
             sıkışırsa `String::concat` başarısız oluyor, `operator+=`
             bunu YUTUYOR ve gövde kesiliyor — ama Content-Length tutarlı
             olduğu için tarayıcı hata görmüyor. Biçim denetimi ikisini de
             kapatıyor. */
      if (this.pilKaynak === 'satir') {
        /* PU13: USB / köprü — `/pil` yok; durum `p`nin B satırından (pilSatiri). İzleyici
           (köprüde sürücü değil) komut gönderemez: yalnız kartın kendi satırları. */
        if (this.bagli && this.surucuyum) await this.gonder('p').catch(() => {});
        return;
      }
      /* Kart tek yanıtta en çok 150 nokta veriyor (`kalan=`); yeniden bağlanma dolgusunda AYNI
         yoklamada devam (ağ çekirdeğinde, ölçümü bloklamıyor — PL4). */
      for (let dolgu = 0; dolgu < PIL_DOLGU_AZAMI; dolgu++) {
        let m;
        try {
          if (this.pilKaynak === 'demo') {
            if (typeof SahteKart === 'undefined' || typeof SahteKart.pilSayfa !== 'function') return;
            m = SahteKart.pilSayfa(this.pilYerelSira);
          } else {
            const y = await fetch(this.kartAdres('/pil?sira=' + this.pilYerelSira), { cache: 'no-store' });
            if (!y.ok) {
              this.pilHataMetni = 'kart yanıt vermiyor (HTTP ' + y.status + ')';
              return;
            }
            m = await y.text();
          }
        } catch (e) {
          this.pilHataMetni = 'karta ulaşılamıyor: ' + e.message;
          return;
        }
        if (m.indexOf('durum=') !== 0) {
          this.pilHataMetni = 'beklenmeyen yanıt — kart adresi doğru mu?';
          return;
        }
        this.pilHataMetni = '';
        const AYRAC = '\n--\n';
        const k0 = m.indexOf(AYRAC);
        const bas = k0 < 0 ? m : m.slice(0, k0);
        const govde = k0 < 0 ? '' : m.slice(k0 + AYRAC.length);
        const a = {};
        for (const s of bas.split('\n')) {
          const k = s.indexOf('=');
          if (k > 0) a[s.slice(0, k)] = s.slice(k + 1);
        }
        /* 🔴 3F (PU12): kartın halkası SIFIRLANDI (yeni test, `p1`): `sira` bizdekinden küçük.
           Eski testin sırasıyla sormak yeni testin noktalarını HİÇ getirmiyordu (kart o sırayı
           henüz üretmemiş → 0 nokta). Yerel kopya baştan, AYNI döngüde 0'dan istenir. Kart
           yeniden başladıysa (BEKLEMEDE, sira 0) eski testin eğrisi KORUNUR. */
        const kartSira = parseInt(a.sira, 10) || 0;
        if (kartSira < this.pilYerelSira && (a.durum === 'CALISIYOR' || kartSira > 0)) {
          this.pilDcirListe = [];
          await this.pilYerelSifirla();
          continue;
        }
        this.pilDurumYaz({
          durum: a.durum || '-', hata: a.hata || '-', mah: parseFloat(a.mah), wh: parseFloat(a.wh),
          coulomb: parseFloat(a.coulomb), ocv: parseFloat(a.ocv), vson: parseFloat(a.vson), kesme: parseFloat(a.kesme),
          dcirAni: parseFloat(a.dcir_ani), dcirOtr: parseFloat(a.dcir_otr), dcirN: parseInt(a.dcir_n, 10), sira: kartSira,
        }, true);
        /* 🔴 BOŞLUK: kart istediğimiz noktayı artık tutmuyorsa `ilk_sira`
           istediğimizden BÜYÜK döner. Bunu SAKLAMIYORUZ — işaretliyoruz. */
        const ilk = parseInt(a.ilk_sira) || 0;
        if (ilk > this.pilYerelSira && this.pilYerelSira > 0) {
          this.pilBosluk += ilk - this.pilYerelSira;
          const isaret = Object.freeze({ sira: this.pilYerelSira, bosluk: true, adet: ilk - this.pilYerelSira });
          this.pilNokta.push(isaret);
          await this.pilKaydet([isaret]);
          this.pilYerelSira = ilk;
        }
        const yeni = [];
        let sira = ilk;
        for (const s of govde.split('\n')) {
          if (!s) continue;
          const p = s.split(',');
          if (p.length < 3) continue;
          yeni.push(Object.freeze({ sira: sira++, ms: +p[0], v: +p[1], i: +p[2] }));
        }
        if (yeni.length) {
          this.pilNokta.push(...yeni);
          this.pilYerelSira = sira;
          this.pilSonMs = yeni[yeni.length - 1].ms;
          await this.pilKaydet(yeni);
        }
        this.pilCiz();
        if (!((parseInt(a.kalan, 10) || 0) > 0) || !yeni.length) return;
      }
    },
    /** `/pil` alanları ya da `p`nin B satırı → durum (PU8: sayaçlar KARTIN). `yoklamadan`: bu yanıt
     *  zaten son hal — bitiş geçişi yeni bir istek doğurmaz. */
    pilDurumYaz(a, yoklamadan = false) {
      const sayi = (x, v) => (Number.isFinite(x) ? x : v);
      this.pilHata = a.hata || '-';
      this.pilMah = sayi(a.mah, 0);
      this.pilWh = sayi(a.wh, 0);
      this.pilCoulomb = sayi(a.coulomb, 0);
      this.pilOcv = sayi(a.ocv, 0);
      this.pilVson = sayi(a.vson, 0);
      this.pilKesme = sayi(a.kesme, 0);
      this.pilDcirAni = sayi(a.dcirAni, 0);
      this.pilDcirOtr = sayi(a.dcirOtr, 0);
      this.pilDcirN = sayi(a.dcirN, 0);
      this.pilSira = sayi(a.sira, 0);
      this.pilKesmeBilinen = true;
      this.pilTazeZaman = Date.now();
      this.pilBayat = false;
      if (a.durum === 'CALISIYOR') this.pilDcirGozle(this.pilDcirN, this.pilDcirAni, this.pilDcirOtr, this.pilMah);
      this.pilDurumAyarla(a.durum, yoklamadan);
    },
    /** PU10: `dcir_n` arttı → son ölçüm listeye (mAh yoklama anında: "≈"); arada görülmeyen
     *  numaralar "görülmedi" (değerleri kayıtta). Zaman kartın kuralından (pilDcirAniMs). */
    pilDcirGozle(n, rAni, rOtr, mah) {
      const l = this.pilDcirListe;
      const son = l.reduce((x, d) => Math.max(x, d.no), 0);
      if (!(n > son)) return;
      const yeni = l.slice();
      for (let k = son + 1; k < n; k++) yeni.push({ no: k, tMs: pilDcirAniMs(k), gorulmedi: true });
      yeni.push({ no: n, tMs: pilDcirAniMs(n), rAni, rOtr, mah, yaklasik: true });
      this.pilDcirListe = yeni;
      this.pilSakla();
      this.pilCiz();
    },
    /** Durum geçişi (kartın satırından ya da yoklamadan). Bitişte: oturum beklemesi düşer,
     *  son hal alınmadıysa (`bayat`) Pil sekmesi görünürse BİR `/pil`, değilse sekme açılınca;
     *  sonra kayıt kaynağı (PU11). */
    pilDurumAyarla(yeni, yoklamadan = false) {
      const eski = this.pilDurum;
      this.pilDurum = yeni;
      if (eski === yeni) return;
      if (yeni === 'CALISIYOR') {
        this.pilDuyuru = this.m.pilCalisiyor;
        /* test (yeniden) suruyor: kayit kaynagi canli kopyaya doner, bitince yeniden acilir */
        this.pilKayitOzet = null;
        this._pilKayit = null;
        this._pilKayitDenendi = null;
      }
      if (eski === 'CALISIYOR') {
        this.pilDuyuru = this.metin('pl.duyuru_bitti', { durum: this.pilDurumYazi });
        this.pilOturumBekle = null;
        if (yoklamadan) {
          this.pilBayat = false;
        } else {
          this.pilBayat = true;
          if (this.bagli && this.gorunum === 'pil' && this.sayfaGorunur) this.pilTazele();
        }
        this.pilKayitIste();
      }
    },
    /** Tek seferlik durum (PL4): eşzamanlı ikinci istek yok. */
    async pilTazele() {
      if (!this.bagli || this._pilMesgul) return;
      this._pilMesgul = true;
      try {
        /* yerel kopya (IndexedDB) once: yoksa yenilemede `/pil` 0'dan istenir, egri iki kez gelir */
        if (this._pilYuklendi) await this._pilYuklendi;
        await this.pilYokla();
      } finally {
        this._pilMesgul = false;
      }
      this.pilKayitIste();
    },
    /** Bağlanınca bir kez (PL4): acil şerit için durum. Köprü algılaması (kopruYokla, beklenmez)
     *  bitene dek en çok ~3 s — köprüde `/pil` yok, `p` gerekir (PU13). */
    async pilIlkTazele() {
      this.pilBayat = true;
      for (let k = 0; k < 30 && !this._kopruBilindi; k++) await new Promise((coz) => setTimeout(coz, 100));
      await this.pilTazele();
    },
    /** PL4: sürekli yoklama yalnız `pilYoklamaAcik` iken; nesil sayacı eski döngüyü durdurur. */
    pilYoklamaKur(acik) {
      if (this.pilZaman) { clearTimeout(this.pilZaman); this.pilZaman = null; }
      this._pilNesil = (this._pilNesil || 0) + 1;
      if (!acik) return;
      const nesil = this._pilNesil;
      const tik = async () => {
        if (nesil !== this._pilNesil || !this.pilYoklamaAcik) return;
        await this.pilTazele();
        if (nesil !== this._pilNesil || !this.pilYoklamaAcik) return;
        this.pilZaman = setTimeout(tik, PIL_YOKLAMA_MS);
      };
      tik();
    },
    /** Pil sekmesi göründü: modül (ilk kez), durum bayatsa BİR `/pil` (test sürüyorsa yoklama
     *  zaten başlar), bitmiş testin kaydı. */
    pilGorundu() {
      this.pilAcik = true;
      if (this.bagli && this.pilBayat && !this.pilCalisiyor) this.pilTazele();
      this.pilKayitIste();
    },
    /** Kartın pil satırları (pilSatirOlayi) — PASİF: her istemci SSE'den alır (PL4). */
    pilSatiri(satir) {
      const o = pilSatirOlayi(satir);
      if (!o) {
        /* PU7: `Ga` (oturuma ad) reddi — komuttan sonraki 5 s içinde gelen `! G…` */
        if (/^! ?G\b/.test(satir) && Date.now() - (this._pilAdZamani || 0) < RET_PENCERESI_MS) {
          this.pilUyari = { tur: 'kart', metin: this.metin('pl.kart_reddetti', { satir }) };
        }
        return;
      }
      if (o.tur === 'durum') {
        this.pilDurumYaz(o, true);
        this.pilSonMs = o.sureS * 1000;
        return;
      }
      if (o.tur === 'basladi') {
        this.pilYeniTest();
        this.pilOcv = o.ocv; this.pilKesme = o.kesme; this.pilHata = '-';
        this.pilMah = 0; this.pilWh = 0; this.pilCoulomb = 0; this.pilVson = o.ocv;
        this.pilDcirAni = 0; this.pilDcirOtr = 0; this.pilDcirN = 0; this.pilSira = 0;
        this.pilKesmeBilinen = true;
        this.pilTazeZaman = Date.now();
        this.pilSonMs = 0;
        this.pilDurumAyarla('CALISIYOR');
        /* PU4: kartın BAŞLATTIĞI kesme bu panelin istediği değil → yük HEMEN kesilir. Yanlış
           kesmeyle deşarj (ör. kurşun-asit 3 V'a kadar) pili bitirir. */
        const ist = this._pilIstenenKesme;
        this._pilIstenenKesme = null;
        if (Number.isFinite(ist) && Math.abs(o.kesme - ist) > 0.0006) {
          this.pilDurdurKomut();
          this.pilUyari = { tur: 'panel', metin: this.metin('pl.hata_kesme_farkli', { kart: this.bicim(o.kesme, 3), istenen: this.bicim(ist, 3) }) };
        }
        return;
      }
      if (o.tur === 'bitti') { this.pilMah = o.mah; this.pilWh = o.wh; this.pilHata = '-'; this.pilDurumAyarla('BITTI'); return; }
      if (o.tur === 'durduruldu') { this.pilDurumAyarla('DURDURULDU'); return; }
      if (o.tur === 'sure') { this.pilHata = 'azami sure asildi'; this.pilDurumAyarla('HATA'); return; }
      if (o.tur === 'calismiyor') {
        /* p0'a "zaten çalışmıyor": panel çalışıyor sanıyorduysa son hali sor */
        if (this.pilCalisiyor) this.pilDurumAyarla('BEKLEMEDE');
        return;
      }
      if (o.tur === 'reddedildi') {
        this.pilHata = o.hata;
        this.pilDurumAyarla('HATA');
        this.pilUyari = { tur: 'kart', metin: this.metin('pl.kart_reddetti', { satir }) };
        return;
      }
      if (o.tur === 'kaydedilmiyor') {
        this.pilKayitYok = o.neden;
        this.pilOturumBekle = null;
        this.pilOturum = null;
        this.pilSakla();
        this.pilUyari = { tur: 'kart', metin: this.metin('pl.kart_kaydedilmiyor', { satir }) };
        return;
      }
      if (o.tur === 'kesme') {
        this.pilKesme = o.v;
        this.pilKesmeBilinen = true;
        this._pilKesmeOnay = o.v;
        return;
      }
      /* PL5 (E9): komuttan sonraki 5 s içinde gelen `! pil…` / `! P:` o komutun reddi — OLDUĞU GİBİ */
      if (o.tur === 'ret' && Date.now() - this.pilKomutZamani < RET_PENCERESI_MS) {
        this.pilUyari = { tur: 'kart', metin: this.metin('pl.kart_reddetti', { satir }) };
      }
    },
    /** BAŞLADI görüldü: yerel kopya, DCIR listesi, oturum ve kayıt kaynağı baştan (PU12). PİL
     *  oturumu, p1'den önce açık olan oturumdan FARKLI ilk KAYIT durumlu G'dir (PU6). */
    pilYeniTest() {
      const g = this.kayit.g;
      this.pilOturumBekle = { onceki: g && g.durum === KDR.KAYIT ? g.oturum : null, zaman: Date.now() };
      this.pilOturum = null;
      this.pilKayitYok = '';
      this.pilDcirListe = [];
      this.pilKayitOzet = null;
      this._pilKayit = null;
      this._pilKayitDenendi = null;
      this.pilKayitDurum = '';
      this.pilSakla();
      this.pilYerelSifirla();
    },
    /** PU6: PİL oturumunun numarası YALNIZ `G` satırından (`/pil` ve OLAY taşımıyor). */
    pilGIsle(o) {
      if (!o || o.durum !== KDR.KAYIT) return;
      const b = this.pilOturumBekle;
      if (b) {
        if (o.oturum === b.onceki && Date.now() - b.zaman < 15000) return;   // eski ölçüm oturumu henüz kapanmadı
        this.pilOturumBekle = null;
        if (o.oturum !== b.onceki) this.pilOturumKur(o.oturum, false);
        return;
      }
      /* Test sürerken açılan sayfa: başlangıç GÖRÜLMEDİ. Pil sürerken `Gb` reddedilir ve p1 açık
         ölçüm kaydını kapatır → kayıttaki oturum PİL'dir (p1'den sonraki ilk ~1 s hariç). */
      if (this.pilCalisiyor && !this.pilOturum && !this.pilKayitYok) this.pilOturumKur(o.oturum, true);
    },
    pilOturumKur(no, gorulmedi) {
      this.pilOturum = { no, gorulmedi: !!gorulmedi };
      this.pilSakla();
      const ad = this.pilAdBekleyen;
      if (ad) { this.pilAdBekleyen = ''; this.pilAdGonder(ad); }
    },
    /** PU7: oturuma ad (`Ga<oturum> <ad>`); numara bilinmiyorsa başlatmada bekletilir. */
    pilAdGonder(ad) {
      const k = pilAdKomutu(this.pilOturum ? this.pilOturum.no : 0, ad);
      if (k.hata) {
        this.pilUyari = { tur: 'panel', metin: this.metin(k.hata, { bayt: k.bayt, azami: NOT_METIN_AZAMI_BAYT }) };
        return Promise.resolve(false);
      }
      this._pilAdZamani = Date.now();
      return this.gonder(k.komut).then(() => true, () => false);
    },
    pilAdVer() {
      return this.pilAdGonder(this.pilAd).then((g) => { if (g) this.pilAd = ''; return g; });
    },
    /** Son testin oturumu ve DCIR listesi yenilemeden sonra da dursun (localStorage; kart başına değil). */
    pilSakla() {
      try {
        localStorage.setItem(PIL_SAKLA, JSON.stringify({ oturum: this.pilOturum, kayitYok: this.pilKayitYok,
          dcir: this.pilDcirListe }));
      } catch (e) { /* özel kip: yenilemede bağlantı / tablo kaybolur, ölçüm etkilenmez */ }
    },
    pilSaklananiOku() {
      let v = null;
      try { v = JSON.parse(localStorage.getItem(PIL_SAKLA)); } catch (e) { v = null; }
      if (!v || typeof v !== 'object') return;
      if (v.oturum && Number.isInteger(v.oturum.no) && v.oturum.no > 0) this.pilOturum = { no: v.oturum.no, gorulmedi: !!v.oturum.gorulmedi };
      if (typeof v.kayitYok === 'string') this.pilKayitYok = v.kayitYok;
      if (Array.isArray(v.dcir)) this.pilDcirListe = v.dcir.filter((d) => d && Number.isInteger(d.no) && d.no > 0);
    },
    /** PL5 + PU4: kesme (gerekirse `P<v>` + kartın onayı) → `p1`. Kart onaylamazsa p1 GİTMEZ. */
    async pilBaslat() {
      if (this.pilBaslatiliyor) return false;
      const giris = String(this.pilKesmeGiris || '').trim();
      const k = giris ? pilKesmeKomutu(giris) : this.pilKesmeBilinen ? { v: this.pilKesme } : { hata: 'pl.hata_kesme_yok' };
      const panel = (anahtar, d = {}) => { this.pilUyari = { tur: 'panel', metin: this.metin(anahtar, d) }; return false; };
      if (k.hata) return panel(k.hata);
      const ad = String(this.pilAd || '').trim();
      if (ad) {
        const a = pilAdKomutu(1, ad);
        if (a.hata) return panel(a.hata, { bayt: a.bayt, azami: NOT_METIN_AZAMI_BAYT });
      }
      if (!this.bagli) return panel('pl.hata_bagli_degil');
      this.pilUyari = null;
      this.pilBaslatiliyor = true;
      try {
        if (!this.pilKesmeBilinen || Math.abs(k.v - this.pilKesme) > 0.0006) {
          this.pilKesmeGiris = String(k.v);
          const v = await this.pilKesmeGonder();
          if (v === null) return false;
          if (!(await this.pilKesmeOnayBekle(v))) return panel('pl.hata_kesme_onay', { v });
        }
        this._pilIstenenKesme = k.v;
        this.pilAdBekleyen = ad;
        this.pilAd = '';
        this.pilKesmeGiris = '';
        this.pilKomutZamani = Date.now();
        await this.gonder('p1');
        return true;
      } catch (e) {
        return panel('pl.hata_gonderilemedi', { mesaj: (e && e.message) || String(e) });
      } finally {
        this.pilBaslatiliyor = false;
      }
    },
    pilDurdurKomut() { this.gonder('p0'); },
    /** PL5: kesme gerilimini karta yaz (`P<v>`, NVS). Geçersizse komut GİTMEZ, sebep alanın
     *  yanında (WIG; eskiden en üstteki genel kutudaydı). Dönüş gönderilen v ya da null. */
    pilKesmeGonder() {
      const k = pilKesmeKomutu(this.pilKesmeGiris);
      if (k.hata) {
        this.pilUyari = { tur: 'panel', metin: this.metin(k.hata) };
        return Promise.resolve(null);
      }
      this.pilKomutZamani = Date.now();
      this._pilKesmeOnay = null;
      return this.gonder('P' + k.v).then(() => k.v);
    },
    /** PU4: kartın `* pil kesme gerilimi <v> V` satırını bekle (WiFi'de yanıt gövdesinde, USB /
     *  köprüde akışta gelir). */
    async pilKesmeOnayBekle(v) {
      const son = Date.now() + PIL_KESME_ONAY_MS;
      while (Date.now() < son) {
        if (Number.isFinite(this._pilKesmeOnay) && Math.abs(this._pilKesmeOnay - v) <= 0.0006) return true;
        await new Promise((coz) => setTimeout(coz, 50));
      }
      return Number.isFinite(this._pilKesmeOnay) && Math.abs(this._pilKesmeOnay - v) <= 0.0006;
    },
    pilHazirSec(v) { this.pilKesmeGiris = String(v); },
    pilCsvIndir() {
      const satir = ['sira,ms,volt,amper,bosluk'];
      for (const n of this.pilNokta) {
        satir.push(n.bosluk ? (n.sira + ',,,,1')
                            : [n.sira, n.ms, n.v, n.i, 0].join(','));
      }
      const a = document.createElement('a');
      a.href = URL.createObjectURL(
        new Blob([satir.join('\n')], { type: 'text/csv' }));
      a.download = 'pil-testi.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    },
    /** PL6: pil CSV'si KAYITTAN (3C `pilCsv`: noktalar + DCIR satırları, Excel-TR). */
    pilKayitCsv() {
      const r = this._pilKayit;
      if (!r || typeof r.csv !== 'function' || typeof document === 'undefined') return;
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([r.csv('tr')], { type: 'text/csv' }));
      a.download = 'pil-oturum-' + r.ozet.oturum + '.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    },
    /* ── 3F — eğri modülü (ekran/pil.js; PL3) ── */
    async pilModYukle() {
      if (this._pilGrafik || this.pilModDurum === 'yukleniyor') return;
      this.pilModDurum = 'yukleniyor';
      try {
        const mod = await import('./ekran/pil.js');
        await this.$nextTick();
        const tuval = this.$refs.pilTuval;
        if (!tuval) throw new Error('pil tuvali yok');
        this._pilMod = mod;
        this._pilGrafik = new mod.PilGrafik(tuval, { pencere: window, degisti: (b) => { this.pilBilgi = b; } });
        this.pilModDurum = 'hazir';
        this.pilCiz();
        this.pilKayitIste();
      } catch (e) {
        /* Modul inmedi (kart yeniden basliyor, bayat goruntu): sebep + care ekranda. DURDUR ve
           okuma kartlari bu modulu BEKLEMEZ (PU1). */
        this.pilModDurum = 'yuklenemedi';
      }
    },
    pilCiz() {
      if (!this._pilGrafik || this.gorunum !== 'pil') return;
      const k = this._pilKayit;
      this._pilGrafik.ciz({ nokta: this.pilNokta, kayit: k, eksen: this.pilEksen,
        dcir: k ? k.ozet.dcir : this.pilDcirListe, dil: this.dil });
    },
    pilImlecTemizle() { if (this._pilGrafik) this._pilGrafik.imlecTemizle(); },
    /** PU11: test sürmüyor ve oturum biliniyorsa (Pil sekmesi görünürken) kaydı bir kez aç. */
    pilKayitIste() {
      /* durum BILINMEDEN (yenileme sonrasi ilk /pil gelmeden) kayit acilmaz: suren testin yarim
         kaydi "bitmis testin kaynagi" sanilirdi (T3F yenilemede yakaladi) */
      if (!this._pilMod || this.pilCalisiyor || this.pilBayat || !this.pilOturum || this.gorunum !== 'pil') return;
      const no = this.pilOturum.no;
      if (this._pilKayitDenendi === no) return;
      this._pilKayitDenendi = no;
      this.pilKayitYukle(no);
    },
    async pilKayitYukle(no) {
      const mod = this._pilMod;
      const kartAdres = (y) => this.kartAdres(y);
      this.pilKayitDurum = 'yukleniyor';
      this.pilKayitMesaj = '';
      let r = await mod.pilKaydiAc({ oturum: no, kimlik: null }, { kartAdres, dil: this.dil });
      if (r.hata === 'pl.hata_kayit_yok' && this.bagli) {
        this.pilKayitDurum = 'esitleniyor';
        const e = await mod.pilKaydiEsitle({ kartAdres, kartTaban: this.kartTaban, tasiyici: this.bagliTasiyici || this.tasiyiciAdi,
          kopruda: this.kopruda, bagli: this.bagli, gonder: (k) => this.gonder(k) });
        if (e.durum === 'tamam') r = await mod.pilKaydiAc({ oturum: no, kimlik: null }, { kartAdres, dil: this.dil });
        else if (e.durum !== 'uygun_degil') r = { hata: 'pl.hata_esitleme', d: { mesaj: e.mesaj || e.durum } };
      }
      if (!this.pilOturum || this.pilOturum.no !== no) return;      // bu arada yeni test başladı
      if (r.hata) {
        this.pilKayitDurum = r.hata === 'pl.hata_kayit_yok' ? 'yok' : 'hata';
        this.pilKayitMesaj = r.d && r.d.mesaj ? r.d.mesaj : '';
        return;
      }
      this._pilKayit = r;
      this.pilKayitOzet = r.ozet;
      this.pilKayitDurum = '';
      this.pilCiz();
    },
    enerjiSifirla() { this.gonder('e'); },
    hizliOlc() { this.gonder('w'); },
    elleGonder() {
      if (this.elleKomut) { this.gonder(this.elleKomut); this.elleKomut = ''; }
    },

    /* ─────────────────────────────────────────────── osiloskop denetimi */
    /* B22.5 — İKİ ÇÖZÜCÜ, TEK GÖSTERİCİ.
       Taşıyıcı ikili destekliyorsa (`yetenek.skop === 'ikili'`) kart
       `tB` ile ASCII DÖKMEDEN yakalıyor ve gövde `/skop.bin`'den
       çekiliyor: 4000 örnekte 20 250 B yerine 8 032 B, ve dökümün
       kendisi SSE'yi tıkamıyor.
       ⚠ İkisi de AYNI `osiloTopla` yapısını kurup AYNI `osiloBitir()`
         çağırıyor. Çizim kodu iki kez yazılmıyor — yazılsaydı ikisi
         ayrışırdı ve biri sessizce yanlış çizerdi. */
    osiloYakala() {
      this.osiloBekliyor = true;
      this.osiloTopla = null;
      this.skopAcikKayit = null;     // canli yakalama: artik arsiv kaydi degil
      this.skopKayitliCik();         // 3E (OS6): kayitli yakalama da degil
      this.skopKomutZamani = Date.now();
      this.skopYakalamaUyari = '';
      /* 🔴 KÖPRÜDE ASCII YOLU DOĞRU OLAN — sezgiye ters ama ölçülebilir.
         `tB` + `/skop.bin` WiFi'de doğru: dökümü SSE'den geçirmeyip
         gövdeyi ayrı çekiyor, aynı veri iki kez taşınmıyor.
         Köprüde durum TERS: köprü karta USB'den bağlı ve dökümü ZATEN
         seri porttan almak zorunda (arşive düşmesi için tek yol; kartta
         ikili-seri dökümü diye bir şey yok). O döküm geldiğine göre
         ayrıca `/skop.bin` çekmek AYNI dalgayı ikinci kez taşımak ve
         AYNI dalgayı iki kez çizmek olurdu — B22.5'te tam da bundan
         kaçınılmıştı.
         Pahalı bağlantı kart↔köprü (115 200 baud, 4000 örnek ≈ 1.8 s);
         köprü↔tarayıcı LAN. Bedel her iki durumda da seri portta
         ödeniyor, yani ASCII yolu burada BEDAVA. */
      if (this.skopArsivVar) {
        this.gonder('t');
      } else if (this.yetenek.skop === 'ikili') {
        /* 🔴 B40 — SABİT 400 ms BEKLEME KALDIRILDI. Yakalama süresi zaman
           tabanına ve tetiğe bağlı: OTO kipte tetik yoksa zaman aşımı
           `pencere × 4 + 300 ms`, tb7'de ~1.1 s. 400 ms sonra çekilen
           `/skop.bin` kilidi yakalamada bulup 200 ms bekliyor ve 503
           dönüyordu — yavaş zaman tabanlarında WiFi skobu hiç
           çalışmıyordu. Artık kartın "* skop yakalandi (ikili)" satırı
           GELİNCE çekiliyor (`satirIsle`). */
        this.skopIkiliOlcum = null;   // önceki yakalamanın ölçümü bu kayda yapışmasın
        this.skopIkiliBekle = true;
        this.gonder('tB');
      } else {
        this.gonder('t');
      }
      setTimeout(() => { this.osiloBekliyor = false; }, 20000);
    },

    async skopIkiliAl() {
      /* ⚠ KÖPRÜDE BU İSTEK UZUN SÜREBİLİR. Kartta gövde hazır bekliyor;
         köprüde ise köprü kartın ASCII dökümünü seri porttan topluyor
         (4000 örnek ~20 KB, 115 200 baud'da ~1.8 s). Sunucu 503 dönerse
         SEBEBİ gövdede yazıyor — "alınamadı (503)" tek başına kullanıcıya
         "tetiklenemedi mi, kırpık mı" sorusunu yanıtlamıyor. */
      const y = await fetch(this.kartAdres('/skop.bin')).catch(() => null);
      if (!y || !y.ok) {
        const neden = y ? await y.text().catch(() => '') : '';
        this.hata = 'İkili skop dökümü alınamadı'
                  + (y ? ' (' + y.status + ')' : '')
                  + (neden ? ': ' + neden : '');
        this.osiloBekliyor = false;
        return false;
      }
      return this.skopIkiliCoz(await y.arrayBuffer());
    },

    /* 🔴 TEK İKİLİ ÇÖZÜCÜ. Canlı yakalama da arşivden açılan eski kayıt
       da buradan geçiyor. İki çözücü yazılsaydı biri sessizce başka bir
       dalga çizerdi — bu projenin defalarca yandığı ayrışma sınıfı
       (DEVIR 4.1, 4.15, B17). */
    skopIkiliCoz(b) {
      if (b.byteLength < 32) {
        this.hata = 'skop.bin çok kısa'; this.osiloBekliyor = false; return false;
      }
      const d = new DataView(b);
      /* İmza denetimi: kısmi/yanlış yanıt sessizce çizilmesin. */
      if (d.getUint8(0) !== 0x53 || d.getUint8(1) !== 0x33
          || d.getUint8(2) !== 0x42) {
        this.hata = 'skop.bin imzası yanlış'; this.osiloBekliyor = false; return false;
      }
      const adet = d.getUint16(4, true);
      if (b.byteLength < 32 + adet * 2) {
        this.hata = 'skop.bin eksik (' + b.byteLength + ' B, ' + adet + ' örnek)';
        this.osiloBekliyor = false;
        return false;
      }
      this.osiloTopla = {
        adet,
        hz: d.getUint32(8, true),
        voltAdim: d.getFloat32(12, true),
        voltOfset: d.getFloat32(16, true),
        tetikIdx: d.getUint16(24, true),
        tdivUs: d.getUint32(20, true),
        kip: d.getUint8(26),
        tetiklendi: d.getUint8(27) === 1,
        /* B43: canlı yakalamada onaydan önce gelen `M`. Arşiv kaydına
           BAĞLANMIYOR — o anki bekleyen ölçüm başka bir dalganındır.
           (Arşiv kayıtlarında ölçüm satırı yok: bilinen eksik.) */
        olcum: this.skopArsivtenAciliyor ? null : this.skopIkiliOlcum,
        veri: [],
      };
      this.skopIkiliOlcum = null;
      /* DataView ile AÇIKÇA küçük-endian — Uint16Array platformun
         endian'ını kullanır ve sessizce yanlış okuyabilirdi. */
      for (let i = 0; i < adet; i++) {
        this.osiloTopla.veri.push(d.getUint16(32 + i * 2, true));
      }
      this.osiloBitir();
      return true;
    },
    /* ── skop arşivi (B35) ─────────────────────────────────────────
       Köprü kipinde her yakalama `Serial`den geçtiği için köprünün
       `.satir` günlüğüne düşüyor; liste o günlükten TÜRETİLİYOR, ayrı
       bir dosyada tutulmuyor (iki temsil ayrışırdı). */
    async kopruYokla() {
      /* Kart `/durum` açmıyor; yanıt gelmesi köprüde olduğumuzun
         kanıtı. Ayrı bir "köprü müsün" ucu ikinci bir gerçek kaynağı
         olurdu. Hata durumunda SESSİZCE kapalı kalıyor — arşiv bir ek
         özellik, yokluğu ölçümü etkilemiyor. */
      try {
        const y = await fetch(this.kartAdres('/durum'), { cache: 'no-store' });
        if (!y.ok) { this.skopArsivVar = false; this.kopruda = false; return; }
        const d = await y.json();
        this.skopArsivVar = !!d.skop_arsiv;
        this.kopruda = !!(d && d.kart);          // 3D (D1): seritte "köprü"
        if (this.skopArsivVar) await this.skopKayitlariYukle();
      } catch (e) { this.skopArsivVar = false; this.kopruda = false; } finally { this._kopruBilindi = true; }
    },

    async skopKayitlariYukle(gun) {
      if (!this.skopArsivVar) return;
      this.skopKayitMesgul = true;
      try {
        const s = gun ? ('?gun=' + encodeURIComponent(gun)) : '';
        const y = await fetch(this.kartAdres('/skop/liste' + s),
                              { cache: 'no-store' });
        if (!y.ok) return;
        const d = await y.json();
        this.skopGunler = d.gunler || [];
        this.skopGun = d.gun || '';
        this.skopKayitlar = d.kayitlar || [];
      } catch (e) {
        this.hata = 'Kayıt listesi alınamadı: ' + e.message;
      } finally {
        this.skopKayitMesgul = false;
      }
    },

    async skopKayitAc(kyt) {
      this.skopKayitMesgul = true;
      try {
        const y = await fetch(this.kartAdres(
          '/skop/al?gun=' + encodeURIComponent(kyt.gun) + '&ms=' + kyt.ms),
          { cache: 'no-store' });
        if (!y.ok) {
          this.hata = 'Kayıt açılamadı (' + y.status + ')';
          return;
        }
        /* AYNI çözücü — canlı yakalamayla tek satır bile farklı kod
           çalışmıyor, yoksa eski kayıt başka çizilirdi. */
        /* Arsivden aciyoruz: liste degismedi, tazelemek bosuna bir
           HTTP turu olurdu. */
        this.skopArsivtenAciliyor = true;
        if (this.skopIkiliCoz(await y.arrayBuffer())) {
          this.skopAcikKayit = { gun: kyt.gun, ms: kyt.ms };
          /* 🔴 B45 — ARŞİV KAYDININ ÖLÇÜM SATIRI. Köprü listede `M`
             satırını zaten taşıyor (`olcum`); açılan kayıtta hiç
             kullanılmıyordu. ZAMAN büyüklükleri (f, T, duty, tr, tf, n)
             o satırdan. GERİLİMLER ise kaydın HAM kodlarından, eksenle
             AYNI çeviriyle (`kodVolt`) yeniden: B43 öncesi firmware'in
             yazdığı `M` gerilimleri doğrusal modeldi ve eksenle 7 V
             çelişiyordu — eski kayıt açılınca o çelişki geri gelmesin. */
          this.osilo.olcum = this.skopArsivOlcum(kyt.olcum, this.osilo.veri);
          /* Arşiv kaydı açılınca sürekli yakalama DURUYOR: yoksa bir
             sonraki tur kaydın üstüne canlı dalgayı çizer ve kullanıcı
             hangisine baktığını bilemez. */
          if (this.surekli) this.surekliDegis();
        }
      } catch (e) {
        this.hata = 'Kayıt açılamadı: ' + e.message;
      } finally {
        this.skopKayitMesgul = false;
        this.skopArsivtenAciliyor = false;
      }
    },

    /* B45 — arşiv kaydı için ölçüm: zaman büyüklükleri kaydın `M`
       satırından, gerilimler ham kodlardan `kodVolt` ile. `M` yoksa
       yalnızca gerilimler. Kayıt boşsa null. */
    skopArsivOlcum(mSatir, veri) {
      if (!veri || !veri.length) return null;
      const o = (mSatir && mSatir.startsWith('M ')) ? this.skopMCoz(mSatir) : {};
      let top = 0, kare = 0, hmin = veri[0], hmax = veri[0];
      for (const k of veri) {
        const v = this.kodVolt(k);
        top += v; kare += v * v;
        if (k < hmin) hmin = k;
        if (k > hmax) hmax = k;
      }
      const n = veri.length, ort = top / n;
      const ac = kare / n - ort * ort;
      o.Vmax = this.kodVolt(hmax);
      o.Vmin = this.kodVolt(hmin);
      o.Vpp = o.Vmax - o.Vmin;
      o.Vort = ort;
      o.Vrms = Math.sqrt(kare / n);
      o.Vac = ac > 0 ? Math.sqrt(ac) : 0;
      /* Zaman alanları `M`de yoksa UYDURULMUYOR (0 yazmak "duty %0"
         gösterirdi); `skopOlcumler` eksik alanı atlıyor. */
      return o;
    },

    /* `M f=<Hz> T=<s> Vpp=<V> … n=<çevrim>` — TEK ayrıştırıcı: ASCII
       dökümü ve ikili yol (B43) aynı satırı buradan okuyor. */
    skopMCoz(satir) {
      const o = {};
      for (const alan of satir.slice(2).trim().split(/\s+/)) {
        const e = alan.indexOf('=');
        if (e > 0) o[alan.slice(0, e)] = parseFloat(alan.slice(e + 1));
      }
      return o;
    },

    /* 🔴 TEK ÇEVİRİ NOKTASI — kod → giriş volt.
       `kod * voltAdim - voltOfset` DÖRT ayrı yerde yazılıydı (tetik
       seviyesi, tepe değeri, dikey ölçek, çizim döngüsü). Kalibrasyon
       düzeltmesi eklenince dördünün de değişmesi gerekirdi; biri
       unutulsa ızgara etiketi bir şey, iz başka şey gösterirdi ve hata
       SESSİZ olurdu. Artık hepsi buradan geçiyor.

       Kalibrasyon varsa: V = (mv(kod)/1000) * oran - ofset
       Yoksa            : V = kod * voltAdim - voltOfset   (eski yol) */
    kodVolt(kod) {
      const o = this.osilo;
      const of = o ? (o.voltOfset || 0)
                   : (1.71531250 * (38.03703704 - 1));
      /* 3E (OS6): kayitli yakalama KENDI egrisini tasir (`o.kal`; kart o yakalamayi
         egrisiz olcmusse null) — canli kartin `CT` tablosu ona uygulanmaz. */
      const k = o && o.kal !== undefined ? o.kal : this.skopKal;
      if (k) return this.kalMv(kod, k) / 1000 * k.oran - of;
      const va = o ? o.voltAdim : (3.10 / 4096 * 38.03703704);
      return kod * va - of;
    },

    /* Tabloyu doğrusal aradeğerleyerek ham kodun mV karşılığı.
       Tablo dışına taşan kod uçtaki eğimle uzatılıyor — kırpılsaydı
       doyuma giren bir sinyal DÜZ bir çizgi gibi görünür ve kırpıldığı
       anlaşılmazdı. */
    kalMv(kod, kal = this.skopKal) {
      const { kod: ks, mv: vs } = kal;
      const n = ks.length;
      if (kod <= ks[0]) {
        const e = (vs[1] - vs[0]) / (ks[1] - ks[0]);
        return vs[0] + (kod - ks[0]) * e;
      }
      if (kod >= ks[n - 1]) {
        const e = (vs[n - 1] - vs[n - 2]) / (ks[n - 1] - ks[n - 2]);
        return vs[n - 1] + (kod - ks[n - 1]) * e;
      }
      let i = 0;
      while (i < n - 2 && ks[i + 1] < kod) i++;
      return vs[i] + (vs[i + 1] - vs[i]) * (kod - ks[i]) / (ks[i + 1] - ks[i]);
    },

    skopZaman(ms) {
      /* Köprünün damgası AÇILIŞINDAN İTİBAREN geçen ms — duvar saati
         değil. Duvar saati gibi gösterip yanıltmak yerine olduğu gibi
         "köprü açıldıktan sonra" diye yazılıyor. */
      const s = Math.floor(ms / 1000);
      const d = Math.floor(s / 60), sn = s % 60;
      return d ? `${d} dk ${String(sn).padStart(2, '0')} sn`
               : `${sn} sn`;
    },

    osiloOtomatik() {
      this.osiloBekliyor = true;
      this.osiloTopla = null;
      this.skopAcikKayit = null;
      this.skopKayitliCik();
      this.skopKomutZamani = Date.now();
      this.skopYakalamaUyari = '';
      this.gonder('ta');
      setTimeout(() => { this.osiloBekliyor = false; }, 30000);
    },
    tabanDegistir(yon) {
      const y = Math.max(0, Math.min(SKOP_TDIV.length - 1, this.skopTdiv + yon));
      if (y === this.skopTdiv) return;
      this.skopTdiv = y;
      this.gonder('tb' + y);
    },
    tabanSec(i) {
      this.skopTdiv = i;
      this.gonder('tb' + i);
    },
    skopKomut(k) { this.gonder(k); },

    /* ── sürekli yakalama (RUN/STOP) ──────────────────────────────
       Gerçek dijital osiloskoplar da tek bir "canlı akış" göstermiyor:
       bir kayıt yakalayıp ekrana basıyor, sonra yeniden tetiklenip bir
       daha yakalıyor. Saniyede yeterince tekrarlanınca canlı görünüyor.
       Aradaki boşluğa "ölü zaman" deniyor ve iyi cihazlarda saniyede
       on binlerce yakalama olur.

       Bizde tavan AKTARIM: 1000 örnek ASCII olarak 115200 baud'da
       ~0.43 s sürüyor, yani saniyede ~2 yakalama. Canlı gibi değil ama
       ayar çevirirken tepki veriyor. İkili biçim + yerel USB CDC ile
       çok daha hızlanır (bkz. DEVIR.md 4.11). */
    surekliDegis() {
      this.surekli = !this.surekli;
      if (this.surekli) {
        this.surekliT0 = Date.now();
        this.surekliSayac = 0;
        this.surekliTur();
      } else if (this.surekliZaman) {
        clearTimeout(this.surekliZaman);
        this.surekliZaman = null;
      }
    },
    surekliTur() {
      if (!this.surekli) return;
      /* 🔴 ÖNCEKİ YAKALAMA BİTMEDEN YENİSİNİ İSTEME.
         Eskiden tur koşulsuzdu: her 500 ms'de bir yeni yakalama. Karta
         doğrudan (WiFi) bağlıyken bu sorun değildi — `tB` ucuz ve gövde
         ayrı çekiliyor. Köprüde ise döküm ASCII olarak SERİ PORTTAN
         geçiyor ve 4000 örnek 115 200 baud'da ~1.8 s sürüyor. Koşulsuz
         tur her 500 ms'de bir `t` daha yollayıp kuyruk biriktirirdi:
         seri hat dolar, bloklar birbirini keser (çözücünün `kirpilan`
         sayacı artar) ve arşiv KIRPIK kayıtlarla dolardı.
         `osiloBekliyor` hem `osiloBitir()` hem 20 s'lik tavan tarafından
         temizleniyor, yani kapı kendini kurtarıyor — takılı kalmaz. */
      let bekleme = this.demo ? 120 : 500;
      if (this.osiloBekliyor) {
        bekleme = 150;                 // meşgul: yalnızca yokla
      } else {
        this.osiloYakala();
        this.surekliSayac++;
        const ge = (Date.now() - this.surekliT0) / 1000;
        if (ge > 0.5) this.surekliHiz = this.surekliSayac / ge;
        if (ge > 4) { this.surekliT0 = Date.now(); this.surekliSayac = 0; }
      }
      /* Bir sonraki turu, aktarım bitsin diye kısa bir gecikmeyle kur. */
      this.surekliZaman = setTimeout(() => this.surekliTur(), bekleme);
    },

    /* ── fare ile kaydırma ────────────────────────────────────────── */
    surukBasla(e) {
      if (!this.osilo) return;
      this.suruk = { x: e.clientX, y: e.clientY,
                     yk: this.yatayKaydir, dk: this.dikeyKaydir };
      e.preventDefault();
    },
    surukHareket(e) {
      if (!this.suruk || !this.osilo) return;
      const el = this.$refs.osiloTuval;
      if (!el) return;
      const kutu = el.getBoundingClientRect();
      const dx = (e.clientX - this.suruk.x) / kutu.width;
      const dy = (e.clientY - this.suruk.y) / kutu.height;

      /* Yatay: görünen pencere kadar kaydır (yakınlaştırma oranıyla ölçekli) */
      const g = 1 / this.yatayZoom;
      this.yatayKaydir = Math.max(g / 2, Math.min(1 - g / 2,
                                                  this.suruk.yk - dx * g));
      /* Dikey: yalnız elle kipte anlamlı; otomatikse elle kipe geç.
         dikeyKaydir artarken iz yukarı gidiyor (bkz. osiloCiz'deki
         `ote`), fare aşağı çekilince dy pozitif — bu yüzden çıkarma:
         iz fareyi izlesin, yatay eksendeki gibi. */
      if (dy !== 0) {
        if (this.dikeyOto && Math.abs(dy) > 0.02) this.dikeyOto = false;
        if (!this.dikeyOto) {
          this.dikeyKaydir = Math.max(-2, Math.min(2,
                                      this.suruk.dk - dy * 2));
        }
      }
      this.osiloCiz();
    },
    surukBitir() { this.suruk = null; },

    /* ── yakınlaştırma denetimleri (kartı hiç meşgul etmez) ── */
    dikeyBuyut(k) {
      this.dikeyOto = false;
      this.dikeyZoom = Math.max(0.2, Math.min(50, this.dikeyZoom * k));
      this.osiloCiz();
    },
    dikeyKaydirDegis(d) {
      this.dikeyOto = false;
      this.dikeyKaydir = Math.max(-2, Math.min(2, this.dikeyKaydir + d));
      this.osiloCiz();
    },
    dikeySifirla() {
      this.dikeyOto = true; this.dikeyZoom = 1; this.dikeyKaydir = 0;
      this.osiloCiz();
    },
    yatayBuyut(k) {
      const n = this.osilo ? this.osilo.adet : 1000;
      this.yatayZoom = Math.max(1, Math.min(n / 20, this.yatayZoom * k));
      this.osiloCiz();
    },
    yatayKaydirDegis(d) {
      const g = 1 / this.yatayZoom;
      this.yatayKaydir = Math.max(g / 2, Math.min(1 - g / 2,
                                                  this.yatayKaydir + d * g));
      this.osiloCiz();
    },
    yatayTetigeGit() {
      if (!this.osilo || !this.osilo.adet) return;
      this.yatayKaydir = this.osilo.tetikIdx / this.osilo.adet;
      this.yatayKaydirDegis(0);
    },
    yatarSifirla() {
      this.yatayZoom = 1; this.yatayKaydir = 0.5; this.osiloCiz();
    },
    /* Fare tekerleği: dikey zoom (Shift basılıysa yatay) */
    tekerlek(e) {
      if (!this.osilo) return;
      e.preventDefault();
      const k = e.deltaY < 0 ? 1.25 : 1 / 1.25;
      if (e.shiftKey) this.yatayBuyut(k); else this.dikeyBuyut(k);
    },

    /* Yakalama tamamlandı: veriyi kilitle ve çiz. */
    osiloBitir() {
      const t = this.osiloTopla;
      if (!t) return;
      if (t.veri.length > t.adet) t.veri.length = t.adet;
      this.osilo = t;
      if (t.tdivUs) {
        const i = SKOP_TDIV.indexOf(t.tdivUs);
        if (i >= 0) this.skopTdiv = i;
      }
      this.osiloTopla = null;
      this.osiloBekliyor = false;
      this.skopYakalamaUyari = '';
      /* 3E (OS6): canli (ya da kopru arsivinden) bir yakalama cizildi — kayitli degil */
      this.skopKayitliCik();
      /* Yeni kayıt geldi: yatay yakınlaştırmayı sıfırla, dikeyi koru
         (kullanıcı bir kademeye kilitlemişse orada kalsın). */
      this.yatayZoom = 1;
      this.yatayKaydir = 0.5;
      this.$nextTick(() => { this.osiloCiz(); this.spektrumCiz(); });
      /* TEK TAMAMLANMA NOKTASI: ASCII yolu da ikili yol da buradan
         geciyor, yani liste tazeleme tek yerde duruyor. `skopIkiliAl`
         icinde kalsaydi koprudeki ASCII yakalamalari listeye HIC
         dusmezdi — kopruda ASCII yolu kullaniliyor. */
      if (!this.skopArsivtenAciliyor) this.skopListeTazeleGerekirse();
    },

    /* Canli yakalama bitince arsiv listesini tazele — yeni kayit hemen
       gorunsun. `surekli` kipte YAPILMIYOR: saniyede birkac yakalamada
       her turda liste cekmek kopruyu bosuna mesgul eder. */
    skopListeTazeleGerekirse() {
      if (this.skopArsivVar && !this.surekli) this.skopKayitlariYukle(this.skopGun);
    },

    gecmisiTemizle() {
      this.onay = null;                  // WIG: iki asamali onay buradan geldi
      this.gecmis = [];
      this.ilkMs = null;
      this.msKaydir = 0;
      this.donmus = false;              // 3D: dondurulmus kopya da birakilir
      this.grafikCiz();
    },

    csvIndir() {
      const satirlar = ['saniye;volt;amper;watt'];
      for (const g of this.gecmis) {
        const h = (x) => (Number.isNaN(x) ? '' : String(x));   // B27 A2: veri yok = boş hücre
        satirlar.push(`${g.t.toFixed(3)};${h(g.v)};${h(g.i)};${h(g.w)}`.replace(/\./g, ','));
      }
      const bl = new Blob(['﻿' + satirlar.join('\r\n')],
                          { type: 'text/csv;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(bl);
      a.download = 'olcum-' + new Date().toISOString().slice(0, 19)
                     .replace(/[:T]/g, '-') + '.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    },

    // ─────────────────────────────────────────────── çizim
    tuvalHazirla(el) {
      if (!el) return null;
      const o = window.devicePixelRatio || 1;
      const g = el.getBoundingClientRect().width;

      /* Mantıksal yükseklik İLK çağrıda saklanmalı.
         Saklamazsak: ilk çağrıda el.height = 260 okunur ve el.height
         260×DPR yapılır; İKİNCİ çağrıda el.height artık 520 döner, çizim
         520 px'lik bir alana göre yerleşir ama görünür alan hâlâ 260 px'tir
         → izin altı ve zaman ekseni etiketleri EKRANIN DIŞINDA kalır. */
      if (!el.dataset.boy) el.dataset.boy = String(el.height);
      const y = Number(el.dataset.boy);

      if (el.width !== Math.round(g * o) || el.height !== Math.round(y * o)) {
        el.width = Math.round(g * o);
        el.height = Math.round(y * o);
        el.style.height = y + 'px';
      }
      const c = el.getContext('2d');
      c.setTransform(o, 0, 0, o, 0, 0);
      c.clearRect(0, 0, g, y);
      return { c, g, y };
    },

    renk(ad) {
      return getComputedStyle(document.documentElement)
               .getPropertyValue(ad).trim() || '#888';
    },

    /* 3E (OS2): osiloskop izgarasi 10 x 8 BOLME — yatay 10 bolme kartin zaman tabani
       sozlesmesi (pencere = SKOP_BOLME x tdiv, tdivEtiket "…/böl"), dikey 8. Orta eksenler
       `--kenar-koyu` ile (tema belirteci; uc gorunumde okunur), digerleri `--kenar-c`. */
    izgara(c, g, y, sol, ust, en, boy) {
      c.lineWidth = 1;
      for (const [renk, orta] of [['--kenar-c', false], ['--kenar-koyu', true]]) {
        c.strokeStyle = this.renk(renk);
        c.beginPath();
        for (let i = 0; i <= SKOP_BOLME_X; i++) {
          if ((i === SKOP_BOLME_X / 2) !== orta) continue;
          const xx = Math.round(sol + en * i / SKOP_BOLME_X) + .5;
          c.moveTo(xx, ust); c.lineTo(xx, ust + boy);
        }
        for (let i = 0; i <= SKOP_BOLME_Y; i++) {
          if ((i === SKOP_BOLME_Y / 2) !== orta) continue;
          const yy = Math.round(ust + boy * i / SKOP_BOLME_Y) + .5;
          c.moveTo(sol, yy); c.lineTo(sol + en, yy);
        }
        c.stroke();
      }
    },

    grafikPlanla() {
      if (grafikBekliyor) return;
      if (typeof requestAnimationFrame !== 'function') { this.grafikCiz(); return; }
      grafikBekliyor = true;
      requestAnimationFrame(() => { grafikBekliyor = false; this.grafikCiz(); });
    },

    /* 3D (D3): canli grafik `ekran/canli.js` + `ortak/grafik.js`. Eski elle
       cizim (ust/alt esleme, tepe etiketi, sifir cizgisi) kalkti: grafik.js
       eksenleri yaziyor, negatifi gosteriyor (G3 tam min/maks), NaN'da cizgiyi
       kesiyor (G2); gurultu tabani `enAzAralik` (B45 korunuyor — olcekTabani);
       "tepe / veri yok" lejanti HTML'de (ekran/canli.js canliLejant).
       Canli gizliyken (baska ekran) cizilmiyor — geri donunce watch.gorunum ciziyor. */
    grafikCiz() {
      if (!this._canli || this.gorunum !== 'canli') return;
      this._canli.ciz(this.canliDurumu());
    },

    /* B45 — zaman grafiği ölçek tabanı: kanal başına 20 LSB (A ve V);
       güç için pencerede görülen |V| ve |I| ile çarpılmış hali.
       LSB'ler kartın bildirdiği menzil ve şönt'ten (`akimMenzilAralik`
       ile aynı kaynak) — sabit sayı değil. */
    olcekTabani(veri) {
      const sont = this.kartSont !== null ? this.kartSont : parseFloat(this.sontSecim);
      const iLsb = (isFinite(sont) && sont > 0) ? ADS_PGA_V / 32768 / sont : 78.1e-6;
      const vLsb = this.menzil === 1 ? 18.78e-3 : 1.042e-3;
      let vEnb = 0, iEnb = 0;
      for (const d of veri) {
        if (!Number.isNaN(d.v)) vEnb = Math.max(vEnb, Math.abs(d.v));
        if (!Number.isNaN(d.i)) iEnb = Math.max(iEnb, Math.abs(d.i));
      }
      const v = 20 * vLsb, i = 20 * iLsb;
      return { v, i, w: vEnb * i + iEnb * v };
    },

    osiloCiz() {
      const t = this.tuvalHazirla(this.$refs.osiloTuval);
      if (!t) return;
      const { c, g, y } = t;
      const sol = 52, sag = 12, ust = 10, alt = 24;
      const en = g - sol - sag, boy = y - ust - alt;

      this.izgara(c, g, y, sol, ust, en, boy);

      if (!this.osilo) {
        c.fillStyle = this.renk('--cok-soluk');
        c.font = '13px system-ui, sans-serif';
        c.textAlign = 'center';
        c.fillText(this.os.tuvalBos, g / 2, y / 2);
        return;
      }

      /* ⚠ `voltAdim`/`voltOfset` ARTIK BURADA OKUNMUYOR: kod→volt
         çevirisi tek noktada (`kodVolt`). Burada tutulsalardı ölçek
         düzeltmesi geldiğinde biri güncellenip diğeri unutulabilirdi. */
      const { veri, hz, adet } = this.osilo;
      if (!adet || adet < 2) return;

      /* Yatay pencere: yakınlaştırma yapılmışsa kaydın bir bölümü.
         Kart yeniden tetiklenmiyor — elimizdeki kaydın içinde geziniyoruz. */
      const { bas, son } = this.gorunurAralik;
      const say = son - bas;
      if (say < 2) return;

      /* Dikey ölçek.
         Oto kipte: görünen bölümün min–max'ı, %8 pay ile. Böylece
         yakınlaştırınca ölçek de o bölüme uyum sağlıyor.
         Elle kipte: aynı merkez etrafında dikeyZoom kadar daraltılmış
         aralık, dikeyKaydir kadar ötelenmiş. */
      let hmin = veri[bas], hmax = veri[bas];
      for (let i = bas; i < son; i++) {
        if (veri[i] < hmin) hmin = veri[i];
        if (veri[i] > hmax) hmax = veri[i];
      }
      let vmin = this.kodVolt(hmin),
          vmax = this.kodVolt(hmax);
      let pay = (vmax - vmin) * 0.08;
      if (pay < 1e-4) pay = Math.max(Math.abs(vmax) * 0.05, 0.01);
      vmin -= pay; vmax += pay;

      if (!this.dikeyOto) {
        const merkez = (vmax + vmin) / 2;
        const yari = ((vmax - vmin) / 2) / this.dikeyZoom;
        const ote = this.dikeyKaydir * yari * 2;
        vmin = merkez - yari - ote;
        vmax = merkez + yari - ote;
      }
      const araliktan = (v) =>
        ust + boy * (1 - (this.kodVolt(v) - vmin) / (vmax - vmin));

      /* Kırpma: ekranın dışına taşan izi çizme (aksi halde ızgaranın
         üstüne/altına taşar). */
      c.save();
      c.beginPath();
      c.rect(sol, ust, en, boy);
      c.clip();

      /* Tetik anı — görünen pencerenin içindeyse */
      const tIdx = this.osilo.tetikIdx || 0;
      if (this.osilo.tetiklendi && tIdx >= bas && tIdx < son) {
        const xt = sol + en * (tIdx - bas) / (say - 1);
        c.strokeStyle = this.renk('--watt');
        c.lineWidth = 1;
        c.setLineDash([4, 4]);
        c.beginPath(); c.moveTo(xt, ust); c.lineTo(xt, ust + boy); c.stroke();
        c.setLineDash([]);
      }

      /* Tetik seviyesi çizgisi — nereye ayarlandığı görünsün */
      if (this.skopEsik > 0) {
        const ye = araliktan(this.skopEsik);
        if (ye > ust && ye < ust + boy) {
          c.strokeStyle = this.renk('--cok-soluk');
          c.lineWidth = 1;
          c.setLineDash([2, 5]);
          c.beginPath(); c.moveTo(sol, ye); c.lineTo(sol + en, ye); c.stroke();
          c.setLineDash([]);
        }
      }

      c.strokeStyle = this.renk('--volt');
      c.lineWidth = 1.4;
      c.beginPath();
      for (let i = bas; i < son; i++) {
        const x = sol + en * (i - bas) / (say - 1);
        const yy = araliktan(veri[i]);
        (i === bas) ? c.moveTo(x, yy) : c.lineTo(x, yy);
      }
      c.stroke();
      c.restore();

      /* Tetik etiketi kırpmanın dışında (üst kenarda) */
      if (this.osilo.tetiklendi && tIdx >= bas && tIdx < son) {
        const xt = sol + en * (tIdx - bas) / (say - 1);
        c.fillStyle = this.renk('--watt');
        c.font = '10px ui-monospace, monospace';
        c.textAlign = 'center';
        c.fillText('T', xt, ust - 1);
      }

      // dikey eksen: üst / orta / alt
      c.fillStyle = this.renk('--cok-soluk');
      c.font = '11px ui-monospace, monospace';
      c.textAlign = 'right';
      c.fillText(vmax.toFixed(2) + ' V', sol - 6, ust + 10);
      c.fillText(((vmax + vmin) / 2).toFixed(2), sol - 6, ust + boy / 2 + 4);
      c.fillText(vmin.toFixed(2), sol - 6, ust + boy - 2);

      // yatay eksen: tetik anı sıfır, öncesi negatif
      const t0 = (bas - tIdx) / hz;
      const t1 = (son - 1 - tIdx) / hz;
      c.textAlign = 'left';
      c.fillText(muh(t0, 's', 1), sol, y - 6);
      c.textAlign = 'center';
      c.fillText(muh((t0 + t1) / 2, 's', 1), sol + en / 2, y - 6);
      c.textAlign = 'right';
      c.fillText(muh(t1, 's', 1), g - sag, y - 6);

      // yakınlaştırma göstergesi
      if (this.yatayZoom > 1 || !this.dikeyOto) {
        c.fillStyle = this.renk('--cok-soluk');
        c.font = '10px ui-monospace, monospace';
        c.textAlign = 'right';
        c.fillText(`yatay ${this.yatayZoomEtiket} · dikey ${this.dikeyZoomEtiket}`,
                   g - sag, ust + 11);
      }
    },
  },
}).mount('#uyg');
