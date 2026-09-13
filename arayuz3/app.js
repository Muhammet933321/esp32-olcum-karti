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
   ═══════════════════════════════════════════════════════════════════════ */

const { createApp } = Vue;

/* Zaman tabanı merdiveni — firmware'deki SKOP_TDIV_US ile AYNI olmalı
   (kod/olcum-karti-a2/olcum-karti-a2.ino). Doğrulama zinciri (A5) iki
   listenin ayrışmadığını sınıyor. */
const SKOP_TDIV = [100, 200, 500, 1000, 2000, 5000,
                   10000, 20000, 50000, 100000, 200000, 500000];

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
      if (!uyg.durduruldu) uyg.hata = 'Okuma hatası: ' + e.message;
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
const GORUNUMLER = [
  { id: 'olcum',  ad: 'Ölçüm',     alt: 'V · I · P · enerji · zaman grafiği' },
  { id: 'skop',   ad: 'Osiloskop', alt: 'yakalama · tetik · hızlı güç ölçümü' },
  { id: 'pil',    ad: 'Pil testi', alt: 'deşarj eğrisi · mAh · Wh · iç direnç' },
  { id: 'ayar',   ad: 'Ayarlar',   alt: 'kalibrasyon · şönt · menzil · ağ' },
  { id: 'konsol', ad: 'Konsol',    alt: 'ham satırlar · komut' },
];
const GORUNUM_VARSAYILAN = 'olcum';

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
  return GORUNUMLER.some((g) => g.id === h) ? h : GORUNUM_VARSAYILAN;
}

createApp({
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

      // geçmiş: { t (sn), v, i, w }
      gecmis: [],
      ilkMs: null,
      pencere: 60,
      gosterV: true, gosterI: true, gosterW: true,

      // osiloskop
      osilo: null,
      osiloBekliyor: false,
      skopIkiliBekle: false,  // B40: `tB` gönderildi, onay satırı bekleniyor
      skopIkiliOlcum: null,   // B43: ikili yakalamanın `M` satırı (onaydan ÖNCE gelir)
      osiloTopla: null,
      skopAyar: null,        // kartın bildirdiği T satırı
      skopTdiv: 5,           // zaman tabanı indeksi (0..11)
      skopKip: 0,            // 0 oto · 1 normal · 2 tek atış
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
      pilZaman: null,      // B27 A4: uyarlanir yoklama zamanlayicisi
      pilMah: 0, pilWh: 0, pilCoulomb: 0,
      pilOcv: 0, pilVson: 0, pilKesme: 3.0,
      pilDcirAni: 0, pilDcirOtr: 0, pilDcirN: 0,
      pilSira: 0,          // kartın ürettiği toplam nokta
      pilYerelSira: 0,     // bizde olan son sıra
      pilNokta: [],        // {sira, ms, v, i} · boşlukta {sira, bosluk:true}
      pilBosluk: 0,
      pilHataMetni: '',        // kaç nokta kayboldu
      pilKesmeGiris: '',
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
    /* B27 A4: yoklama aralığı — testi izlerken 2 s, boşta 10 s.
       Her istek kartta ~15 ms ölçüm kaybı demek. */
    pilYoklamaAralik() {
      return (this.pilDurum === 'CALISIYOR' || this.gorunum === 'pil') ? 2000 : 10000;
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
    sureGoster() {
      if (!this.gecmis.length) return '—';
      const s = Math.floor(this.gecmis[this.gecmis.length - 1].t);
      const sa = Math.floor(s / 3600), dk = Math.floor((s % 3600) / 60);
      return sa ? `${sa}s ${dk}dk` : dk ? `${dk}dk ${s % 60}sn` : `${s} sn`;
    },

    osiloTepe() {
      if (!this.osilo) return 0;
      return this.kodVolt(Math.max(...this.osilo.veri));
    },
  },

  watch: {
    /* B27 Aşama 1: gizli (display:none) tuval 0 genişlik okur; görünüme
       dönünce yeniden çizilmeli. Adres çubuğunu da eşitle. */
    gorunum(v) {
      if (typeof location !== 'undefined' && location.hash !== '#/' + v) {
        try { history.replaceState(null, '', '#/' + v); } catch (e) { /* file:// */ }
      }
      this.$nextTick(() => { this.grafikCiz(); this.osiloCiz(); });
    },
    /* B22.2: cizimi tazele VE tercihi sakla. Bu alanlar her acilista
       yeniden giriliyordu — localStorage hic kullanilmiyordu. */
    pencere(v) { this.grafikCiz(); this.ayarYaz('pencere', v); },
    gosterV(v) { this.grafikCiz(); this.ayarYaz('gosterV', v); },
    gosterI(v) { this.grafikCiz(); this.ayarYaz('gosterI', v); },
    gosterW(v) { this.grafikCiz(); this.ayarYaz('gosterW', v); },
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
    /* B27 A2: sayfayı KART ya da KÖPRÜ sunduysa kendiliğinden bağlan.
       Kullanıcı kartın adresini açmışsa ölçümü görmek istiyor; "Karta
       bağlan"a basmak fazladan bir adımdı ve headless doğrulamada da
       sayfa hep "bağlı değil" halinde kalıyordu. localhost/file:// ve
       ?demo'da DEĞİL — orada taşıyıcı USB ya da sahte kart. */
    this.kopruyuAlgila().then(() => { if (this.otomatikBaglanmali()) this.baglan(); });
    window.addEventListener('resize', () => { this.grafikCiz(); this.osiloCiz(); });
    window.addEventListener('hashchange', () => { this.gorunum = hashtenGorunum(); });
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
    this.pilYukle().then(() => {
      const tik = () => {
        if (this.bagli) this.pilYokla();
        this.pilZaman = setTimeout(tik, this.pilYoklamaAralik);
      };
      this.pilZaman = setTimeout(tik, this.pilYoklamaAralik);
    });
  },

  methods: {
    gorunumeGit(id) { this.gorunum = id; },
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
      return (this.kartTaban || '').replace(/\/+$/, '') + yol;
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
      this.gosterI = this.ayarOku('gosterI', this.gosterI);
      this.gosterW = this.ayarOku('gosterW', this.gosterW);
      this.sontSecim = this.ayarOku('sontSecim', this.sontSecim);
      this.sebekeHz = this.ayarOku('sebekeHz', this.sebekeHz);
      this.raporMs = this.ayarOku('raporMs', this.raporMs);
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
        this.hata = 'demo kipi acilamadi: ' + e.message;
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

      // canli akis: gercek kart gibi rapor araliginda bir D satiri.
      // B27 A2: aralik sahte karttan okunuyor (`r<ms>` ile degisir),
      // o yuzden setInterval degil kendini yeniden kuran setTimeout.
      const tik = () => {
        const aralik = SahteKart.raporAralik();
        this.demoMs += aralik;
        const d = SahteKart.dSatiri(this.demoMs, this.demoJ);
        this.demoJ += d.w * aralik / 1000;
        this.satirIsle(d.satir);
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
      this.gunluk.push({ metin, giden });
      if (this.gunluk.length > 400) this.gunluk.splice(0, this.gunluk.length - 400);
      this.$nextTick(() => {
        const k = this.$refs.gunlukKutu;
        if (k) k.scrollTop = k.scrollHeight;
      });
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
        this.kopruYokla();
      } catch (e) {
        // Kullanıcı port seçim kutusunu kapattıysa bu hata değil.
        if (e.name !== 'NotFoundError') this.hata = 'Bağlanamadı: ' + e.message;
      }
    },

    async kes() {
      await this.tasiyici.kapat(this);
      this.bagli = false;
      this.bagliTasiyici = null;
      this.kaydet('— bağlantı kesildi —');
    },

    /* ⚠ ÇAĞRI YERLERİ DEĞİŞMEDİ: `gonder('z')`, `gonder('F' + d)` …
       hepsi aynı şekilde duruyor. Değişen yalnızca burası. */
    async gonder(metin) {
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
        if (this.kartMs) this.sonAralik = yeniMs - this.kartMs;
        this.kartMs = yeniMs;
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

        if (this.ilkMs === null) this.ilkMs = this.kartMs;
        /* 🔴 B27 A2 — K1'in GRAFIK yarisi eksikti: kartlar "veri yok"
           derken grafik sahte 1.72 V'u duz cizgi olarak cizmeye, "tepe
           1.72 V" yazmaya devam ediyordu (kullanicinin ekran goruntusu,
           2026-09-12). Gecersiz kanal NaN olarak giriyor: cizgi KOPAR,
           tepe etiketi susar, CSV'de hucre bos kalir. */
        this.gecmis.push({
          t: (this.kartMs - this.ilkMs) / 1000,
          v: this.voltGecersiz  ? NaN : this.volt,
          i: this.amperGecersiz ? NaN : this.amper,
          w: this.gucGecersiz   ? NaN : this.watt,
        });
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
      if (satir.startsWith('!')) {
        this.osiloBekliyor = false; this.skopIkiliBekle = false; this.skopIkiliOlcum = null;
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
    agSifreGonder() { this.gonder('Np' + this.agSifre); this.agSifre = ''; },
    agWebSifreGonder() {
      /* Bos gondermek parolayi KALDIRIR — firmware bunu ayrica soyluyor. */
      this.gonder('Ns' + this.agWebSifre);
      this.agWebSifre = '';
    },

    /* Köprüden sürücülüğü devral. Yetki sunucuda; arayüz yalnızca
       durumu gösteriyor ve devri istiyor — politikayı İKİ YERDE
       tutmak bu projenin cezalandırdığı ayrışma deseni olurdu. */
    async devral() {
      const y = await fetch(this.kartAdres('/devral'), {
        method: 'POST',
        headers: { 'X-Olcum': '1', 'X-Jeton': this.jeton || '' },
      }).catch(() => null);
      if (y && y.ok) { this.surucuyum = true; this.hata = ''; }
      else this.hata = 'Devralınamadı' + (y ? ' (' + y.status + ')' : '');
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
    },
    kalibreA() {
      const a = parseFloat(this.kalibA.replace(',', '.'));
      if (isFinite(a) && a !== 0) { this.gonder('i' + a); this.kalibA = ''; }
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
    fazGonder() {
      const d = parseFloat(String(this.fazKal).replace(',', '.'));
      if (!isFinite(d)) { this.hata = 'Faz kalibrasyonu: sayı girin (µs)'; return; }
      if (d < -2000 || d > 2000) {
        this.hata = 'Faz kalibrasyonu −2000 … +2000 µs arası olmalı';
        return;
      }
      this.hata = '';
      this.gonder('F' + d);
      this.fazKal = '';
    },

    /* B22.1: FABRIKA SIFIRLAMA. Bozulmus bir NVS kaydindan kurtulmanin
       baska yolu yok. Iki asamali onay — tarayici confirm() kullanilmiyor
       cunku o hem sinanamiyor hem de kip kilitliyor. */
    fabrikaSifirla() {
      if (!this.sifirlaOnay) { this.sifirlaOnay = true; return; }
      this.sifirlaOnay = false;
      this.gonder('R!');
    },
    /* ── B21 · IndexedDB: sekme kapansa da veri kaybolmasın ─────────
       ⚠ IndexedDB tarayıcının verisidir — "tarayıcı verilerini temizle"
       denince gider. ASIL ARŞİV `pilCsvIndir()`. */
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
      const db = await this.pilDb();
      const iw = db.transaction('nokta', 'readwrite').objectStore('nokta');
      for (const n of noktalar) iw.put(n);
    },
    async pilYukle() {
      const db = await this.pilDb();
      const hepsi = await new Promise((coz) => {
        const r = db.transaction('nokta').objectStore('nokta').getAll();
        r.onsuccess = () => coz(r.result || []);
        r.onerror = () => coz([]);
      });
      hepsi.sort((a, b) => a.sira - b.sira);
      this.pilNokta = hepsi;
      this.pilYerelSira = hepsi.length ? hepsi[hepsi.length - 1].sira + 1 : 0;
    },
    async pilTemizle() {
      const db = await this.pilDb();
      db.transaction('nokta', 'readwrite').objectStore('nokta').clear();
      this.pilNokta = []; this.pilYerelSira = 0; this.pilBosluk = 0;
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
      let m;
      try {
        const y = await fetch(this.kartAdres('/pil?sira=' + this.pilYerelSira));
        if (!y.ok) {
          this.pilHataMetni = 'kart yanıt vermiyor (HTTP ' + y.status + ')';
          return;
        }
        m = await y.text();
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
      this.pilDurum = a.durum || '-';
      this.pilHata = a.hata || '-';
      this.pilMah = parseFloat(a.mah) || 0;
      this.pilWh = parseFloat(a.wh) || 0;
      this.pilCoulomb = parseFloat(a.coulomb) || 0;
      this.pilOcv = parseFloat(a.ocv) || 0;
      this.pilVson = parseFloat(a.vson) || 0;
      this.pilKesme = parseFloat(a.kesme) || 0;
      this.pilDcirAni = parseFloat(a.dcir_ani) || 0;
      this.pilDcirOtr = parseFloat(a.dcir_otr) || 0;
      this.pilDcirN = parseInt(a.dcir_n) || 0;
      this.pilSira = parseInt(a.sira) || 0;
      /* 🔴 BOŞLUK: kart istediğimiz noktayı artık tutmuyorsa `ilk_sira`
         istediğimizden BÜYÜK döner. Bunu SAKLAMIYORUZ — işaretliyoruz. */
      const ilk = parseInt(a.ilk_sira) || 0;
      if (ilk > this.pilYerelSira && this.pilYerelSira > 0) {
        this.pilBosluk += ilk - this.pilYerelSira;
        this.pilNokta.push({ sira: this.pilYerelSira, bosluk: true });
      }
      if (!govde) return;
      const yeni = [];
      let sira = ilk;
      for (const s of govde.split('\n')) {
        if (!s) continue;
        const p = s.split(',');
        if (p.length < 3) continue;
        yeni.push({ sira: sira++, ms: +p[0], v: +p[1], i: +p[2] });
      }
      if (!yeni.length) return;
      this.pilNokta.push(...yeni);
      this.pilYerelSira = sira;
      await this.pilKaydet(yeni);
    },
    pilBaslat() { this.gonder('p1'); },
    pilDurdurKomut() { this.gonder('p0'); },
    pilKesmeGonder() {
      const v = parseFloat(String(this.pilKesmeGiris).replace(',', '.'));
      if (isFinite(v) && v >= 0.5 && v <= 38.5) {
        this.gonder('P' + v);
        this.pilKesmeGiris = '';
      }
    },
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
        if (!y.ok) { this.skopArsivVar = false; return; }
        const d = await y.json();
        this.skopArsivVar = !!d.skop_arsiv;
        if (this.skopArsivVar) await this.skopKayitlariYukle();
      } catch (e) { this.skopArsivVar = false; }
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
      const k = this.skopKal;
      if (k) return this.kalMv(kod) / 1000 * k.oran - of;
      const va = o ? o.voltAdim : (3.10 / 4096 * 38.03703704);
      return kod * va - of;
    },

    /* Tabloyu doğrusal aradeğerleyerek ham kodun mV karşılığı.
       Tablo dışına taşan kod uçtaki eğimle uzatılıyor — kırpılsaydı
       doyuma giren bir sinyal DÜZ bir çizgi gibi görünür ve kırpıldığı
       anlaşılmazdı. */
    kalMv(kod) {
      const { kod: ks, mv: vs } = this.skopKal;
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
      /* Yeni kayıt geldi: yatay yakınlaştırmayı sıfırla, dikeyi koru
         (kullanıcı bir kademeye kilitlemişse orada kalsın). */
      this.yatayZoom = 1;
      this.yatayKaydir = 0.5;
      this.$nextTick(() => this.osiloCiz());
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
      this.gecmis = [];
      this.ilkMs = null;
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

    izgara(c, g, y, sol, ust, en, boy) {
      c.strokeStyle = this.renk('--kenar-c');
      c.lineWidth = 1;
      c.beginPath();
      for (let i = 0; i <= 4; i++) {
        const yy = Math.round(ust + boy * i / 4) + .5;
        c.moveTo(sol, yy); c.lineTo(sol + en, yy);
      }
      c.stroke();
    },

    grafikPlanla() {
      if (grafikBekliyor) return;
      if (typeof requestAnimationFrame !== 'function') { this.grafikCiz(); return; }
      grafikBekliyor = true;
      requestAnimationFrame(() => { grafikBekliyor = false; this.grafikCiz(); });
    },

    grafikCiz() {
      const t = this.tuvalHazirla(this.$refs.grafik);
      if (!t) return;
      const { c, g, y } = t;
      const sol = 52, sag = 12, ust = 10, alt = 24;
      const en = g - sol - sag, boy = y - ust - alt;

      this.izgara(c, g, y, sol, ust, en, boy);

      if (!this.gecmis.length) {
        c.fillStyle = this.renk('--cok-soluk');
        c.font = '13px system-ui, sans-serif';
        c.textAlign = 'center';
        c.fillText('veri yok — karta bağlan', g / 2, y / 2);
        return;
      }

      const sonT = this.gecmis[this.gecmis.length - 1].t;
      const basT = Math.max(0, sonT - this.pencere);
      const veri = this.gecmis.filter(d => d.t >= basT);
      if (veri.length < 2) return;

      const seriler = [
        { ac: this.gosterV, al: 'v', renk: this.renk('--volt'),  ad: 'V' },
        { ac: this.gosterI, al: 'i', renk: this.renk('--amper'), ad: 'A' },
        { ac: this.gosterW, al: 'w', renk: this.renk('--watt'),  ad: 'W' },
      ].filter(s => s.ac);

      /* 🔴 B45 — GRAFİK NEGATİFİ GÖSTEREMİYORDU. Ölçek `1 - deger/enb`
         ile sıfırı tuvalin ALTINA koyuyordu; kart çift yönlü (±32 V,
         ±2.56 A, negatif güç = kaynak) ama negatif her nokta tuvalin
         dışına çiziliyordu — boştaki akımın ±3 µA gürültüsünün yalnız
         pozitif yarısı görünüyordu (tarayıcıda görüldü). Pencerede
         negatif varsa sıfır ORTADA, yoksa altta; sıfır çizgisi çiziliyor.

         🔴 B45 — GÜRÜLTÜ TAM EKRANA YAYILIYORDU. Ölçek her zaman tepe
         değerdi: giriş boşken 0.05 LSB'lik gürültü ekranı dolduruyor ve
         etiket "tepe 0.0 mA" derken iz dev bir sinyal gibi görünüyordu.
         Taban: kanalın 20 LSB'si (`olcekTabani`). Gerçek bir sinyal
         (10 mA = 128 LSB) tabanın üstünde, eskisi gibi ölçekleniyor. */
      const taban = this.olcekTabani(veri);
      for (const s of seriler) {
        const { enb, tepe, negatif, tabanda, gecerli } = this.grafikOlcek(veri, s.al, taban[s.al]);
        /* negatif varsa [-enb, +enb] -> [alt, üst]; yoksa [0, enb] */
        const yOl = (deger) => negatif ? ust + boy * (1 - deger / enb) / 2
                                      : ust + boy * (1 - deger / enb);

        // sıfır çizgisi — serinin renginde, soluk ve kesikli
        c.save();
        c.strokeStyle = s.renk;
        c.globalAlpha = .35;
        c.setLineDash([4, 4]);
        c.lineWidth = 1;
        c.beginPath();
        const y0 = Math.round(yOl(0)) + .5;
        c.moveTo(sol, y0); c.lineTo(sol + en, y0);
        c.stroke();
        c.restore();

        c.strokeStyle = s.renk;
        c.lineWidth = 1.8;
        c.lineJoin = 'round';
        c.beginPath();
        let kopuk = true;
        for (const d of veri) {
          const deger = d[s.al];
          if (Number.isNaN(deger)) { kopuk = true; continue; }
          const x = sol + en * (d.t - basT) / Math.max(this.pencere, 1e-6);
          const yy = yOl(deger);
          kopuk ? c.moveTo(x, yy) : c.lineTo(x, yy);
          kopuk = false;
        }
        c.stroke();

        /* Tepe değeri sağ üstte. B27 A2: etiket çizginin ÜSTÜNE
           biniyordu ve ikisi de okunmuyordu; arkasına tuval zemini
           rengiyle bir şerit koyuluyor. B45: taban devredeyse ölçek de
           yazılıyor — "tepe 0.0 mA" tek başına ekrandaki izi açıklamaz. */
        const bicimle = (x) => s.al === 'v' ? x.toFixed(2) + ' V'
                             : s.al === 'i' ? (x * 1e3).toFixed(1) + ' mA'
                             : (x * 1e3).toFixed(1) + ' mW';
        const etiket = !gecerli ? 'veri yok'
                     : 'tepe ' + bicimle(tepe)
                       + (tabanda ? ' · ölçek ' + (negatif ? '±' : '') + bicimle(enb) : '');
        c.font = '600 11px ui-monospace, monospace';
        c.textAlign = 'right';
        const ey = ust + 12 + seriler.indexOf(s) * 14;
        const en_ = c.measureText(etiket).width;
        c.fillStyle = this.renk('--zemin-2');
        c.globalAlpha = .85;
        c.fillRect(g - sag - en_ - 4, ey - 10, en_ + 8, 14);
        c.globalAlpha = 1;
        c.fillStyle = s.renk;
        c.fillText(etiket, g - sag, ey);
      }

      // zaman ekseni — B45: sol etiket izin altına biniyordu, şerit kondu
      c.font = '11px ui-monospace, monospace';
      const solMetin = `-${this.pencere} sn`;
      c.fillStyle = this.renk('--zemin-2');
      c.globalAlpha = .85;
      c.fillRect(sol - 2, y - 17, c.measureText(solMetin).width + 4, 14);
      c.globalAlpha = 1;
      c.fillStyle = this.renk('--cok-soluk');
      c.textAlign = 'left';
      c.fillText(solMetin, sol, y - 6);
      c.textAlign = 'right';
      c.fillText('şimdi', g - sag, y - 6);
    },

    /* B45 — bir serinin ölçeği. B27 A2: NaN = o pencerede kanal yanıt
       vermedi; ölçeğe girmez, çizgiyi koparır. `negatif` sıfırın yerini
       (ortada / altta), `tabanda` ölçeğin gürültü tabanından geldiğini
       söyler. Ayrı metot: çizimden bağımsız sınanabilsin. */
    grafikOlcek(veri, al, taban) {
      let enb = 0, gecerli = 0, negatif = false;
      for (const d of veri) {
        if (Number.isNaN(d[al])) continue;
        gecerli++;
        enb = Math.max(enb, Math.abs(d[al]));
        if (d[al] < 0) negatif = true;
      }
      const tepe = enb;
      const tabanda = enb < taban;
      if (tabanda) enb = taban;
      if (enb <= 0) enb = 1;
      return { enb, tepe, negatif, tabanda, gecerli };
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
        c.fillText('yakalama yok — “Yakala” düğmesine bas', g / 2, y / 2);
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
