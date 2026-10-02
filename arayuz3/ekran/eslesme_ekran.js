/* ═══════════════════════════════════════════════════════════════════════
   3H-2 — AYARLAR > ESLESTIRME EKRANI              (ekran/eslesme_ekran.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H-2 kararlari" (ES1,
   ES3, ES7-ES9) ve EU11-EU13, EU21, EU25-EU27, EU30. Istemci (depo, imzali
   istek, akis) ekran/eslesme.js'te; bu modul onu app.js'in TEK istemcisi
   olarak alir (prop `istemciAl`), kendisi karta istek yollamaz.

   EU30: bu modul ve metinleri (ortak/sozluk_es.js) YALNIZ Ayarlar >
   Eslestirme acilinca iner — eslesmis tarayicinin acilisina GIRMEZ
   (yalniz istemci iner; 3D siniri). Kabugun es. metinleri sozluk.js'te.
   ⚠ Parola `ref` ile okunur, esles cagrilmadan ONCE alan bosaltilir; Vue
     durumuna girmez, hicbir yere yazilmaz (B7 + T3H2 tarar).
   ═══════════════════════════════════════════════════════════════════════ */

import { adGecerli, PAROLA_EN_AZ } from '/ortak/imza.js';
import { utf8Kodla } from '/ortak/kripto.js';
import { ceviriEs } from '/ortak/sozluk_es.js';

/* ── metinler (sozluk anahtarlari; ES10) ────────────────────────────── */
export const ES_METIN = Object.freeze({
  baslik: 'es.baslik', aciklama: 'es.aciklama', bKimlik: 'es.b_kimlik', bZorunlu: 'es.b_zorunlu', bMisafir: 'es.b_misafir',
  bSaat: 'es.b_saat', acik: 'es.acik', kapali: 'es.kapali', denetleniyor: 'es.d_denetleniyor',
  ad: 'es.ad', adIpucu: 'es.ad_ipucu', parola: 'es.parola', parolaIpucu: 'es.parola_ipucu', eslestir: 'es.eslestir',
  eslesiyor: 'es.eslesiyor', unut: 'es.unut', unutEminim: 'es.unut_eminim', unutUyari: 'es.unut_uyari',
  listeBaslik: 'es.liste_baslik', listeTablo: 'es.liste_tablo', lN: 'es.l_n', lAd: 'es.l_ad', lEklenme: 'es.l_eklenme',
  lSon: 'es.l_son', lIslem: 'es.l_islem', buTarayici: 'es.bu_tarayici', kaldir: 'es.kaldir', kaldirEminim: 'es.kaldir_eminim',
  kaldirUyari: 'es.kaldir_uyari', saatBaslik: 'es.saat_baslik', saatAyarla: 'es.saat_ayarla', saatIpucu: 'es.saat_ipucu',
  saatNtpVar: 'es.saat_ntp_var', saatEslesmeli: 'es.saat_eslesmeli', guvBaslik: 'es.guv_baslik', guvAciklama: 'es.guv_aciklama',
  anahtarBaslik: 'es.anahtar_baslik', anahtarAciklama: 'es.anahtar_aciklama', bildirimBaslik: 'es.bildirim_baslik',
  bildirimAciklama: 'es.bildirim_aciklama', yenile: 'ay.yenile', vazgec: 'kl.vazgec',
  yabanciBaslik: 'es.yabanci_baslik', yabanciAciklama: 'es.yabanci_aciklama', yabanciSil: 'es.yabanci_sil', silEminim: 'es.sil_eminim',
});
/** /eslestir/bilgi `saat`: 0 yok, 1 NTP, 2 cihazdan (guvenlik_esp.h guv_saat_kaynak). */
export const SAAT_METIN = Object.freeze(['es.saat_yok', 'es.saat_ntp', 'es.saat_cihaz']);
const DURUM_METIN = Object.freeze({ yok: 'es.d_yok', hazir: 'es.d_hazir', tanimiyor: 'es.d_tanimiyor', ag: 'es.d_ag',
  kartYok: 'es.d_kart_yok' });
const UYGUN_METIN = Object.freeze({ usb: 'es.uygun_usb', demo: 'es.uygun_demo', taban: 'es.uygun_taban' });
const UNUT_METIN = Object.freeze({ silindi: 'es.unutuldu', ulasilamadi: 'es.unutuldu_ulasilamadi',
  tanimiyordu: 'es.unutuldu_tanimiyor', hata: 'es.unutuldu_hata', yok: 'es.unutuldu_yok' });
const SONUC_METIN = Object.freeze({ eslesti: 'es.eslesti', kaldirildi: 'es.kaldirildi', kaldirHata: 'es.kaldir_hata',
  listeHata: 'es.liste_hata', saatTamam: 'es.saat_tamam', saatHata: 'es.saat_hata' });

export function metinler(harita, dil) {
  const m = {};
  for (const [a, k] of Object.entries(harita)) m[a] = ceviriEs(k, dil);
  return m;
}

/** ES1: eslestirme yalniz panel kartin KENDI adresinden (akis kipi, bos taban; 3C C1 ile ayni kural). */
export function eslesmeUygunlugu({ kartTaban = '', tasiyici = 'akis' } = {}) {
  if (tasiyici === 'seri') return { uygun: false, neden: 'usb' };
  if (tasiyici === 'demo') return { uygun: false, neden: 'demo' };
  if (String(kartTaban || '').trim()) return { uygun: false, neden: 'taban' };
  return { uygun: true, neden: null };
}

/** ES7: varsayilan cihaz adi — tarayici/isletim sistemi (listede ayirt edilsin). ASCII, <= 24 bayt. */
export function varsayilanAd(ua) {
  const s = String(ua || '');
  const t = /Edg\//.test(s) ? 'Edge' : /Firefox\//.test(s) ? 'Firefox' : /(Chrome|CriOS)\//.test(s) ? 'Chrome'
    : /Safari\//.test(s) ? 'Safari' : '';
  const i = /iPhone|iPad|iPod/.test(s) ? 'iOS' : /Android/.test(s) ? 'Android' : /Windows/.test(s) ? 'Windows'
    : /Mac OS X|Macintosh/.test(s) ? 'macOS' : /Linux|X11/.test(s) ? 'Linux' : '';
  return t ? (i ? `${t}/${i}` : t) : 'Tarayici';
}

const KART_RET = /^\/eslestir\/(baslat|kanit): (\d+) ([\s\S]*)$/;

/**
 * ES3: eslestirme hatasi -> {anahtar, d} (sozluk). Kartin metni `kart`ta, 429'da Retry-After
 * saniyesi `sn`de (istemci son yanittan yakalar).
 */
export function retSebebi(h, { retry = null } = {}) {
  const ad = h && h.name;
  const mesaj = String((h && h.message) || h || '');
  if (ad === 'TypeError' || ad === 'AbortError' || ad === 'TimeoutError') return { anahtar: 'es.ret_ag', d: { mesaj } };
  if (ad === 'DegerHatasi') {
    if (/parola en az/.test(mesaj)) return { anahtar: 'es.ret_kisa', d: { en_az: PAROLA_EN_AZ } };
    if (/^ad /.test(mesaj)) return { anahtar: 'es.ret_ad', d: {} };
    return { anahtar: 'es.ret_bilgi', d: { mesaj } };
  }
  if (ad === 'CalismaHatasi') {
    const m = KART_RET.exec(mesaj);
    if (m) {
      const kod = m[2];
      const kart = m[3].trim();
      if (kod === '403') return { anahtar: m[1] === 'kanit' ? 'es.ret_parola' : 'es.ret_kart_parola', d: { kart } };
      if (kod === '429') return { anahtar: 'es.ret_bekle', d: { kart, sn: retry === null || retry === undefined ? '?' : String(retry) } };
      if (kod === '409') return { anahtar: 'es.ret_dolu', d: { kart } };
      if (kod === '410') return { anahtar: 'es.ret_sure', d: { kart } };
      return { anahtar: 'es.ret_http', d: { kod, kart } };
    }
    if (/kart kaniti YANLIS/.test(mesaj)) return { anahtar: 'es.ret_sahte', d: {} };
  }
  if (ad === 'HttpHatasi') return { anahtar: 'es.ret_http', d: { kod: String(h.durum), kart: '' } };
  return { anahtar: 'es.ret_diger', d: { mesaj } };
}

/* ── Vue bileseni (Ayarlar > Eslestirme) ────────────────────────────── */

const SABLON = `
<div class="es-mod">
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.baslik }}</h2>
    <p class="ipucu">{{ m.aciklama }}</p>
    <div class="ay-ust">
      <p class="ay-ozet" data-es-durum tabindex="-1" aria-live="polite">{{ durumYazi }}</p>
      <button type="button" @click="yenile" :disabled="calisiyor" :aria-busy="calisiyor ? 'true' : 'false'">{{ m.yenile }}</button>
    </div>
    <dl class="ay-bilgi" v-if="bilgi" data-es-bilgi>
      <dt>{{ m.bKimlik }}</dt><dd><code>{{ bilgi.kimlik }}</code></dd>
      <dt>{{ m.bZorunlu }}</dt><dd data-es-zorunlu>{{ bilgi.zorunlu ? m.acik : m.kapali }}</dd>
      <dt>{{ m.bMisafir }}</dt><dd data-es-misafir>{{ bilgi.misafir ? m.acik : m.kapali }}</dd>
      <dt>{{ m.bSaat }}</dt><dd data-es-saat>{{ saatYazi }}</dd>
    </dl>
    <p v-if="uygunluk.neden" class="ipucu" data-es-uygun>{{ uygunYazi }}</p>
    <form v-else-if="!cihaz && bilgi" class="es-form" data-es-form @submit.prevent="eslestir">
      <div class="alan">
        <label for="es-ad">{{ m.ad }}</label>
        <input id="es-ad" type="text" name="cihaz-adi" v-model="ad" autocomplete="off" autocapitalize="off" spellcheck="false"
               maxlength="24" :aria-invalid="retAlan === 'ad' ? 'true' : null"
               :aria-describedby="retAlan === 'ad' ? 'es-ad-ipucu es-ret' : 'es-ad-ipucu'" required>
        <span class="ipucu" id="es-ad-ipucu">{{ m.adIpucu }}</span>
      </div>
      <div class="alan">
        <label for="es-parola">{{ m.parola }}</label>
        <input id="es-parola" ref="parola" type="password" name="parola" autocomplete="current-password"
               :aria-invalid="retAlan === 'parola' ? 'true' : null"
               :aria-describedby="retAlan === 'parola' ? 'es-parola-ipucu es-ret' : 'es-parola-ipucu'" required>
        <span class="ipucu" id="es-parola-ipucu">{{ m.parolaIpucu }}</span>
      </div>
      <button type="submit" class="birincil" data-es-eslestir :disabled="calisiyor" :aria-busy="calisiyor ? 'true' : 'false'">{{ calisiyor ? m.eslesiyor : m.eslestir }}</button>
    </form>
    <div class="ay-duyuru" aria-live="polite"><p v-if="sonuc" class="ipucu" data-es-sonuc>{{ sonuc }}</p></div>
    <p v-if="ret" id="es-ret" class="hata" role="alert" data-es-ret>{{ ret }}</p>
    <div v-if="cihaz" class="dugme-grup">
      <template v-if="unutOnay">
        <button type="button" class="tehlike" data-es-unut-eminim @click="unut">{{ m.unutEminim }}</button>
        <button type="button" data-es-unut-vazgec @click="unutVazgec">{{ m.vazgec }}</button>
      </template>
      <button v-else type="button" data-es-unut @click="unutBasla" :disabled="calisiyor">{{ m.unut }}</button>
    </div>
    <p v-if="unutOnay" class="uyari" role="alert">{{ m.unutUyari }}</p>
  </section>

  <section class="kart" v-if="hazir" data-ay-bolum="eslestirme">
    <h2 id="es-liste-baslik" tabindex="-1">{{ m.listeBaslik }}</h2>
    <p v-if="listeHata" class="hata" role="alert" data-es-liste-hata>{{ listeHata }}</p>
    <div v-if="liste.length" class="ay-tablo-sarmal">
      <table class="ay-tablo" data-es-liste>
        <caption class="gorunmez">{{ m.listeTablo }}</caption>
        <thead><tr>
          <th scope="col">{{ m.lN }}</th><th scope="col">{{ m.lAd }}</th><th scope="col">{{ m.lEklenme }}</th>
          <th scope="col">{{ m.lSon }}</th><th scope="col">{{ m.lIslem }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="c in liste" :key="c.n" :data-es-cihaz="c.n" :class="{ 'ay-etkin': c.n === kendiN }">
            <th scope="row">{{ c.n }}</th>
            <td class="ay-metin">{{ c.ad }} <span v-if="c.n === kendiN" class="kl-rozet kl-nerede-ikisi">{{ c.n === kendiN ? m.buTarayici : '' }}</span></td>
            <td>{{ zaman(c.eklenme) }}</td><td>{{ zaman(c.son) }}</td>
            <td class="ay-islem">
              <button v-if="c.n === kendiN" type="button" :data-es-kendi="c.n" @click="unutBasla">{{ m.unut }}</button>
              <template v-else-if="kaldirOnay === c.n">
                <button type="button" class="tehlike" :data-es-kaldir-eminim="c.n" @click="kaldir(c.n)">{{ m.kaldirEminim }}</button>
                <button type="button" @click="kaldirVazgec(c.n)">{{ m.vazgec }}</button>
              </template>
              <button v-else type="button" :data-es-kaldir="c.n" @click="kaldirBasla(c.n)" :disabled="calisiyor">{{ m.kaldir }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="kaldirOnay !== null" class="uyari" role="alert">{{ m.kaldirUyari }}</p>
  </section>

  <section class="kart" v-if="yabanci.length" data-ay-bolum="eslestirme" data-es-yabanci>
    <h2 id="es-yabanci-baslik" tabindex="-1">{{ m.yabanciBaslik }}</h2>
    <p class="ipucu">{{ m.yabanciAciklama }}</p>
    <ul class="es-yabanci">
      <li v-for="y in yabanci" :key="y.kimlik" :data-es-yabanci-kayit="y.kimlik">
        <span class="ay-metin"><code>{{ y.kimlik }}</code> · {{ y.ad }} ({{ m.lN }} {{ y.n }})</span>
        <span class="dugme-grup">
          <template v-if="yabanciOnay === y.kimlik">
            <button type="button" class="tehlike" :data-es-yabanci-eminim="y.kimlik" @click="yabanciSil(y.kimlik)">{{ m.silEminim }}</button>
            <button type="button" @click="yabanciVazgec(y.kimlik)">{{ m.vazgec }}</button>
          </template>
          <button v-else type="button" :data-es-yabanci-sil="y.kimlik" @click="yabanciBasla(y.kimlik)">{{ m.yabanciSil }}</button>
        </span>
      </li>
    </ul>
  </section>

  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.saatBaslik }}</h2>
    <p class="ipucu">{{ m.saatIpucu }}</p>
    <button v-if="hazir && bilgi && bilgi.saat !== 1" type="button" data-es-saat-ayarla @click="saatAyarla" :disabled="calisiyor">{{ m.saatAyarla }}</button>
    <p v-else-if="bilgi && bilgi.saat === 1" class="ipucu" data-es-ntp>{{ m.saatNtpVar }}</p>
    <p v-else class="ipucu">{{ m.saatEslesmeli }}</p>
  </section>

  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.guvBaslik }}</h2>
    <p class="ipucu" data-es-guv>{{ m.guvAciklama }}</p>
  </section>
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.anahtarBaslik }}</h2>
    <p class="ipucu" data-es-anahtar>{{ m.anahtarAciklama }}</p>
  </section>
  <section class="kart" data-ay-bolum="eslestirme">
    <h2>{{ m.bildirimBaslik }}</h2>
    <p class="ipucu" data-es-bildirim>{{ m.bildirimAciklama }}</p>
  </section>
</div>`;

function zamanYaz(s) {
  if (!(s > 0)) return '—';
  const d = new Date(s * 1000);
  const i = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}`;
}

export const EslestirmeEkrani = {
  name: 'EslestirmeEkrani',
  props: {
    istemciAl: { type: Function, required: true },     // app.js eslesmeIstemcisi (TEK istemci)
    kartTaban: { type: String, default: '' },
    tasiyici: { type: String, default: 'akis' },
    bagli: { type: Boolean, default: false },
    dilSecim: { type: String, default: 'tr' },
    etkin: { type: Boolean, default: true },
  },
  template: SABLON,
  data() {
    return {
      ad: varsayilanAd(globalThis.navigator ? globalThis.navigator.userAgent : ''),
      durum: 'bilinmiyor', bilgi: null, bilgiKod: null, cihaz: null, agMesaj: '',
      calisiyor: false, ret: '', retAlan: null, sonuc: '', liste: [], listeHata: '', kaldirOnay: null, unutOnay: false,
      yabanci: [], yabanciOnay: null,
    };
  },
  computed: {
    dil() { return this.dilSecim === 'en' ? 'en' : 'tr'; },
    m() { return metinler(ES_METIN, this.dil); },
    uygunluk() { return eslesmeUygunlugu({ kartTaban: this.kartTaban, tasiyici: this.tasiyici }); },
    uygunYazi() { return this.uygunluk.neden ? ceviriEs(UYGUN_METIN[this.uygunluk.neden], this.dil) : ''; },
    hazir() { return this.durum === 'hazir' && !!this.cihaz; },
    kendiN() { return this.cihaz ? this.cihaz.n : null; },
    saatYazi() { return this.bilgi ? ceviriEs(SAAT_METIN[this.bilgi.saat] || SAAT_METIN[0], this.dil) : '—'; },
    durumYazi() {
      const c = this.cihaz || {};
      if (this.durum === 'bilinmiyor') return this.m.denetleniyor;
      if (this.durum === 'ag') return ceviriEs(DURUM_METIN.ag, this.dil, { mesaj: this.agMesaj || '—' });
      if (this.durum === 'yok' && !this.bilgi) return ceviriEs(DURUM_METIN.kartYok, this.dil, { kod: this.bilgiKod === null ? '?' : this.bilgiKod });
      if (this.durum === 'tanimiyor') {
        return ceviriEs(DURUM_METIN.tanimiyor, this.dil, { n: c.n, ad: c.ad, mesaj: c.tanimiyorMesaj || '—' });
      }
      return ceviriEs(DURUM_METIN[this.durum] || DURUM_METIN.yok, this.dil, { n: c.n, ad: c.ad });
    },
  },
  watch: {
    etkin(v) { if (v) this.yenile(); else { this.kaldirOnay = null; this.unutOnay = false; this.yabanciOnay = null; } },
  },
  mounted() {
    if (this.etkin) this.yenile();
  },
  methods: {
    zaman(s) { return zamanYaz(s); },
    _odakla(secici) {
      this.$nextTick(() => {
        if (typeof document === 'undefined') return;
        const e = document.querySelector(secici);
        if (e && typeof e.focus === 'function') e.focus();
      });
    },
    _al(ist) {
      this.durum = ist.durum;
      this.bilgi = ist.bilgi ? { ...ist.bilgi } : null;
      this.bilgiKod = ist.bilgiKod;
      this.cihaz = ist.cihaz ? { n: ist.cihaz.n, ad: ist.cihaz.ad, tanimiyorMesaj: ist.cihaz.tanimiyorMesaj || '' } : null;
    },
    /** Kartin bilgisi + bu tarayicinin kaydi (+ eslesmisse cihaz listesi). */
    async yenile() {
      this.kaldirOnay = null;
      this.unutOnay = false;
      this.yabanciOnay = null;
      if (this.uygunluk.neden) { this.durum = 'yok'; return; }
      let ist;
      try {
        ist = await this.istemciAl();
        await ist.coz(true);
        this._al(ist);
      } catch (h) {
        this.durum = 'ag';
        this.agMesaj = (h && h.message) || String(h);
        return;
      }
      await this.yabanciYukle(ist);
      if (this.hazir) await this.listeYukle(ist);
    },
    /** EU26: bu tarayicida baska kart kimligine ait kayitlar (yalniz yerel silinebilir). */
    async yabanciYukle(ist) {
      try {
        const i = ist || await this.istemciAl();
        this.yabanci = typeof i.yabancilar === 'function' ? await i.yabancilar() : [];
      } catch (h) {
        this.yabanci = [];
      }
    },
    yabanciBasla(k) {
      this.yabanciOnay = k;
      this._odakla('[data-es-yabanci-eminim="' + k + '"]');
    },
    yabanciVazgec(k) {
      this.yabanciOnay = null;
      this._odakla('[data-es-yabanci-sil="' + k + '"]');
    },
    /** EU26: ikinci asama — YALNIZ silahli satirin kaydi, YALNIZ bu tarayicidan. */
    async yabanciSil(k) {
      if (this.yabanciOnay !== k) return;
      this.yabanciOnay = null;
      try {
        const ist = await this.istemciAl();
        await ist.yerelSil(k);
        await this.yabanciYukle(ist);
      } catch (h) {
        this.sonuc = ceviriEs('es.ret_diger', this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this._odakla(this.yabanci.length ? '#es-yabanci-baslik' : '[data-es-durum]');
    },
    async listeYukle(ist) {
      this.listeHata = '';
      try {
        const l = await (ist || await this.istemciAl()).cihazListe();
        if (l === null) { this._al(ist || await this.istemciAl()); this.liste = []; return; }
        this.liste = l;
      } catch (h) {
        this.liste = [];
        this.listeHata = ceviriEs(SONUC_METIN.listeHata, this.dil, { mesaj: (h && h.message) || String(h) });
      }
    },
    /** ES3: parola alandan okunur ve esles cagrilmadan ONCE bosaltilir; Vue durumuna girmez. */
    async eslestir() {
      const alan = this.$refs.parola;
      const parola = alan ? alan.value : '';
      if (alan) alan.value = '';
      this.ret = '';
      this.retAlan = null;
      this.sonuc = '';
      if (!adGecerli(this.ad)) {
        this.ret = ceviriEs('es.ret_ad', this.dil);
        this.retAlan = 'ad';
        this._odakla('#es-ad');
        return;
      }
      if (utf8Kodla(parola).length < PAROLA_EN_AZ) {
        this.ret = ceviriEs('es.ret_kisa', this.dil, { en_az: PAROLA_EN_AZ });
        this.retAlan = 'parola';
        this._odakla('#es-parola');
        return;
      }
      this.calisiyor = true;
      let ist = null;
      try {
        ist = await this.istemciAl();
        const c = await ist.esles(this.ad, parola);
        this._al(ist);
        this.sonuc = ceviriEs(SONUC_METIN.eslesti, this.dil, { n: c.n });
        await this.listeYukle(ist);
        this._odakla('[data-es-durum]');              // EU27: form kalkti — odak durum satirina
      } catch (h) {
        const r = retSebebi(h, { retry: ist ? ist.sonRetry : null });
        this.ret = ceviriEs(r.anahtar, this.dil, r.d);
        this.retAlan = r.anahtar === 'es.ret_ad' ? 'ad' : 'parola';
        this._odakla(this.retAlan === 'ad' ? '#es-ad' : '#es-parola');
      }
      this.calisiyor = false;
    },
    unutBasla() {
      this.unutOnay = true;
      this._odakla('[data-es-unut-eminim]');
    },
    unutVazgec() {
      this.unutOnay = false;
      this._odakla('[data-es-unut]');
    },
    async unut() {
      if (!this.unutOnay) return;
      this.unutOnay = false;
      this.calisiyor = true;
      this.ret = '';
      try {
        const ist = await this.istemciAl();
        const r = await ist.unut();
        this._al(ist);
        this.liste = [];
        this.sonuc = ceviriEs(UNUT_METIN[r.kart] || UNUT_METIN.hata, this.dil, { n: r.n, kod: r.kod === null || r.kod === undefined ? '?' : r.kod });
        if (r.kart === 'yok') await this.yenile();   // EU21: ekran bayatti — gercek durumu goster
      } catch (h) {
        this.ret = ceviriEs('es.ret_diger', this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
      this._odakla(!this.cihaz && this.bilgi ? '#es-ad' : '[data-es-durum]');   // EU27: tiklanan dugme DOM'dan kalkti
    },
    kaldirBasla(n) {
      this.kaldirOnay = n;
      this._odakla('[data-es-kaldir-eminim="' + n + '"]');
    },
    kaldirVazgec(n) {
      this.kaldirOnay = null;
      this._odakla('[data-es-kaldir="' + n + '"]');
    },
    /** ES7: ikinci asama — YALNIZ silahli satirin cihazi kaldirilir. */
    async kaldir(n) {
      if (this.kaldirOnay !== n) return;
      this.kaldirOnay = null;
      this.calisiyor = true;
      try {
        const ist = await this.istemciAl();
        const r = await ist.cihazSil(n);
        this.sonuc = r.tamam ? ceviriEs(SONUC_METIN.kaldirildi, this.dil, { n })
          : ceviriEs(SONUC_METIN.kaldirHata, this.dil, { n, mesaj: r.mesaj || '—' });
        await this.listeYukle(ist);
      } catch (h) {
        this.sonuc = ceviriEs(SONUC_METIN.kaldirHata, this.dil, { n, mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
      this._odakla('#es-liste-baslik');              // EU27: "Eminim, kaldir" DOM'dan kalkti
    },
    /** ES8: yalniz dugmeyle (otomatik degil). */
    async saatAyarla() {
      this.calisiyor = true;
      try {
        const ist = await this.istemciAl();
        const r = await ist.saatAyarla();
        this._al(ist);
        this.sonuc = r.tamam ? ceviriEs(SONUC_METIN.saatTamam, this.dil, { zaman: zamanYaz(r.unix) })
          : ceviriEs(SONUC_METIN.saatHata, this.dil, { mesaj: r.mesaj || '—' });
      } catch (h) {
        this.sonuc = ceviriEs(SONUC_METIN.saatHata, this.dil, { mesaj: (h && h.message) || String(h) });
      }
      this.calisiyor = false;
    },
  },
};
