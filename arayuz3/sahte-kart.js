/* ═══════════════════════════════════════════════════════════════════════
   SAHTE KART — donanım olmadan arayüzü çalıştırmak için

   Bu dosya firmware'in YERİNE geçiyor: aynı seri komutları alıyor, aynı
   protokol satırlarını (`D`, `S2`, `M`, `T`, `E`) üretiyor. Arayüzün
   ayrıştırıcısı, çizimi, ölçüm paneli ve denetimleri GERÇEK yollarından
   çalışıyor — sadece seri port taklit ediliyor.

   ⚠ Buradaki ölçüm hesapları DEMO içindir. Kartın gerçek ölçüm matematiği
   `kod/olcum-karti-a2/olcum2.h` içindeki `skop_olc()` fonksiyonudur ve
   doğrulama zincirinin A6 adımında AVR emülatöründe sınanır. Bu dosya o
   koda karşı bir kanıt DEĞİLDİR, yalnızca arayüzü beslemek içindir.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';

const SahteKart = (() => {
  /* Firmware ile AYNI sabitler — olcum-karti-a2.ino ve olcum2.h */
  const HZ_AZAMI = 83333;
  const HZ_ASGARI = 611;
  const AZAMI_ADET = 4000;
  const BOLME = 10;
  const TDIV_US = [100, 200, 500, 1000, 2000, 5000,
                   10000, 20000, 50000, 100000, 200000, 500000];
  const ADC_TAVAN = 3.10;
  const ADC_SAYIM = 4096;   // B20: LSB = tam olcek/4096
  const BOLME_ORANI = 38.03703704;   // B19: 100k/2.7k, çift yönlü
  const VOLT_ADIM = ADC_TAVAN / ADC_SAYIM * BOLME_ORANI;
  // B19: ofset VREF*ORAN DEGIL, VREF*(ORAN-1) — bkz. olcum3.h
  const VOLT_OFSET = 1.71531250 * (BOLME_ORANI - 1);

  /* Skop ayarları — firmware'deki SkopAyar'ın aynısı */
  const ayar = { tdiv: 6, esik: 2048, kenar: 0, histerezis: 40,
                 on: 25, kip: 0, onay: 2 };   // B47: onay 1/2 (gürültü reddi)

  /* Prob ucundaki test sinyalleri. Kullanıcı üstteki menüden seçiyor. */
  const SINYALLER = {
    sinus50: {
      ad: '50 Hz sinüs (şebeke frekansı)',
      f: 50,
      uret: (t) => 12 + 9 * Math.sin(2 * Math.PI * 50 * t),
    },
    sinus1k: {
      ad: '1 kHz sinüs',
      f: 1000,
      uret: (t) => 12 + 9 * Math.sin(2 * Math.PI * 1000 * t),
    },
    kare1k: {
      ad: '1 kHz kare dalga (%50)',
      f: 1000,
      uret: (t) => ((t * 1000) % 1 < 0.5 ? 21.5 : 2.5),
    },
    pwm: {
      ad: '20 kHz PWM (%30 duty) — SMPS kapı sinyali',
      f: 20000,
      uret: (t) => ((t * 20000) % 1 < 0.30 ? 14.5 : 0.4),
    },
    smps: {
      ad: '20 kHz anahtarlama + çalma (ringing)',
      f: 20000,
      uret: (t) => {
        const faz = (t * 20000) % 1;
        const taban = faz < 0.30 ? 14.5 : 0.4;
        /* kenar sonrası sönümlü çalma — gerçek bir MOSFET drain'i gibi */
        const dt = faz < 0.30 ? faz / 20000 : (faz - 0.30) / 20000;
        const calma = 7 * Math.exp(-dt * 9e5) *
                      Math.sin(2 * Math.PI * 2.2e5 * dt);
        return taban + (faz < 0.30 ? calma : -calma);
      },
    },
    dogrultulmus: {
      ad: '100 Hz doğrultulmuş (köprü çıkışı, dalgalanmalı)',
      f: 100,
      uret: (t) => 14 + 2.2 * Math.abs(Math.sin(2 * Math.PI * 50 * t)),
    },
    dc: {
      ad: 'Sabit 12 V (periyodik sinyal yok)',
      f: 0,
      uret: () => 12.0,
    },
  };

  let secili = 'sinus50';
  let gurultuKod = 6;          // ADC kodu cinsinden tepe gürültü

  /* skop_taban_coz() — firmware ile birebir aynı formül */
  function tabanCoz(tdivIdx) {
    const pencere = TDIV_US[tdivIdx] * BOLME * 1e-6;
    let hz = (BOLME * 100) / pencere;
    if (hz > HZ_AZAMI) hz = HZ_AZAMI;
    if (hz < HZ_ASGARI) hz = HZ_ASGARI;
    hz = Math.round(hz);
    let n = Math.round(pencere * hz);
    if (n > AZAMI_ADET) n = AZAMI_ADET;
    if (n < 100) n = 100;
    return { hz, n };
  }

  /* Prob gerilimini ADC koduna çevirir — kırpma dahil.
     Kart 0..48.7 V arasını görüyor; dışına çıkan kırpılıyor. */
  function kod(volt) {
    let k = Math.round((volt + VOLT_OFSET) / VOLT_ADIM
                       + (Math.random() - 0.5) * gurultuKod);
    if (k < 0) k = 0;
    if (k > 4095) k = 4095;
    return k;
  }

  /* Tetik arar; bulursa tetik indeksini döndürür, bulamazsa -1.
     Firmware'deki histerezis mantığının aynısı. */
  function tetikAra(veri, on) {
    let hazir = false;
    for (let i = 1; i < veri.length; i++) {
      const v = veri[i], o = veri[i - 1];
      if (ayar.kenar === 0) {
        if (!hazir) { if (v + ayar.histerezis < ayar.esik) hazir = true; }
        else if (o < ayar.esik && v >= ayar.esik) return i;
      } else {
        if (!hazir) { if (v > ayar.esik + ayar.histerezis) hazir = true; }
        else if (o > ayar.esik && v <= ayar.esik) return i;
      }
    }
    return -1;
  }

  /* Demo ölçümleri. Gerçek karttaki skop_olc() bunun yerine geçiyor. */
  function olc(veri, hz) {
    const n = veri.length;
    let mn = veri[0], mx = veri[0], top = 0, kt = 0;
    for (const v of veri) {
      if (v < mn) mn = v; if (v > mx) mx = v;
      const x = v * VOLT_ADIM - VOLT_OFSET; top += x; kt += x * x;
    }
    const ort = top / n;
    const rms = Math.sqrt(kt / n);
    const acv = kt / n - ort * ort;
    const o = {
      Vmax: mx * VOLT_ADIM - VOLT_OFSET, Vmin: mn * VOLT_ADIM - VOLT_OFSET,
      Vpp: (mx - mn) * VOLT_ADIM, Vort: ort, Vrms: rms,
      Vac: acv > 0 ? Math.sqrt(acv) : 0,
      f: 0, T: 0, duty: 0, tr: 0, tf: 0, n: 0,
    };
    const orta = (mn + mx) / 2, hist = (mx - mn) / 8;
    if (hist < 1) return o;

    let hazir = false, ilk = -1, son = -1, say = 0;
    for (let i = 1; i < n; i++) {
      const v = veri[i], p = veri[i - 1];
      if (!hazir) { if (v < orta - hist) hazir = true; }
      else if (v >= orta) {
        const d = v - p;
        const k = (i - 1) + (Math.abs(d) < 1e-9 ? 0 : (orta - p) / d);
        if (say === 0) ilk = k;
        son = k; say++; hazir = false;
      }
    }
    if (say >= 2) {
      const per = (son - ilk) / (say - 1);
      if (per > 0) {
        o.n = say - 1;
        o.T = per / hz;
        o.f = hz / per;
        let ust = 0, tp = 0;
        for (let i = Math.floor(ilk); i <= Math.floor(son) && i < n; i++) {
          if (veri[i] >= orta) ust++;
          tp++;
        }
        if (tp > 0) o.duty = 100 * ust / tp;
      }
    }
    return o;
  }

  /* Bir yakalama üretir ve protokol satırlarını döndürür. */
  function yakala() {
    const { hz, n } = tabanCoz(ayar.tdiv);
    const s = SINYALLER[secili];
    const on = Math.floor(n * ayar.on / 100);

    /* Gerçek kart halka tamponunu sürekli doldurup tetik bekliyor.
       Burada onun karşılığı: ihtiyaç duyduğumuzdan UZUN bir kayıt üretip
       içinde tetiği arıyoruz, sonra çevresinden bir pencere kesiyoruz.

       ⚠ Tamponu DÖNDÜRMEK (rotate) yanlış olurdu: sarma noktasında
       gerçekte var olmayan bir kenar oluşur ve frekans ölçümü bozulur. */
    const uzun = n * 3;
    const t0 = Math.random() * (s.f > 0 ? 1 / s.f : 0.01);
    const ham = [];
    for (let i = 0; i < uzun; i++) ham.push(kod(s.uret(t0 + i / hz)));

    /* Tetiği, öncesinde `on` kadar ve sonrasında (n-on) kadar örnek
       kalacak aralıkta ara. */
    let tMutlak = -1;
    let hazir = false;
    for (let i = 1; i < uzun; i++) {
      const v = ham[i], o = ham[i - 1];
      let vurdu = false;
      if (ayar.kenar === 0) {
        if (!hazir) { if (v + ayar.histerezis < ayar.esik) hazir = true; }
        else if (o < ayar.esik && v >= ayar.esik) vurdu = true;
      } else {
        if (!hazir) { if (v > ayar.esik + ayar.histerezis) hazir = true; }
        else if (o > ayar.esik && v <= ayar.esik) vurdu = true;
      }
      if (vurdu) { hazir = false; if (i >= on && i + (n - on) <= uzun) { tMutlak = i; break; } }
    }

    const tetiklendi = tMutlak >= 0;
    if (!tetiklendi && ayar.kip !== 0) return ['! tetiklenemedi'];

    const bas = tetiklendi ? tMutlak - on : 0;
    const cikti = ham.slice(bas, bas + n);
    const tIdx = tetiklendi ? on : 0;

    const m = olc(cikti, hz);
    const sat = [];
    sat.push(`S2 ${n} ${hz} ${VOLT_ADIM.toFixed(6)} ${tIdx} ` +
             `${TDIV_US[ayar.tdiv]} ${ayar.kip} ${tetiklendi ? 1 : 0} ` +
             `${VOLT_OFSET.toFixed(6)}`);   // B19: 9. alan
    sat.push(`M f=${m.f.toFixed(3)} T=${m.T.toFixed(9)} ` +
             `Vpp=${m.Vpp.toFixed(4)} Vmax=${m.Vmax.toFixed(4)} ` +
             `Vmin=${m.Vmin.toFixed(4)} Vort=${m.Vort.toFixed(4)} ` +
             `Vrms=${m.Vrms.toFixed(4)} Vac=${m.Vac.toFixed(4)} ` +
             `duty=${m.duty.toFixed(2)} tr=${m.tr.toFixed(9)} ` +
             `tf=${m.tf.toFixed(9)} n=${m.n}`);
    for (let i = 0; i < n; i += 16) {
      sat.push(cikti.slice(i, i + 16).join(' '));
    }
    sat.push('E');
    return sat;
  }

  function ayarSatiri() {
    const { hz, n } = tabanCoz(ayar.tdiv);
    return `T tdiv=${ayar.tdiv}/${TDIV_US.length - 1} ` +
           `(${TDIV_US[ayar.tdiv]} us/bolme) hz=${hz} adet=${n} ` +
           `pencere_ms=${(1000 * n / hz).toFixed(2)} esik=${ayar.esik} ` +
           `kenar=${ayar.kenar ? 'dusen' : 'yukselen'} ` +
           `hist=${ayar.histerezis} on=${ayar.on}% kip=${ayar.kip} onay=${ayar.onay}`;
  }

  /* Otomatik kurulum — firmware'deki skop_otomatik()'in karşılığı */
  function otomatik() {
    const s = SINYALLER[secili];
    if (!s.f) return ['! otomatik kurulum: periyodik sinyal yok'];

    /* ekranda ~4 çevrim olacak kademeyi seç */
    const hedefUs = (4 / s.f) / BOLME * 1e6;
    let enIyi = 0, enFark = Infinity;
    for (let i = 0; i < TDIV_US.length; i++) {
      const fark = Math.abs(Math.log(TDIV_US[i] / hedefUs));
      if (fark < enFark) { enFark = fark; enIyi = i; }
    }
    ayar.tdiv = enIyi;

    /* tetiği dalganın ortasına, histerezisi genliğin %10'una */
    const { hz, n } = tabanCoz(ayar.tdiv);
    let mn = 4095, mx = 0;
    for (let i = 0; i < n; i++) {
      const k = kod(s.uret(i / hz));
      if (k < mn) mn = k; if (k > mx) mx = k;
    }
    ayar.esik = Math.round((mn + mx) / 2);
    ayar.histerezis = Math.max(4, Math.round((mx - mn) / 10));
    return [ayarSatiri()].concat(yakala());
  }

  /* Seri komut işleyici — firmware'deki komut_calistir()'in karşılığı */
  let menzil = 0;         // 0 NORMAL, 1 YUKSEK
  let otoMenzil = true;
  /* B27 A2: rapor araligi — firmware ile AYNI sinirlar (20..5000) ve
     ayni kirpma davranisi; demo kipinde `r5` yazan 20 ms aldigini gormeli. */
  let raporMs = 200;
  const RAPOR_EN_AZ = 20, RAPOR_EN_COK = 5000;

  /* ── 3D — KAYIT MOTORU (demo) ───────────────────────────────────────
     Firmware'in `G` alt komutlari (b d ? n p) ve kendiliginden bastigi
     `G` / `GA` / `GT` / `GP` satirlari — BICIM olcum-karti-a3.ino
     kayit_durum_bas / kayit_ga_bas / kayit_gt_bas / kayit_gp_bas ile ayni
     (B7 alan sayisini firmware'den turetip sinar). Ret metinleri firmware'in
     metni. Kayitta saniyede bir G satiri (kayitTik). */
  const KAYIT_HIZLARI = [0, 20, 100, 200, 1000, 10000, 60000];
  const kayit = { durum: 1, oturum: 0, nokta: 0, sonraki: 120, onay: 0, doluluk: 18, onaysiz: 18,
                  dusen: 0, hiz: 200, sonG: 0, artik: 0, bayt: 0 };
  const plan = { durum: 0, bas: 0, sure: 0, hiz: 0, oturum: 0 };
  /* 3E (OS5): osiloskop gunlugu — firmware `kayit_skop_komut` metinleri ve GT satiri */
  const gunluk = { etkin: 0, aralik: 0, yakalama: 0, yazilamayan: 0 };
  const gtSatiri = () => `GT ${gunluk.etkin} ${gunluk.aralik} ${gunluk.yakalama} ${gunluk.yazilamayan}`;
  const gSatiri = () => `G ${kayit.durum} ${kayit.oturum} ${kayit.nokta} ${kayit.sonraki} ${kayit.onay}`
    + ` ${kayit.doluluk} ${kayit.onaysiz} ${kayit.dusen} 2900 1300 4 300 0`;
  const gaSatiri = () => `GA 480 ${kayit.durum === 2 && kayit.hiz === 0 ? kayit.nokta : 0} 0 0`;
  const gpSatiri = () => `GP ${plan.durum} ${plan.bas} ${plan.sure} ${plan.hiz} ${plan.oturum}`;
  function kayitBaslat(h) {
    kayit.durum = 2; kayit.oturum = kayit.sonraki++; kayit.nokta = 0; kayit.hiz = h; kayit.artik = 0;
  }
  function kayitKomut(k) {
    const alt = k[1];
    if (!alt || alt === '?') return [gSatiri(), gaSatiri(), gtSatiri(), gpSatiri()];
    if (alt === 't') {
      const r = k.slice(2);
      if (r === 'd') {
        const cikti = gunluk.etkin ? [] : ['! G: osiloskop gunlugu yok'];
        if (gunluk.etkin) {
          cikti.push(`* G osiloskop gunlugu durdu: ${gunluk.yakalama} yakalama, ${gunluk.yazilamayan} yazilamayan`);
          gunluk.etkin = 0;
        }
        return cikti;
      }
      const ms = Number(r);
      if (!/^\d{1,7}$/.test(r) || (ms !== 0 && (ms < 1000 || ms > 3600000))) {
        return ['! G: Gt<ms> — 0 (her tetik) ya da 1000..3600000; Gtd durdurur'];
      }
      if (gunluk.etkin) return ['! G: osiloskop gunlugu zaten suruyor (Gtd)'];
      Object.assign(gunluk, { etkin: 1, aralik: ms, yakalama: 0, yazilamayan: 0 });
      return ['* G osiloskop gunlugu basladi: ' + (ms ? ms + " ms'de bir" : 'her tetikte') + ' — SKOP oturumu'];
    }
    if (alt === 'b') {
      const h = Number(k.slice(2));
      if (!/^\d+$/.test(k.slice(2)) || !KAYIT_HIZLARI.includes(h)) {
        return ['! G: hiz 0 (her ornek) / 20/100/200/1000/10000/60000 ms olmali'];
      }
      kayitBaslat(h);
      return ['* G istek kuyrukta — sonuc G satirinda', gSatiri()];
    }
    if (alt === 'd') {
      if (kayit.durum === 2) { kayit.durum = 1; kayit.oturum = 0; }
      if (plan.durum === 2) plan.durum = 3;
      return ['* G istek kuyrukta — sonuc G satirinda', gSatiri()];
    }
    if (alt === 'n') {
      const m = /^Gn(\d+)(@\d+)?( (.*))?$/.exec(k);
      if (!m || Number(m[1]) === 0) return ['! G: oturum numarasi gerekli (yalniz rakam, 0 degil)'];
      if (!m[4]) return ["! G: numaradan sonra bosluk ve metin (Gn'de metin zorunlu)"];
      return ['* G not kuyrukta (verilmemis oturuma yazilmaz; sonuc esitlenen dosyada)'];
    }
    if (alt === 'p') {
      const r = k.slice(2);
      if (r === '-') {
        const vardi = plan.durum === 1 || plan.durum === 2;
        if (plan.durum === 2 && kayit.durum === 2) { kayit.durum = 1; kayit.oturum = 0; }
        plan.durum = 0;
        return [vardi ? '* G plan iptal' : '* G plan yok (bekleyen ya da suren plan yoktu)'];
      }
      if (!r || r === '?') return [gpSatiri()];
      const m = /^(\d+),(\d+),(\d+)$/.exec(r);
      if (!m) return ['! G: Gp<unix>,<sure_s>,<hiz_ms> ya da Gp+<saniye>,<sure_s>,<hiz_ms>; Gp- iptal'];
      const [bas, sure, hiz] = [Number(m[1]), Number(m[2]), Number(m[3])];
      const simdi = Math.floor(Date.now() / 1000);
      if (!KAYIT_HIZLARI.includes(hiz)) return ['! G: hiz 0 (her ornek) / 20/100/200/1000/10000/60000 ms olmali'];
      if (bas < 1700000000 || bas - simdi > 366 * 86400) {
        return ['! G: baslangic anlamsiz (unix saniye, en fazla 1 yil ileri; goreli icin Gp+<saniye>)'];
      }
      if (sure > 30 * 86400) return ['! G: sure en fazla 30 gun'];
      if (sure && bas + sure <= simdi) return ['! G: planin penceresi gecmis'];
      if (plan.durum === 2) return ['! G: plan suruyor — once Gp- (kaydini da durdurur)'];
      Object.assign(plan, { durum: 1, bas, sure, hiz, oturum: 0 });
      return [`* G plan kuruldu: ${bas} (+${bas - simdi} s), ${sure} s, ${hiz} ms — GP durum`];
    }
    return ['! G: alt komut b<ms> d ? o<sira> F!  a<id> e<id> n<id> x<id>:<sira>  t<ms> td  p<plan>'];
  }
  /* Demo dongusunden (app.js demoVeri) her D satirinda: kayitta nokta birikir,
     saniyede bir G satiri; plan zamani gelince oturum acilir. */
  function kayitTik(ms) {
    const cikti = [];
    const simdi = Math.floor(Date.now() / 1000);
    if (plan.durum === 1 && simdi >= plan.bas) {
      if (kayit.durum === 2) plan.durum = 4;
      else { kayitBaslat(plan.hiz); plan.durum = 2; plan.oturum = kayit.oturum; }
      cikti.push('* G plan basladi', gSatiri());
    } else if (plan.durum === 2 && plan.sure && simdi >= plan.bas + plan.sure) {
      plan.durum = 3;
      if (kayit.durum === 2) { kayit.durum = 1; kayit.oturum = 0; }
      cikti.push('* G plan suresi doldu — kayit kapaniyor', gSatiri());
    }
    if (kayit.durum === 2) {
      const gecen = kayit.sonG ? ms - kayit.sonG : 0;
      if (!kayit.sonG || gecen >= 1000) {
        const yeni = kayit.hiz ? gecen / kayit.hiz + kayit.artik : gecen * 0.5;
        kayit.nokta += Math.floor(yeni);
        kayit.artik = yeni - Math.floor(yeni);
        kayit.bayt += Math.floor(yeni) * (kayit.hiz ? 36 : 6);
        while (kayit.bayt >= 11923) { kayit.bayt -= 11923; kayit.doluluk++; kayit.onaysiz++; }
        kayit.sonG = ms;
        cikti.push(gSatiri());
      }
    } else {
      kayit.sonG = 0;
    }
    return cikti;
  }

  function komut(k) {
    k = String(k).trim();
    const c = k[0], alt = k[1];
    if (c === 'G') return kayitKomut(k);

    /* B36 — kalibrasyon tablosu. Sahte kart GERÇEK kartın protokolünü
       konuşmak zorunda: ayrışırsa demo, arayüzü gerçek yolundan
       sınamayı bırakır (bu projenin tekrarlayan hatası).
       Değerler GERÇEK KARTTAN alındı (2026-09-12, ESP32-S3 N16R8
       eFuse eğrisi) — uydurulmadı. */
    if (c === 'C' && alt === 'T') {
      return ['CT 17 oran=38.037037 ofset=63.530090 tavan_mv=3100.0'
            + ' 0:0 256:229 512:452 768:667 1024:883 1280:1095'
            + ' 1536:1309 1792:1524 2048:1739 2304:1954 2560:2165'
            + ' 2816:2372 3072:2568 3328:2750 3584:2914 3840:3053'
            + ' 4095:3160'];
    }

    if (c === 't') {
      /* 1C-3 / 3E: gunluk surerken ELLE yakalama yok (firmware skop_komut ile ayni metin) */
      if (gunluk.etkin && (!alt || (alt >= '0' && alt <= '9') || alt === 'B' || alt === 'a' || alt === 'K')) {
        return ['! skop: osiloskop gunlugu suruyor — elle yakalama yok (once Gtd)'];
      }
      if (!alt || (alt >= '0' && alt <= '9')) {
        if (alt) ayar.esik = parseInt(k.slice(1), 10) || ayar.esik;
        return yakala();
      }
      if (alt === '?') return [ayarSatiri()];
      if (alt === 'a') return otomatik();
      if (alt === 'b') {
        const v = parseInt(k.slice(2), 10);
        if (v >= 0 && v < TDIV_US.length) { ayar.tdiv = v; return [ayarSatiri()]; }
        return [`! tdiv 0..${TDIV_US.length - 1}`];
      }
      if (alt === '+') { ayar.tdiv = Math.min(TDIV_US.length - 1, ayar.tdiv + 1); return [ayarSatiri()]; }
      if (alt === '-') { ayar.tdiv = Math.max(0, ayar.tdiv - 1); return [ayarSatiri()]; }
      if (alt === 'l') { ayar.esik = Math.max(0, Math.min(4095, parseInt(k.slice(2), 10) || 0)); return [ayarSatiri()]; }
      if (alt === 'e') { ayar.kenar = parseInt(k.slice(2), 10) ? 1 : 0; return [ayarSatiri()]; }
      if (alt === 'h') { ayar.histerezis = Math.max(0, parseInt(k.slice(2), 10) || 0); return [ayarSatiri()]; }
      if (alt === 'p') { ayar.on = Math.max(0, Math.min(90, parseInt(k.slice(2), 10) || 0)); return [ayarSatiri()]; }
      if (alt === 'm') { ayar.kip = Math.max(0, Math.min(2, parseInt(k.slice(2), 10) || 0)); return [ayarSatiri()]; }
      if (alt === 'n') {
        const v = parseInt(k.slice(2), 10);
        if (v !== 1 && v !== 2) return ['! onay 1=tek ornek 2=iki ornek (gurultu reddi)'];
        ayar.onay = v; return [ayarSatiri()];
      }
      return ['! skop: t ta tb tl te th tp tm tn t? t+ t-'];
    }
    /* ASAMA 3 komut kumesi — firmware'in komut_calistir()'i ile AYNI
       harfler. Yanlis harf gonderilirse burasi da "bilinmeyen komut"
       der, yani demo kipi gercek kartla ayni sekilde davranir. */
    if (c === '?') {
      return ['A menzil=' + (menzil ? 'YUKSEK' : 'NORMAL') +
              ' oto=' + (otoMenzil ? 1 : 0) +
              ' n_kazanc=1.000000 n_sifir=-1646' +
              ' y_kazanc=1.000000 y_sifir=-91' +
              ' sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=' + raporMs,
              'R normal=+-32.44 V/1.0424 mV  yuksek=+-613.71 V/18.781 mV',
              'L normal -32.44 .. 35.87 V  yuksek -613.71 .. 617.14 V'];
    }
    if (c === '#') {
      return ['I2C: 0x48 0x49',
              '  beklenen: 0x48 (akim)  0x49 (gerilim) — bulunan 2'];
    }
    if (c === 'h' || c === 'Y') return ['Komutlar: ? # e z g n y a Z i s t w'];
    if (c === 'w') {
      /* B8 hizli yol — demo: PF 0.62'lik reaktif yuk.
         Son alan hizalamasiz guc; gercek kartta oldugu gibi SAPIK. */
      const vr = 12.02, ir = 0.0184, pf = 0.62;
      const s_ = vr * ir, p_ = s_ * pf;
      return [`W ${p_.toFixed(5)} ${s_.toFixed(5)} ${pf.toFixed(4)} ` +
              `${vr.toFixed(4)} ${ir.toFixed(5)} 12.0100 0.01820 297 ` +
              `${(p_ * 1.134).toFixed(5)} 1`,     // B39: kal=1 (gercek kart gibi)
              '  pencere 7.20 ms — 50 Hz icin 0.36 cevrim ' +
              '(1 cevrimin altinda yanlilik BUYUK)'];
    }
    if (c === 'e') return ['* enerji sifirlandi'];
    if (c === 'r') {
      if (k.length > 1) {
        let v = parseInt(k.slice(1), 10);
        if (!Number.isFinite(v)) v = raporMs;
        raporMs = Math.max(RAPOR_EN_AZ, Math.min(RAPOR_EN_COK, v));
      }
      return ['* rapor araligi ' + raporMs + ' ms'];
    }
    if (c === 'z') return ['* gerilim sifiri (' +
                           (menzil ? 'YUKSEK' : 'NORMAL') + ') ham=-1646'];
    if (c === 'Z') return ['* akim sifiri ham=-2'];
    if (c === 'n' || c === 'y') {
      menzil = (c === 'y') ? 1 : 0;
      otoMenzil = false;
      return ['* menzil ' + (menzil ? 'YUKSEK' : 'NORMAL') +
              ' (otomatik kapatildi)'];
    }
    if (c === 'a') {
      otoMenzil = k[1] === '1';
      return ['* otomatik menzil ' + (otoMenzil ? 'acik' : 'kapali')];
    }
    if (c === 'g') {
      const g = parseFloat(k.slice(1));
      /* Firmware sifira yakin girisi REDDEDIYOR — demo da reddetmeli,
         yoksa arayuz gercekte olmayan bir davranisa gore yazilir. */
      const esik = 0.05 * (menzil ? 613.71 : 32.44);
      if (!isFinite(g) || Math.abs(g) < esik) {
        return ["! kazanc kalibrasyonu reddedildi — giris tam olcegin " +
                "%5'inden kucuk"];
      }
      return [`* gerilim kazanci 1.002140  ${(g / 1.00214).toFixed(4)} -> ${g.toFixed(4)}`];
    }
    if (c === 'i') {
      const a = parseFloat(k.slice(1));
      if (!isFinite(a) || a === 0) return ['! akim kalibrasyonu reddedildi — akim cok kucuk'];
      return [`* akim duzeltmesi 0.998300`];
    }
    if (c === 's') {
      const r = parseFloat(k.slice(1));
      if (!(r > 1e-4)) return ['! sont degeri gecersiz'];
      return [`* sont ${r.toFixed(6)} ohm, menzil +-${(0.256 / r).toFixed(4)} A`];
    }
    return ['! bilinmeyen komut — `h` yardim'];
  }

  return {
    komut,
    kayitTik,                            // 3D: kayit motoru (G satirlari)
    raporAralik() { return raporMs; },   // B27 A2: demo dongusu bunu okur
    sinyaller: SINYALLER,
    sinyalSec(ad) { if (SINYALLER[ad]) secili = ad; },
    seciliSinyal() { return secili; },
    gurultuAyarla(k) { gurultuKod = Math.max(0, k); },
    /* Sürekli ölçüm akışı için tek bir D satırı üretir */
    /* Surekli olcum akisi icin tek bir D satiri.
       ASAMA 3: 9 alan (8. alan <menzil> eklendi) ve degerler CIFT YONLU —
       akim periyodik olarak isaret degistiriyor ki arayuzun negatif guc
       gosterimi demo kipinde de gorulebilsin. */
    dSatiri(ms, enerjiJ) {
      const v = 12 + 0.35 * Math.sin(ms / 4000) + 0.02 * (Math.random() - 0.5);
      /* 25 saniyede bir yon degistiren akim: yuk <-> kaynak */
      const a = 0.0182 * Math.sin(ms / 25000) +
                0.006 * Math.sin(ms / 7000 + 1) +
                0.00004 * (Math.random() - 0.5);
      const w = v * a;
      return {
        satir: `D ${v.toFixed(4)} ${a.toFixed(6)} ${w.toFixed(5)} ` +
               `${enerjiJ.toFixed(4)} ${(enerjiJ / 3600).toFixed(7)} ` +
               `${ms} ${Math.round(0.86 * raporMs)} ${menzil} 0`,   // B27/K1: durum=0; B27 A2: ornek = 860/s x aralik
        w,
      };
    },
    menzilSimdi() { return menzil; },
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SahteKart;
