/* ═══════════════════════════════════════════════════════════════════════
   3H-1 — AYARLAR: kalibrasyon gecmisi · depolama · gelismis   (ekran/ayarlar.js)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H kararlari" (AY1-AY7)
   ve "3H-1 uygulama kararlari". Ayarlar'in ESKI kartlari (baglanti, ag,
   kalibrasyon, gorunum) ve yeni Dil karti index.html'de / app.js'te; bu modul
   YALNIZ uc yeni bolumu tasir ve o bolumlerden biri ilk acilinca iner
   (app.js `ayarModGerekli`, defineAsyncComponent).
     AY5 KALIBRASYON GECMISI — SALT OKUMA. Kaynak: panel kartin KENDI adresinden
         acildiysa (3C C1 on kosulu) `/kal/liste`; olmazsa / reddedilirse bu
         tarayicidaki en yeni kopya (esitlemenin yazdigi kalibrasyon.json).
         Gecmisi degistiren HICBIR komut yok (kk/kn/kt kartta, Konsol'dan).
     AY4 DEPOLAMA — akis basina boyut / oturum / son sira / son esitleme / arsiv
         secimi (C3, salt gosterim) / "eski kart kopyasi"; storage.estimate +
         persisted + persist (guvenli baglam yoksa SEBEP); kopya silme Kayitlar'la
         ayni iki asamali onay.
     AY6 GELISMIS — firmware (acilis afisi gorulduyse), panel surumu (kartin
         arayuz goruntusunun kunyesi `/kunye.json`, arayuz-uret.py yazar), baglanti
         yolu; tarayici ayarlarini sifirla: YALNIZ `olcum.` onekli localStorage
         anahtarlari, iki asamali, sonra sayfa yeniden yuklenir.
   NEDEN IKI ASAMALI YUKLEME: kalibrasyon gecmisi ve depolama IndexedDB zincirini
   (esitleme.js + depo_idb.js ve ortak/ modulleri, ~43 KB gzip) ister; Gelismis
   istemez. Zincir bu dosyaya DINAMIK `import()` ile gelir — Gelismis tek dosya
   indirir (karttan her istek olcum dongusunu blokluyor).
   ⚠ Saf fonksiyonlar Vue'suz ve DOM'suz (B7 bolum 30 node'da sinar); bilesen
     ortama (fetch, storage, localStorage, location) yalniz `_` onekli yardimci
     yontemlerden erisir — testte degistirilir.
   ═══════════════════════════════════════════════════════════════════════ */

import { ceviri, ceviriKod } from '/ortak/sozluk.js';

/* ── sabitler ───────────────────────────────────────────────────────── */

/** Bu modulun tasidigi bolumler (app.js AYAR_BOLUMLERI `mod: true` ile AYNI; B7 karsilastirir). */
export const MOD_BOLUMLER = Object.freeze(['kal-gecmis', 'depolama', 'gelismis']);
/** Panelin localStorage onegi (app.js ayarYaz, tema, dil, arsiv, pil hepsi bununla). */
export const AYAR_ONEK = 'olcum.';
/** kalgec.h KALGEC_UYARI: bu kadar kayittan sonra "dolmak uzere" (B7 firmware'den okur). */
export const KAL_UYARI = 35;

/** AY5: degerler tablosu — alan yolu firmware'in `/kal/liste` JSON'u (kal_liste_sayfa) ile
 *  AYNI sirada (B7 firmware kaynagindan turetip karsilastirir); etiket sozlukten. */
export const KAL_ALANLARI = Object.freeze([
  Object.freeze({ alan: 'normal.n', ad: 'ay.kd_normal_n' }),
  Object.freeze({ alan: 'normal.pga', ad: 'ay.kd_normal_pga' }),
  Object.freeze({ alan: 'normal.kazanc', ad: 'ay.kd_normal_kazanc' }),
  Object.freeze({ alan: 'normal.sifir_ham', ad: 'ay.kd_normal_sifir_ham' }),
  Object.freeze({ alan: 'normal.tau', ad: 'ay.kd_normal_tau' }),
  Object.freeze({ alan: 'yuksek.n', ad: 'ay.kd_yuksek_n' }),
  Object.freeze({ alan: 'yuksek.pga', ad: 'ay.kd_yuksek_pga' }),
  Object.freeze({ alan: 'yuksek.kazanc', ad: 'ay.kd_yuksek_kazanc' }),
  Object.freeze({ alan: 'yuksek.sifir_ham', ad: 'ay.kd_yuksek_sifir_ham' }),
  Object.freeze({ alan: 'yuksek.tau', ad: 'ay.kd_yuksek_tau' }),
  Object.freeze({ alan: 'i_ofset', ad: 'ay.kd_i_ofset' }),
  Object.freeze({ alan: 'i_pga', ad: 'ay.kd_i_pga' }),
  Object.freeze({ alan: 'sont_ohm', ad: 'ay.kd_sont_ohm' }),
  Object.freeze({ alan: 'i_duzeltme', ad: 'ay.kd_i_duzeltme' }),
  Object.freeze({ alan: 'sebeke_hz', ad: 'ay.kd_sebeke_hz' }),
  Object.freeze({ alan: 'faz0', ad: 'ay.kd_faz0' }),
  Object.freeze({ alan: 'faz1', ad: 'ay.kd_faz1' }),
]);

/* ── metinler (sozluk anahtarlari; AY7) ─────────────────────────────── */
export const AYE_METIN = Object.freeze({
  yenile: 'ay.yenile', yukleniyor: 'ay.yukleniyor',
  kalBaslik: 'ay.kal_baslik', kalSalt: 'ay.kal_salt', kalHic: 'ay.kal_hic', kalTaslak: 'ay.kal_taslak',
  kalTablo: 'ay.kal_tablo', kalNo: 'ay.kal_no', kalTarih: 'ay.kal_tarih', kalTur: 'ay.kal_tur',
  kalKaynak: 'ay.kal_kaynak', kalNot: 'ay.kal_not', kalDurum: 'ay.kal_durum', kalEtkin: 'ay.kal_etkin',
  kalDegerler: 'ay.kal_degerler', kalAlan: 'ay.kal_alan', kalDeger: 'ay.kal_deger',
  depoBaslik: 'ay.depo_baslik', kotaBaslik: 'ay.kota_baslik', kota: 'ay.kota', kalici: 'ay.kalici',
  kaliciIste: 'ay.kalici_iste', depoTablo: 'ay.depo_tablo', depoAkis: 'ay.depo_akis', depoBoyut: 'ay.depo_boyut',
  depoOturum: 'ay.depo_oturum', depoSonSira: 'ay.depo_son_sira', depoSon: 'ay.depo_son', depoArsiv: 'ay.depo_arsiv',
  depoDurum: 'ay.depo_durum', depoIslem: 'ay.depo_islem', arsivAcik: 'ay.arsiv_acik', arsivKapali: 'ay.arsiv_kapali',
  arsivIpucu: 'ay.arsiv_ipucu', kayitlaraGit: 'ay.kayitlara_git', depoBos: 'ay.depo_bos',
  depoKartBilinmiyor: 'ay.depo_kart_bilinmiyor',
  kopyaGuncel: 'kl.kopya_guncel', kopyaEski: 'kl.kopya_eski', sil: 'kl.sil', silOnay: 'kl.sil_onay',
  vazgec: 'kl.vazgec', silUyari: 'kl.sil_uyari',
  gelBaslik: 'ay.gel_baslik', fw: 'ay.fw', fwYok: 'ay.fw_yok', panel: 'ay.panel', tasiyici: 'ay.tasiyici',
  konsolIpucu: 'ay.konsol_ipucu', konsolaGit: 'ay.konsola_git',
  sifirlaBaslik: 'ay.sifirla_baslik', sifirla: 'ay.sifirla', sifirlaUyari: 'ay.sifirla_uyari', sifirlaYok: 'ay.sifirla_yok',
});

/** Kalibrasyon kaynaginin karttan okunamama sebebi -> sozluk anahtari. */
const KAL_NEDEN = Object.freeze({
  imza: 'ay.kal_neden_imza', yok: 'ay.kal_neden_yok', ag: 'ay.kal_neden_ag', bozuk: 'ay.kal_neden_bozuk',
  usb: 'ay.kal_neden_usb', demo: 'ay.kal_neden_demo', taban: 'ay.kal_neden_taban',
});
const TASIYICI_METIN = Object.freeze({ seri: 'ay.tas_seri', akis: 'ay.tas_akis', demo: 'ay.tas_demo' });

export function metinler(harita, dil) {
  const m = {};
  for (const [a, k] of Object.entries(harita)) m[a] = ceviri(k, dil);
  return m;
}

/* ── SAF fonksiyonlar (B7 node'da sinar) ────────────────────────────── */

/** Bayt -> metin. ekran/kayitlar.js baytYaz ile AYNI (B7 karsilastirir; o modul burada
 *  ice aktarilsaydi Kayitlar'in grafik zinciri Ayarlar'a inerdi). */
export function boyutYaz(n) {
  if (!(n >= 0)) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1024 / 1024).toFixed(2) + ' MB';
}

/** ms (unix) -> yerel `YYYY-AA-GG SS:DD:SN`; gecersizse null. Dile gore DEGISMEZ (AY3). */
export function zamanYaz(ms) {
  if (!(ms > 0)) return null;
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return null;
  const i = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${i(d.getMonth() + 1)}-${i(d.getDate())} ${i(d.getHours())}:${i(d.getMinutes())}:${i(d.getSeconds())}`;
}

const tam = (x) => (Number.isInteger(x) && x >= 0 ? x : null);

/** AY5: `/kal/liste` (ya da kalibrasyon.json kopyasi) -> {adet, taslak, etkin, azami, kayitlar}
 *  numara sirasinda; bozuk kayit `{no, bozuk: true}` olarak KALIR (Y6: sessizce atlanmaz).
 *  Bicimsiz girdi -> null (atmaz). */
export function kalListesiCoz(v) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || !Array.isArray(v.kayitlar)) return null;
  const kayitlar = [];
  for (const k of v.kayitlar) {
    if (!k || typeof k !== 'object' || !(Number.isInteger(k.no) && k.no > 0)) continue;
    if (k.bozuk) { kayitlar.push({ no: k.no, bozuk: true }); continue; }
    kayitlar.push({ no: k.no, bozuk: false, unix: tam(k.unix) || 0, acilis: tam(k.acilis), tur: tam(k.tur),
      kaynak: tam(k.kaynak), not: typeof k.not === 'string' ? k.not : '',
      kal: k.kal && typeof k.kal === 'object' ? k.kal : null });
  }
  kayitlar.sort((a, b) => a.no - b.no);
  return { adet: tam(v.adet) ?? kayitlar.length, taslak: v.taslak === 1 || v.taslak === true,
    etkin: tam(v.etkin) || 0, azami: tam(v.azami), kayitlar };
}

/** Gecmis tablosunun satirlari, YENIDEN ESKIYE; tur/kaynak sozluk ailelerinden. */
export function kalSatirlari(liste, dil) {
  if (!liste) return [];
  return [...liste.kayitlar].reverse().map((k) => {
    if (k.bozuk) {
      const b = ceviri('kal.durum.bozuk', dil);
      return { no: k.no, bozuk: true, etkin: false, tarih: '—', tur: b, kaynak: '—', not: '' };
    }
    return { no: k.no, bozuk: false, etkin: liste.etkin === k.no,
      tarih: zamanYaz(k.unix * 1000) || ceviri('ay.kal_saatsiz', dil, { acilis: k.acilis === null ? '?' : k.acilis }),
      tur: ceviriKod('kal.tur.', k.tur, dil), kaynak: ceviriKod('kal.kaynak.', k.kaynak, dil), not: k.not };
  });
}

/** Bir kaydin degerleri: [{alan, ad, deger}] — deger JSON sayisinin kendisi (firmware %.9g),
 *  yoksa / null ise "—". Birim etikette (sozluk). */
export function kalDegerleri(kal, dil) {
  if (!kal || typeof kal !== 'object') return [];
  return KAL_ALANLARI.map((a) => {
    const v = a.alan.split('.').reduce((o, p) => (o && typeof o === 'object' ? o[p] : undefined), kal);
    return { alan: a.alan, ad: ceviri(a.ad, dil), deger: typeof v === 'number' && Number.isFinite(v) ? String(v) : '—' };
  });
}

/** AY4: tarayici depolama bilgisi var mi. `navigator.storage` yalniz GUVENLI baglamda
 *  (https / localhost) — kartin http:// adresinde YOK. neden: null | 'guvensiz' | 'yok'. */
export function depolamaDestegi({ storage, guvenli } = {}) {
  if (storage && typeof storage.estimate === 'function') return { destek: true, neden: null };
  return { destek: false, neden: guvenli === false ? 'guvensiz' : 'yok' };
}

/** Kota yazisi (sayi bicimi dile gore DEGISMEZ: nokta). Bilgi yoksa ''. */
export function kotaYazi(k, dil) {
  if (!k || !(k.quota > 0) || !(k.usage >= 0)) return '';
  return ceviri('ay.kota_metin', dil, { kullanilan: boyutYaz(k.usage), kota: boyutYaz(k.quota),
    yuzde: (100 * k.usage / k.quota).toFixed(1) });
}

/**
 * AY4: depolama satirlari, YENIDEN ESKIYE (akis olusma zamani). Kart biliniyorsa (C1 on kosulu
 * tamam, `/kayit/liste` yanitladi) "eski kart kopyasi" = kimligi kartinkinden farkli; bilinmiyorsa
 * en yeni acilan akis guncel sayilir (kimlik degisince YENI akis acilir — C2).
 */
export function depoSatirlari({ akislar = [], oturumSayisi = new Map(), kartKimlik = null, arsiv = () => false } = {}) {
  const sirali = [...akislar].sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
  const kartBilinen = kartKimlik !== null && kartKimlik !== undefined;
  return sirali.map((a, i) => {
    const guncel = kartBilinen ? a.kimlik === kartKimlik : i === 0;
    return { kimlik: a.kimlik, bayt: a.bayt, boyut: boyutYaz(a.bayt),
      oturum: oturumSayisi.has(a.kimlik) ? oturumSayisi.get(a.kimlik) : null,
      sonSira: a.durum && Number.isInteger(a.durum.son_sira) ? a.durum.son_sira : null,
      zaman: a.guncelleme || null, guncel, eski: !guncel, kartBilinen, arsiv: !!arsiv(a.kimlik) };
  });
}

/** AY6: panelin localStorage anahtarlari (`olcum.` onekli), sirali. Depo engelliyse []. */
export function olcumAnahtarlari(depo) {
  const a = [];
  try {
    if (!depo) return a;
    for (let i = 0; i < depo.length; i++) {
      const k = depo.key(i);
      if (typeof k === 'string' && k.startsWith(AYAR_ONEK)) a.push(k);
    }
  } catch (e) { return []; }
  return a.sort();
}

/** AY6: YALNIZ `olcum.` anahtarlarini sil; silinenleri dondur. Kayit kopyalari (IndexedDB) KALIR. */
export function ayarlariSifirla(depo) {
  const a = olcumAnahtarlari(depo);
  const silinen = [];
  for (const k of a) {
    try { depo.removeItem(k); silinen.push(k); } catch (e) { /* engelli depo: kalir */ }
  }
  return silinen;
}

/** `/kunye.json` (arayuz-uret.py `panel_kunyesi`) -> {surum, dosya, bayt}; bicimsizse null. */
export function kunyeCoz(v) {
  if (!v || typeof v !== 'object' || !/^[0-9a-f]{12}$/.test(v.surum || '')) return null;
  if (!Number.isInteger(v.dosya) || !Number.isInteger(v.icerik_bayt)) return null;
  return { surum: v.surum, dosya: v.dosya, bayt: v.icerik_bayt };
}

/* ── Vue bileseni ───────────────────────────────────────────────────── */

const SABLON = `
<div class="ay-mod">
  <!-- ═══ AY5 — KALIBRASYON GECMISI (salt okuma) -->
  <section class="kart" v-show="bolum === 'kal-gecmis'" data-ay-bolum="kal-gecmis">
    <h2>{{ m.kalBaslik }}</h2>
    <div class="ay-ust">
      <p class="ipucu ay-kaynak" aria-live="polite" data-ay-kal-kaynak>{{ kalYukleniyor ? m.yukleniyor : kalKaynakYazi }}</p>
      <button type="button" @click="kalYukle" :disabled="kalYukleniyor" :aria-busy="kalYukleniyor ? 'true' : 'false'">{{ m.yenile }}</button>
    </div>
    <p class="ipucu">{{ m.kalSalt }}</p>
    <p v-if="kalOzet" class="ay-ozet" data-ay-kal-ozet>{{ kalOzet }}</p>
    <p v-if="kalListe && kalListe.taslak" class="uyari" data-ay-kal-taslak>{{ m.kalTaslak }}</p>
    <p v-if="kalDoluYazi" class="uyari">{{ kalDoluYazi }}</p>
    <div v-if="kalSatir.length" class="ay-tablo-sarmal">
      <table class="ay-tablo" data-ay-kal-tablo>
        <caption class="gorunmez">{{ m.kalTablo }}</caption>
        <thead><tr>
          <th scope="col">{{ m.kalNo }}</th><th scope="col">{{ m.kalTarih }}</th><th scope="col">{{ m.kalTur }}</th>
          <th scope="col">{{ m.kalKaynak }}</th><th scope="col">{{ m.kalNot }}</th><th scope="col">{{ m.kalDurum }}</th>
          <th scope="col">{{ m.kalDegerler }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in kalSatir" :key="r.no" :data-ay-kal="r.no" :class="{ 'ay-etkin': r.etkin }">
            <th scope="row">{{ r.no }}</th><td>{{ r.tarih }}</td><td class="ay-metin">{{ r.tur }}</td>
            <td class="ay-metin">{{ r.kaynak }}</td><td class="ay-metin">{{ r.not }}</td>
            <td class="ay-metin">{{ r.etkin ? m.kalEtkin : '' }}</td>
            <td><button type="button" :disabled="r.bozuk" :aria-pressed="kalSecili === r.no ? 'true' : 'false'"
                        aria-controls="ay-kal-deger" :data-ay-kal-sec="r.no" @click="kalSec(r.no)">{{ m.kalDegerler }}</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="!kalYukleniyor && kalDenendi" class="ipucu" data-ay-kal-hic>{{ m.kalHic }}</p>
    <div id="ay-kal-deger" class="ay-tablo-sarmal" v-if="kalDegerTablo.length">
      <table class="ay-tablo" data-ay-kal-degerler>
        <caption class="ay-tablo-baslik">{{ kalDegerBaslik }}</caption>
        <thead><tr><th scope="col">{{ m.kalAlan }}</th><th scope="col">{{ m.kalDeger }}</th></tr></thead>
        <tbody>
          <tr v-for="d in kalDegerTablo" :key="d.alan" :data-ay-alan="d.alan">
            <th scope="row" class="ay-metin">{{ d.ad }} <span class="ay-alan-ad">{{ d.alan }}</span></th><td>{{ d.deger }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- ═══ AY4 — DEPOLAMA -->
  <section class="kart" v-show="bolum === 'depolama'" data-ay-bolum="depolama">
    <h2>{{ m.kotaBaslik }}</h2>
    <template v-if="kotaDestek.destek">
      <p class="ay-ozet" data-ay-kota>{{ kotaMetni || m.yukleniyor }}</p>
      <progress v-if="kota" class="ay-kota" :value="kota.usage" :max="kota.quota" :aria-label="m.kota"></progress>
      <p class="ay-ozet" data-ay-kalici>{{ m.kalici }}: {{ kaliciYazi }}</p>
      <button v-if="kalici !== true" type="button" data-ay-kalici-iste @click="kaliciIste" :disabled="kaliciIsteniyor">{{ m.kaliciIste }}</button>
    </template>
    <p v-else class="ipucu" data-ay-kota-yok>{{ kotaSebep }}</p>
    <div class="ay-duyuru" aria-live="polite"><p v-if="kaliciSonucMetni" class="ipucu" data-ay-kalici-sonuc>{{ kaliciSonucMetni }}</p></div>
  </section>
  <section class="kart" v-show="bolum === 'depolama'" data-ay-bolum="depolama">
    <h2>{{ m.depoBaslik }}</h2>
    <div class="ay-ust">
      <p class="ipucu ay-kaynak" aria-live="polite">{{ depoYukleniyor ? m.yukleniyor : depoHataMetni }}</p>
      <button type="button" @click="depoYukle" :disabled="depoYukleniyor" :aria-busy="depoYukleniyor ? 'true' : 'false'">{{ m.yenile }}</button>
    </div>
    <div v-if="depoSatir.length" class="ay-tablo-sarmal">
      <table class="ay-tablo" data-ay-depo-tablo>
        <caption class="gorunmez">{{ m.depoTablo }}</caption>
        <thead><tr>
          <th scope="col">{{ m.depoAkis }}</th><th scope="col">{{ m.depoBoyut }}</th><th scope="col">{{ m.depoOturum }}</th>
          <th scope="col">{{ m.depoSonSira }}</th><th scope="col">{{ m.depoSon }}</th><th scope="col">{{ m.depoArsiv }}</th>
          <th scope="col">{{ m.depoDurum }}</th><th scope="col">{{ m.depoIslem }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in depoSatir" :key="r.kimlik" :data-ay-akis="r.kimlik">
            <th scope="row">{{ r.kimlik }}</th><td>{{ r.boyut }}</td><td>{{ r.oturum === null ? '—' : r.oturum }}</td>
            <td>{{ r.sonSira === null ? '—' : r.sonSira }}</td><td>{{ zaman(r.zaman) }}</td>
            <td class="ay-metin">{{ r.arsiv ? m.arsivAcik : m.arsivKapali }}</td>
            <td class="ay-metin"><span class="kl-rozet" :class="r.guncel ? 'kl-nerede-ikisi' : 'kl-dikkat'">{{ r.guncel ? m.kopyaGuncel : m.kopyaEski }}</span></td>
            <td class="ay-islem">
              <template v-if="silOnay === r.kimlik">
                <button type="button" class="tehlike" :data-ay-sil-eminim="r.kimlik" @click="kopyaSil(r.kimlik)">{{ m.silOnay }}</button>
                <button type="button" @click="silVazgec(r.kimlik)">{{ m.vazgec }}</button>
              </template>
              <button v-else type="button" :data-ay-sil="r.kimlik" @click="silBasla(r.kimlik)" :disabled="depoYukleniyor">{{ m.sil }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="!depoYukleniyor && depoDenendi" class="ipucu" data-ay-depo-bos>{{ m.depoBos }}</p>
    <p v-if="silOnay !== null" class="uyari" role="alert">{{ m.silUyari }}</p>
    <p v-if="depoSatir.length && !depoSatir[0].kartBilinen" class="ipucu">{{ m.depoKartBilinmiyor }}</p>
    <p class="ipucu">{{ m.arsivIpucu }} <a href="#/kayitlar">{{ m.kayitlaraGit }}</a></p>
  </section>

  <!-- ═══ AY6 — GELISMIS -->
  <section class="kart" v-show="bolum === 'gelismis'" data-ay-bolum="gelismis">
    <h2>{{ m.gelBaslik }}</h2>
    <dl class="ay-bilgi">
      <dt>{{ m.fw }}</dt><dd data-ay-fw :class="{ 'ay-aciklama': !afisSurum }">{{ afisSurum || m.fwYok }}</dd>
      <dt>{{ m.panel }}</dt><dd data-ay-panel aria-live="polite" :class="{ 'ay-aciklama': !kunye }">{{ panelYazi }}</dd>
      <dt>{{ m.tasiyici }}</dt><dd data-ay-tasiyici>{{ tasiyiciYazi }}</dd>
    </dl>
    <p class="ipucu">{{ m.konsolIpucu }} <a href="#/konsol">{{ m.konsolaGit }}</a></p>
  </section>
  <section class="kart" v-show="bolum === 'gelismis'" data-ay-bolum="gelismis">
    <h2>{{ m.sifirlaBaslik }}</h2>
    <template v-if="anahtarlar.length">
      <p class="ipucu">{{ sifirlaAciklama }}</p>
      <ul class="ay-anahtarlar" data-ay-anahtarlar><li v-for="a in anahtarlar" :key="a"><code>{{ a }}</code></li></ul>
      <div class="dugme-grup">
        <template v-if="sifirlaOnay">
          <button type="button" class="tehlike" data-ay-sifirla-eminim @click="sifirla">{{ sifirlaEminim }}</button>
          <button type="button" data-ay-sifirla-vazgec @click="sifirlaVazgec">{{ m.vazgec }}</button>
        </template>
        <button v-else type="button" data-ay-sifirla @click="sifirlaBasla">{{ m.sifirla }}</button>
      </div>
      <p v-if="sifirlaOnay" class="uyari" role="alert">{{ m.sifirlaUyari }}</p>
    </template>
    <p v-else class="ipucu" data-ay-sifirla-yok>{{ m.sifirlaYok }}</p>
  </section>
</div>`;

export const AyarlarEkrani = {
  name: 'AyarlarEkrani',
  props: {
    bolum: { type: String, default: 'gelismis' },
    kartAdres: { type: Function, required: true },
    /* 3H-2 (ES4): app.js'in TEK istek katmani (eslesmisse imzali); yoksa bugunku yol */
    kartIstek: { type: Function, default: null },
    kartTaban: { type: String, default: '' },
    tasiyici: { type: String, default: 'akis' },
    bagli: { type: Boolean, default: false },
    afisSurum: { type: String, default: '' },
    dilSecim: { type: String, default: 'tr' },
    etkin: { type: Boolean, default: true },
  },
  template: SABLON,
  data() {
    return {
      /* AY5 */
      kalYukleniyor: false, kalDenendi: false, kalListe: null, kalKaynak: null, kalNeden: null, kalNedenD: {},
      kalYerel: null, kalSecili: null,
      /* AY4 */
      depoYukleniyor: false, depoDenendi: false, depoSatir: [], depoHata: '', silOnay: null,
      kotaDestek: { destek: false, neden: null }, kota: null, kalici: null, kaliciIsteniyor: false, kaliciSonuc: '',
      kaliciHata: '',
      /* AY6 */
      kunye: null, kunyeNeden: '', kunyeDenendi: false, anahtarlar: [], sifirlaOnay: false,
    };
  },
  computed: {
    dil() { return this.dilSecim === 'en' ? 'en' : 'tr'; },
    m() { return metinler(AYE_METIN, this.dil); },
    /* ── AY5 */
    kalSatir() { return kalSatirlari(this.kalListe, this.dil); },
    kalKaynakYazi() {
      const p = [];
      if (this.kalKaynak === 'kart') p.push(ceviri('ay.kal_kaynak_kart', this.dil));
      if (this.kalKaynak === 'yerel' && this.kalYerel) {
        p.push(ceviri('ay.kal_kaynak_yerel', this.dil, { kimlik: this.kalYerel.kimlik,
          zaman: zamanYaz(this.kalYerel.zaman) || '—' }));
      }
      if (this.kalNeden) {
        p.push(ceviri('ay.kal_neden', this.dil, { neden: ceviri(KAL_NEDEN[this.kalNeden] || KAL_NEDEN.bozuk, this.dil, this.kalNedenD) }));
      }
      return p.join(' ');
    },
    kalOzet() {
      const l = this.kalListe;
      if (!l) return '';
      const etkin = l.etkin ? ceviri('ay.kal_etkin_no', this.dil, { no: l.etkin }) : '—';
      return ceviri('ay.kal_ozet', this.dil, { adet: l.adet, azami: l.azami === null ? '—' : l.azami, etkin });
    },
    kalDoluYazi() {
      const l = this.kalListe;
      return l && l.adet >= KAL_UYARI ? ceviri('ay.kal_dolu', this.dil, { adet: l.adet, azami: l.azami === null ? '—' : l.azami }) : '';
    },
    kalDegerTablo() {
      if (!this.kalListe || this.kalSecili === null) return [];
      const k = this.kalListe.kayitlar.find((x) => x.no === this.kalSecili);
      return k && !k.bozuk ? kalDegerleri(k.kal, this.dil) : [];
    },
    kalDegerBaslik() { return ceviri('ay.kal_deger_baslik', this.dil, { no: this.kalSecili === null ? '—' : this.kalSecili }); },
    /* ── AY4 */
    kotaMetni() { return kotaYazi(this.kota, this.dil); },
    kotaSebep() {
      return ceviri(this.kotaDestek.neden === 'guvensiz' ? 'ay.kota_guvensiz' : 'ay.kota_yok', this.dil);
    },
    kaliciYazi() {
      return ceviri(this.kalici === true ? 'ay.kalici_acik' : this.kalici === false ? 'ay.kalici_kapali' : 'ay.kalici_bilinmiyor', this.dil);
    },
    kaliciSonucMetni() {
      if (!this.kaliciSonuc) return '';
      return ceviri(this.kaliciSonuc, this.dil, { mesaj: this.kaliciHata || '—' });
    },
    depoHataMetni() { return this.depoHata ? ceviri('ay.depo_hata', this.dil, { mesaj: this.depoHata }) : ''; },
    /* ── AY6 */
    panelYazi() {
      if (this.kunye) {
        return ceviri('ay.panel_metin', this.dil, { surum: this.kunye.surum, dosya: this.kunye.dosya, boyut: boyutYaz(this.kunye.bayt) });
      }
      if (!this.kunyeDenendi) return this.m.yukleniyor;
      return ceviri('ay.panel_yok', this.dil, { neden: this.kunyeNeden || '—' });
    },
    tasiyiciYazi() { return ceviri(TASIYICI_METIN[this.tasiyici] || this.tasiyici, this.dil); },
    sifirlaAciklama() { return ceviri('ay.sifirla_aciklama', this.dil, { n: this.anahtarlar.length }); },
    sifirlaEminim() { return ceviri('ay.sifirla_eminim', this.dil, { n: this.anahtarlar.length }); },
  },
  watch: {
    bolum() { this.bolumAcildi(); },
    etkin(v) { if (v) this.bolumAcildi(); else { this.silOnay = null; this.sifirlaOnay = false; } },
  },
  mounted() {
    this.bolumAcildi();
  },
  methods: {
    zaman(ms) { return zamanYaz(ms) || '—'; },
    /* ── ortam (testte degistirilir) ── */
    async _esAl() { return import('./esitleme.js'); },
    async _idbAl() { return import('./depo_idb.js'); },
    _depolama() {
      const n = typeof navigator !== 'undefined' ? navigator : null;
      return { storage: n ? n.storage : undefined, guvenli: typeof isSecureContext === 'boolean' ? isSecureContext : undefined };
    },
    _yerelDepo() {
      try { return globalThis.localStorage || null; } catch (e) { return null; }
    },
    _yenidenYukle() { globalThis.location.reload(); },
    /** Tek ag kapisi (3H-2 ES4): istek katmani (varsa) ya da bugunku yol. */
    _istek(yol, secenekler) {
      return this.kartIstek ? this.kartIstek(yol, secenekler) : fetch(this.kartAdres(yol), secenekler);
    },
    async _den() {
      if (!this._denSoz) {
        this._denSoz = this._esAl().then((es) => ({ es, den: new es.EsitlemeDenetcisi({ kartAdres: this.kartAdres, istek: this.kartIstek }) }));
      }
      return this._denSoz;
    },

    /** Gorunur olan bolumun verisi (her gorunuste tazelenir; kunye bir kez). */
    bolumAcildi() {
      if (!this.etkin) return;
      this.silOnay = null;
      this.sifirlaOnay = false;
      if (this.bolum === 'kal-gecmis' && !this.kalDenendi && !this.kalYukleniyor) this.kalYukle();
      if (this.bolum === 'depolama') { this.depoYukle(); this.kotaOku(); }
      if (this.bolum === 'gelismis') { this.anahtarlarOku(); if (!this.kunyeDenendi) this.kunyeYukle(); }
    },

    /* ═══ AY5 — kalibrasyon gecmisi ═══════════════════════════════════ */
    /** Once kart (C1 on kosulu tamamsa `/kal/liste`), olmazsa bu tarayicidaki en yeni kopya. */
    async kalYukle() {
      this.kalYukleniyor = true;
      this.kalNeden = null;
      this.kalNedenD = {};
      let liste = null;
      let kaynak = null;
      try {
        const { es } = await this._den();
        const u = es.esitlemeUygunlugu({ kartTaban: this.kartTaban, tasiyici: this.tasiyici });
        if (!u.uygun) {
          this.kalNeden = u.neden;
        } else {
          try {
            const y = await this._istek('/kal/liste', { cache: 'no-store' });
            if (y.status === 200) {
              liste = kalListesiCoz(await y.json().catch(() => null));
              if (liste) kaynak = 'kart'; else this.kalNeden = 'bozuk';
            } else if (y.status === 401) {
              this.kalNeden = 'imza';
            } else {
              this.kalNeden = 'yok';
              this.kalNedenD = { kod: y.status };
            }
          } catch (h) {
            this.kalNeden = 'ag';
            this.kalNedenD = { mesaj: (h && h.message) || String(h) };
          }
        }
        if (!liste) {
          /* yerel kopya okunamazsa (IndexedDB yok / ozel kip) kartin sebebi EZILMEZ */
          const yerel = await this.kalYerelOku(es).catch(() => null);
          if (yerel) { liste = yerel.liste; kaynak = 'yerel'; this.kalYerel = yerel.bilgi; }
        }
      } catch (h) {
        this.kalNeden = 'ag';
        this.kalNedenD = { mesaj: (h && h.message) || String(h) };
      }
      this.kalListe = liste;
      this.kalKaynak = kaynak;
      if (liste && (this.kalSecili === null || !liste.kayitlar.some((k) => k.no === this.kalSecili && !k.bozuk))) {
        this.kalSecili = liste.etkin || null;
      }
      this.kalDenendi = true;
      this.kalYukleniyor = false;
    },
    /** Bu tarayicidaki EN YENI akisin kalibrasyon kopyasi (esitlemenin yazdigi kalibrasyon.json). */
    async kalYerelOku(es) {
      const { den } = await this._den();
      const akislar = [...await den.akislar()].sort((a, b) => (b.olusma || 0) - (a.olusma || 0));
      const idb = await this._idbAl();
      const vt = await idb.vtAc();
      for (const a of akislar) {
        if (!a.kalVar) continue;
        const liste = kalListesiCoz(es.kalJsonCoz(await idb.idbDepo(vt, a.kimlik).kalOku()));
        if (liste) return { liste, bilgi: { kimlik: a.kimlik, zaman: a.guncelleme || null } };
      }
      return null;
    },
    kalSec(no) { this.kalSecili = this.kalSecili === no ? null : no; },

    /* ═══ AY4 — depolama ══════════════════════════════════════════════ */
    async depoYukle() {
      if (this.depoYukleniyor) return;
      this.depoYukleniyor = true;
      this.depoHata = '';
      try {
        const { es, den } = await this._den();
        const akislar = await den.akislar();
        const sayi = new Map();
        for (const a of akislar) {
          try { sayi.set(a.kimlik, (await den.akisVerisi(a.kimlik)).oturumlar.size); } catch (h) { /* sayi bilinmiyor: "—" */ }
        }
        let kartKimlik = null;
        if (es.esitlemeUygunlugu({ kartTaban: this.kartTaban, tasiyici: this.tasiyici }).uygun) {
          const r = await den.kartListesi();
          if (r && r.durum === 'tamam') kartKimlik = r.liste.kimlik;
        }
        this.depoSatir = depoSatirlari({ akislar, oturumSayisi: sayi, kartKimlik, arsiv: (k) => es.arsivOku(k) });
      } catch (h) {
        this.depoHata = (h && h.message) || String(h);
        this.depoSatir = [];
      }
      this.depoDenendi = true;
      this.depoYukleniyor = false;
    },
    /** estimate (kullanim / kota) + persisted (kalici mi). Destek yoksa sebep (kotaSebep). */
    async kotaOku({ kaliciDa = true } = {}) {
      const o = this._depolama();
      this.kotaDestek = depolamaDestegi(o);
      if (!this.kotaDestek.destek) { this.kota = null; return; }
      try {
        const e = await o.storage.estimate();
        this.kota = e && e.quota > 0 ? { usage: e.usage || 0, quota: e.quota } : null;
      } catch (h) { this.kota = null; }
      if (!kaliciDa) return;
      try {
        this.kalici = typeof o.storage.persisted === 'function' ? !!(await o.storage.persisted()) : null;
      } catch (h) { this.kalici = null; }
    },
    /** persist() — tarayicinin VERDIGI sonuc yazilir (izin istemi olmayabilir; sessiz ret de sonuc). */
    async kaliciIste() {
      const o = this._depolama();
      if (!o.storage || typeof o.storage.persist !== 'function') return;
      this.kaliciIsteniyor = true;
      this.kaliciHata = '';
      try {
        const v = !!(await o.storage.persist());
        this.kalici = v;
        this.kaliciSonuc = v ? 'ay.kalici_verildi' : 'ay.kalici_reddedildi';
      } catch (h) {
        this.kaliciHata = (h && h.message) || String(h);
        this.kaliciSonuc = 'ay.kalici_hata';
      }
      this.kaliciIsteniyor = false;
      await this.kotaOku({ kaliciDa: false });     // kalici: persist()'in KENDI sonucu kalir
    },
    /* Kopya silme — Kayitlar'la AYNI iki asama (silBasla silahlar, YALNIZ silahli kopya silinir). */
    silBasla(kimlik) {
      this.silOnay = kimlik;
      this._odakla('[data-ay-sil-eminim="' + kimlik + '"]');
    },
    silVazgec(kimlik) {
      this.silOnay = null;
      this._odakla('[data-ay-sil="' + kimlik + '"]');
    },
    async kopyaSil(kimlik) {
      if (this.silOnay !== kimlik) return;
      this.silOnay = null;
      const { den } = await this._den();
      await den.akisSil(kimlik);
      await this.depoYukle();
      await this.kotaOku();
    },
    _odakla(secici) {
      this.$nextTick(() => {
        if (typeof document === 'undefined') return;
        const e = document.querySelector(secici);
        if (e && typeof e.focus === 'function') e.focus();
      });
    },

    /* ═══ AY6 — gelismis ══════════════════════════════════════════════ */
    async kunyeYukle() {
      this.kunyeNeden = '';
      try {
        const y = await this._istek('/kunye.json', { cache: 'no-store' });
        if (y.status === 200) {
          this.kunye = kunyeCoz(await y.json().catch(() => null));
          if (!this.kunye) this.kunyeNeden = 'JSON';
        } else {
          this.kunyeNeden = 'HTTP ' + y.status;
        }
      } catch (h) {
        this.kunyeNeden = (h && h.message) || String(h);
      }
      this.kunyeDenendi = true;
    },
    anahtarlarOku() { this.anahtarlar = olcumAnahtarlari(this._yerelDepo()); },
    sifirlaBasla() {
      this.anahtarlarOku();
      this.sifirlaOnay = true;
      this._odakla('[data-ay-sifirla-eminim]');
    },
    sifirlaVazgec() {
      this.sifirlaOnay = false;
      this._odakla('[data-ay-sifirla]');
    },
    /** Iki asamanin ikincisi: YALNIZ `olcum.` anahtarlari silinir, sayfa yeniden yuklenir. */
    sifirla() {
      if (!this.sifirlaOnay) return;
      this.sifirlaOnay = false;
      ayarlariSifirla(this._yerelDepo());
      this._yenidenYukle();
    },
  },
};
