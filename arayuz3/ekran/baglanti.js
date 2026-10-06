/* "ⓘ Bağlantı" penceresi (2026-10-06): hangi ölçümde neyi nereye takacağın — kutunun ön paneli
   resmi + kısa talimat. KAPALI başlar; düğmeye basınca bu modül iner (açılış bütçesi).
   Kullanıcı: "PopUp şeklinde çıksa ... boyutları farklı, standart olsun" → sayfanın ortasında
   SABİT boyutlu kalıcı pencere (role=dialog, aria-modal): arka plan karartılır, arkaya tıklama /
   × / Esc kapatır, Tab pencerenin içinde döner, sayfa arkada kaymaz. Boyut içerikten bağımsız
   (CSS .bb-pencere); her sekmede aynı.
   Resim ve metin ÜRETİLİYOR: ortak/src/baglanti_veri.js <- uretim/baglanti.py <- kutu_veri.py
   (PANEL_ON + BAGLANTI_REHBER). Burada yalnız gösterim; içerik değişikliği orada yapılır. */
import { BAGLANTI } from '/ortak/baglanti_veri.js';

const ODAKLANIR = 'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

export const BaglantiBilgi = {
  props: {
    ekran: { type: String, required: true },     // 'canli' | 'pil' | 'skop'
    dil: { type: String, default: 'tr' },
    menzil: { default: null },                   // kartin menzili: 1 (HV) ise o sekme secili gelir
  },
  emits: ['kapat'],
  data() {
    const liste = BAGLANTI.ekranlar[this.ekran] || [];
    const hv = liste.findIndex((k) => k.menzil !== null && k.menzil === this.menzil);
    return { sec: hv >= 0 ? hv : 0 };
  },
  computed: {
    d() { return this.dil === 'en' ? 'en' : 'tr'; },
    liste() { return BAGLANTI.ekranlar[this.ekran] || []; },
    kalem() { return this.liste[this.sec] || null; },
    y() { const y = BAGLANTI.yazi; const d = this.d; return { pencere: y.pencere[d], kapat: y.kapat[d], uyari: y.uyari[d] }; },
    baslikId() { return `bb-baslik-${this.ekran}`; },
  },
  mounted() {
    this._tus = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); this.$emit('kapat'); return; }
      if (e.key !== 'Tab' || !this.$refs.pencere) return;
      const o = [...this.$refs.pencere.querySelectorAll(ODAKLANIR)];
      if (!o.length) return;
      const ilk = o[0];
      const son = o[o.length - 1];
      if (e.shiftKey && document.activeElement === ilk) { e.preventDefault(); son.focus(); }
      else if (!e.shiftKey && document.activeElement === son) { e.preventDefault(); ilk.focus(); }
    };
    window.addEventListener('keydown', this._tus);
    this._tasma = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    this.$nextTick(() => { if (this.$refs.kapat) this.$refs.kapat.focus(); });
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this._tus);
    document.body.style.overflow = this._tasma || '';
  },
  template: `
  <teleport to="body">
    <div class="bb-arka" data-bb="arka" @click.self="$emit('kapat')">
      <section ref="pencere" class="kart baglanti-bilgi bb-pencere" :data-baglanti="ekran" role="dialog"
               aria-modal="true" :aria-labelledby="baslikId">
        <div class="bb-ust">
          <h2 :id="baslikId">{{ y.pencere }}</h2>
          <div v-if="liste.length > 1" class="bb-sekmeler" role="tablist">
            <button v-for="(k, i) in liste" :key="k.kimlik" type="button" role="tab" :data-bb-sekme="k.kimlik"
                    :aria-selected="i === sec ? 'true' : 'false'" :class="{ secili: i === sec }"
                    @click="sec = i">{{ k.baslik[d] }}</button>
          </div>
          <span class="bosluk"></span>
          <button ref="kapat" type="button" class="bb-kapat" data-bb="kapat" :aria-label="y.kapat" :title="y.kapat"
                  @click="$emit('kapat')">×</button>
        </div>
        <div v-if="kalem" class="bb-govde" :data-bb-kalem="kalem.kimlik">
          <div class="bb-sema" v-html="kalem.svg[d]"></div>
          <div class="bb-metin">
            <ul><li v-for="(s, i) in kalem.satirlar[d]" :key="i" v-html="s"></li></ul>
            <p v-if="kalem.uyari" class="bb-uyari" role="note"><b>{{ y.uyari }}:</b> <span v-html="kalem.uyari[d]"></span></p>
          </div>
        </div>
      </section>
    </div>
  </teleport>`,
};
