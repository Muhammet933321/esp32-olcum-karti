/* ═══════════════════════════════════════════════════════════════════════
   4H — PANEL PC KOPRUSUNDE: bildirim bolumu · kabuk surumu · yerel ag uyarisi   (ekran/pc_kopru.js)

   Kararlar tasarim/2026-10-03-alt-proje-4-pc.md "4H uygulama kararlari".
   YALNIZ KOPRUDE INER (kartin sundugu panel bu dosyayi hic istemez):
     * ekran/ayarlar.js (Gelismis) — sayfa dongu kokenindeyse ve 4D'nin karari (`/durum`
       `pc_arsiv: true`) "pc" ise dinamik `import()`; yerel ag istemcisi indirmez.
     * app.js — yalniz koprunun `403 + X-Kopru-Ret: lan` yanitinda (kart bu basligi yollamaz).
   Bildirim bolumu koprunun `GET /bildirim/durum`unu okur, ac/kapa ve dili `POST /bildirim/ayar`
   ile yazar (X-Olcum + JSON; kopru KATI dogrular ve ayar.json'a birlestirir). Panel kendisi hicbir
   sey saklamaz; araci parolalari bu yolda YOK (kartta, yalniz USB).
   Metinler ortak/src/sozluk_pc.js (TR + EN). Duzen sinifi yeni CSS istemez (skop-kume / skop-secim /
   skop-alan / ay-*): acilistaki style.css buyumez.
   ⚠ Saf fonksiyonlar Vue'suz ve DOM'suz (B7 bolum 34 node'da sinar); ag `_getir`den (testte degisir).
   ═══════════════════════════════════════════════════════════════════════ */

import { ceviriPc } from '/ortak/sozluk_pc.js';

/** Koprunun bildirim siniflari — kopru/pc_bildirim.py SINIFLAR ile AYNI sira (B7 karsilastirir). */
export const BILDIRIM_SINIFLARI = Object.freeze(['kopuk', 'bitti', 'dolu', 'esik', 'yeniden_basladi', 'kacirilan', 'deneme']);
const SINIF_METIN = Object.freeze({
  kopuk: 'pc.bl_s_kopuk', bitti: 'pc.bl_s_bitti', dolu: 'pc.bl_s_dolu', esik: 'pc.bl_s_esik',
  yeniden_basladi: 'pc.bl_s_yeniden_basladi', kacirilan: 'pc.bl_s_kacirilan', deneme: 'pc.bl_s_deneme',
});
/** Sablonun metinleri (sozluk anahtarlari — sozluk_pc testi literal olarak bulsun). */
const PM = Object.freeze({ baslik: 'pc.bl_baslik', siniflar: 'pc.bl_siniflar', dil: 'pc.bl_dil', aciklama: 'pc.bl_aciklama',
  yukleniyor: 'ay.yukleniyor', yenile: 'ay.yenile' });
const DILLER = Object.freeze([Object.freeze({ id: 'tr', ad: 'ay.dil_tr' }), Object.freeze({ id: 'en', ad: 'ay.dil_en' })]);

/** Yerel ag istemcisinin cevrilmis "salt okuma" uyarisi (app.js, koprunun isaretli 403'u). */
export function lanMetni(dil) { return ceviriPc('pc.lan_salt', dil); }

/** `/durum` -> koprunun sundugu kabugun surumu (sw.js SURUM, 12 onaltilik); yoksa ''. */
export function kabukCoz(d) {
  return d && typeof d === 'object' && /^[0-9a-f]{12}$/.test(d.kabuk || '') ? d.kabuk : '';
}

/** Kabuk surumunu koprunun `/durum`undan oku (kopru ucu: imza katmanina girmez — EU8'). Hata -> ''. */
export async function kabukAl(kartAdres) {
  try {
    const y = await fetch(kartAdres('/durum'), { cache: 'no-store', credentials: 'omit' });
    return y.ok ? kabukCoz(await y.json().catch(() => null)) : '';
  } catch (h) { return ''; }
}

/** unix s -> yerel `YYYY-AA-GG SS:DD:SN` (dile gore DEGISMEZ — AY3); gecersizse '—'. */
function zamanYaz(s) {
  if (!(s > 0)) return '—';
  const d = new Date(s * 1000);
  const i = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}:${i(d.getSeconds())}`;
}

/** `/bildirim/durum` -> tek satir baglanti durumu (kapali / abone / bagli degil / alinamadi). */
export function bildirimDurumYazi(d, dil) {
  const t = (a, v) => ceviriPc(a, dil, v);
  if (!d || typeof d !== 'object') return t('pc.bl_alinamadi', { mesaj: 'JSON' });
  if (d.hata) return t('pc.bl_alinamadi', { mesaj: d.hata });
  if (d.etkin === false) return t('pc.bl_kapali', { neden: d.neden || '—' });
  const kart = t(d.kart_cevrimici === true ? 'pc.bl_kart_acik' : d.kart_cevrimici === false ? 'pc.bl_kart_kapali' : 'pc.bl_kart_bilinmiyor');
  return d.abone === true ? t('pc.bl_abone', { kart }) : t('pc.bl_bagli_degil', { mesaj: d.mesaj || '—', kart });
}

/** Son olay zamani ve turu (koprunun `son_olay` unix s, `son_olay_tur` kartin olay adi). */
export function sonOlayYazi(d, dil) {
  if (!d || typeof d !== 'object' || !(d.son_olay > 0)) return ceviriPc('pc.bl_son_yok', dil);
  return ceviriPc('pc.bl_son', dil, { zaman: zamanYaz(d.son_olay), tur: d.son_olay_tur || '—' });
}

/** Yazma govdesi: {bildirim: {<sinif>: bool}} ve/veya {dil}; kopruyle AYNI kural (bilinmeyen alan,
 *  sinif, bool olmayan deger, bilinmeyen dil, bos degisiklik -> null: istek HIC gitmez). */
export function ayarGovdesi(degisiklik) {
  if (!degisiklik || typeof degisiklik !== 'object' || Array.isArray(degisiklik)) return null;
  if (Object.keys(degisiklik).some((a) => a !== 'bildirim' && a !== 'dil')) return null;
  const g = {};
  if ('bildirim' in degisiklik) {
    const b = degisiklik.bildirim;
    if (!b || typeof b !== 'object' || Array.isArray(b) || !Object.keys(b).length) return null;
    if (Object.entries(b).some(([s, v]) => !BILDIRIM_SINIFLARI.includes(s) || typeof v !== 'boolean')) return null;
    g.bildirim = { ...b };
  }
  if ('dil' in degisiklik) {
    if (!DILLER.some((d) => d.id === degisiklik.dil)) return null;
    g.dil = degisiklik.dil;
  }
  return Object.keys(g).length ? JSON.stringify(g) : null;
}

const SABLON = `
<section class="kart" data-pc-bildirim>
  <h2>{{ m.baslik }}</h2>
  <div class="ay-ust">
    <p class="ipucu ay-kaynak" aria-live="polite" data-pc-bl-durum>{{ yukleniyor && !durum ? m.yukleniyor : durumYazi }}</p>
    <button type="button" @click="yukle" :disabled="yukleniyor" :aria-busy="yukleniyor ? 'true' : 'false'">{{ m.yenile }}</button>
  </div>
  <p class="ipucu" data-pc-bl-son>{{ sonYazi }}</p>
  <p v-if="uyari" class="uyari" data-pc-bl-uyari>{{ uyari }}</p>
  <fieldset class="skop-kume" :disabled="!ayar || kaydediliyor" data-pc-bl-siniflar>
    <legend>{{ m.siniflar }}</legend>
    <div class="skop-secim">
      <label v-for="s in siniflar" :key="s.id"><input type="checkbox" :checked="!!(ayar && ayar[s.id])" :data-pc-bl-sinif="s.id"
             @change="sinifDegistir(s.id, $event.target.checked)"> {{ s.ad }}</label>
    </div>
    <label class="skop-alan">{{ m.dil }}
      <select :value="dilAyar" data-pc-bl-dil @change="dilDegistir($event.target.value)">
        <option v-for="d in diller" :key="d.id" :value="d.id">{{ d.ad }}</option>
      </select>
    </label>
  </fieldset>
  <div class="ay-duyuru" aria-live="polite"><p v-if="sonuc" :class="sonucHata ? 'uyari' : 'ipucu'" data-pc-bl-sonuc>{{ sonuc }}</p></div>
  <p class="ipucu">{{ m.aciklama }}</p>
</section>`;

export const PcBildirimBolumu = {
  name: 'PcBildirimBolumu',
  props: {
    kartAdres: { type: Function, required: true },
    dilSecim: { type: String, default: 'tr' },
  },
  template: SABLON,
  data() {
    return { durum: null, yukleniyor: false, kaydediliyor: false, sonuc: '', sonucHata: false };
  },
  computed: {
    dil() { return this.dilSecim === 'en' ? 'en' : 'tr'; },
    m() { const m = {}; for (const [a, k] of Object.entries(PM)) m[a] = this.t(k); return m; },
    durumYazi() { return bildirimDurumYazi(this.durum, this.dil); },
    sonYazi() { return sonOlayYazi(this.durum, this.dil); },
    ayar() { const a = this.durum && this.durum.ayar; return a && typeof a === 'object' ? a : null; },
    dilAyar() { return this.durum && this.durum.dil === 'en' ? 'en' : 'tr'; },
    uyari() { return this.durum && this.durum.ayar_uyari ? this.t('pc.bl_uyari', { mesaj: this.durum.ayar_uyari }) : ''; },
    siniflar() { return BILDIRIM_SINIFLARI.map((id) => ({ id, ad: this.t(SINIF_METIN[id]) })); },
    diller() { return DILLER.map((d) => ({ id: d.id, ad: this.t(d.ad) })); },
  },
  mounted() { this.yukle(); },
  methods: {
    t(a, d = null) { return ceviriPc(a, this.dil, d); },
    _getir(yol, sec) { return fetch(this.kartAdres(yol), sec); },
    async yukle() {
      this.yukleniyor = true;
      try {
        const y = await this._getir('/bildirim/durum', { cache: 'no-store', credentials: 'omit' });
        this.durum = y.ok ? await y.json().catch(() => ({ hata: 'JSON' }))
          : { hata: y.status === 403 && y.headers && y.headers.get('X-Kopru-Ret') === 'lan' ? lanMetni(this.dil) : 'HTTP ' + y.status };
      } catch (h) {
        this.durum = { hata: (h && h.message) || String(h) };
      }
      this.yukleniyor = false;
    },
    /** Tek degisiklik yazilir; kopru reddederse sebep yazilir ve durum yeniden okunur (gercek hal). */
    async kaydet(degisiklik) {
      const govde = ayarGovdesi(degisiklik);
      if (govde === null) return;
      this.kaydediliyor = true;
      this.sonuc = '';
      try {
        const y = await this._getir('/bildirim/ayar', { method: 'POST', cache: 'no-store', credentials: 'omit',
          headers: { 'Content-Type': 'application/json', 'X-Olcum': '1' }, body: govde });
        if (y.ok) {
          const j = await y.json().catch(() => null);
          if (j && typeof j === 'object') this.durum = { ...(this.durum || {}), ayar: j.ayar, dil: j.dil, ayar_uyari: j.ayar_uyari };
          this.sonuc = this.t('pc.bl_kaydedildi');
          this.sonucHata = false;
        } else {
          const lan = y.status === 403 && y.headers && y.headers.get('X-Kopru-Ret') === 'lan';
          const metin = lan ? '' : await y.text().catch(() => '');
          this.sonuc = lan ? lanMetni(this.dil) : this.t('pc.bl_kayit_hata', { mesaj: metin || 'HTTP ' + y.status });
          this.sonucHata = true;
          await this.yukle();
        }
      } catch (h) {
        this.sonuc = this.t('pc.bl_kayit_hata', { mesaj: (h && h.message) || String(h) });
        this.sonucHata = true;
      }
      this.kaydediliyor = false;
    },
    sinifDegistir(sinif, acik) { return this.kaydet({ bildirim: { [sinif]: acik } }); },
    dilDegistir(dil) { return this.kaydet({ dil }); },
  },
};
