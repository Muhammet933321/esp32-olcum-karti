/* ═══════════════════════════════════════════════════════════════════════
   IMLEC OKUMASININ ACIKLAMASI                     (ekran/imlec_aciklama.js)

   2026-10-07 (kullanici): A, B, ΔT, "V A/B", ΔV, A ORT, YÜK, ENERJİ ne
   demek? Okuma izgarasinin yaninda "ⓘ Bu değerler ne demek?" dugmesi;
   acilinca her alan bir satir (terim + aciklama). TEK bilesen uc yerde:
     kip 'canli'  Canli (app.js; defineAsyncComponent — grafik dondurulunca iner)
     kip 'kayit'  kayit gorunumu (ekran/kayit_gorunum.js, statik)
     kip 'kr'     Karsilastirma (ekran/karsilastir.js, statik)
   Satirlar ekranin GERCEKTEN gosterdigi alanlar (canliOkuma / okumaSatirlari /
   kr tablosu); metinler formullere gore (ortak/src/sozluk_imlec.js basi).
   KAPALI baslar; acik/kapali yalniz bu bilesende (kalici degil).
   ⚠ Saf fonksiyonlar Vue'suz (B7 node'da sinar).
   ═══════════════════════════════════════════════════════════════════════ */

import { ceviriImlec } from '/ortak/sozluk_imlec.js';

/** Kip -> [terim anahtari, aciklama anahtari], ekrandaki SIRAYLA. */
export const IMLEC_ACIKLAMA_SATIR = Object.freeze({
  canli: Object.freeze([
    ['ia.t_ab', 'ia.ab_canli'], ['ia.t_dt', 'ia.dt'], ['ia.t_deger_canli', 'ia.deger'], ['ia.t_dv', 'ia.dv'],
    ['ia.t_ort_i', 'ia.ort_i'], ['ia.t_yuk', 'ia.yuk'], ['ia.t_enerji', 'ia.enerji'], ['ia.t_bosluk', 'ia.bosluk'],
  ]),
  kayit: Object.freeze([
    ['ia.t_ab', 'ia.ab_kayit'], ['ia.t_dt', 'ia.dt'], ['ia.t_deger_kayit', 'ia.deger'], ['ia.t_fark', 'ia.fark'],
    ['ia.t_ort', 'ia.ort'], ['ia.t_minmaks', 'ia.minmaks'], ['ia.t_yuk', 'ia.yuk'], ['ia.t_enerji', 'ia.enerji'],
    ['ia.t_sure', 'ia.sure'], ['ia.t_bosluk', 'ia.bosluk'],
  ]),
  kr: Object.freeze([
    ['ia.t_ab', 'ia.ab_kr'], ['ia.t_deger_kr', 'ia.deger_kr'], ['ia.t_fark', 'ia.fark'], ['ia.t_ort', 'ia.ort'],
    ['ia.t_yuk', 'ia.yuk'], ['ia.t_enerji', 'ia.enerji'], ['ia.t_bosluk', 'ia.bosluk'],
  ]),
});

/** Kipin satirlari secili dilde: [{a, terim, metin}]. Bilinmeyen kip -> 'kayit'. */
export function imlecAciklamaSatirlari(kip, dil = 'tr') {
  const l = Object.prototype.hasOwnProperty.call(IMLEC_ACIKLAMA_SATIR, kip) ? IMLEC_ACIKLAMA_SATIR[kip]
    : IMLEC_ACIKLAMA_SATIR.kayit;
  return l.map(([t, a]) => ({ a, terim: ceviriImlec(t, dil), metin: ceviriImlec(a, dil) }));
}

let sayac = 0;

export const ImlecAciklama = {
  name: 'ImlecAciklama',
  props: {
    kip: { type: String, default: 'kayit' },
    dil: { type: String, default: 'tr' },
  },
  data() {
    sayac += 1;
    return { acik: false, kimlik: 'imlec-aciklama-' + sayac };
  },
  computed: {
    dugme() { return ceviriImlec('ia.dugme', this.dil); },
    baslik() { return ceviriImlec('ia.baslik', this.dil); },
    satirlar() { return imlecAciklamaSatirlari(this.kip, this.dil); },
  },
  template: `
<div class="imlec-aciklama yazdirma-yok" :data-imlec-aciklama="kip">
  <button type="button" class="imlec-aciklama-dugme" :aria-expanded="acik ? 'true' : 'false'" :aria-controls="kimlik"
          @click="acik = !acik"><span aria-hidden="true">ⓘ</span> {{ dugme }}</button>
  <dl v-if="acik" :id="kimlik" class="imlec-aciklama-liste" :aria-label="baslik">
    <div v-for="s in satirlar" :key="s.a" class="imlec-aciklama-satir" :data-ia="s.a">
      <dt>{{ s.terim }}</dt><dd>{{ s.metin }}</dd>
    </div>
  </dl>
</div>`,
};
