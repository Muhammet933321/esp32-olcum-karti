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

createApp({
  data() {
    return {
      destekli: 'serial' in navigator,
      bagli: false,
      hata: '',

      // anlık ölçüm
      volt: 0, amper: 0, watt: 0, joule: 0, wh: 0, kartMs: 0,
      ornekAdet: 0, sonAralik: 0,

      // geçmiş: { t (sn), v, i, w }
      gecmis: [],
      ilkMs: null,
      pencere: 60,
      gosterV: true, gosterI: true, gosterW: true,

      // osiloskop
      osilo: null,
      osiloBekliyor: false,
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

      // fare ile kaydırma
      suruk: null,

      // demo kipi
      demo: false,
      demoSinyal: 'sinus50',
      demoZaman: null,
      demoMs: 0,
      demoJ: 0,

      // denetimler
      sontSecim: '10',
      kalibV: '', kalibA: '',
      elleKomut: '',

      // günlük
      gunluk: [],
    };
  },

  computed: {
    ornekSayisi() { return this.gecmis.length; },

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
      const va = this.osilo ? this.osilo.voltAdim
                            : (3.10 / 4095 * 15.70588235);
      return this.skopEsik * va;
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
        l.push({ ad: 'Periyot', d: muh(o.T, 's', 3) });
      } else {
        l.push({ ad: 'Frekans', d: 'periyodik değil', vurgu: false });
      }
      l.push({ ad: 'Vpp', d: muh(o.Vpp, 'V', 3), vurgu: true });
      l.push({ ad: 'Vmax', d: muh(o.Vmax, 'V', 3) });
      l.push({ ad: 'Vmin', d: muh(o.Vmin, 'V', 3) });
      l.push({ ad: 'Vort', d: muh(o.Vort, 'V', 3) });
      l.push({ ad: 'Vrms', d: muh(o.Vrms, 'V', 3) });
      l.push({ ad: 'Vac (RMS)', d: muh(o.Vac, 'V', 3) });
      if (o.f > 0) l.push({ ad: 'Duty', d: o.duty.toFixed(1) + ' %' });
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
    orneklemeHizi() {
      if (!this.ornekAdet || !this.sonAralik) return '—';
      const hz = this.ornekAdet / (this.sonAralik / 1000);
      return (hz >= 1000 ? (hz / 1000).toFixed(1) + 'k' : Math.round(hz)) + ' /sn';
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

    sureGoster() {
      if (!this.gecmis.length) return '—';
      const s = Math.floor(this.gecmis[this.gecmis.length - 1].t);
      const sa = Math.floor(s / 3600), dk = Math.floor((s % 3600) / 60);
      return sa ? `${sa}s ${dk}dk` : dk ? `${dk}dk ${s % 60}sn` : `${s} sn`;
    },

    osiloTepe() {
      if (!this.osilo) return 0;
      return Math.max(...this.osilo.veri) * this.osilo.voltAdim;
    },
  },

  watch: {
    pencere() { this.grafikCiz(); },
    gosterV() { this.grafikCiz(); },
    gosterI() { this.grafikCiz(); },
    gosterW() { this.grafikCiz(); },
  },

  mounted() {
    window.addEventListener('resize', () => { this.grafikCiz(); this.osiloCiz(); });
    window.addEventListener('mousemove', (e) => this.surukHareket(e));
    window.addEventListener('mouseup', () => this.surukBitir());
    this.grafikCiz();
    this.osiloCiz();
    // ?demo — donanım olmadan arayüzü görmek için sahte veri üretir
    if (location.search.includes('demo')) this.demoVeri();
  },

  methods: {
    bicim(x, n) {
      if (!isFinite(x)) return '—';
      return x.toFixed(n);
    },

    /* Donanımsız önizleme: gerçek firmware satırlarını taklit eder.
       Adres çubuğuna ?demo eklenince çalışır. */
    /* ?demo — donanim olmadan arayuzu calistirir.
       Seri port yerine SahteKart devreye giriyor (arayuz/sahte-kart.js);
       ayristirici, cizim ve olcum paneli GERCEK yolundan calisiyor. */
    demoVeri() {
      this.demo = true;
      this.bagli = true;
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

      // canli akis: gercek kart gibi 200 ms'de bir D satiri
      this.demoZaman = setInterval(() => {
        this.demoMs += 200;
        const d = SahteKart.dSatiri(this.demoMs, this.demoJ);
        this.demoJ += d.w * 0.2;
        this.satirIsle(d.satir);
      }, 200);

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
    async baglan() {
      this.hata = '';
      try {
        this.port = await navigator.serial.requestPort();
        await this.port.open({ baudRate: 115200 });
        this.bagli = true;
        this.kaydet('— bağlandı, 115200 baud —');
        this.okumayaBasla();
      } catch (e) {
        if (e.name !== 'NotFoundError') this.hata = 'Bağlanamadı: ' + e.message;
      }
    },

    async kes() {
      this.durduruldu = true;
      try {
        if (this.okuyucu) await this.okuyucu.cancel().catch(() => {});
        if (this.kapanis) await this.kapanis.catch(() => {});
        if (this.port) await this.port.close();
      } catch (e) { /* kapanışta hata önemli değil */ }
      this.bagli = false;
      this.port = null;
      this.kaydet('— bağlantı kesildi —');
    },

    async okumayaBasla() {
      this.durduruldu = false;
      const cozucu = new TextDecoderStream();
      this.kapanis = this.port.readable.pipeTo(cozucu.writable).catch(() => {});
      this.okuyucu = cozucu.readable.getReader();

      let tampon = '';
      try {
        while (true) {
          const { value, done } = await this.okuyucu.read();
          if (done) break;
          tampon += value;
          let n;
          while ((n = tampon.indexOf('\n')) >= 0) {
            this.satirIsle(tampon.slice(0, n).trim());
            tampon = tampon.slice(n + 1);
          }
        }
      } catch (e) {
        if (!this.durduruldu) this.hata = 'Okuma hatası: ' + e.message;
      } finally {
        this.okuyucu.releaseLock();
      }
    },

    async gonder(metin) {
      /* Demo kipi: seri port yerine sahte kart. Arayuzun geri kalani
         (ayristirici, cizim, olcum paneli) GERCEK yolundan calisir. */
      if (this.demo) {
        this.kaydet(metin, true);
        const yanit = SahteKart.komut(metin);
        for (const sat of yanit) this.satirIsle(sat);
        return;
      }
      if (!this.port) return;
      const yazici = this.port.writable.getWriter();
      try {
        await yazici.write(new TextEncoder().encode(metin + '\n'));
        this.kaydet(metin, true);
      } finally {
        yazici.releaseLock();
      }
    },

    // ─────────────────────────────────────────────── satır ayrıştırma
    satirIsle(satir) {
      if (!satir) return;

      // Osiloskop yakalaması sürüyorsa: önce M (ölçüm) ve E (bitiş)
      // satırlarını ayır, kalanı ham veri olarak topla.
      if (this.osiloTopla) {
        if (satir[0] === 'M' && satir[1] === ' ') {
          // M f=<Hz> T=<s> Vpp=<V> ... n=<çevrim>
          const o = {};
          for (const alan of satir.slice(2).trim().split(/\s+/)) {
            const e = alan.indexOf('=');
            if (e > 0) o[alan.slice(0, e)] = parseFloat(alan.slice(e + 1));
          }
          this.osiloTopla.olcum = o;
          return;
        }
        if (satir.trim() === 'E') {
          this.osiloBitir();
          return;
        }
        for (const p of satir.split(/\s+/)) {
          const v = parseInt(p, 10);
          if (!isNaN(v)) this.osiloTopla.veri.push(v);
        }
        if (this.osiloTopla.veri.length >= this.osiloTopla.adet) {
          this.osiloBitir();
        }
        return;
      }

      const p = satir.split(/\s+/);

      // S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
      if (p[0] === 'S2' && p.length >= 8) {
        this.osiloTopla = {
          adet: parseInt(p[1], 10),
          hz: parseFloat(p[2]),
          voltAdim: parseFloat(p[3]),
          tetikIdx: parseInt(p[4], 10),
          tdivUs: parseInt(p[5], 10),
          kip: parseInt(p[6], 10),
          tetiklendi: p[7] === '1',
          olcum: null,
          veri: [],
        };
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

        if (this.ilkMs === null) this.ilkMs = this.kartMs;
        this.gecmis.push({
          t: (this.kartMs - this.ilkMs) / 1000,
          v: this.volt, i: this.amper, w: this.watt,
        });
        if (this.gecmis.length > 20000) this.gecmis.splice(0, 5000);
        this.grafikCiz();
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
      if (satir.startsWith('!')) this.osiloBekliyor = false;
    },

    // ─────────────────────────────────────────────── komutlar
    komut(k) { this.gonder(k); },

    /* Aşama 2 komut kümesi. Aşama 1'de bunlar 'r', 'kv', 'ka' idi;
       Aşama 2 firmware'i 's', 'v', 'i' bekliyor. Eski adlar gönderilirse
       kart "! bilinmeyen komut" der ve düğmeler sessizce çalışmaz. */
    sontGonder() { this.gonder('s' + this.sontSecim); },
    kalibreV() {
      const v = parseFloat(this.kalibV.replace(',', '.'));
      if (isFinite(v) && v > 0) { this.gonder('v' + v); this.kalibV = ''; }
    },
    kalibreA() {
      const a = parseFloat(this.kalibA.replace(',', '.'));
      if (isFinite(a) && a > 0) { this.gonder('i' + a); this.kalibA = ''; }
    },
    elleGonder() {
      if (this.elleKomut) { this.gonder(this.elleKomut); this.elleKomut = ''; }
    },

    /* ─────────────────────────────────────────────── osiloskop denetimi */
    osiloYakala() {
      this.osiloBekliyor = true;
      this.osiloTopla = null;
      this.gonder('t');
      setTimeout(() => { this.osiloBekliyor = false; }, 20000);
    },
    osiloOtomatik() {
      this.osiloBekliyor = true;
      this.osiloTopla = null;
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
      this.osiloYakala();
      this.surekliSayac++;
      const ge = (Date.now() - this.surekliT0) / 1000;
      if (ge > 0.5) this.surekliHiz = this.surekliSayac / ge;
      if (ge > 4) { this.surekliT0 = Date.now(); this.surekliSayac = 0; }
      /* Bir sonraki turu, aktarım bitsin diye kısa bir gecikmeyle kur. */
      this.surekliZaman = setTimeout(() => this.surekliTur(),
                                     this.demo ? 120 : 500);
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
    },

    gecmisiTemizle() {
      this.gecmis = [];
      this.ilkMs = null;
      this.grafikCiz();
    },

    csvIndir() {
      const satirlar = ['saniye;volt;amper;watt'];
      for (const g of this.gecmis) {
        satirlar.push(`${g.t.toFixed(3)};${g.v};${g.i};${g.w}`.replace(/\./g, ','));
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

      // Her seri kendi ölçeğinde çizilir (birimleri farklı).
      for (const s of seriler) {
        let enb = 0;
        for (const d of veri) enb = Math.max(enb, Math.abs(d[s.al]));
        if (enb <= 0) enb = 1;

        c.strokeStyle = s.renk;
        c.lineWidth = 1.8;
        c.lineJoin = 'round';
        c.beginPath();
        veri.forEach((d, i) => {
          const x = sol + en * (d.t - basT) / Math.max(this.pencere, 1e-6);
          const yy = ust + boy * (1 - d[s.al] / enb);
          i ? c.lineTo(x, yy) : c.moveTo(x, yy);
        });
        c.stroke();

        // tepe değeri sağ üstte
        c.fillStyle = s.renk;
        c.font = '600 11px ui-monospace, monospace';
        c.textAlign = 'right';
        const etiket = s.al === 'v' ? enb.toFixed(2) + ' V'
                     : s.al === 'i' ? (enb * 1e3).toFixed(1) + ' mA'
                     : (enb * 1e3).toFixed(1) + ' mW';
        c.fillText('tepe ' + etiket, g - sag,
                   ust + 12 + seriler.indexOf(s) * 14);
      }

      // zaman ekseni
      c.fillStyle = this.renk('--cok-soluk');
      c.font = '11px ui-monospace, monospace';
      c.textAlign = 'left';
      c.fillText(`-${this.pencere} sn`, sol, y - 6);
      c.textAlign = 'right';
      c.fillText('şimdi', g - sag, y - 6);
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

      const { veri, voltAdim, hz, adet } = this.osilo;
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
      let vmin = hmin * voltAdim, vmax = hmax * voltAdim;
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
        ust + boy * (1 - (v * voltAdim - vmin) / (vmax - vmin));

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
