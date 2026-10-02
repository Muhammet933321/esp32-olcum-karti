/* ═══════════════════════════════════════════════════════════════════════
   3C — KAYITLAR                                     (ekran/kayitlar.js)

   Liste (karar C4) + kayit gorunumune yonlendirme (C7). Bu modul app.js'e
   `defineAsyncComponent(() => import('./ekran/kayitlar.js'))` ile, ekran
   ILK acildiginda iner: karttan her dosya istegi olcum dongusunu blokluyor
   ve sayfanin acilis istekleri (B7: <= 8) buyumesin.

   LISTE = kartin dizini (`/kayit/liste`) ∪ bu tarayicidaki oturumlar.
   Satir: tur · ad · baslangic · sure · nokta · etiketler · NEREDE · durum.
     nerede  'kart'     yalniz kartta (esitlenmemis; kart temizlerse gider)
             'tarayici' yalniz bu tarayicida (kart silmis ya da eski kart)
             'ikisi'    ikisinde (yerel kopya eksikse "eksik kopya")
   Ayni oturum = ayni (akis kimligi, oturum no). Kartin akisindan baska bir
   kimligin oturumu "eski kart kopyasi" (C2: kimlik degisince yeni akis).
   SIRA (yeni -> eski): once kartin guncel akisi, sonra bu tarayicidaki eski
   akislar (olusma zamanina gore), akis icinde oturum numarasi azalan —
   oturum no akis icinde zamanla artiyor, saatsiz oturum da yerini bulur.
   ARAMA Turkce karakter duyarsiz (stok-takip `ara` gibi: "aku" -> "Akü"),
   ad / etiket / not metninde; "#12" yalniz 12 numarali oturumu, "12"
   numarayi ya da metni bulur.

   ROTA: `#/kayitlar` liste · `#/kayit/<no>` kayit · `#/kayit/<no>@<kimlik>`
   eski akistaki kayit · sonuna `/rapor` yazdirilabilir rapor. Geri tusu
   calisir (her acilis bir gecmis girdisi).
   3G (KR1): satirlarda karsilastirma secim kutusu (yalniz bu tarayicidaki
   kopyasi olan, grafigi olan oturum; en cok KR_AZAMI), "Karsilastir" ->
   `#/karsilastir/<no>@<kimlik>,…` (ekran/karsilastir.js).
   ⚠ Saf fonksiyonlar Vue'suz (B7 node'da sinar); bilesen globalThis.Vue'yu
     yalniz calisirken kullanir.
   ═══════════════════════════════════════════════════════════════════════ */

import { zamanEkseni } from '/ortak/disari.js';
import { ceviri } from '/ortak/sozluk.js';
import { OTURUM_OLCUM, OTURUM_PIL, OTURUM_SKOP } from '/ortak/kayit.js';
import {
  KayitGorunumu, oturumTuru, metinler, sureYaz, tarihYaz, TUR_METIN, NEREDE_METIN,
} from './kayit_gorunum.js';
import {
  EsitlemeDenetcisi, esitlemeUygunlugu, onayIslevi, arsivOku, arsivYaz, dilOku,
} from './esitleme.js';

/* ── SAF fonksiyonlar ───────────────────────────────────────────────── */

/** Turkce karakter duyarsiz kucuk harf: "AKÜ ŞARJ İı" -> "aku sarj ii". */
export function metinSadele(s) {
  return String(s === null || s === undefined ? '' : s).toLocaleLowerCase('tr-TR')
    .replace(/ı/g, 'i')                    // noktasiz i NFD ile AYRISMAZ; c g o s u isaretleri asagida duser
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/** Hash -> {oturum, kimlik, rapor}; liste icin oturum null. */
export function rotaCoz(hash) {
  const h = String(hash || '').replace(/^#\/?/, '');
  const m = /^kayit\/(\d+)(?:@(\d+))?(\/rapor)?\/?$/.exec(h);
  if (!m) return { oturum: null, kimlik: null, rapor: false };
  return { oturum: Number(m[1]), kimlik: m[2] === undefined ? null : Number(m[2]), rapor: !!m[3] };
}

/** {oturum, kimlik?, rapor?} -> hash. oturum yoksa liste. */
export function rotaYaz({ oturum = null, kimlik = null, rapor = false } = {}) {
  if (oturum === null || oturum === undefined) return '#/kayitlar';
  return `#/kayit/${oturum}${kimlik === null || kimlik === undefined ? '' : '@' + kimlik}${rapor ? '/rapor' : ''}`;
}

/** Kartin `tur` + `hiz_ms` alanlarindan ekran turu (yerel oturumTuru ile ayni adlar). */
export function kartTuru(tur, hizMs) {
  if (tur === OTURUM_PIL) return 'pil';
  if (tur === OTURUM_SKOP) return 'skop';
  if (tur === OTURUM_OLCUM) return hizMs === 0 ? 'ayrinti' : 'olcum';
  return 'bilinmeyen';
}

/** Oturumun baslangicindan son verisine gecen sure (ms); bilinmiyorsa null.
 *  Liste icin HAFIF hesap: son nokta / son ayrintili kayit / son yakalama. */
export function oturumSuresiMs(o) {
  const eksen = zamanEkseni(o);
  const seg = (s) => {
    let n = 0;
    for (const d of eksen.devamSiralari) if (d <= s) n++;
    return eksen.segmentler[n];
  };
  let son = null;
  if (o.noktalar.length) {
    let enb = o.noktalar[0];
    for (const p of o.noktalar) if (p[0] > enb[0]) enb = p;
    son = { sira: enb[0], ms: enb[1].kart_ms };
  } else if (o.ayrinti.length) {
    let r = o.ayrinti[0];
    for (const x of o.ayrinti) if (x.ilk > r.ilk) r = x;
    let us = 0;
    for (const q of r.ornekler) us += 4 * q[2];
    son = { sira: r.ilk, ms: r.t0_ms + Math.round(us / 1000) };
  } else if (o.skoplar.size) {
    let y = null;
    for (const [s, x] of o.skoplar) if (x.meta && (y === null || s > y[0])) y = [s, x];
    if (y) son = { sira: 0, ms: y[1].meta.t_ms + y[1].meta.sure_ms };
  }
  if (!son) return null;
  const s = seg(son.sira);
  if (!s || s.kartMs === null || s.ofsetMs === null) return null;
  return s.ofsetMs + ((son.ms - s.kartMs) | 0);
}

/** Yerel oturumun satir alanlari. */
export function yerelSatir(kimlik, o, yerelSon = 0) {
  const tur = oturumTuru(o);
  let nokta = o.noktalar.length;
  if (tur === 'ayrinti') nokta = o.ayrinti.reduce((n, r) => n + r.ornekler.length, 0);
  if (tur === 'skop') nokta = o.skoplar.size;
  return {
    kimlik, oturum: o.id, tur, ad: o.ad, etiketler: [...o.etiketler],
    notlar: [...o.notlar.values()].map((n) => n.metin),
    unix: o.basla ? o.basla.unix_s : 0, sureMs: oturumSuresiMs(o), nokta,
    yerelde: true, kartta: false, bitti: !!o.bitir, sebep: o.bitir ? o.bitir.sebep : null,
    yerelSon, kartSon: 0, kartDurum: 0, basiSilindi: !!o.basi_eksik && !o.basla,
  };
}

/** Kart dizini girdisi -> satir alanlari. */
export function kartSatiri(kimlik, k) {
  return {
    kimlik, oturum: k.id, tur: kartTuru(k.tur, k.hiz_ms), ad: null, etiketler: [], notlar: [],
    unix: k.unix_s || 0, sureMs: null, nokta: Number.isFinite(k.nokta) ? k.nokta : null,
    yerelde: false, kartta: true, bitti: k.durum === 2, sebep: null, yerelSon: 0,
    kartSon: k.son || 0, kartDurum: k.durum, basiSilindi: !!k.basi_silindi,
  };
}

/**
 * C4 birlesim. kart: `/kayit/liste` JSON ya da null (bilinmiyor). yereller: akisVerisi
 * sonuclari ({kimlik, oturumlar, sonSira}), YENIDEN ESKIYE. Donus: sirali satirlar.
 */
export function listeBirlestir({ kart = null, yereller = [] } = {}) {
  const guncel = kart ? kart.kimlik : null;
  const akisSira = [];
  if (guncel !== null) akisSira.push(guncel);
  for (const y of yereller) if (!akisSira.includes(y.kimlik)) akisSira.push(y.kimlik);
  const varsayilan = akisSira.length ? akisSira[0] : null;
  const satirlar = new Map();
  for (const y of yereller) {
    for (const o of y.oturumlar.values()) {
      satirlar.set(`${y.kimlik}:${o.id}`, yerelSatir(y.kimlik, o, (y.sonSira && y.sonSira.get(o.id)) || 0));
    }
  }
  if (kart) {
    for (const k of kart.oturumlar) {
      const a = `${guncel}:${k.id}`;
      const ks = kartSatiri(guncel, k);
      const ys = satirlar.get(a);
      if (!ys) {
        satirlar.set(a, ks);
        continue;
      }
      satirlar.set(a, {
        ...ys, kartta: true, kartSon: ks.kartSon, kartDurum: ks.kartDurum,
        tur: ys.tur === 'bilinmeyen' ? ks.tur : ys.tur, unix: ys.unix || ks.unix,
        nokta: ks.nokta !== null && ks.nokta > (ys.nokta || 0) && ys.tur !== 'skop' ? ks.nokta : ys.nokta,
        bitti: ys.bitti || ks.bitti, basiSilindi: ks.basiSilindi,
      });
    }
  }
  const aktif = kart ? kart.aktif : 0;
  const cikti = [...satirlar.values()].map((s) => {
    const nerede = s.kartta && s.yerelde ? 'ikisi' : s.kartta ? 'kart' : 'tarayici';
    const kayitta = s.kartta && s.kimlik === guncel && aktif === s.oturum;
    return {
      ...s,
      anahtar: `${s.kimlik}:${s.oturum}`,
      nerede,
      eskiKart: guncel !== null && s.kimlik !== guncel,
      eksik: nerede === 'ikisi' && s.kartSon > s.yerelSon,
      durum: kayitta ? 'kayitta' : s.bitti ? 'bitti' : 'acik',
      grup: akisSira.indexOf(s.kimlik),
      adres: rotaYaz({ oturum: s.oturum, kimlik: s.kimlik === varsayilan ? null : s.kimlik }),
      aramaMetni: metinSadele([s.ad || '', ...s.etiketler, ...s.notlar].join(' ')),
    };
  });
  return cikti.sort((a, b) => a.grup - b.grup || b.oturum - a.oturum);
}

/** Tur suzgecinin grubu: ayrintili olcum de "olcum". */
export function turGrubu(tur) {
  return tur === 'ayrinti' ? 'olcum' : tur;
}

/** Tek arama parcasi (sadelesmis) bu satira uyar mi. */
export function aramaUyar(s, p) {
  if (/^#\d+$/.test(p)) return s.oturum === Number(p.slice(1));
  if (/^\d+$/.test(p) && s.oturum === Number(p)) return true;
  return s.aramaMetni.includes(p);
}

/** Arama (bosluklu parcalarin HEPSI) + tur + nerede suzgeci. */
export function satirSuz(satirlar, { arama = '', tur = 'hepsi', nerede = 'hepsi' } = {}) {
  const parcalar = metinSadele(arama).split(/\s+/).filter(Boolean);
  return satirlar.filter((s) => (tur === 'hepsi' || turGrubu(s.tur) === tur)
    && (nerede === 'hepsi' || s.nerede === nerede)
    && parcalar.every((p) => aramaUyar(s, p)));
}

/** Kayit gorunumunun hangi akistan acilacagi: rota kimligi, yoksa varsayilan akis. */
export function rotaAkisi(rota, satirlar) {
  if (rota.kimlik !== null) return rota.kimlik;
  const s = satirlar.find((x) => x.oturum === rota.oturum && x.grup === 0);
  if (s) return s.kimlik;
  const herhangi = satirlar.find((x) => x.grup === 0);
  return herhangi ? herhangi.kimlik : null;
}

/* ── 3G: karsilastirma secimi (KR1, KR5) ────────────────────────────── */

/** KR1: en fazla bu kadar kayit karsilastirilir. Tek kaynak (karsilastir.js de bunu kullanir). */
export const KR_AZAMI = 6;
/** Grafigi olan ekran turleri: zaman grafigi skop gunlugunde yok (yakalama tablosu). */
export const KR_TURLER = Object.freeze(['olcum', 'ayrinti', 'pil']);

/**
 * KR1/KR5: satir karsilastirmaya eklenebilir mi. Donus {uygun, sebep (sozluk anahtari | null)}.
 * Yalniz bu tarayicidaki kopyasi olan (yerelde) ve grafigi olan oturum; secili olmayan satir
 * secim KR_AZAMI'ya ulasinca eklenemez (secili olan her zaman cikarilabilir).
 */
export function secilebilir(satir, { seciliMi = false, adet = 0 } = {}) {
  if (!satir || !satir.yerelde) return { uygun: false, sebep: 'kr.sec_kartta' };
  if (satir.tur === 'skop') return { uygun: false, sebep: 'kr.sec_skop' };
  if (!KR_TURLER.includes(satir.tur) || !(satir.nokta > 0)) return { uygun: false, sebep: 'kr.sec_bos' };
  if (!seciliMi && adet >= KR_AZAMI) return { uygun: false, sebep: 'kr.sec_dolu' };
  return { uygun: true, sebep: null };
}

/**
 * KR1 adresi: `#/karsilastir/<no>[@kimlik],…` + secime bagli olmayan durum sorguda
 * (`?x=<kip>&k=<kanal>`; varsayilan 'baslangic' / 'V' yazilmaz). Kayitlar listesi kimligi
 * HER ZAMAN yazar (3E S4 kurali: eski kart kopyasinda yanlis oturum acilmasin).
 * Cozucusu ekran/karsilastir.js karsilastirRotaCoz — B7 ikisinin birbirinin tersi oldugunu sinar.
 */
export function karsilastirRotaYaz({ secim = [], kip = 'baslangic', kanal = 'V' } = {}) {
  let h = '#/karsilastir';
  const p = secim.map((s) => `${s.oturum}${s.kimlik === null || s.kimlik === undefined ? '' : '@' + s.kimlik}`);
  if (p.length) h += '/' + p.join(',');
  const q = [];
  if (kip && kip !== 'baslangic') q.push('x=' + kip);
  if (kanal && kanal !== 'V') q.push('k=' + kanal);
  return h + (q.length ? '?' + q.join('&') : '');
}

export function baytYaz(n) {
  if (!(n >= 0)) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1024 / 1024).toFixed(2) + ' MB';
}

/* ── metinler (sozluk anahtarlari; C8) ──────────────────────────────── */
export const KL_METIN = Object.freeze({
  baslik: 'kl.baslik', esitle: 'kl.esitle', esitleniyor: 'kl.esitleniyor', yenile: 'kl.yenile',
  ilerleme: 'kl.ilerleme', nedenTaban: 'kl.neden_taban', nedenUsb: 'kl.neden_usb',
  nedenDemo: 'kl.neden_demo', nedenYok: 'kl.neden_yok', nedenImza: 'kl.neden_imza',
  nedenMesgul: 'kl.neden_mesgul', nedenHost: 'kl.neden_host', nedenAg: 'kl.neden_ag',
  nedenBozuk: 'kl.neden_bozuk', nedenHata: 'kl.neden_hata', nedenAkis: 'kl.neden_akis',
  nedenKilit: 'kl.neden_kilit', nedenDepo: 'kl.neden_depo', sonucYeni: 'kl.sonuc_yeni',
  sonucGuncel: 'kl.sonuc_guncel', onayGitti: 'kl.onay_gitti', onayDogrulanmadi: 'kl.onay_dogrulanmadi',
  onayBagliDegil: 'kl.onay_bagli_degil', bekleyen: 'kl.bekleyen', kalHata: 'kl.kal_hata',
  arsiv: 'kl.arsiv', arsivAciklama: 'kl.arsiv_aciklama', kartOzet: 'kl.kart_ozet', kartYok: 'kl.kart_yok',
  ara: 'kl.ara', turHepsi: 'kl.tur_hepsi', neredeHepsi: 'kl.nerede_hepsi', durumKayitta: 'kl.durum_kayitta',
  durumAcik: 'kl.durum_acik', durumBitti: 'kl.durum_bitti', eksik: 'kl.eksik', eskiKart: 'kl.eski_kart',
  basiSilindi: 'kl.basi_silindi', saatsiz: 'kl.saatsiz', bos: 'kl.bos', bosSuzgec: 'kl.bos_suzgec',
  noktaKisa: 'kl.nokta_kisa', ornekKisa: 'kl.ornek_kisa', yakalamaKisa: 'kl.yakalama_kisa',
  kopyalar: 'kl.kopyalar', kopyaSatir: 'kl.kopya_satir', kopyaGuncel: 'kl.kopya_guncel',
  kopyaEski: 'kl.kopya_eski', sil: 'kl.sil', silOnay: 'kl.sil_onay', vazgec: 'kl.vazgec',
  silUyari: 'kl.sil_uyari', yalnizKartta: 'kl.yalniz_kartta', bulunamadi: 'kl.bulunamadi',
  listeyeDon: 'kl.listeye_don', yukleniyor: 'kl.yukleniyor', ipucu: 'kl.ipucu',
  turSec: 'kl.tur_sec', neredeSec: 'kl.nerede_sec', liste: 'kl.liste',
  arsivOnayUyari: 'kl.arsiv_onay_uyari', arsivEminim: 'kl.arsiv_eminim',
});

/* 3G (KR8): listedeki karsilastirma secimi metinleri (`kr.` ailesi; ekran/karsilastir.js ile ortak). */
export const KL_KR_METIN = Object.freeze({
  karsilastir: 'kr.karsilastir', secimTemizle: 'kr.secim_temizle', secimBilgi: 'kr.secim_bilgi',
  secimYok: 'kr.secim_yok', sec: 'kr.sec', secCikar: 'kr.sec_cikar',
});

/* ── Vue bileseni ───────────────────────────────────────────────────── */

const SABLON = `
<div class="kl">
  <template v-if="rota.oturum !== null">
    <kayit-gorunumu v-if="secili" :key="seciliAnahtar" :veri="secili" :rapor="rota.rapor" :etkin="etkin"
      :dil="dil" :liste-adresi="'#/kayitlar'" :kayit-adresi="kayitAdresi(false)"
      :rapor-adresi="kayitAdresi(true)"></kayit-gorunumu>
    <section v-else class="kart">
      <a class="kg-geri" href="#/kayitlar">{{ m.listeyeDon }}</a>
      <p v-if="yukleniyor" class="ipucu">{{ m.yukleniyor }}</p>
      <p v-else class="uyari" data-kl-acilmadi>{{ seciliHata }}</p>
      <button v-if="seciliKartta && esitlenebilir" type="button" class="birincil" @click="esitle"
              :disabled="esitleniyor">{{ esitleniyor ? m.esitleniyor : m.esitle }}</button>
    </section>
  </template>

  <template v-else>
    <section class="kart">
      <h1>{{ m.baslik }}</h1>
      <div class="kl-ust">
        <div class="kl-durum">
          <span v-if="kartOzet" class="kl-kart-ozet">{{ kartOzet }}</span>
          <span v-else class="kl-kart-ozet kl-soluk">{{ m.kartYok }}</span>
        </div>
        <div class="dugme-grup">
          <button v-if="esitlenebilir" type="button" class="birincil kl-esitle" @click="esitle"
                  :disabled="esitleniyor" :aria-busy="esitleniyor ? 'true' : 'false'">{{ esitleniyor ? esitlemeYazisi : m.esitle }}</button>
          <button type="button" @click="yenile" :disabled="esitleniyor">{{ m.yenile }}</button>
        </div>
      </div>
      <!-- WIG: esitleme sonucu / sebebi KALICI bir canli bolgede (v-if ile sonradan eklenen
           role=status her ekran okuyucuda duyurulmuyor; bolge once DOM'da olmali). -->
      <div class="kl-duyuru" aria-live="polite">
        <p v-if="nedenMetni" class="uyari kl-neden" :data-neden="neden">{{ nedenMetni }}</p>
        <p v-if="sonuc" class="ipucu kl-sonuc">{{ sonuc }}</p>
      </div>
      <!-- WIG: arsivi ACMAK iki asamali (karta geri alinamaz "aldim" onaylari gider, kart
           kayitlari silebilir); kapatmak aninda. -->
      <label v-if="kartKimlik !== null" class="kl-arsiv">
        <input type="checkbox" :checked="arsiv || arsivOnay" @change="arsivDegisti($event.target.checked)"> {{ m.arsiv }}
      </label>
      <p v-if="arsivOnay" class="uyari kl-arsiv-onay">{{ m.arsivOnayUyari }}
        <span class="dugme-grup" style="margin-top:8px">
          <button type="button" class="kl-arsiv-eminim" @click="arsivOnayla">{{ m.arsivEminim }}</button>
          <button type="button" class="kl-arsiv-vazgec" @click="arsivVazgec">{{ m.vazgec }}</button>
        </span>
      </p>
      <p v-if="kartKimlik !== null" class="ipucu">{{ m.arsivAciklama }}</p>
    </section>

    <section class="kart">
      <h2>{{ m.liste }}</h2>
      <div class="kl-suzgec">
        <input type="search" class="kl-ara" v-model="arama" :placeholder="m.ara" :aria-label="m.ara"
               autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" enterkeyhint="search">
        <select v-model="turSuzgec" :aria-label="m.turSec">
          <option value="hepsi">{{ m.turHepsi }}</option>
          <option value="olcum">{{ turAdi('olcum') }}</option>
          <option value="pil">{{ turAdi('pil') }}</option>
          <option value="skop">{{ turAdi('skop') }}</option>
        </select>
        <select v-model="neredeSuzgec" :aria-label="m.neredeSec">
          <option value="hepsi">{{ m.neredeHepsi }}</option>
          <option value="kart">{{ neredeAdi('kart') }}</option>
          <option value="tarayici">{{ neredeAdi('tarayici') }}</option>
          <option value="ikisi">{{ neredeAdi('ikisi') }}</option>
        </select>
      </div>
      <p class="ipucu">{{ m.ipucu }}</p>
      <!-- 3G (KR1): karsilastirma secimi. Kutu baglantinin DISINDA (ic ice etkilesimli oge yok);
           secilemeyen satirin kutusu kapali ve SEBEBI etiketinde (KR5). -->
      <div class="kl-karsilastir" v-if="satirlar.length">
        <span class="kl-secim-bilgi" aria-live="polite">{{ secimBilgi }}</span>
        <span class="bosluk"></span>
        <button v-if="secim.length" type="button" @click="secimTemizle" data-kl-secim-temizle>{{ km.secimTemizle }}</button>
        <a v-if="secim.length >= 2" class="kl-karsilastir-git" :href="secimAdresi" data-kl-karsilastir>{{ km.karsilastir }}</a>
        <button v-else type="button" class="birincil" disabled data-kl-karsilastir>{{ km.karsilastir }}</button>
      </div>
      <div class="kl-liste">
        <div v-for="s in gorunenSatirlar" :key="s.anahtar" class="kl-satir-sarmal">
          <label class="kl-sec" :title="secimDurumlari[s.anahtar].ipucu">
            <input type="checkbox" :data-kl-sec="s.anahtar" :checked="secimDurumlari[s.anahtar].secili"
                   :disabled="!secimDurumlari[s.anahtar].uygun" :aria-label="secimDurumlari[s.anahtar].etiket"
                   @change="secimDegistir(s, $event.target.checked)">
          </label>
          <a class="kl-satir" :href="s.adres"
             :data-oturum="s.oturum" :data-kimlik="s.kimlik" :data-nerede="s.nerede">
            <span class="kl-tur">{{ turAdi(s.tur) }}</span>
            <span class="kl-ad">{{ s.ad || ('#' + s.oturum) }}<span v-if="s.ad" class="kl-no"> #{{ s.oturum }}</span></span>
            <span class="kl-bilgi">{{ baslangic(s) }} · {{ sure(s.sureMs) }} · {{ noktaYazi(s) }}</span>
            <span class="kl-rozetler">
              <span class="kl-rozet" :class="'kl-nerede-' + s.nerede">{{ neredeAdi(s.nerede) }}</span>
              <span class="kl-rozet" :class="'kl-durum-' + s.durum">{{ durumAdi(s.durum) }}</span>
              <span v-if="s.eksik" class="kl-rozet kl-dikkat">{{ m.eksik }}</span>
              <span v-if="s.eskiKart" class="kl-rozet kl-dikkat">{{ m.eskiKart }}</span>
              <span v-if="s.basiSilindi" class="kl-rozet">{{ m.basiSilindi }}</span>
              <span v-for="e in s.etiketler" :key="e" class="kl-rozet kl-etiket">{{ e }}</span>
            </span>
          </a>
        </div>
      </div>
      <p v-if="!gorunenSatirlar.length" class="ipucu kl-bos">{{ satirlar.length ? m.bosSuzgec : m.bos }}</p>
    </section>

    <section class="kart" v-if="kopyalar.length">
      <h2>{{ m.kopyalar }}</h2>
      <div class="kl-kopya" v-for="k in kopyalar" :key="k.kimlik" :data-kimlik="k.kimlik">
        <span class="kl-kopya-metin">{{ k.metin }}</span>
        <span class="kl-rozet" :class="k.guncel ? 'kl-nerede-ikisi' : 'kl-dikkat'">{{ k.guncel ? m.kopyaGuncel : m.kopyaEski }}</span>
        <span class="bosluk"></span>
        <template v-if="silOnay === k.kimlik">
          <button type="button" :data-kl-sil-eminim="k.kimlik" @click="kopyaSil(k.kimlik)">{{ m.silOnay }}</button>
          <button type="button" @click="silVazgec(k.kimlik)">{{ m.vazgec }}</button>
        </template>
        <button v-else type="button" :data-kl-sil="k.kimlik" @click="silBasla(k.kimlik)" :disabled="esitleniyor">{{ m.sil }}</button>
      </div>
      <p v-if="silOnay !== null" class="uyari">{{ m.silUyari }}</p>
    </section>
  </template>
</div>`;

const vueAl = () => globalThis.Vue;

export const KayitlarEkrani = {
  name: 'KayitlarEkrani',
  components: { 'kayit-gorunumu': KayitGorunumu },
  props: {
    kartAdres: { type: Function, required: true },
    /* 3H-2 (ES4): app.js'in TEK istek katmani (eslesmisse imzali); yoksa bugunku yol */
    kartIstek: { type: Function, default: null },
    kartTaban: { type: String, default: '' },
    tasiyici: { type: String, default: 'akis' },
    bagli: { type: Boolean, default: false },
    gonder: { type: Function, default: null },
    etkin: { type: Boolean, default: true },
    /* 3H (AY3): kabugun secili dili — degisince ANINDA (yeniden yukleme yok). */
    dilSecim: { type: String, default: null },
  },
  template: SABLON,
  data() {
    return {
      rota: rotaCoz(globalThis.location ? globalThis.location.hash : ''),
      dil: this.dilSecim === 'en' || this.dilSecim === 'tr' ? this.dilSecim : dilOku(),   // 3H: kabuktan
      arama: '', turSuzgec: 'hepsi', neredeSuzgec: 'hepsi',
      kartDurum: null, kartMesaj: '', kartKimlik: null, kartOzetVeri: null,
      esitleniyor: false, ilerleme: 0, sonuc: '', esitlemeNeden: null, esitlemeMesaj: '',
      arsiv: false, arsivOnay: false, satirlar: [], kopyalar: [], silOnay: null,
      secili: null, seciliAnahtar: '', seciliHata: '', seciliKartta: false, yukleniyor: false,
      secim: [],                 // 3G (KR1): [{anahtar, oturum, kimlik}] — secim sirasi = renk sirasi
    };
  },
  created() {
    this._den = new EsitlemeDenetcisi({ kartAdres: this.kartAdres, istek: this.kartIstek });
    this._kartListe = null;
    this._yereller = [];
  },
  computed: {
    m() { return metinler(KL_METIN, this.dil); },
    uygunluk() { return esitlemeUygunlugu({ kartTaban: this.kartTaban, tasiyici: this.tasiyici }); },
    esitlenebilir() { return this.uygunluk.uygun && this.kartDurum === 'tamam'; },
    /** Gosterilecek sebep: on kosul (C1), kart yaniti ya da son esitlemenin hatasi. */
    neden() {
      if (!this.uygunluk.uygun) return this.uygunluk.neden;
      if (this.kartDurum && this.kartDurum !== 'tamam') return this.kartDurum;
      return this.esitlemeNeden;
    },
    nedenMetni() {
      const n = this.neden;
      if (!n) return '';
      const harita = { taban: 'nedenTaban', usb: 'nedenUsb', demo: 'nedenDemo', yok: 'nedenYok',
        imza: 'nedenImza', mesgul: 'nedenMesgul', host: 'nedenHost', ag: 'nedenAg', bozuk: 'nedenBozuk',
        hata: 'nedenHata', akis: 'nedenAkis', kilit: 'nedenKilit', depo: 'nedenDepo' };
      const anahtar = KL_METIN[harita[n] || 'nedenHata'];
      const mesaj = this.esitlemeNeden === n ? this.esitlemeMesaj : this.kartMesaj;
      return ceviri(anahtar, this.dil, { mesaj: mesaj || '—' });
    },
    kartOzet() {
      const k = this.kartOzetVeri;
      if (!k) return '';
      return ceviri(KL_METIN.kartOzet, this.dil, { oturum: k.oturum, doluluk: (k.doluluk / 10).toFixed(1),
        onaysiz: (k.onaysiz / 10).toFixed(1) });
    },
    esitlemeYazisi() {
      return this.m.esitleniyor + (this.ilerleme ? ' ' + ceviri(KL_METIN.ilerleme, this.dil,
        { boyut: baytYaz(this.ilerleme) }) : '');
    },
    gorunenSatirlar() {
      return satirSuz(this.satirlar, { arama: this.arama, tur: this.turSuzgec, nerede: this.neredeSuzgec });
    },
    km() { return metinler(KL_KR_METIN, this.dil); },
    /** 3G (KR1/KR5): satir basina secim durumu — secili mi, eklenebilir mi, etiket ve sebep. */
    secimDurumlari() {
      const d = {};
      const adet = this.secim.length;
      for (const s of this.satirlar) {
        const secili = this.secim.some((x) => x.anahtar === s.anahtar);
        const u = secilebilir(s, { seciliMi: secili, adet });
        const ad = s.ad || `${ceviri(TUR_METIN[s.tur] || TUR_METIN.bilinmeyen, this.dil)} #${s.oturum}`;
        const sebep = u.sebep ? ceviri(u.sebep, this.dil) : '';
        d[s.anahtar] = { secili, uygun: u.uygun, sebep: u.sebep, ipucu: sebep,
          etiket: ceviri(secili ? KL_KR_METIN.secCikar : KL_KR_METIN.sec, this.dil, { ad })
            + (sebep ? ' — ' + sebep : '') };
      }
      return d;
    },
    secimBilgi() {
      return this.secim.length ? ceviri(KL_KR_METIN.secimBilgi, this.dil, { n: this.secim.length, azami: KR_AZAMI })
        : ceviri(KL_KR_METIN.secimYok, this.dil, { azami: KR_AZAMI });
    },
    secimAdresi() {
      return karsilastirRotaYaz({ secim: this.secim.map((x) => ({ oturum: x.oturum, kimlik: x.kimlik })) });
    },
  },
  watch: {
    etkin(v) { if (v) this.etkinlesti(); },
    rota() { this.kayitAc(); },
    /* C1 on kosulu degisti (Ayarlar'da adres / tasiyici): kartin dizinini yeniden sor. */
    kartTaban() { this.onKosulDegisti(); },
    tasiyici() { this.onKosulDegisti(); },
    /* 3H (AY3): dil degisti — metinler computed; kurulmus kopya satirlari yeniden yazilir. */
    dilSecim(v) {
      if (v !== 'tr' && v !== 'en') return;
      this.dil = v;
      this.listeKur();
    },
  },
  mounted() {
    this._hash = () => { this.rota = rotaCoz(location.hash); };
    window.addEventListener('hashchange', this._hash);
    this.etkinlesti();
  },
  beforeUnmount() {
    window.removeEventListener('hashchange', this._hash);
  },
  methods: {
    turAdi(t) { return ceviri(TUR_METIN[t] || TUR_METIN.bilinmeyen, this.dil); },
    neredeAdi(n) { return ceviri(NEREDE_METIN[n], this.dil); },
    durumAdi(d) { return this.m[{ kayitta: 'durumKayitta', acik: 'durumAcik', bitti: 'durumBitti' }[d]]; },
    sure(ms) { return sureYaz(ms); },
    baslangic(s) { return tarihYaz(s.unix) || this.m.saatsiz; },
    noktaYazi(s) {
      if (s.nokta === null || s.nokta === undefined) return '—';
      const b = s.tur === 'skop' ? this.m.yakalamaKisa : s.tur === 'ayrinti' ? this.m.ornekKisa : this.m.noktaKisa;
      return s.nokta + ' ' + b;
    },
    /** 3G (KR1): secime ekle / cikar; KR_AZAMI ve KR5 kurali secilebilir()'de (kutu zaten kapali). */
    secimDegistir(s, acik) {
      const var_ = this.secim.some((x) => x.anahtar === s.anahtar);
      if (!acik) {
        this.secim = this.secim.filter((x) => x.anahtar !== s.anahtar);
        return;
      }
      if (var_ || !secilebilir(s, { seciliMi: false, adet: this.secim.length }).uygun) return;
      this.secim = [...this.secim, { anahtar: s.anahtar, oturum: s.oturum, kimlik: s.kimlik }];
    },
    secimTemizle() { this.secim = []; },
    kayitAdresi(rapor) {
      const s = this.satirlar.find((x) => x.oturum === this.rota.oturum
        && x.kimlik === (this.secili ? this.secili.kimlik : null));
      return rotaYaz({ oturum: this.rota.oturum, kimlik: s && s.grup === 0 ? null : this.rota.kimlik, rapor });
    },
    /** Ekran gorunur oldu: once yerel kopya (hizli), sonra (C1 on kosulu tamamsa) esitleme —
     *  esitle() kartin dizinini kendisi tazeliyor; degilse yalniz dizin. */
    async etkinlesti() {
      if (this._calisiyor) return;
      this._calisiyor = true;
      try {
        await this.yereliYukle();
        if (this.uygunluk.uygun) {
          await this.esitle();
        } else {
          await this.kartYenile();
          this.listeKur();
          await this.kayitAc();
        }
      } finally {
        this._calisiyor = false;
      }
    },
    async onKosulDegisti() {
      this.esitlemeNeden = null;
      if (this.etkin && this.uygunluk.uygun && !this._calisiyor) {
        await this.esitle();
        return;
      }
      await this.kartYenile();
      this.listeKur();
    },
    async yereliYukle() {
      const yereller = [];
      try {
        const ozet = await this._den.akislar();
        for (const a of ozet) yereller.push({ ...(await this._den.akisVerisi(a.kimlik)), olusma: a.olusma });
      } catch (h) {
        this.esitlemeNeden = 'depo';
        this.esitlemeMesaj = (h && h.message) || String(h);
      }
      this._yereller = vueAl().markRaw(yereller);
      this.listeKur();
    },
    async kartYenile() {
      this.kartMesaj = '';
      if (!this.uygunluk.uygun) {
        this._kartListe = null;
        this.kartDurum = null;
        this.kartKimlik = null;
        this.kartOzetVeri = null;
        return;
      }
      const r = await this._den.kartListesi();
      this.kartDurum = r.durum;
      if (r.durum === 'tamam') {
        this._kartListe = vueAl().markRaw(r.liste);
        if (this.kartKimlik !== r.liste.kimlik) this.arsivOnay = false;   // onay kart basina
        this.kartKimlik = r.liste.kimlik;
        this.arsiv = arsivOku(r.liste.kimlik);
        this.kartOzetVeri = { oturum: r.liste.oturumlar.length, doluluk: r.liste.doluluk_binde || 0,
          onaysiz: r.liste.onaysiz_binde || 0 };
      } else {
        this._kartListe = null;
        this.kartKimlik = null;
        this.kartOzetVeri = null;
        this.kartMesaj = r.mesaj || '';
      }
    },
    listeKur() {
      const yereller = [...this._yereller];
      /* guncel akisi one al, kalanini yeniden eskiye */
      yereller.sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
      this.satirlar = listeBirlestir({ kart: this._kartListe, yereller });
      /* 3G: listeden dusen ya da artik secilemeyen (kopyasi silinen) oturum secimden cikar */
      this.secim = this.secim.filter((x) => this.satirlar.some((s) => s.anahtar === x.anahtar
        && secilebilir(s, { seciliMi: true }).uygun));
      const guncel = this._kartListe ? this._kartListe.kimlik : null;
      this.kopyalar = yereller.map((y) => ({ kimlik: y.kimlik, guncel: y.kimlik === guncel,
        metin: ceviri(KL_METIN.kopyaSatir, this.dil, { kimlik: y.kimlik, boyut: baytYaz(y.bayt),
          son: y.durum ? y.durum.son_sira : 0, oturum: y.oturumlar.size }) }));
    },
    async yenile() {
      this.sonuc = '';
      this.esitlemeNeden = null;
      await this.yereliYukle();
      await this.kartYenile();
      this.listeKur();
      await this.kayitAc();
    },
    /** Esitle (C1-C3). Her esitleme TAZE dizinle baslar: kimlik (akis) o anki karttan — eski
     *  bir dizinle baslamak, kart bu arada bicimlendiyse esitlemeyi "akis degisti" ile durdururdu.
     *  Esitleme ortasinda yine degisirse (yaris) dizin bir kez daha alinip YENI akisa gecilir.
     *  Onay islevi kimlik belli olduktan SONRA kurulur (arsiv secimi kart basina). */
    async esitle() {
      if (this.esitleniyor) return;
      this.esitleniyor = true;
      this.ilerleme = 0;
      this.sonuc = '';
      this.esitlemeNeden = null;
      try {
        await this.kartYenile();
        for (let deneme = 0; deneme < 2 && this.esitlenebilir; deneme++) {
          const kimlik = this._kartListe.kimlik;
          const onay = onayIslevi({ arsiv: this.arsiv, bagli: this.bagli, gonder: this.gonder });
          const r = await this._den.esitle({ kimlik, onay, ilerleme: (b) => { this.ilerleme = b; } });
          if (r.durum === 'tamam') {
            this.sonuc = this.sonucMetni(r.sonuc, onay);
            break;
          }
          this.esitlemeNeden = r.durum;
          this.esitlemeMesaj = r.mesaj;
          if (r.durum !== 'akis') break;
          await this.kartYenile();
          if (!this._kartListe || this._kartListe.kimlik === kimlik) break;   // akis gercekten degismedi
          this.esitlemeNeden = null;
        }
      } finally {
        this.esitleniyor = false;
      }
      await this.yereliYukle();
      await this.kartYenile();
      this.listeKur();
      await this.kayitAc();
    },
    sonucMetni(r, onay) {
      const p = [ceviri(r.yeni_kayit ? KL_METIN.sonucYeni : KL_METIN.sonucGuncel, this.dil,
        { yeni: r.yeni_kayit, son: r.son_sira })];
      if (r.bekleyen) p.push(ceviri(KL_METIN.bekleyen, this.dil, { bekleyen: r.bekleyen }));
      if (this.arsiv && !onay) p.push(this.m.onayBagliDegil);
      else if (onay) p.push(r.onay_dogrulandi ? this.m.onayGitti : this.m.onayDogrulanmadi);
      if (r.kalibrasyon_hata) p.push(ceviri(KL_METIN.kalHata, this.dil, { hata: r.kalibrasyon_hata }));
      return p.join(' ');
    },
    /* WIG: ACMAK iki asamali — isaretlemek yalniz onayi sorar (yazmaz, esitlemez); kapatmak aninda. */
    arsivDegisti(acik) {
      if (acik && !this.arsiv) {
        this.arsivOnay = true;
        this._odakla('.kl-arsiv-eminim');
        return;
      }
      this.arsivOnay = false;
      this.arsiv = !!acik;
      if (this.kartKimlik !== null) arsivYaz(this.kartKimlik, this.arsiv);
    },
    arsivOnayla() {
      this.arsivOnay = false;
      this.arsiv = true;
      if (this.kartKimlik !== null) arsivYaz(this.kartKimlik, true);
      if (this.esitlenebilir) this.esitle();
    },
    arsivVazgec() {
      this.arsivOnay = false;
      this._odakla('.kl-arsiv input');
    },
    /* WIG: kopya silme onayinda odak kaybolmasin (tiklanan dugme DOM'dan kalkiyor). */
    silBasla(kimlik) {
      this.silOnay = kimlik;
      this._odakla('[data-kl-sil-eminim="' + kimlik + '"]');
    },
    silVazgec(kimlik) {
      this.silOnay = null;
      this._odakla('[data-kl-sil="' + kimlik + '"]');
    },
    _odakla(secici) {
      this.$nextTick(() => {
        if (typeof document === 'undefined') return;
        const e = document.querySelector(secici);
        if (e && typeof e.focus === 'function') e.focus();
      });
    },
    async kopyaSil(kimlik) {
      this.silOnay = null;
      await this._den.akisSil(kimlik);
      await this.yenile();
    },
    /** Rotadaki oturumu bu tarayicinin kopyasindan ac (C5). */
    async kayitAc() {
      const r = this.rota;
      if (r.oturum === null) {
        this.secili = null;
        this.seciliHata = '';
        return;
      }
      const kimlik = rotaAkisi(r, this.satirlar);
      const satir = this.satirlar.find((x) => x.oturum === r.oturum && x.kimlik === kimlik) || null;
      const yerel = this._yereller.find((y) => y.kimlik === kimlik);
      const o = yerel ? yerel.oturumlar.get(r.oturum) : null;
      this.seciliKartta = !!(satir && satir.kartta);
      if (!o) {
        this.secili = null;
        this.seciliHata = satir && satir.kartta ? this.m.yalnizKartta
          : ceviri(KL_METIN.bulunamadi, this.dil, { oturum: r.oturum });
        return;
      }
      const anahtar = `${kimlik}:${r.oturum}:${yerel.bayt}`;
      if (this.secili && this.seciliAnahtar === anahtar) return;
      this.seciliHata = '';
      this.seciliAnahtar = anahtar;
      this.secili = vueAl().markRaw({ oturum: o, kayitlar: yerel.kayitlar, kimlik, kal: yerel.kal, satir });
    },
  },
};
