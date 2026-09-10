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
                 on: 25, kip: 0 };

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
           `hist=${ayar.histerezis} on=${ayar.on}% kip=${ayar.kip}`;
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

  function komut(k) {
    k = String(k).trim();
    const c = k[0], alt = k[1];

    if (c === 't') {
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
      return ['! skop: t ta tb tl te th tp tm t? t+ t-'];
    }
    /* ASAMA 3 komut kumesi — firmware'in komut_calistir()'i ile AYNI
       harfler. Yanlis harf gonderilirse burasi da "bilinmeyen komut"
       der, yani demo kipi gercek kartla ayni sekilde davranir. */
    if (c === '?') {
      return ['A menzil=' + (menzil ? 'YUKSEK' : 'NORMAL') +
              ' oto=' + (otoMenzil ? 1 : 0) +
              ' n_kazanc=1.000000 n_sifir=-1646' +
              ' y_kazanc=1.000000 y_sifir=-91' +
              ' sont=0.100000 i_duz=1.000000 i_ofset=0',
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
              `${(p_ * 1.134).toFixed(5)}`,
              '  pencere 7.20 ms — 50 Hz icin 0.36 cevrim ' +
              '(1 cevrimin altinda yanlilik BUYUK)'];
    }
    if (c === 'e') return ['* enerji sifirlandi'];
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
               `${ms} 172 ${menzil}`,
        w,
      };
    },
    menzilSimdi() { return menzil; },
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SahteKart;
