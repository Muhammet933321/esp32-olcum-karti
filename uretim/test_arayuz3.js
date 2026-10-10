/* ═══════════════════════════════════════════════════════════════════════
   B7 — Asama 3 arayuzu   (node uretim/test_arayuz3.js)

   Iki is yapiyor:

   1) ARAYUZ <-> FIRMWARE KOMUT DENETIMI
      Arayuzun gonderebilecegi HER komut harfini, firmware'in gercekten
      tanidigi `case` harfleriyle karsilastirir.

      NEDEN: Asama 2'de bu tam olarak ters gitti. DEVIR 4.1 app.js'teki
      uc komutu duzeltti ama index.html'deki UCUNU ATLADI:
          "Ayarlari goster" -> 'd'   (boyle bir komut yok, '?' olmali)
          "Enerjiyi sifirla" -> 'e'  (Asama 2'de enerji sifirlama YOK)
          "Akimi sifirla"   -> 's'   (o SONT komutu, 'z' olmali)
      Uc dugme sessizce calismiyordu ve hicbir test bunu gormuyordu,
      cunku testler yalnizca app.js'e bakiyordu. Bu test HTML'e de bakiyor.

   2) ASAMA 3 PROTOKOLU
      9 alanli D satiri, <menzil> alani, cift yonlu degerler, negatif guc.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const KOK = path.join(__dirname, '..');
const ARAYUZ = path.join(KOK, 'arayuz3');
const APP = path.join(ARAYUZ, 'app.js');
const HTML = path.join(ARAYUZ, 'index.html');
const INO = path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum-karti-a3.ino');

/* EU32 (W3): tembel ekran zincirlerinin metinleri ayri sozluklerde (ortak/src/sozluk_kayit.js: Kayitlar /
   kayit gorunumu / Karsilastirma; sozluk_ay.js: Ayarlar modulu). Bir METNIN icerigini sinayan iddialar anahtari
   hangi sozlukte olursa olsun bulsun diye BIRLESIK gorunum; hangi anahtarin ACILISTA oldugu ayri iddialarda
   (EU30/EU32) ve ortak/test/sozluk_{kayit,ay}.test.js'te olculur. */
function sozlukTum() {
  const SZa = require(path.join(KOK, 'ortak', 'src', 'sozluk.js'));
  const KY = require(path.join(KOK, 'ortak', 'src', 'sozluk_kayit.js'));
  const AYs = require(path.join(KOK, 'ortak', 'src', 'sozluk_ay.js'));
  const SOZLUK = Object.freeze({ ...SZa.SOZLUK, ...KY.SOZLUK_KAYIT, ...AYs.SOZLUK_AY });
  return { ...SZa, SOZLUK, ceviri: (a, d, v) => SZa.sozluktenCeviri(SOZLUK, a, d, v) };
}

// ── Vue taklidi
let secenekler = null;
const sandbox = {
  /* 3C: `defineAsyncComponent` taklidi yukleyiciyi SAKLIYOR — bolum 24
     onun hangi modulu istedigine bakiyor (cagirmiyor: vm'de dinamik import yok). */
  Vue: { createApp(o) { secenekler = o; return { mount() { return {}; } }; },
         defineAsyncComponent(yukleyici) { return { __asenkron: true, yukleyici }; } },
  navigator: { serial: {} },
  window: { addEventListener() {}, devicePixelRatio: 1 },
  document: { documentElement: {}, createElement: () => ({ click() {} }) },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }),
  setTimeout: () => 0,
  console,
};
vm.createContext(sandbox);

/* ═══ 3A (P4): app.js tarayicida ES MODULU ════════════════════════════
   vm betik kipinde `import` yok. Ice aktarma satirlari SOKULUYOR (satir
   sayisi korunarak — yigin izleri dogru satiri gostersin) ve adlar,
   modulun KENDISI node'da yuklenerek (`require(esm)`) baglama konuyor.
   Yani test modulun bir kopyasini degil GERCEK dosyasini kullaniyor.
   ⚠ Tanimadigimiz bicimde bir `import`/`export` kalirsa vm SyntaxError
     ile coker — sessizce atlanmaz.
   ⚠ "use strict": tarayicidaki modul STRICT kipte kosuyor (bildirilmemis
     ada atama ReferenceError). vm de oyle kossun ki 3A oncesi gevsek
     kipte gizli kalan bir atama burada da kirmiziya donsun. */
const ICE_AKTARMA = /^import\s*\{([^}]*)\}\s*from\s*'([^']+)';[ \t]*$/gm;
function modulYolu(kimden, yol) {
  /* `/ortak/x.js` -> `ortak/src/x.js`: kart, kopru ve sunucu.py'nin
     esleme kuraliyla AYNI (arayuz-uret.py `kaynak_yolu`). */
  if (yol.startsWith('/ortak/')) return path.join(KOK, 'ortak', 'src', yol.slice('/ortak/'.length));
  return path.resolve(path.dirname(kimden), yol);
}
const ICE_AKTARILAN = [];          // {yol, dosya, adlar} — bolum 23 kullaniyor
const appBetik = fs.readFileSync(APP, 'utf8').replace(ICE_AKTARMA, (_, adlar, yol) => {
  const dosya = modulYolu(APP, yol);
  const mod = require(dosya);
  const bagli = [];
  for (const parca of adlar.split(',').map((s) => s.trim()).filter(Boolean)) {
    const [kaynak, yerel] = parca.split(/\s+as\s+/).map((s) => s.trim());
    if (!(kaynak in mod)) throw new Error(`${yol} '${kaynak}' disa aktarmiyor`);
    sandbox[yerel || kaynak] = mod[kaynak];
    bagli.push(yerel || kaynak);
  }
  ICE_AKTARILAN.push({ yol, dosya, adlar: bagli });
  return '';
});
vm.runInContext('"use strict"; ' + appBetik, sandbox, { filename: 'app.js' });

/* Tarayicinin app.js'ten baslayarak STATIK olarak indirecegi her modul
   (gecisli): `ortak/` modulleri birbirini `./x.js` ile, cok satirli
   `import {\n …\n} from "…"` bicimiyle cagiriyor. `goruntu` = kartta
   (LittleFS) ve sunucularda istenecek yol. */
const ITHAL_DESENI = /^\s*(?:import|export)\s[^'"]*?\bfrom\s*['"]([^'"]+)['"]|^\s*import\s*['"]([^'"]+)['"]/gm;
function goruntuYolu(dosya) {
  const ortak = path.relative(path.join(KOK, 'ortak', 'src'), dosya);
  if (!ortak.startsWith('..') && !path.isAbsolute(ortak)) return 'ortak/' + ortak.split(path.sep).join('/');
  return path.relative(ARAYUZ, dosya).split(path.sep).join('/');
}
function iceAktarmaGrafigi(bas = APP) {
  const gorulen = new Map();
  const yigin = [bas];
  while (yigin.length) {
    const kimden = yigin.pop();
    const kaynak = fs.existsSync(kimden) ? fs.readFileSync(kimden, 'utf8') : '';
    for (const m of yorumsuz(kaynak).matchAll(ITHAL_DESENI)) {
      const dosya = modulYolu(kimden, m[1] || m[2]);
      if (gorulen.has(dosya)) continue;
      gorulen.set(dosya, { yol: m[1] || m[2], dosya, goruntu: goruntuYolu(dosya),
                           kimden: path.basename(kimden), var: fs.existsSync(dosya) });
      yigin.push(dosya);
    }
  }
  return [...gorulen.values()];
}

function ornek() {
  const o = Object.assign({}, secenekler.data());
  Object.assign(o, secenekler.methods);
  o.$nextTick = () => {};
  o.$refs = {};
  o.grafikCiz = () => {};
  o.osiloCiz = () => {};
  for (const [ad, fn] of Object.entries(secenekler.computed || {})) {
    Object.defineProperty(o, ad, { get: fn.bind(o) });
  }
  return o;
}

/* [!] ASENKRON IDDIA KUYRUGU (B27 A2).
   Bir `.then()` icinde yazilan `ok()` OZET SATIRINDAN SONRA kosuyordu:
   sayilmiyor, kirmizi olsa bile surec 0 ile cikiyordu — yani iddia
   degil, susleme. Asenkron iddialar buraya birakiliyor ve ozetten ONCE
   (bolum 12'nin zincirinde) bekleniyor. */
const SONRA = [];

let gecti = 0, kaldi = 0;
/* 3C: asenkron zincir ASKIDA kalirsa (bir Promise hic cozulmez) node olay
   dongusu bosalip 0 ile cikiyordu — ozet satiri HIC basilmadan. Sayim
   kilidi bunu yakaliyordu ama cikis kodu "yesil" diyordu. Ozete
   ulasilmadan cikis artik KIRMIZI. */
let ozetBasildi = false;
process.on('exit', () => {
  if (!ozetBasildi) {
    console.log('[!!] B7 ozete ULASAMADI — asenkron iddia zinciri askida kaldi');
    process.exitCode = 1;
  }
});
function ok(ad, kosul, ek = '') {
  if (kosul) { gecti++; console.log(`[OK] ${ad}${ek ? '  ' + ek : ''}`); }
  else { kaldi++; console.log(`[!!] ${ad}${ek ? '  ' + ek : ''}`); }
}
function yakin(ad, a, b, tol = 1e-9) {
  ok(ad, Math.abs(a - b) <= tol, `${a} ~ ${b}`);
}

console.log('B7 — Asama 3 arayuzu (arayuz3/)\n');

/* ═════════════════ 1. ARAYUZ <-> FIRMWARE KOMUT DENETIMI ═════════════ */
console.log('--- 1. Arayuzun gonderdigi her komut firmwarece taniniyor mu ---');

const ino = fs.readFileSync(INO, 'utf8');
/* 1D: `guv_seri_komut` E komutunun ALT dagiticisi (E? Ex Ep Ez Em Et Er) — oradaki
   `case` etiketleri ust duzey komut harfi DEGIL; sayilsaydi 'm' gibi olmayan bir
   komut "arayuzde yok" diye kirmizi yanardi. Govde cikarilip taraniyor; govde
   bulunamazsa (ad degisti) hic cikarilmaz ve iddia yine kirmiziya doner. */
const inoUst = ino.replace(/static void guv_seri_komut\([\s\S]*?\n}\n/, '')
  /* 1E: `bld_seri_komut` Q'nun alt dagiticisi (Q? Qu Qk Qp Qc Qd Q1 Q0 Qt Qv QR!) — ayni sebep */
  .replace(/static void bld_seri_komut\([\s\S]*?\n}\n/, '');
const firmwareHarfleri = new Set(
  [...inoUst.matchAll(/case '(.)':/g)].map((m) => m[1])
);
console.log('     firmware: ' + [...firmwareHarfleri].sort().join(' '));

/* Arayuzun gonderdikleri — HEM app.js HEM index.html taranıyor.
   Asama 2'de yalnizca app.js taranmisti ve index.html'deki uc hatali
   komut fark edilmemisti. */
const appKaynak = fs.readFileSync(APP, 'utf8');
const htmlKaynak = fs.readFileSync(HTML, 'utf8');
/* 3A (P4): yeni ekranlar `ekran/*.js` modulleri. Komut, fetch ve tuval
   belirteci tarayicilari onlara da bakiyor — app.js'ten bir ekrana tasinan
   `gonder('x')` ya da ciplak `fetch(` gozden kacmasin. */
const EKRAN = path.join(ARAYUZ, 'ekran');
const ekranKaynaklari = (fs.existsSync(EKRAN) ? fs.readdirSync(EKRAN) : [])
  .filter((a) => a.endsWith('.js')).sort()
  .map((a) => ({ ad: 'ekran/' + a, kaynak: fs.readFileSync(path.join(EKRAN, a), 'utf8') }));
const kodKaynaklari = [{ ad: 'app.js', kaynak: appKaynak }].concat(ekranKaynaklari);

/* Sayfanin BAGLADIGI stil dosyalari — elle liste degil. Bir stil dosyasi
   eklenir/cikarilirsa butun CSS iddialari kendiliginden onu izler. */
const CSS_YOLLARI = [...htmlKaynak.matchAll(
  /<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"/g)]
  .map((m) => m[1])
  .filter((u) => !/^https?:/.test(u))
  .map((u) => path.join(ARAYUZ, u));
const cssOku = () => CSS_YOLLARI.filter((p) => fs.existsSync(p))
  .map((p) => fs.readFileSync(p, 'utf8')).join('\n');

/* [!] B22.2: YORUMLAR CIKARILIYOR.
   Bir yorumda ornek olarak `gonder('x')` yazmak, komutu GONDERMEK degildir.
   B22.2'de tasiyici katmaninin aciklama yorumu tam olarak bunu yaziyordu ve
   ileri yon denetimi "arayuz 'x' komutu gonderiyor, firmware'de yok" diye
   kirmiziya dondu. Tersi daha kotu olurdu: firmware'e eklenip arayuze
   konmamis bir komut, YALNIZCA bir yorumda adi geciyor diye "erisilebilir"
   sayilabilirdi — ters yon denetiminin butun degeri kaybolurdu.
   (Ayni sinif kusur bu oturumda CSS sinifi, NVS imzasi ve `faz_kal` alani
   denetimlerinde de cikti. Metin tabanli her iddia KODA bakmali.) */
function yorumsuz(kaynak) {
  return kaynak
    .replace(/\/\*[\s\S]*?\*\//g, ' ')     // /* ... */
    .replace(/<!--[\s\S]*?-->/g, ' ')      // <!-- ... -->  (index.html)
    .replace(/^\s*\/\/.*$/gm, ' ');        // satir basindaki //
}

function komutlariTopla(ham, etiket) {
  const kaynak = yorumsuz(ham);
  const bulunan = [];
  // gonder('x'...)  ve  komut('x')  bicimleri
  for (const m of kaynak.matchAll(/(?:gonder|komut)\(\s*'([^']*)'/g)) {
    bulunan.push({ k: m[1], nerede: etiket });
  }
  /* [!] B20: yukaridaki kalip cagrinin ILK karakterinin tirnak olmasini
     istiyor, o yuzden UCLU ifadeleri kaciriyordu:
         this.gonder(m === 1 ? 'y' : 'n')
     'n' ve 'y' bu yuzden "arayuzde yok" gorunuyordu. Ikinci gecis,
     cagri parantezinin ICINDEKI butun tirnakli sabitleri topluyor. */
  for (const m of kaynak.matchAll(/(?:gonder|komut)\(([^)]*)\)/g)) {
    for (const q of m[1].matchAll(/'([^']*)'/g)) {
      /* Yalnizca HARFLE baslayanlar komut olabilir: `gonder('a' + ...)`
         cagrisindaki '1' / '0' komut degil ARGUMAN. Firmware'in butun
         komut harfleri A-Z / a-z. */
      if (q[1] && /^[A-Za-z]/.test(q[1])
          && !bulunan.some((b) => b.k === q[1])) {
        bulunan.push({ k: q[1], nerede: etiket + ' (uclu)' });
      }
    }
  }
  return bulunan;
}

const gonderilenler = kodKaynaklari.flatMap((k) => komutlariTopla(k.kaynak, k.ad))
  .concat(komutlariTopla(htmlKaynak, 'index.html'));

ok('Arayuzde komut gonderen cagri bulundu', gonderilenler.length > 0,
   `${gonderilenler.length} cagri`);

const bilinmeyen = [];
for (const { k, nerede } of gonderilenler) {
  if (!k) continue;                       // gonder(degisken) — atlanir
  const harf = k[0];
  if (!firmwareHarfleri.has(harf)) bilinmeyen.push(`${nerede}: '${k}'`);
}
ok('Arayuzun gonderdigi HER komut firmware\'de tanimli',
   bilinmeyen.length === 0,
   bilinmeyen.length ? bilinmeyen.join(', ') : `${gonderilenler.length} cagri denetlendi`);

/* [!] B20 (2026-09-10) — TERS YON. Yukarisi yalnizca "arayuzun gonderdigi
   her komut firmware'de var mi" diye soruyordu. Bu denetim TEK YONLU
   oldugu icin, firmware'e YENI bir komut eklenip arayuze konmamasi
   GORUNMUYORDU: B17 `f` (sebeke frekansi) ve `F` (faz kalibrasyonu)
   komutlarini ekledi, arayuze hic koymadi ve zincir 70/70 yesildi.
   Sonucu sessiz degildi: fabrika ayari 50 Hz oldugu icin DC olcen bir
   kullanici gucu %82 yuksek okuyor ve duzeltecek denetim bulamiyordu. */
const gonderilenHarfler = new Set(
  gonderilenler.map((x) => (x.k || '')[0]).filter(Boolean));
/* Kullaniciya acik OLMAYAN komutlar — arayuzde bulunmalari beklenmiyor.
   Her biri icin GEREKCE yazili; listeye bir harf eklemek bilincli bir
   karar olmali. */
const ARAYUZSUZ = {
  h: 'yardim — seri port icin',
  /* B34: `c<ham>` ham ADC kodunun fabrika-kalibre mV karsiligini veren
     bir SORGU. Arayuzun elinde hic ham kod olmuyor — kart `/skop.bin`'de
     ham kod + TEK olcek carpani yolluyor ve arayuz volta o carpanla
     ceviriyor. Bu komut olcum betikleri icin var: olculmus bir supurmeyi
     KAYNAGI DEGISTIRMEDEN kalibrasyondan gecirmeye yariyor (B34'te
     "egri ADC'nin mi kaynagin mi" sorusu boyle yanitlandi).
     ⚠ Kalibrasyon skop eksenine uygulanirsa (DEVIR 5.12.48'deki acik
     karar) bu satir DUSMELI: o zaman arayuzun da bir soyleyecegi olur. */
  c: 'ham kod -> kalibre mV sorgusu; olcum betikleri icin',
  Y: 'yardim (es anlamli)',
  /* B26: TEZGAH TESHIS komutu — blokaj sayaclarini sifirlar.
     `tezgah_kart.py` bununla acilis isinmasini disarida birakip
     KARARLI HAL olcuyor (cift cekirdek karari, DEVIR 5.12.34).

     Neden B20'nin `f`/`F` durumundan FARKLI: o ikisi kullanicinin
     OKUDUGU degeri degistiriyordu (sebeke frekansi yanlis kalinca guc
     %82 yanlis okunuyordu), yani arayuzde olmamalari gercek bir kusurdu.
     `K` hicbir olcumu, kalibrasyonu ya da gosterilen degeri
     degistirmiyor — yalnizca teshis sayaclarini sifirliyor. Arayuzde
     blokaj sayaci PANELI de yok; olsaydi dugmesi oraya konurdu.
     ⚠ Arayuze bir gun blokaj/tani paneli eklenirse bu harf listeden
     CIKARILACAK. */
  K: 'blokaj sayaci sifirlama — tezgah teshisi, olcumu etkilemiyor',
  /* B72 (1A-2) `G` (kayit komutu) BURADAN CIKTI — 3C: Kayitlar ekrani
     `Go<sira>` onayini panelin komut yolundan gonderiyor (ekran/esitleme.js
     onayIslevi; yalniz "bu tarayici arsivdir" seciliyse, C3). Kaydi baslat /
     durdur / plan (Gb Gd Gp) ekranlari 3D'de (Canli); harfin bir alt komutu
     (Go) arayuzde oldugu icin ters yon denetimi gecer. */
  /* 1B: KALIBRASYON GECMISI (k? durum · kl liste · kv<no> degerler ·
     kk<t><not> taslagi kaydet · kn<no> not · kt<no><t> tur). Kalibrasyonu
     DEGISTIREN komutlar (z g Z i s f F) panelde zaten var; `k` yalniz
     gecmise not/tur yazar ve listeler — okunan degeri degistirmez (B20'nin
     f/F durumundan farki). Ekrani alt proje 3 (Ayarlar > kalibrasyon
     gecmisi). ⚠ O ekran gelince bu satir CIKARILACAK. */
  k: 'kalibrasyon gecmisi — ekrani alt proje 3; okunan degeri degistirmez',
  /* 1D: eslestirme (Ep), cihaz silme (Ex), imza zorunlulugu (Ez), misafir (Em),
     PBKDF2 turu (Et/Er). BILEREK yalniz USB: firmware /komut ucunda 'E'yi 403
     ile reddeder (B72.F76), kopru.py de reddeder. Ep'nin yaniti cihaz anahtari
     ve yalniz ham UART'a basilir — panele KONULMAZ, alt proje 3'te de. */
  E: 'eslestirme/zorunluluk — YALNIZ USB seri konsol (web /komut 403 verir)',
  /* 1E: MQTT bildirim ayari (Qu adres, Qk/Qp kart, Qc/Qd cihaz kullanici/parola, Q1/Q0,
     Qt deneme, Qv sinama, QR! yeni anahtar). BILEREK yalniz USB: araci parolalari aga
     cikmaz; firmware /komut ucunda 'Q'yu 403 ile reddeder (B72.Q8), kopru.py de reddeder.
     Panele KONULMAZ; alt proje 3'te en fazla salt-okur durum (Q? sirsiz). */
  Q: 'MQTT bildirim ayari — YALNIZ USB seri konsol (araci parolalari; web /komut 403 verir)',
};
const arayuzdeYok = [...firmwareHarfleri]
  .filter((h) => !gonderilenHarfler.has(h) && !(h in ARAYUZSUZ));
ok('Firmware\'in HER kullanici komutu arayuzden erisilebilir',
   arayuzdeYok.length === 0,
   arayuzdeYok.length
     ? `arayuzde YOK: ${arayuzdeYok.map((h) => `'${h}'`).join(', ')}`
     : `${firmwareHarfleri.size} komut harfi, ${Object.keys(ARAYUZSUZ).length} tanesi bilerek disarida`);

/* B20: `f` ve `F` ozellikle sinaniyor — bu ikisi B17'de eklenip
   unutulmustu, bir daha ayni sekilde kaybolmasinlar. */
/* Bu iki iddia fonksiyonun VARLIGINI degil GOVDESINI siniyor: adi duran
   ama icinden gonder() cikarilmis bir fonksiyon testi kandirmasin. */
function govdeIcinde(kaynak, ad, aranan) {
  /* [!] B21: once `ad + '('` araniyordu ve bu, adin bir YORUMDA gecmesine
     kaniyordu — `pilCsvIndir` iddiasi bu yuzden yanlislikla kirmizi
     yandi (helper yorumu bulup bir SONRAKI fonksiyonun govdesine
     bakiyordu). Artik TANIM bicimi araniyor: satir basi + ad + '() {'.
     Bulunamazsa eski gevsek kalibba dusulyor (async/parametreli
     tanimlar icin). */
  let i = -1;
  for (const kalip of ['\n    ' + ad + '(', '\n    async ' + ad + '(',
                       '\n  ' + ad + '(', '\n  async ' + ad + '(']) {
    const k = kaynak.indexOf(kalip);
    if (k >= 0 && (i < 0 || k < i)) i = k;
  }
  if (i < 0) i = kaynak.indexOf(ad + '(');
  if (i < 0) return false;
  const j = kaynak.indexOf('{', i);
  if (j < 0) return false;
  let d = 0;
  for (let k = j; k < kaynak.length; k++) {
    if (kaynak[k] === '{') d++;
    else if (kaynak[k] === '}') { d--; if (d === 0)
      return kaynak.slice(j, k + 1).includes(aranan); }
  }
  return false;
}
ok('B20: sebeke frekansi `f` arayuzde',
   gonderilenHarfler.has('f') && govdeIcinde(appKaynak, 'sebekeGonder', "gonder('f'"),
   'olcek duzeltmesi kullaniciya acik');
ok('B20: faz kalibrasyonu `F` arayuzde',
   gonderilenHarfler.has('F') && govdeIcinde(appKaynak, 'fazGonder', "gonder('F'"),
   'menzil basina faz duzeltmesi kullaniciya acik');
ok('B20: olcek carpani kullaniciya GOSTERILIYOR',
   appKaynak.includes('sebekeUyari') && htmlKaynak.includes('sebekeUyari'),
   'DC olcumunde %82 hata artik gorunur');

/* ── B21: pil kapasite testi arayuzu ────────────────────────────────── */
ok('B21: testi baslatma `p1` arayuzde',
   govdeIcinde(appKaynak, 'pilBaslat', "gonder('p1')"),
   'kesme denetimi kartta, ama tetigi arayuz cekiyor');
ok('B21: testi durdurma `p0` arayuzde',
   govdeIcinde(appKaynak, 'pilDurdurKomut', "gonder('p0')"),
   'kullanici her an durdurabiliyor');
ok('B21: kesme gerilimi `P` arayuzde',
   govdeIcinde(appKaynak, 'pilKesmeGonder', "gonder('P'"),
   'kesme gerilimi kullanici tarafindan ayarlanabiliyor');
/* 3F: sinir artik FIRMWARE'den olculuyor (eskiden app.js'te "v <= 38.5" metni araniyordu):
   `P` komutunun alt siniri (ino) ve PIL_AZAMI_V (pil_test.h) panelin sabitleriyle ayni, ve
   uretici sinirin bir ustunu / altini GONDERMIYOR. */
{
  const pilH = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'pil_test.h'), 'utf8');
  const azami = Number((/#define PIL_AZAMI_V\s+([\d.]+)f/.exec(pilH) || [])[1]);
  const enaz = Number((/if \(!\(v >= ([\d.]+)f\) \|\| !\(v <= PIL_AZAMI_V\)\)/.exec(ino) || [])[1]);
  const K = vm.runInContext('pilKesmeKomutu', sandbox);
  ok('B21: kesme girisi MOSFET Vdss sinirinda kirpiliyor (sinirlar FIRMWARE`den: P komutu + PIL_AZAMI_V)',
     azami === 38.5 && enaz === 0.5 && vm.runInContext('PIL_KESME_AZAMI_V', sandbox) === azami
     && vm.runInContext('PIL_KESME_ENAZ_V', sandbox) === enaz
     && K('38.5').komut === 'P38.5' && K('38.51').hata && K('0.5').komut === 'P0.5' && K('0.49').hata,
     `${enaz} … ${azami} V`);
}
/* Bu iddia adin GECTIGINI degil, boslugun GERCEKTEN SAYILDIGINI ve
   grafige ISARET olarak konuldugunu siniyor — yoksa degisken adini
   birakip mantigi silmek testi kandirirdi. */
ok('B21: [!] BOSLUK kullaniciya GOSTERILIYOR',
   govdeIcinde(appKaynak, 'pilYokla', 'this.pilBosluk +=')
   && govdeIcinde(appKaynak, 'pilYokla', 'bosluk: true')
   && htmlKaynak.includes('pilBosluk'),
   'kart penceresinden uzun kopmada egride bosluk olur — sessizce '
   + 'interpolasyon YAPILMIYOR, sayilip isaretleniyor');
ok('B21: [!] J7/J3 montaj tuzagi arayuzde YAZIYOR',
   /J7/.test(htmlKaynak) && /J3/.test(htmlKaynak),
   'yuk J3\'e baglanirsa kesme calismaz — kullanici bunu gormeli');
ok('B21: veri IndexedDB\'de (sekme kapansa da kalir)',
   appKaynak.includes('indexedDB.open'),
   'localStorage 5 MB ile sinirli; 24 saatlik test sigmaz');
ok('B21: CSV disari aktarma var',
   govdeIcinde(appKaynak, 'pilCsvIndir', 'text/csv'),
   'IndexedDB tarayici verisi — "verileri temizle" denince gider, '
   + 'ASIL ARSIV CSV');

/* ── B22.1 ─────────────────────────────────────────────────────────────
   Faz kalibrasyonunun BIRIMI ornek -> mikrosaniye oldu (K2). Bu, ters yon
   komut denetiminin GOREMEYECEGI bir ayrisma sinifi: harf ('F') iki
   tarafta da duruyor, degisen ANLAM. Arayuz +-1 ile kirpmaya devam
   etseydi kullanici 292 us'lik gercek duzeltmeyi HIC giremezdi ve sebebi
   gorunmezdi (eski govde sinir disi degeri sessizce yutuyordu). */
ok('B22.1: faz kalibrasyonu arayuzde MIKROSANIYE',
   govdeIcinde(appKaynak, 'fazGonder', '2000') &&
   !govdeIcinde(appKaynak, 'fazGonder', 'd >= -1 && d <= 1'),
   'firmware siniri +-2000 us — arayuz ayni siniri kullanmali');
ok('B22.1: faz birimi SABLONDA da us yaziyor',
   /Faz kalibrasyonu[^<]*µs/.test(htmlKaynak) &&
   !/Faz kalibrasyonu, örnek/.test(htmlKaynak),
   'etiket "ornek" derse kullanici 0.02 girer, 75 kat kucuk duzeltme');
/* IKI ret yolu var: sayi degil, ve sinir disi. Tek `this.hata` aramak
   yetmiyordu — sinir disi dalinin mesajini silen mutasyon KACTI. */
ok('B22.1: fazGonder HER ret yolunda sebebini soyluyor',
   govdeIcinde(appKaynak, 'fazGonder', 'sayı girin') &&
   govdeIcinde(appKaynak, 'fazGonder', '2000 µs arası olmalı'),
   'sayi-degil ve sinir-disi AYRI AYRI bildiriliyor; tek `this.hata` '
   + 'aramak yetmiyordu (mutasyon kacmisti)');

/* `R!` fabrika sifirlama — bozulmus NVS'ten tek kurtulus yolu.
   Onay eki hem firmware'de hem arayuzde: kazara tetiklenmemeli. */
ok('B22.1: fabrika sifirlama arayuzden erisilebilir',
   govdeIcinde(appKaynak, 'fabrikaSifirla', "gonder('R!')"),
   'ciplak `R` firmware\'de reddediliyor, onay eki sart');
/* Bayragin ADININ gecmesi yetmez — ERKEN DONUS kapisi durmali. Ilk
   yazimda `sifirlaOnay` aranıyordu ve "onayi kaldir" mutasyonu KACTI:
   kapi silinse bile govdede `this.sifirlaOnay = false;` duruyordu. */
/* ── B22.4: AG KURULUMU ────────────────────────────────────────────────
   Kartin WiFi'sini kartin WiFi'si uzerinden kurmak tavuk-yumurta olurdu;
   akis USB ile baglanip ag bilgilerini yazmak. Ters yon denetimi `N`
   harfini zaten zorunlu kiliyor, bu iddialar HANGI alt komutlarin
   erisilebildigini civiliyor. */
ok('B22.4: ag adi ve parolasi arayuzden yazilabiliyor',
   govdeIcinde(appKaynak, 'agSsidGonder', "gonder('Na'") &&
   govdeIcinde(appKaynak, 'agSifreGonder', "gonder('Np'"),
   'USB ile bagla, WiFi kur, sonra kablosuza gec');
ok('B22.4: web parolasi arayuzden kurulabiliyor',
   govdeIcinde(appKaynak, 'agWebSifreGonder', "gonder('Ns'"),
   'komut ucunun tek parola korumasi');
ok('B22.4: ag durumu ve ac/kapa sablonda',
   htmlKaynak.includes("komut('N?')") && htmlKaynak.includes("komut('N1')") &&
   htmlKaynak.includes("komut('N0')"));
/* Parolalar duz metin gidiyor — kart TLS konusmuyor. Kullanici ag
   uzerinden kuruyorsa bunu BILMELI. */
ok('B22.4: ag uzerinden kurulumda duz metin UYARISI var',
   /tasiyiciAdi !== 'seri'[\s\S]{0,400}şifrelenmeden/.test(htmlKaynak),
   'USB disinda parola duz metin gidiyor');

/* ── B22.5: IKI COZUCU, TEK GOSTERICI ──────────────────────────────────
   ASCII dokumu 4000 ornekte 20 250 B; ikili 8 032 B. Ikisi de AYNI
   `osiloTopla` yapisini kurup AYNI `osiloBitir()`i cagirmali — cizim
   kodu iki kez yazilsaydi ikisi ayrisir ve BIRI SESSIZCE YANLIS cizerdi
   (bu projenin uc kez yandigi sinif). */
ok('B22.5: ikili skop cozucusu var',
   govdeIcinde(appKaynak, 'skopIkiliAl', '/skop.bin'));
ok('B22.5: iki cozucu de AYNI gostericiyi cagiriyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'osiloBitir()') &&
   appKaynak.includes("satir.trim() === 'E'"),
   'ikili yol da osiloBitir(), ASCII yol da');
ok('B22.5: yakalama YETENEGE gore yol seciyor',
   govdeIcinde(appKaynak, 'osiloYakala', "yetenek.skop === 'ikili'") &&
   govdeIcinde(appKaynak, 'osiloYakala', "gonder('tB')"),
   'ayni veriyi ASCII + ikili olarak IKI KEZ tasima');
/* Kismi ya da yanlis yanit SESSIZCE cizilmemeli — bu, `pilYokla`'nin
   B22.2'de kapatilan sessiz-sifir kusurunun ikili karsiligi. */
ok('B22.5: ikili yanit IMZASI denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', '0x53') &&
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'imzası'),
   'S3B degilse cizme, SEBEBINI soyle');
ok('B22.5: ikili yanit UZUNLUGU denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', '32 + adet * 2'),
   'kesik govde sessizce yarim grafik cizmesin');
/* [!] Endian ACIKCA kucuk: `Uint16Array` platformun endian'ini kullanir
   ve bir gun sessizce ters okuyabilirdi. */
ok('B22.5: endian ACIKCA kucuk-endian',
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'getUint16(32 + i * 2, true)') &&
   !govdeIcinde(appKaynak, 'skopIkiliCoz', 'new Uint16Array'),
   'DataView + true; Uint16Array platforma birakirdi');

ok('B22.1: fabrika sifirlama IKI ASAMALI onay istiyor',
   govdeIcinde(appKaynak, 'fabrikaSifirla', 'if (!this.sifirlaOnay)') &&
   govdeIcinde(appKaynak, 'fabrikaSifirla', 'return;') &&
   htmlKaynak.includes('sifirlaOnay'),
   'tek tikla tum kalibrasyon silinmemeli');

/* Asama 2'nin hatalarinin tekrarlanmadigini ACIKCA sina */
const tumKomutlar = gonderilenler.map((x) => x.k);
ok('Ayarlari goster `?` gonderiyor (Asama 2\'de `d` idi — komut yok)',
   tumKomutlar.includes('?') && !tumKomutlar.includes('d'));
ok('Akimi sifirla `Z` gonderiyor (Asama 2\'de `s` idi — o sont komutu)',
   tumKomutlar.includes('Z'));
ok('Gerilim kalibresi `g` (Asama 2\'de `v` idi)',
   appKaynak.includes("gonder('g' + v)"));
ok('Gerilim sifiri `z` — Asama 3\'te AKIM degil GERILIM sifiri',
   appKaynak.includes("sifirlaV() { this.gonder('z'); }"));

/* ═════════════════ 2. ASAMA 3 PROTOKOLU ═════════════════════════════ */
console.log('\n--- 2. D satiri: 9 alan ve <menzil> ---');
{
  const u = ornek();
  u.satirIsle('D 12.3456 0.025300 0.312345 1.2340 0.0003428 45678 172 0');
  yakin('volt', u.volt, 12.3456);
  yakin('amper', u.amper, 0.0253);
  yakin('watt', u.watt, 0.312345);
  ok('ornek sayisi', u.ornekAdet === 172, String(u.ornekAdet));
  ok('menzil = 0 (NORMAL)', u.menzil === 0, String(u.menzil));
  ok('menzil adi NORMAL', u.menzilAd === 'NORMAL', u.menzilAd);
  ok('menzil araligi gosteriliyor', u.menzilAralik.includes('32.44'),
     u.menzilAralik);

  u.satirIsle('D 480.5 1.2 576.6 100.0 0.0277 46678 172 1');
  ok('menzil = 1 (YUKSEK)', u.menzil === 1, String(u.menzil));
  ok('menzil adi YUKSEK', u.menzilAd === 'YÜKSEK', u.menzilAd);
  ok('yuksek menzil araligi', u.menzilAralik.includes('613.7'), u.menzilAralik);
}

console.log('\n--- 3. ASAMA 2 satiri da bozulmadan okunmali (8 alan) ---');
{
  const u = ornek();
  u.satirIsle('D 12.3456 0.025300 0.312345 1.2340 0.0003428 45678 172');
  yakin('volt yine okunuyor', u.volt, 12.3456);
  ok('menzil bilinmiyor -> null', u.menzil === null, String(u.menzil));
  ok('menzil adi "—"', u.menzilAd === '—', u.menzilAd);
}

console.log('\n--- 4. CIFT YONLU gosterim ---');
{
  const u = ornek();
  u.satirIsle('D -24.5000 -0.150000 3.67500 -5.0 -0.00139 1000 172 0');
  ok('negatif gerilim okundu', u.volt < 0, String(u.volt));
  ok('negatif akim okundu', u.amper < 0, String(u.amper));
  ok('negatif akim isaretiyle gosteriliyor',
     String(u.akimGoster).startsWith('-'), u.akimGoster);
  ok('akim birimi mA secildi', u.akimBirim === 'mA', u.akimBirim);
  ok('pozitif guc "yuk cekiyor"', u.gucYon === 'yük çekiyor', u.gucYon);

  // negatif guc: yuk kaynak durumuna gecmis
  u.satirIsle('D 12.0000 -0.150000 -1.80000 -5.0 -0.00139 1200 172 0');
  ok('negatif guc okundu', u.watt < 0, String(u.watt));
  ok('negatif guc "kaynak" diye isaretleniyor',
     u.gucYon.includes('kaynak'), u.gucYon);
  ok('negatif enerji okunabiliyor', u.joule < 0, String(u.joule));

  /* 🔴 B27/K1 — `durum` alani: ADC yanit vermeyince "veri yok".
     Gercek kartta tek ADS ile gorulen satir: `... 97 0 1` -> bit0 = V yok.
     Firmware sessizce 0 donup kalibrasyon sabitini ters cevirince ekranda
     "1.716 V" cikiyordu; arayuz bunu ARTIK olcum sanmamali. */
  u.satirIsle('D 1.7156 0.000012 0.00004 0.0000 0.0000000 67704 97 0 1');
  ok('durum=1: gerilim GECERSIZ isaretleniyor', u.voltGecersiz === true,
     `adsDurum=${u.adsDurum}`);
  ok('durum=1: akim hala GECERLI', u.amperGecersiz === false, '');
  ok('durum=1: guc gecersiz (V yoksa V*I de yok)', u.gucGecersiz === true, '');
  ok('durum=1: guc yonu etiketi BOS (sahte sayiya etiket yok)',
     u.gucYon === '', JSON.stringify(u.gucYon));
  u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68000 97 0 2');
  ok('durum=2: akim GECERSIZ, gerilim gecerli',
     u.amperGecersiz === true && u.voltGecersiz === false, '');
  u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68200 97 0 0');
  ok('durum=0: ikisi de gecerli', !u.voltGecersiz && !u.amperGecersiz, '');
  ok('eski firmware (9 alan) -> durum 0 sayilir (guven)',
     (u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68400 97 0'), u.adsDurum === 0),
     `adsDurum=${u.adsDurum}`);

  /* B27/K5 — sont menusu KARTI gostermeli, tarayiciyi degil.
     Gercek kartin `?` cevabi (sont=0.100000) menude '0.1' secmeli;
     listede olmayan bir deger menuyu bozmamali ama gercek gorunmeli. */
  u.sontSecim = '10';
  u.satirIsle('A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=-1646 '
              + 'y_kazanc=1.000000 y_sifir=-91 sont=0.100000 i_duz=1.000000 i_ofset=0');
  ok('K5: `?` cevabindan kartSont okunuyor', u.kartSont === 0.1, String(u.kartSont));
  ok('K5: menu kartin degerine UYDURULUYOR (10 -> 0.1)', u.sontSecim === '0.1',
     u.sontSecim);
  ok('K5: uyusma var, uyari yok', u.sontUyumsuz === false, '');
  ok('K5: kart degeri yaziya dokuluyor', u.kartSontYazi.includes('100') && u.kartSontYazi.includes('mΩ'),
     u.kartSontYazi);
  u.satirIsle('A menzil=NORMAL oto=1 n_kazanc=1 n_sifir=0 y_kazanc=1 y_sifir=0 '
              + 'sont=0.123456 i_duz=1 i_ofset=0');
  ok('K5: listede olmayan deger menuyu DEGISTIRMIYOR', u.sontSecim === '0.1', u.sontSecim);
  ok('K5: ama uyusmazlik UYARILIYOR', u.sontUyumsuz === true, `kartSont=${u.kartSont}`);

  /* B27/K3 — kart "giris rayda" derse ESKI sonuc panelde kalmamali */
  u.satirIsle('W 218.11 218.47 0.9984 61.78 3.536 -61.37 -3.49 297 218.35');
  ok('K3: W satiri hizli sonucu dolduruyor', u.hizli !== null && u.hizli.p > 200,
     String(u.hizli && u.hizli.p));
  u.satirIsle('! hizli yol: giris RAYDA — sinyal yok  V ham ort=14  (bos giris ya da on uc bagli degil)');
  ok('K3: "giris rayda" gelince ESKI sonuc SILINIYOR', u.hizli === null, String(u.hizli));
  ok('K3: hata metni panelde', u.hizliHata.includes('RAYDA'), u.hizliHata);
  u.satirIsle('W 12.0 12.1 0.99 12.0 1.0 12.0 1.0 297 12.0');
  ok('K3: yeni gecerli W hatayi temizliyor', u.hizliHata === '' && u.hizli !== null, '');

  /* B27/K2 — olu bant: gurultu duzeyinde guc etiket URETMEMELI */
  u.satirIsle('D 1.7156 -0.000004 -0.00001 0 0 68600 97 0 0');
  ok('K2: -10 uW "kaynak" etiketi uretmiyor (olu bant)', u.gucYon === '',
     JSON.stringify(u.gucYon));
  u.satirIsle('D 12.0 -0.5 -6.0 0 0 68800 97 0 0');
  ok('K2: -6 W hala "kaynak" diyor (olu bant gercek geri beslemeyi yutmuyor)',
     u.gucYon.includes('kaynak'), u.gucYon);
}

console.log('\n--- 5. Kalibrasyon NEGATIF degeri kabul ediyor mu ---');
{
  const u = ornek();
  const gonderilen = [];
  u.gonder = (k) => gonderilen.push(k);

  u.kalibV = '12.05'; u.kalibreV();
  ok('pozitif gerilim kalibresi g12.05', gonderilen[0] === 'g12.05',
     gonderilen[0]);

  u.kalibV = '-24.5'; u.kalibreV();
  ok('NEGATIF gerilim kalibresi g-24.5 (Asama 2\'de reddedilirdi)',
     gonderilen[1] === 'g-24.5', gonderilen[1]);

  u.kalibA = '-0.25'; u.kalibreA();
  ok('NEGATIF akim kalibresi i-0.25', gonderilen[2] === 'i-0.25',
     gonderilen[2]);

  u.kalibV = '0'; u.kalibreV();
  ok('SIFIR kalibrasyon degeri gonderilmiyor', gonderilen.length === 3,
     `${gonderilen.length} komut`);

  u.sontSecim = '0.1'; u.sontGonder();
  ok('sont komutu s0.1', gonderilen[3] === 's0.1', gonderilen[3]);
  u.menzilSec(1);
  ok('menzil YUKSEK -> y', gonderilen[4] === 'y', gonderilen[4]);
  ok('menzil secince oto kapaniyor', u.otoMenzil === false);
  u.menzilSec(0);
  ok('menzil NORMAL -> n', gonderilen[5] === 'n', gonderilen[5]);
  u.otoMenzil = false; u.otoMenzilDegistir();
  ok('oto menzil acma -> a1', gonderilen[6] === 'a1', gonderilen[6]);
  u.otoMenzilDegistir();
  ok('oto menzil kapatma -> a0', gonderilen[7] === 'a0', gonderilen[7]);
  u.sifirlaV();
  ok('gerilim sifiri -> z', gonderilen[8] === 'z', gonderilen[8]);
  u.sifirlaA();
  ok('akim sifiri -> Z', gonderilen[9] === 'Z', gonderilen[9]);
  u.enerjiSifirla();
  ok('enerji sifirla -> e', gonderilen[10] === 'e', gonderilen[10]);
}

console.log('\n--- 5b. B8 HIZLI YOL (W satiri) ---');
{
  const u = ornek();
  u.satirIsle('W 0.13712 0.22117 0.6200 12.0200 0.01840 12.0100 0.01820 297 0.15550');
  ok('W satiri ayristirildi', u.hizli !== null);
  yakin('gercek guc P', u.hizli.p, 0.13712, 1e-9);
  yakin('gorunur guc S', u.hizli.s, 0.22117, 1e-9);
  yakin('guc faktoru', u.hizli.pf, 0.62, 1e-9);
  yakin('Vrms', u.hizli.vRms, 12.02, 1e-9);
  ok('ornek sayisi', u.hizli.n === 297, String(u.hizli.n));
  yakin('hizalamasiz guc AYRI alanda', u.hizli.pHam, 0.1555, 1e-9);
  ok('hizalama farki gosteriliyor', /düzeltti/.test(u.hizalamaFarki),
     u.hizalamaFarki);

  // Dirençsel yukte hizalamali ve hizalamasiz AYNI olmali
  u.satirIsle('W 1.00000 1.00000 1.0000 10.0000 0.10000 10.0 0.1 297 1.00000');
  ok('Dirençsel yukte "fark yok" deniyor',
     /yok \(dirençsel\)/.test(u.hizalamaFarki), u.hizalamaFarki);

  const gonderilen = [];
  u.gonder = (k) => gonderilen.push(k);
  u.hizliOlc();
  ok('hizli olcum komutu `w`', gonderilen[0] === 'w', gonderilen[0]);
}

console.log('\n--- 6. Demo kart Asama 3 protokolu uretiyor mu ---');
{
  const SahteKart = require(path.join(ARAYUZ, 'sahte-kart.js'));
  const d = SahteKart.dSatiri(1000, 1.5);
  const p = d.satir.split(/\s+/);
  /* 🔴 B27: burasi `p.length === 9` idi — firmware'e alan eklenince (K1
     `durum`) demo kart guncellendi ama bu sabit kaldi ve YANLIS KIRMIZI
     verdi. Beklenen, firmware'in KENDI bicim dizesinden turetiliyor:
     "D " + N adet % => N+1 alan. Demo kart firmware'den sapinca burasi
     kirmizi olur; sabit bir sayi ise firmware degisince kirmizi olurdu. */
  const dBicim = ino.match(/"D (%[^"]*)"/);
  const alanBeklenen = dBicim ? dBicim[1].split(/\s+/).length + 1 : -1;
  ok(`D satiri ${alanBeklenen} alanli (firmware bicim dizesinden)`,
     p.length === alanBeklenen, `${p.length} alan: ${d.satir}`);
  ok('9. alan menzil', p[8] === '0' || p[8] === '1', p[8]);
  ok('10. alan durum (ADC yanit bitleri, demo kartta 0)', p[9] === '0',
     `durum=${p[9]} — demo kartta iki ADC de "var"`);

  const u = ornek();
  u.satirIsle(d.satir);
  ok('arayuz demo satirini ayristirdi', isFinite(u.volt) && u.menzil !== null,
     `${u.volt} V, menzil ${u.menzil}`);

  // demo kart bilinmeyen komutu reddediyor mu
  ok('demo kart `d` komutunu REDDEDIYOR (Asama 2 hatasi)',
     SahteKart.komut('d')[0].startsWith('!'), SahteKart.komut('d')[0]);
  ok('demo kart `?` komutunu taniyor',
     SahteKart.komut('?')[0].startsWith('A '), SahteKart.komut('?')[0]);
  ok('demo kart `Z` (akim sifiri) taniyor',
     SahteKart.komut('Z')[0].includes('akim sifiri'), SahteKart.komut('Z')[0]);
  ok('demo kart sifira yakin kazanc kalibresini reddediyor',
     SahteKart.komut('g0.5')[0].startsWith('!'), SahteKart.komut('g0.5')[0]);

  const w = SahteKart.komut('w');
  ok('demo kart `w` ile W satiri uretiyor', w[0].startsWith('W '), w[0]);
  /* B39: alan sayisi ELLE YAZILMIYOR, firmware'in protokol yorumundan
     (`//   W <P> ... <kal>`) TURETILIYOR. Elle 10 yazan onceki hali,
     firmware 11. alani ekleyince sahte karti geride birakacakti — ya da
     tersine, sahte kart guncellenip firmware unutulsaydi fark etmezdi. */
  const inoKaynak = fs.readFileSync(
    path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum-karti-a3.ino'), 'utf8');
  const wProto = inoKaynak.match(/^\/\/\s+(W <[^\n]*>)\s*$/m);
  const wAlan = wProto ? wProto[1].trim().split(/\s+/).length : -1;
  ok('demo W satirinin alan sayisi FIRMWARE protokoluyle ayni',
     wAlan > 0 && w[0].split(/\s+/).length === wAlan,
     `demo ${w[0].split(/\s+/).length} · firmware ${wAlan} (${wProto ? wProto[1] : 'yorum yok'})`);
  ok('demo pencere yanliligini UYARIYOR', /yanlilik BUYUK/.test(w[1]), w[1]);
}

console.log('\n--- 7. Sablon: menzil ve guc yonu gosteriliyor mu ---');
{
  ok('menzilAd sablonda kullaniliyor', htmlKaynak.includes('menzilAd'));
  ok('menzilAralik sablonda kullaniliyor', htmlKaynak.includes('menzilAralik'));
  ok('gucYon sablonda kullaniliyor', htmlKaynak.includes('gucYon'));
  ok('menzil dugmeleri var', htmlKaynak.includes('menzilSec(0)') &&
     htmlKaynak.includes('menzilSec(1)'));
  ok('gerilim sifirlama dugmesi var', htmlKaynak.includes('sifirlaV'));
  ok('hizli olcum dugmesi var', htmlKaynak.includes('hizliOlc'));
  ok('hizalama farki sablonda', htmlKaynak.includes('hizalamaFarki'));
  /* Hizli yolun MUTLAK dogrulugu sinirli — arayuz bunu SOYLEMELI,
     yoksa kullanici ADS'in degeri yerine bu sayiya guvenir. */
  ok('mutlak deger uyarisi sablonda',
     htmlKaynak.includes('D satırı') && htmlKaynak.includes('ADS1115'));
  /* CSS tuzagi: display tanimlayan sinif [hidden] kuralini ezer. */
  ok('`button.etkin` icinde display kullanilmiyor ([hidden] tuzagi)',
     !/button\.etkin\s*\{[^}]*display/.test(cssOku()));
}

/* ═══════════════════════════════════════════════════════════════════════
   8. VARLIK DENETIMI  (B22.0, 2026-09-10)

   NEDEN EKLENDI: bu zincir 15/15 ve bu dosya 82/82 YESILKEN arayuz
   tarayicida HIC ACILMIYORDU. index.html `style.css` ve
   `vendor/vue.global.prod.js` istiyordu; ikisi de arayuz3/ icinde yoktu.
   sunucu.py onlari `../arayuz`'dan dusuruyordu, ama o dizin 5.12.32'de
   `arsiv/asama1/arayuz`'a tasinmisti. Sonuc: iki 404, Vue tanimsiz,
   app.js ilk satirinda ReferenceError, ekranda ham {{ }} sablonu.

   Hicbir test bunu goremedi cunku:
     * bu dosya Vue'yu KENDISI taklit ediyor, vendor dosyasina ihtiyaci yok
     * proje genelinde bir tane bile dosya-varlik denetimi yoktu
     * "ek.css bagli" denetimi bile yalnizca DIZENIN html'de gectigine
       bakiyor, dosyanin diskte oldugunu DEGIL

   Buradaki iddialar metin degil VARLIK sinaliyor: referans verilen dosya
   gercekten duruyor mu, kullanilan sinif gercekten tanimli mi.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 8. Varlik denetimi: referanslar diskte var mi ---');
{
  /* Dosyayi KOSULSUZ okumak yanlis: eksikse test cokuyor ve hangi iddianin
     dustugu gorunmuyor (yigin izi basiliyor). Once varligini SINA. */
  /* [!] B27 A2: CSS listesi ELLE yazilmiyor, index.html'den TURETILIYOR.
     Once ['style.css','ek.css'] sabitti; ek.css style.css'e katilinca
     test "diskte yok" diye coktu — ama daha kotusu tersi: sayfaya YENI
     bir stil dosyasi baglansa test onu hic gormezdi, yani "her sinif
     tanimli" iddiasi eksik kaynakla calisirdi. */
  const cssYollari = CSS_YOLLARI;
  ok('index.html en az bir stil dosyasi bagliyor', cssYollari.length >= 1,
     cssYollari.map((p) => path.basename(p)).join(' '));
  ok('bagli her stil dosyasi DISKTE var',
     cssYollari.every((p) => fs.existsSync(p)),
     cssYollari.filter((p) => !fs.existsSync(p)).join(' '));
  const oku = (p) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '');

  /* [!] YORUMLAR CIKARILIYOR. Once cikarilmiyordu ve ".kpi kuralini sil"
     mutasyonu KACTI: ek.css'in kendi aciklama yorumunda ".kpi" gectigi icin
     sinif "tanimli" sayiliyordu. Bir iddianin kendi yorumuyla karsilanmasi,
     iddia olmadigi anlamina gelir. */
  const tumCss = cssYollari.map(oku).join('\n').replace(/\/\*[\s\S]*?\*\//g, '');

  /* (a) index.html'in her href/src'i arayuz3/ altinda duruyor mu.
         Disaridan (http) gelen varlik YOK — arayuz internetsiz calismali. */
  /* `(?:^|\s)` sart: `:href="kopruAdresi"` bir Vue BAGLAMASI, dosya yolu
     degil. Onsuz `:href` de eslesiyordu ve B22.2'de eklenen kopru
     baglantisi "diskte yok" diye kirmiziya dondu. */
  const referanslar = [...htmlKaynak.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)]
    .map((m) => m[1])
    .filter((u) => !/^(https?:|data:|#|mailto:)/.test(u));
  /* ⚠ IDDIA SAYISI SABIT TUTULUYOR — referans basina bir `ok()` YOK.
     Once oyleydi ve bir mutasyon kacti: statik <script src="sahte-kart.js">
     geri konunca BIR iddia basarisiz oldu ama AYNI ANDA bir referans (yani
     bir iddia) eklendi; toplam degismedi ve mutasyon gorunmez kaldi.
     Iddia sayisi girdiyle birlikte buyuyorsa, sayim tabanli her denetim
     (dogrula3.py'nin sayim kilidi dahil) korlesir. */
  ok('index.html en az 3 yerel varlik istiyor', referanslar.length >= 3,
     referanslar.join(' '));
  const eksikVarlik = referanslar.filter((r) => !fs.existsSync(path.join(ARAYUZ, r)));
  ok('index.html\'in her yerel varligi DISKTE var',
     eksikVarlik.length === 0, eksikVarlik.join(' ') || referanslar.length + ' referans');

  /* (b) sunucu.py arayuz3/ DISINA cikmiyor. K4'un mekanizmasi buydu:
         bulunamayan dosyayi baska bir dizinden servis etmek. O dizin
         tasininca kusur sessizce ortaya cikti. */
  const sunucu = fs.readFileSync(path.join(ARAYUZ, 'sunucu.py'), 'utf8');
  const govde = sunucu.replace(/"""[\s\S]*?"""/g, '');   // docstring haric
  /* 3A (P4): `/ortak/` ESLEMESI bir dusme DEGIL — onekle kapili, tek dizin,
     `<ad>.js` bicimi. Izin verilen TEK dis dizin `ORTAK` tanimi; baska bir
     `BURASI.parent` ya da `translate_path` (genel yol cevirisi) K4'tur.
     DAVRANISI test_kopru.py sinar: arayuz3'te olmayan `/disari.js` 404. */
  /* 3H-1 (AY6): ikinci dis yol `URETEC` (uretim/arayuz-uret.py) — YALNIZ ice aktarilir
     (`/kunye.json` icin kunye_hesapla); dosya sunma yolunda (read_bytes / open) gecmez. */
  const disari = (govde.match(/BURASI\.parent[^\n]*/g) || [])
    .filter((x) => x.trim() !== 'BURASI.parent / "uretim" / "arayuz-uret.py"');
  const uretecAdi = (govde.match(/^.*\bURETEC\b.*$/gm) || []).map((x) => x.trim());
  ok('sunucu.py dizin disina dusme yapmiyor (K4 mekanizmasi)',
     disari.length === 1 && /^BURASI\.parent \/ "ortak" \/ "src"$/.test(disari[0].trim())
     && /^URETEC = BURASI\.parent \/ "uretim" \/ "arayuz-uret\.py"$/m.test(govde)
     && uretecAdi.length === 3 && uretecAdi.every((x) => /^URETEC = |^if not URETEC\.is_file\(\):$|spec_from_file_location\("arayuz_uret", URETEC\)$/.test(x))
     && /^ORTAK = BURASI\.parent/m.test(govde)
     && /if yol\.startswith\("\/ortak\/"\):\s*\n\s*return self\._ortak\(/.test(govde)
     && !/translate_path/.test(govde),
     disari.join(' | ') || 'dis dizin yok');

  /* (c) sahte-kart.js STATIK baglanmamali — yalnizca ?demo'da dinamik
         iniyor. Kosulsuz baglanirsa 15 936 B her acilista bosuna iner ve
         B22.5'te LittleFS goruntusune de girer. */
  ok('sahte-kart.js statik <script> ile baglanmamis',
     !/<script[^>]+sahte-kart\.js/.test(htmlKaynak));
  ok('sahte-kart.js dinamik yukleniyor (betikYukle)',
     govdeIcinde(appKaynak, 'demoVeri', 'betikYukle') &&
     govdeIcinde(appKaynak, 'betikYukle', 'createElement'));
  /* Betik indikten SONRA demo bayragi acilmali; erken acilirsa gonder()'in
     demo dali SahteKart tanimsizken calisir. */
  /* B22.2: bayrak artik `tasiyiciAdi`. Sira hala onemli — tasiyici demoya
     gecince gonder() SahteKart'a yoneliyor, betik inmemisse tanimsiz. */
  ok('demo tasiyicisi betik yuklendikten SONRA seciliyor',
     govdeIcinde(appKaynak, 'demoVeri', 'await this.betikYukle') &&
     appKaynak.indexOf('await this.betikYukle') <
       appKaynak.indexOf("this.tasiyiciAdi = 'demo'"));

  /* (d) index.html'de STATIK kullanilan her sinif CSS'te tanimli mi.
         `:class="..."` Vue ifadesidir, sinif adi degil — (?:^|\s) onu
         disarida birakiyor; {} olan da sablon/nesne, sinif degil. */
  const siniflar = new Set();
  for (const m of htmlKaynak.matchAll(/(?:^|\s)class="([^"{}]+)"/g)) {
    for (const c of m[1].split(/\s+/)) if (/^[a-z][a-z0-9-]*$/.test(c)) siniflar.add(c);
  }
  /* Lookahead BUYUK HARFI de dislamali: `[a-z0-9-]` ile yazildiginda
     `.kpi` iddiasi `.kpiX` selektoruyle karsilanmis sayiliyordu ve
     "kurali sil" mutasyonu KACIYORDU (B22.0 mutasyon turu). */
  const tanimsizSinif = [...siniflar].filter(
    (c) => !new RegExp('\\.' + c + '(?![A-Za-z0-9_-])').test(tumCss));
  ok('index.html\'deki her statik sinif CSS\'te TANIMLI',
     tanimsizSinif.length === 0, tanimsizSinif.join(' '));

  /* Guvenlik uyarilari govde metninden ayirt edilebilmeli. .uyari
     tanimsizken "Yuku J7'ye baglayin, J3'e degil — yoksa MOSFET baypas
     olur ve KESME CALISMAZ" duz paragraf olarak goruntuleniyordu. */
  ok('J7/J3 baypas uyarisi .uyari sinifiyla isaretli',
     /class="uyari"[\s\S]{0,200}J7/.test(htmlKaynak));
  /* .uyari ile .hata GORSEL olarak ayrilmali: .hata gecici bir hatadir,
     .uyari kalici bir emniyet talimatidir. Ikisi ayni goruntuye sahipse
     kullanici emniyet uyarisini "gecmis bir hata" sanip gozardi eder.

     HAM METIN KARSILASTIRMASI YETMIYOR: iki kural ayri dosyalarda ve ayri
     girintide duruyor, yani govdeleri ANLAMCA ayni olsa bile metinleri
     farkli cikiyordu — "ikisini ayni yap" mutasyonu bu yuzden KACTI.
     Bildirimleri normallestirip KUME olarak karsilastiriyoruz. */
  const bildirimler = (kaynak, secici) => {
    const m = kaynak.match(new RegExp('\\' + secici + '\\s*\\{([^}]*)\\}'));
    if (!m) return null;
    return m[1].split(';').map((d) => d.replace(/\s+/g, ' ').trim().toLowerCase())
      .filter(Boolean).sort().join('|');
  };
  const bUyari = bildirimler(tumCss, '.uyari');
  const bHata = bildirimler(tumCss, '.hata');
  ok('.uyari gorsel olarak .hata\'dan AYRI tanimli',
     bUyari !== null && bHata !== null && bUyari !== bHata);

  /* (e) Yedeksiz var(--x) kullanimi tanimli mi. Tanimsiz olan sessizce
         gecersize duser: renk/kenarlik hic uygulanmaz, hata da vermez. */
  const tanimli = new Set(
    [...tumCss.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]));
  const tanimsizDegisken = [...new Set(
    [...tumCss.matchAll(/var\((--[a-z0-9-]+)\)/g)].map((m) => m[1]))]
    .filter((v) => !tanimli.has(v));
  ok('yedeksiz her CSS degiskeni TANIMLI',
     tanimsizDegisken.length === 0, tanimsizDegisken.join(' '));
}

/* ═══════════════════════════════════════════════════════════════════════
   9. TASIYICI KATMANI (B22.2)

   Bu bolumun cogu METIN degil YAPI siniyor: tasiyicilar vm baglaminda
   gercekten olusturuluyor ve yuzeyleri karsilastiriliyor. Ucunun ayni
   yuzeyi sunmasi, "tek arayuz uc tasima" iddiasinin ta kendisi — biri
   otekilerden ayrisirsa panel kodu dallanmaya baslar ve bu proje tam
   olarak oradan uc kez yandi (DEVIR 4.1, 4.15, B17).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 9. Tasiyici katmani: uc tasima, tek arayuz ---');
{
  const kod = yorumsuz(appKaynak);
  let T = null;
  try { T = vm.runInContext('TASIYICILAR', sandbox); } catch (e) { /* yok */ }

  ok('TASIYICILAR kaydi var', T && typeof T === 'object',
     T ? Object.keys(T).join(' ') : 'YOK');

  if (T) {
    const YUZEY = ['ad', 'yetenek', 'destekli', 'ac', 'kapat', 'gonder'];
    ok('Uc tasiyici kayitli (seri · akis · demo)',
       ['seri', 'akis', 'demo'].every((k) => k in T),
       Object.keys(T).join(' '));

    const eksik = [];
    for (const [k, t] of Object.entries(T)) {
      for (const y of YUZEY) if (!(y in t)) eksik.push(k + '.' + y);
    }
    ok('Her tasiyici AYNI yuzeyi sunuyor', eksik.length === 0,
       eksik.length ? eksik.join(' ') : YUZEY.join(' '));

    /* Yetenek tablosu da ayni SEKILDE olmali: bir tasiyicida olmayan
       alan, sablonda `undefined` olarak sessizce yanlis davranir. */
    const alanlar = Object.keys(T.seri.yetenek).sort().join(',');
    const ayrik = Object.entries(T)
      .filter(([, t]) => Object.keys(t.yetenek).sort().join(',') !== alanlar)
      .map(([k]) => k);
    ok('Yetenek tablolari AYNI alanlara sahip', ayrik.length === 0,
       ayrik.length ? 'ayrisan: ' + ayrik.join(' ') : alanlar);

    /* Modlar arasindaki farkin GERCEKTEN yetenek tablosunda yasadigini
       sina — hepsi ayni degerleri verseydi tablo susleme olurdu. */
    const gecmisler = new Set(Object.values(T).map((t) => t.yetenek.gecmis_s));
    ok('Yetenek tablosu modlari GERCEKTEN ayiriyor', gecmisler.size > 1,
       'gecmis_s: ' + [...gecmisler].join(' / '));
  }

  /* [!] Bu iddia, B22.0'da bulunan sessiz-sifir kusurunun tekrarlanamaz
     halidir: `pilYokla` goreli `fetch('/pil?…')` yapiyordu ve sayfa
     localhost:8772'den servis edildigi icin istek karta HIC gitmiyordu.
     404 govdesi `anahtar=deger` sanilip ayristiriliyor, tum KPI'lar
     sessizce 0 oluyordu. Artik her uzak istek kartAdres()'ten gecmeli. */
  /* 3A: ekran modulleri de taraniyor (yeni ekranlar oraya giriyor). */
  const fetchKodu = kodKaynaklari.map((k) => yorumsuz(k.kaynak)).join('\n');
  const fetchler = [...fetchKodu.matchAll(/fetch\(([^,)]*)/g)].map((m) => m[1].trim());
  const kacak = fetchler.filter((a) => !a.includes('kartAdres('));
  ok('app.js\'te kartAdres() disinda fetch( YOK',
     kacak.length === 0,
     kacak.length ? kacak.join(' | ') : `${fetchler.length} istek, hepsi kartAdres()`);

  ok('kartAdres() taban onekini uyguluyor',
     govdeIcinde(appKaynak, 'kartAdres', 'kartTaban'),
     'bos taban = ayni koken; dolu taban = PC\'den karta dogrudan');

  ok('pilYokla yanit DURUMUNU denetliyor',
     govdeIcinde(appKaynak, 'pilYokla', 'y.ok'),
     'fetch 404\'te REDDETMEZ — denetlenmezse hata sayfasi ayristirilir');
  ok('pilYokla yanit BICIMINI denetliyor',
     govdeIcinde(appKaynak, 'pilYokla', "indexOf('durum=')"),
     'kismi yanit (kartta yigin sikismasi) tutarli Content-Length ile gelir');
  ok('pilYokla basarisizligi KULLANICIYA soyluyor',
     govdeIcinde(appKaynak, 'pilYokla', 'pilHataMetni') &&
     htmlKaynak.includes('pilHataMetni'),
     'sessiz sifir yerine sebep');

  /* Ayristiriciya tasiyiciya ozgu dal girmemeli: tel ustundeki baytlar
     her tasimada ayni oldugu icin tek ayristirici yetiyor. Dal acmak,
     baytlarin ayristigi anlamina gelir. */
  ok('satirIsle icinde tasiyiciya ozgu dal YOK',
     !govdeIcinde(appKaynak, 'satirIsle', 'tasiyiciAdi') &&
     !govdeIcinde(appKaynak, 'satirIsle', 'this.demo'),
     'ayni satirlar seri, akis ve sahte kartta birebir ayni');

  /* Tek kaynak: `demo` artik ayri bir bayrak degil, tasiyicidan turetilen
     computed. Iki bayrak tutmak DEVIR 4.1'in deseniydi. */
  ok('`demo` tasiyicidan TURETILIYOR, ayri bayrak degil',
     /demo\(\)\s*\{\s*return this\.tasiyiciAdi === 'demo'/.test(kod) &&
     !/^\s*demo:\s*false/m.test(kod),
     'tek kaynak');

  /* Tercih kaliciligi: bu alanlar her acilista yeniden giriliyordu. */
  ok('Tercihler localStorage\'da tutuluyor',
     govdeIcinde(appKaynak, 'ayarYaz', 'localStorage.setItem') &&
     govdeIcinde(appKaynak, 'ayarOku', 'localStorage.getItem'),
     'pencere · gostergeler · sont · sebeke Hz · adres · tasiyici');
  ok('localStorage erisimi try/catch icinde',
     govdeIcinde(appKaynak, 'ayarOku', 'catch') &&
     govdeIcinde(appKaynak, 'ayarYaz', 'catch'),
     'ozel kipte ve kota dolunca ERISIMIN KENDISI atiyor');
}

/* ═══════════════════════════════════════════════════════════════════════
   10. GORUNUMLER — hash yonlendirme (B27 Asama 1)

   Tek kaydirmali sayfa bes gorunume bolundu. Iki tuzak var ve ikisi de
   Vue taklidinde GORUNMEZ:
   (a) Gorunum `v-if` ile saklanirsa tuval YOK OLUR: gecmis kaybolmaz ama
       geri donunce bos bir grafik gelir, ilk D satirina kadar. `v-show`
       sart.
   (b) `display:none` tuval 0 genislik okur. Gorunum degisince yeniden
       cizilmezse skop/grafik 300x150 varsayilan olcude, sola yapisik
       kalir. Bu yuzden watch `gorunum` -> $nextTick -> grafikCiz+osiloCiz.
   Ikisi de headless Edge'de DOGRULANDI (nodemo-olcum,skop.png); burada
   yapi ve davranis civileniyor ki sonraki asamalarda kirilirsa gorulsun.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 10. Gorunumler: hash yonlendirme, v-show, yeniden cizim ---');
{
  const kod = yorumsuz(appKaynak);
  const html = yorumsuz(htmlKaynak);

  // app.js'teki liste ile index.html'deki v-show sarmallari BIREBIR ayni mi
  let G = null;
  try { G = vm.runInContext('GORUNUMLER', sandbox); } catch (e) { /* yok */ }
  const appIdler = G ? G.map((g) => g.id) : [];
  const htmlIdler = [...html.matchAll(/<main[^>]*v-show="gorunum === '([a-z]+)'"/g)]
    .map((m) => m[1]);
  /* 3C: altinci gorunum `kayitlar` (C7) — sayi 5'ten 6'ya BILEREK. 3G (KR6): yedinci
     `karsilastir` — 6'dan 7'ye BILEREK. */
  ok('GORUNUMLER listesi var ve 7 gorunum tanimli (3C: kayitlar, 3G: karsilastir)',
     appIdler.length === 7 && appIdler.includes('kayitlar') && appIdler.includes('karsilastir'), appIdler.join(' '));
  ok('index.html\'deki her <main v-show> app.js listesindeki bir gorunum',
     htmlIdler.length === appIdler.length &&
       htmlIdler.every((id) => appIdler.includes(id)) &&
       new Set(htmlIdler).size === htmlIdler.length,
     'html: ' + htmlIdler.join(' '));
  ok('Gorunumler v-show ile saklaniyor, v-if ile DEGIL (tuval canli kalsin)',
     !/<main[^>]*v-if="gorunum/.test(html) && htmlIdler.length === 7);

  // her gorunumun sekmesi var: nav, GORUNUMLER uzerinde v-for
  ok('Sekme seridi GORUNUMLER listesinden uretiliyor (elle kopya degil)',
     /<nav[^>]*class="gorunum-nav"[\s\S]{0,300}v-for="g in gorunumler"/.test(html) &&
       /gorunumler:\s*GORUNUMLER/.test(kod));

  // hash -> gorunum: bilinmeyen hash varsayilana duser, bilinen hash gecer
  let hashten = null;
  try { hashten = vm.runInContext('hashtenGorunum', sandbox); } catch (e) { /* yok */ }
  if (hashten) {
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('hashtenGorunum: #/skop -> skop', dene('#/skop') === 'skop');
    ok('hashtenGorunum: #skop (egik cizgisiz) -> skop', dene('#skop') === 'skop');
    /* 3D (D1): varsayilan gorunum Canli (`canli`); ESKI `#/olcum` adresi de Canli'ya
       duser (yer imi / paylasilmis baglanti bos ekrana gitmesin). */
    ok('hashtenGorunum: bilinmeyen (#/yok) -> varsayilan canli', dene('#/yok') === 'canli');
    ok('hashtenGorunum: bos hash -> varsayilan canli', dene('') === 'canli');
    ok('[!] 3D: ESKI adres #/olcum -> canli (ve #/canli -> canli)', dene('#/olcum') === 'canli'
       && dene('#olcum') === 'canli' && dene('#/canli') === 'canli');
    delete sandbox.location;
  } else {
    ok('hashtenGorunum fonksiyonu sandbox\'ta erisilebilir', false);
  }

  // mounted: hashchange dinleniyor (geri tusu calissin)
  ok('mounted() hashchange olayini dinliyor',
     govdeIcinde(appKaynak, 'mounted', "'hashchange'"));

  // DAVRANIS: watch.gorunum gercekten iki tuvali $nextTick icinde cizdiriyor mu.
  // Sahte `this`: nextTick'i hemen kosuyoruz, cizimleri sayiyoruz.
  const w = secenekler.watch && secenekler.watch.gorunum;
  ok('watch.gorunum tanimli', typeof w === 'function');
  if (typeof w === 'function') {
    let g = 0, o = 0, sp = 0, pc = 0, tick = 0;
    const sahte = {
      $nextTick(fn) { tick++; fn(); },
      grafikCiz() { g++; }, osiloCiz() { o++; }, spektrumCiz() { sp++; }, pilCiz() { pc++; }, skopAcik: false,
    };
    sandbox.location = { hash: '#/olcum' };
    sandbox.history = { replaceState() {} };
    w.call(sahte, 'skop');
    /* 3E: spektrum tuvali (ekran/osiloskop.js) da ayni kurala tabi — gizliyken 0 genislik okur */
    /* 3F: pil egrisi (ekran/pil.js) de ayni kurala tabi */
    ok('gorunum degisince grafik, skop, spektrum VE pil egrisi $nextTick icinde yeniden ciziliyor; Osiloskop modulu kuruluyor',
       tick === 1 && g === 1 && o === 1 && sp === 1 && pc === 1 && sahte.skopAcik === true,
       `nextTick=${tick} grafik=${g} skop=${o} spektrum=${sp} pil=${pc} skopAcik=${sahte.skopAcik}`);
    delete sandbox.location; delete sandbox.history;
  }

  // CSS: sekme sinifi ve etkin durumu tanimli (8. bolum genel sinif
  // denetimini yapiyor; burada ETKIN sekmenin ayirt edildigini civiliyoruz)
  const tumCss = cssOku();
  ok('Etkin sekme gorsel olarak ayirt ediliyor (.gorunum-sekme.etkin)',
     /\.gorunum-sekme\.etkin\s*\{[^}]*(color|border)/.test(tumCss));

  // Bildirimler TEK alanda: ust seritteki dort kosullu blok tek sarmalda
  // (yorumsuz() HTML yorumlarini sildiginden kapanis isareti degil, ilk
  //  <main> sinir: bildirim sarmali gorunumlerden ONCE bitmeli)
  const bildirimBlok = html.match(/<div class="bildirimler">([\s\S]*?)<main /);
  ok('Ust bildirimler tek .bildirimler sarmalinda',
     !!bildirimBlok && ['!destekli', 'kopruAdresi', 'v-if="hata"', '!surucuyum']
       .every((k) => bildirimBlok[1].includes(k)));

  // Kalibrasyon talimati pil sekmesinde DEGIL, ayar sekmesinde.
  // (Gorunumler ayrilinca ortaya cikan yerlesim kusuru — B27 A1.)
  const ayarBlok = html.match(/v-show="gorunum === 'ayar'"([\s\S]*?)<\/main>/);
  const pilBlok = html.match(/v-show="gorunum === 'pil'"([\s\S]*?)<\/main>/);
  ok('"Sira onemli" kalibrasyon talimati AYAR gorunumunde, pilde degil',
     !!ayarBlok && ayarBlok[1].includes('Sıra önemli') &&
       !!pilBlok && !pilBlok[1].includes('Sıra önemli'));
}

/* ═══════════════════════════════════════════════════════════════════════
   11. RAPOR ARALIGI + GRAFIK BOSLUKLARI (B27 A2)

   Kullanicinin ekran goruntusu (2026-09-12) iki sey gosterdi:
   (a) KPI kartlari "veri yok" derken grafik sahte 1.72 V'u DUZ CIZGI
       olarak cizmeye ve "tepe 1.72 V" yazmaya devam ediyordu — K1'in
       grafik yarisi eksikti.
   (b) "463 /sn" etiketi ADC hizini soyluyor, ekran 5/s guncelleniyordu;
       kullanici farki fark etti. Artik iki hiz ayri ve ikisi de OLCULUYOR.
   Ayrica rapor araligi (D satiri sikligi) `r<ms>` ile secilebilir oldu.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 11. Rapor araligi + grafik bosluklari (B27 A2) ---');
{
  const u = ornek();
  u.grafikCiz = secenekler.methods.grafikCiz;      // ornek() bunu susturuyor
  u.grafikPlanla = secenekler.methods.grafikPlanla;

  // (a) gecersiz kanal NaN olarak gecmise giriyor
  u.satirIsle('D 1.7160 0.000003 0.00001 0.0 0.0 1000 93 0 1');
  const s1 = u.gecmis[u.gecmis.length - 1];
  ok('durum=1 (V yok): gecmiste V ve W NaN, I sayi',
     Number.isNaN(s1.v) && Number.isNaN(s1.w) && s1.i === 0.000003,
     JSON.stringify(s1));
  u.satirIsle('D 12.0 0.5 6.0 0.0 0.0 1200 93 0 2');
  const s2 = u.gecmis[u.gecmis.length - 1];
  ok('durum=2 (I yok): I ve W NaN, V sayi',
     Number.isNaN(s2.i) && Number.isNaN(s2.w) && s2.v === 12);
  u.satirIsle('D 12.0 0.5 6.0 0.0 0.0 1400 93 0 0');
  const s3 = u.gecmis[u.gecmis.length - 1];
  ok('durum=0: uc kanal da sayi', [s3.v, s3.i, s3.w].every(Number.isFinite));

  // (b) iki hiz, ikisi de olculen araliktan
  ok('guncellemeHizi 200 ms araliktan "5 güncelleme/s"',
     u.guncellemeHizi === '5 güncelleme/s', u.guncellemeHizi);
  ok('orneklemeHizi 93 ornek / 200 ms = "465 örnek/s"',
     u.orneklemeHizi === '465 örnek/s', u.orneklemeHizi);

  /* 3D (D3): canli grafik artik ortak/src/grafik.js (ekran/canli.js). Eski elle cizimin
     uc davranis iddiasi ("V tamamen NaN: veri yok", "I gecerli: tepe ... mA", "ortadaki
     NaN cizgiyi KOPARIYOR") ZAYIFLATILMADAN yeni koda gore bolum 25'te yeniden yazildi:
     lejant metni gercek modulden, cizginin kopmasi grafik.js'in cizim planindan. */

  // CSV: NaN bos hucre (Blob/URL sanalikta yok; govde denetimi)
  ok('csvIndir NaN hucreyi BOS birakiyor',
     govdeIcinde(appKaynak, 'csvIndir', "Number.isNaN(x) ? ''"));

  // cizim birlestirme: rAF varsa bir kareye toplaniyor
  {
    let cizim = 0, raf = 0;
    const v = ornek();
    v.grafikPlanla = secenekler.methods.grafikPlanla;
    v.grafikCiz = () => { cizim++; };
    sandbox.requestAnimationFrame = (fn) => { raf++; setTimeout(fn, 0); return raf; };
    v.grafikPlanla(); v.grafikPlanla(); v.grafikPlanla();
    ok('uc grafikPlanla() tek requestAnimationFrame\'e birlesiyor',
       raf === 1 && cizim === 0, `raf=${raf} cizim=${cizim}`);
    delete sandbox.requestAnimationFrame;
    v.grafikPlanla();
  }

  // rapor araligi: A satiri -> tercih farkliysa surucu r<ms> yollar
  const gidenler = [];
  u.gonder = async (k) => { gidenler.push(k); };
  u.raporMs = 100; u.surucuyum = true; u.bagli = true;
  const A = 'A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 '
          + 'y_sifir=0 sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200';
  u.satirIsle(A);
  ok('A rapor=200, tercih 100, surucu -> r100 gonderildi',
     u.kartRapor === 200 && gidenler.includes('r100'), gidenler.join(' '));
  gidenler.length = 0; u.surucuyum = false;
  u.satirIsle(A);
  ok('izleyici hicbir sey gondermez', gidenler.length === 0);
  u.surucuyum = true; u.raporMs = 200; gidenler.length = 0;
  u.satirIsle(A);
  ok('A rapor=200, tercih 200 -> gereksiz r yok', gidenler.length === 0);
  u.kartRapor = null;
  u.satirIsle(A.replace(' rapor=200', ''));
  ok('eski firmware (rapor= yok) -> kartRapor dokunulmaz', u.kartRapor === null);

  // kartin yaniti: KIRPILMIS deger tercihi ezer (r5 -> 20)
  u.raporMs = 5;
  u.satirIsle('* rapor araligi 20 ms');
  ok('"* rapor araligi 20 ms" -> kartRapor 20 VE raporMs 20 (kirpma gorunur)',
     u.kartRapor === 20 && u.raporMs === 20);

  // watch: tercih degisince bagli surucu r<ms> yollar
  const w = secenekler.watch && secenekler.watch.raporMs;
  ok('watch.raporMs tanimli', typeof w === 'function');
  if (typeof w === 'function') {
    const g2 = []; const saklanan = [];
    const sahte = { ayarYaz: (k, v) => saklanan.push(k + '=' + v), bagli: true,
                    surucuyum: true, kartRapor: 200, gonder: async (k) => { g2.push(k); } };
    w.call(sahte, 500);
    ok('raporMs 500 -> localStorage + r500', saklanan.includes('raporMs=500') && g2.includes('r500'));
    const g3 = [];
    w.call({ ayarYaz() {}, bagli: false, surucuyum: true, kartRapor: 200,
             gonder: async (k) => { g3.push(k); } }, 500);
    ok('bagli degilken r gonderilmez (baglaninca A ile uydurulur)', g3.length === 0);
  }

  // firmware tarafi.
  // govdeIcinde() JS metotlari icin (girintili tanim); C'de tanim satir
  // basinda `void ad(` ve ilk girintili eslesme bir CAGRI oluyor — yanlis
  // govde. Tanimi tip sozcugu + ad + parametre + `{` ile ariyoruz.
  const cGovde = (kaynak, ad, aranan) => {
    const m = new RegExp('\\n[A-Za-z_][\\w\\s*]*\\b' + ad + '\\([^;{)]*\\)\\s*\\{').exec(kaynak);
    if (!m) return false;
    const j = kaynak.indexOf('{', m.index + m[0].length - 1);
    let d = 0;
    for (let k = j; k < kaynak.length; k++) {
      if (kaynak[k] === '{') d++;
      else if (kaynak[k] === '}') { d--; if (d === 0) return kaynak.slice(j, k + 1).includes(aranan); }
    }
    return false;
  };
  ok('firmware `r<ms>` 20..5000 arasina KIRPIYOR',
     /#define RAPOR_MS_EN_AZ\s+20\b/.test(ino) && /#define RAPOR_MS_EN_COK\s+5000\b/.test(ino)
       && /case 'r':[\s\S]{0,500}if \(v < RAPOR_MS_EN_AZ\)[\s\S]{0,120}if \(v > RAPOR_MS_EN_COK\)/.test(ino));
  ok('firmware A satirinda rapor= var (K5 deseni: kart soyler)',
     cGovde(ino, 'ayar_yaz_seri', '" rapor="'));
  ok('SSE olayi istemci basina TEK write() (dort print degil)',
     cGovde(ino, 'akis_yolla', '.write(') && !cGovde(ino, 'akis_yolla', '.print('));

  // sahte kart ayni davranis
  const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
  ok('sahte kart `r5` -> "* rapor araligi 20 ms" (kirpma firmware ile ayni)',
     SK.komut('r5')[0] === '* rapor araligi 20 ms' && SK.raporAralik() === 20);
  ok('sahte kart `r9999` -> 5000', SK.komut('r9999')[0] === '* rapor araligi 5000 ms');
  SK.komut('r200');
  ok('sahte kart A satirinda rapor=', /\brapor=200\b/.test(SK.komut('?')[0]));
  ok('sahte kart ornek sayisi aralikla olcekleniyor (200 ms -> 172)',
     SK.dSatiri(1000, 0).satir.split(' ')[7] === '172');
  SK.komut('r100');
  ok('… 100 ms -> 86', SK.dSatiri(1100, 0).satir.split(' ')[7] === '86');
  SK.komut('r200');

  // arayuz: secici GORUNUMDE ve secenekler tek listeden
  ok('Yenileme secicisi zaman grafigi arac cubugunda, RAPOR_SECENEKLERI\'nden',
     /v-model\.number="raporMs"[\s\S]{0,200}v-for="s in raporSecenekleri"/.test(yorumsuz(htmlKaynak))
       && /raporSecenekleri:\s*RAPOR_SECENEKLERI/.test(appKaynak));
  ok('Ornekleme kartinda guncellemeHizi gosteriliyor',
     yorumsuz(htmlKaynak).includes('{{ guncellemeHizi }}'));

  /* B27 A2-b: akim kanalinin menzili VE adimi. Kartta olculdu: 0.1 ohm
     sontte ham gurultu tam 1 LSB (78 uA); ekrandaki "7 uA" 96 orneklik
     ortalama. Adim gorunmeden bu sayi gercek akim sanildi. */
  {
    const a = ornek();
    a.kartSont = 0.1;
    ok('akimMenzilAralik 0.1 ohm -> ±2.56 A · 78.1 µA',
       a.akimMenzilAralik === '±2.56 A · 78.1 µA', a.akimMenzilAralik);
    a.kartSont = 10;
    ok('… 10 ohm -> ±25.6 mA · 0.78 µA',
       a.akimMenzilAralik === '±25.6 mA · 0.78 µA', a.akimMenzilAralik);
    /* Kart okunmadiysa menu tercihi YEDEK — ama kart konustuysa KART haklidir
       (sont fiziksel bir gercek; K5 deseni). */
    a.kartSont = null; a.sontSecim = '1';
    ok('kart okunmadan menu tercihi yedek (1 ohm)',
       a.akimMenzilAralik === '±256.0 mA · 7.81 µA', a.akimMenzilAralik);
    a.kartSont = 0.1;
    ok('kart konusunca KART kazaniyor (menu 1 ohm derken kart 0.1)',
       a.akimMenzilAralik === '±2.56 A · 78.1 µA', a.akimMenzilAralik);
    ok('Akim kartinda menzil/adim satiri var',
       yorumsuz(htmlKaynak).includes('{{ akimMenzilAralik }}'));
    ok('ADS kademesi firmware ile ayni (PGA_0256)',
       /const ADS_PGA_V = 0\.256;/.test(appKaynak) &&
       /#define PGA_0256\s+0\.256f/.test(fs.readFileSync(
         path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum3.h'), 'utf8')));
  }

  // otomatik baglanma: sayfayi kart/kopru sunduysa EVET, yerel/demo/file HAYIR
  {
    const v = ornek();
    const karar = (loc, tasiyici = 'akis', bagli = false) => {
      sandbox.location = loc; v.tasiyiciAdi = tasiyici; v.bagli = bagli;
      const r = v.otomatikBaglanmali(); delete sandbox.location; return r;
    };
    const kart = { protocol: 'http:', hostname: 'olcum.local', search: '' };
    ok('kart sunuyor (olcum.local, akis) -> otomatik baglan', karar(kart) === true);
    ok('localhost -> baglanma (gelistirme sunucusu, USB kipi)',
       karar({ protocol: 'http:', hostname: 'localhost', search: '' }) === false);
    ok('file:// -> baglanma',
       karar({ protocol: 'file:', hostname: '', search: '' }) === false);
    ok('?demo -> baglanma (sahte kart)',
       karar({ protocol: 'http:', hostname: 'olcum.local', search: '?demo' }) === false);
    ok('tasiyici seri ise baglanma', karar(kart, 'seri') === false);
    ok('zaten bagliysa tekrar baglanma', karar(kart, 'akis', true) === false);
    /* 4A (PC1): PC koprusu paneli http://olcum.localhost:8770'ten sunuyor. *.localhost
       guvenli baglam (Web Serial de var) ama sayfayi SUNAN kopru: tasiyici akis olmali
       ve kendiliginden baglanmali. Yalniz duz `localhost` gelistirme sunucusu (USB). */
    const pc = { protocol: 'http:', hostname: 'olcum.localhost', host: 'olcum.localhost:8770', search: '' };
    ok('4A: olcum.localhost (PC koprusu) -> otomatik baglan', karar(pc) === true);
    {
      let istek = 0;
      sandbox.location = pc; sandbox.fetch = () => { istek++; return new Promise(() => {}); };
      v.tasiyiciAdi = 'seri';
      const ayarOku = v.ayarOku, kaydet = v.kaydet;
      v.ayarOku = () => null; v.kaydet = () => {};
      v.kopruyuAlgila();                 /* yerel degilse ilk await'ten ONCE karar verir */
      v.ayarOku = ayarOku; v.kaydet = kaydet;
      delete sandbox.location; delete sandbox.fetch;
      ok('4A: olcum.localhost -> kopruyuAlgila tasiyiciyi akis yapiyor (Web Serial degil), /durum yoklamadan',
         v.tasiyiciAdi === 'akis' && istek === 0, `tasiyici=${v.tasiyiciAdi} istek=${istek}`);
    }
    ok('mounted() kopruyuAlgila SONRASINDA otomatikBaglanmali ile baglan() cagiriyor',
       /kopruyuAlgila\(\)\.then\([\s\S]{0,80}?otomatikBaglanmali\(\)\) this\.baglan\(\)/.test(yorumsuz(appKaynak)));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   12. AKIS TASIYICISI: `?` KIMLIKTEN SONRA (B27 A2)

   Gercek kartta CDP ile olculdu: sayfa acilir acilmaz gonderilen `?`
   HER SEFERINDE 403 aliyordu ("gecersiz oturum jetonu") cunku `ac()`
   EventSource'u kurup hemen donuyor, jeton ise `kimlik` olayiyla
   sonradan geliyordu. Sonuc: WiFi yolunda K5 esitlemesi hic calismiyor,
   her acilis bir hata bildirimiyle basliyor.

   Bu bolum ASENKRON ve DAVRANISSAL: sahte EventSource ile `ac()`
   cagriliyor; `kimlik` gelmeden cozulmemeli, gelince cozulmeli, ve
   baglan() akisinda `?` jetonla gitmeli.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 12. Akis tasiyicisi: `?` kimlikten sonra ---');
{
  /* Asenkron bolumde yakalanmayan bir hata surecin SESSIZCE 0 ile
     cikmasina yol acar — 'dogrulama gecti' satiri basilmaz ama kimse
     kirmizi gormez. Acikca kirmizi yap. */
  process.on('unhandledRejection', (e) => {
    console.log('[!!] asenkron bolum COKTU: ' + (e && e.stack || e));
    process.exit(1);
  });
  const T = vm.runInContext('TASIYICILAR', sandbox);
  /* Sahte EventSource: olaylari elle tetikliyoruz. Global olarak sandbox'a
     konuyor cunku `ac()` `new EventSource(...)` diyor. */
  class SahteES {
    constructor(url) { this.url = url; this.dinleyici = {}; SahteES.son = this; }
    addEventListener(ad, fn) { (this.dinleyici[ad] = this.dinleyici[ad] || []).push(fn); }
    tetikle(ad, data) {
      for (const fn of (this.dinleyici[ad] || []).slice()) fn({ data });
    }
    close() {}
  }
  sandbox.EventSource = SahteES;
  const gercekSetTimeout = sandbox.setTimeout;
  sandbox.setTimeout = () => 0;          // 3 s tavan bu testte HIC dolmasin
  sandbox.clearTimeout = () => {};

  const u = ornek();
  u.kartAdres = (yol) => yol;
  u.kaydet = () => {};
  let cozuldu = false;
  const soz = T.akis.ac(u).then(() => { cozuldu = true; });

  (async () => {
    await new Promise((r) => setImmediate(r));
    ok('kimlik gelmeden ac() COZULMUYOR', cozuldu === false);
    ok('EventSource /akis ile acildi', SahteES.son && SahteES.son.url === '/akis');
    SahteES.son.tetikle('kimlik', JSON.stringify({ jeton: 'abc123', surucu: true }));
    await soz;
    ok('kimlik gelince ac() cozuluyor ve jeton alinmis', cozuldu && u.jeton === 'abc123', u.jeton);

    /* baglan() akisi: ac() -> `?`. Gonderilen `?` jetonlu gitmeli. */
    const v = ornek();
    v.kartAdres = (yol) => yol; v.kaydet = () => {};
    v.tasiyiciAdi = 'akis';
    const gidenler = [];
    v.gonder = async (metin) => { gidenler.push({ metin, jeton: v.jeton }); };
    const b = v.baglan();
    await new Promise((r) => setImmediate(r));
    ok('baglan(): kimlik gelmeden `?` GONDERILMEDI', gidenler.length === 0);
    SahteES.son.tetikle('kimlik', JSON.stringify({ jeton: 'xyz789', surucu: true }));
    await b;
    /* ⚠ Iddia "TEK komut" demiyor artik: B36 ile baglantida `CT`
       (kalibrasyon tablosu) da gidiyor. Korunan sey SAYI degil KURAL —
       ilk komut `?` ve gidenlerin HEPSI jetonlu. Sayiya kilitlemek,
       her yeni acilis komutunda bu testi anlamsizca kirardi. */
    ok('baglan(): kimlikten sonra `?` JETONLA gitti',
       gidenler.length >= 1 && gidenler[0].metin === '?'
       && gidenler.every((g) => g.jeton === 'xyz789'),
       JSON.stringify(gidenler));
    ok('baglan(): kalibrasyon tablosu da isteniyor (`CT`)',
       gidenler.some((g) => g.metin === 'CT'),
       'tablo gelmezse skop ekseni duzeltmesiz cizilir');

    /* hata olayi da cozmeli — yoksa baglan() sonsuza kadar askida */
    const w = ornek(); w.kartAdres = (yol) => yol; w.kaydet = () => {};
    let hataCozdu = false;
    const s2 = T.akis.ac(w).then(() => { hataCozdu = true; });
    await new Promise((r) => setImmediate(r));
    SahteES.son.tetikle('error', '');
    await s2;
    ok('akis hatasi ac()\'i cozuyor (askida kalmaz)', hataCozdu);

    sandbox.setTimeout = gercekSetTimeout;
    delete sandbox.EventSource; delete sandbox.clearTimeout;
    await bolum12Bitti();
  })();
}

async function bolum12Bitti() {
/* ═══════════════════════════════════════════════════════════════════════
   13. TASARIM SISTEMI (B27 Asama 2)

   Iki sinif kusur civileniyor:
   (a) TEMA YARIM KALMASI — bir belirtec yalnizca bir temada tanimliysa
       oteki temada `var()` sessizce gecersize duser: renk hic uygulanmaz,
       hata da vermez. Sayfa "bir temada guzel, otekinde okunaksiz" olur.
   (b) ARAYUZ <-> TUVAL AYRISMASI — kanal renkleri hem kartlarda hem
       `app.js`'in ciziminde kullaniliyor (`renk('--volt')`). Ucu de
       tanimli ve BIRBIRINDEN FARKLI olmali; ikisi ayni olursa grafikte
       gerilim ve akim ayirt edilemez.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 13. Tasarim sistemi: temalar, kanal renkleri, hareket ---');
{
  const css = cssOku();
  const blok = (secici) => {
    const i = css.indexOf(secici);
    if (i < 0) return null;
    const a = css.indexOf('{', i), b = css.indexOf('}', a);
    return a < 0 || b < 0 ? null : css.slice(a, b);
  };
  const belirtecler = (govde) => new Set(
    [...(govde || '').matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));

  /* 3A (P1): UC GORUNUM, her biri `<html data-tema>` ile secilen bir blok.
     Koyu blogunun seciciler listesinde ciplak `:root` da var — ozniteligi
     olmayan sayfa (JS'siz, ilk boyama) Koyu cizilir. Eski "acik tema =
     prefers-color-scheme medya blogu" duzeni kalkti: secim JS'te
     (ekran/tema.js + <head> betigi), kullanicinin acik secimi kazaniyor. */
  /* Yorumlar cikarilip kural kural taraniyor; seciciler listesinde
     `:root[data-tema="<ad>"]` gecen ILK kural o temanin blogu. */
  const cssKod = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const temaBlok = (ad) => {
    for (const m of cssKod.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const secici = m[1].trim();
      if (secici.split(',').map((s) => s.trim()).includes(':root[data-tema="' + ad + '"]')) {
        return { secici, govde: m[2] };
      }
    }
    return null;
  };
  const TEMA_ADLARI = ['koyu', 'acik', 'onpanel'];
  const bloklar = Object.fromEntries(TEMA_ADLARI.map((a) => [a, temaBlok(a)]));
  const koyu = belirtecler(bloklar.koyu && bloklar.koyu.govde);
  const acik = belirtecler(bloklar.acik && bloklar.acik.govde);

  ok('Uc gorunum blogu var (koyu · acik · onpanel)',
     TEMA_ADLARI.every((a) => bloklar[a]),
     TEMA_ADLARI.map((a) => a + (bloklar[a] ? '' : ' YOK')).join(' '));
  ok('Koyu VARSAYILAN: ciplak :root (data-tema yokken) Koyu blogunda',
     !!bloklar.koyu && bloklar.koyu.secici.split(',').map((s) => s.trim()).includes(':root')
     && koyu.size >= 20, bloklar.koyu ? `${bloklar.koyu.secici} · ${koyu.size} belirtec` : 'yok');
  ok('Acik tema yalnizca DEGERLERI degistiriyor (yeni belirtec uretmiyor)',
     [...acik].every((b) => koyu.has(b)),
     [...acik].filter((b) => !koyu.has(b)).join(' '));

  /* Renk belirtecleri UC temada da tanimli olmali. Olcu/bicim
     belirtecleri (--mono, --yuvarlak, --gecis, --govde) temaya gore
     degismez; onlar ayri, TEK bir :root blogunda. */
  const renkler = [...koyu].filter((b) =>
    !/^--(mono|govde|yuvarlak|yuvarlak-sm|gecis)$/.test(b));
  const eksikAcik = renkler.filter((b) => !acik.has(b));
  ok('Her renk/golge belirteci ACIK temada da yeniden tanimli',
     eksikAcik.length === 0, eksikAcik.join(' '));

  /* Kanal renkleri: tanimli, birbirinden FARKLI, uc temada da. */
  for (const ad of TEMA_ADLARI) {
    const g = bloklar[ad] ? bloklar[ad].govde : '';
    const oku = (b) => (g.match(new RegExp(b + ':\\s*([^;]+);')) || [])[1];
    const uc = ['--volt', '--amper', '--watt'].map(oku);
    ok(`Kanal renkleri ${ad} temada tanimli ve UCU DE FARKLI`,
       uc.every(Boolean) && new Set(uc.map((x) => x.trim().toLowerCase())).size === 3,
       uc.join(' '));
    const vurgu = oku('--vurgu');
    ok(`Vurgu ${ad} temada kanal renklerinden AYRI`,
       !!vurgu && !uc.map((x) => (x || '').trim().toLowerCase())
                     .includes(vurgu.trim().toLowerCase()),
       `vurgu ${vurgu}`);
  }

  /* app.js'in tuvalde okudugu her belirtec CSS'te tanimli olmali.
     Tanimsizsa getPropertyValue bos doner ve cizgi '#888'e duser —
     grafik sessizce gri cizilir. */
  /* 3A: UC temada da (ve ekran modullerinin okudugu belirtecler de). */
  const tuvalBelirtecleri = [...new Set(kodKaynaklari.flatMap((k) =>
    [...yorumsuz(k.kaynak).matchAll(/renk\('(--[a-z0-9-]+)'\)/g)].map((m) => m[1])))];
  const tuvalEksik = TEMA_ADLARI.flatMap((a) => {
    const b = belirtecler(bloklar[a] && bloklar[a].govde);
    return tuvalBelirtecleri.filter((x) => !b.has(x)).map((x) => a + ':' + x);
  });
  ok('app.js`in tuvalde okudugu her belirtec CSS`te TANIMLI',
     tuvalBelirtecleri.length >= 3 && tuvalEksik.length === 0,
     tuvalEksik.join(' ') || tuvalBelirtecleri.join(' '));

  /* Hareket olculu: reduced-motion karsiligi VAR. */
  ok('prefers-reduced-motion karsiligi var (hareket kapanabiliyor)',
     /@media \(prefers-reduced-motion: reduce\)/.test(css) &&
     /animation-duration:\s*\.01ms\s*!important/.test(css));
  /* Sonsuz animasyon YALNIZCA DURUM GOSTERGELERINDE olabilir: canli
     akis noktasi ve acil durdurma noktasi. Olcum sayisinin oynamasi
     okunakligi bozar — ilk yazimda "en fazla bir tane" demistim, ama
     ikinci mesru gosterge gelince o kural yanlis yere kirmiziya dondu.
     Dogru olcut SAYI degil, HANGI SECICI. */
  /* 3D: `.kayit-nokta` — Canli basligindaki "kayit suruyor" gostergesi (durum, olcum
     sayisi degil). */
  const IZINLI_NABIZ = ['.rozet.acik .nokta', '.acil-nokta', '.kayit-nokta'];
  const nabizli = [...css.matchAll(/([^{}]+)\{[^{}]*animation:[^;]*infinite[^;]*;/g)]
    .map((m) => m[1].trim().split(/[\n,]/).pop().trim());
  ok('Sonsuz animasyon yalnizca durum gostergelerinde',
     nabizli.length > 0 && nabizli.every((s) => IZINLI_NABIZ.includes(s)),
     nabizli.join(' | '));
  ok('Olcum sayilarinda animasyon YOK (hane oynamasin)',
     !nabizli.some((s) => /\.deger|\.kpi-deger|\.skop-olcum-deger/.test(s)),
     nabizli.join(' | '));

  /* Olcum sayilari tabular: hane kaymasin. */
  ok('Olcum ve ikincil sayilar tabular-nums',
     /\.olcum \.deger\s*\{[^}]*tabular-nums/.test(css) &&
     /\.ikincil \.deger\s*\{[^}]*tabular-nums/.test(css));

  /* Tek CSS dosyasi: karttan her ek istek loop()`u blokluyor. */
  ok('Sayfa TEK stil dosyasi bagliyor', CSS_YOLLARI.length === 1,
     CSS_YOLLARI.map((p) => path.basename(p)).join(' '));

  /* Tasiyici seciciyle TASIYICILAR kaydi ortusmeli: ?demo ile tasiyici
     'demo' oluyordu ama menude karsiligi yoktu ve secici BOS gorunuyordu. */
  const menuSecenekleri = [...yorumsuz(htmlKaynak).matchAll(
    /<option value="(seri|akis|demo)"/g)].map((m) => m[1]);
  const T13 = vm.runInContext('TASIYICILAR', sandbox);
  ok('Her tasiyicinin menude bir secenegi var (bos secici yok)',
     Object.keys(T13).every((k) => menuSecenekleri.includes(k)),
     `menu: ${menuSecenekleri.join(' ')} | tasiyici: ${Object.keys(T13).join(' ')}`);
  ok('demo tasiyicisi HER ZAMAN destekli (olu dugme yok)',
     T13.demo.destekli() === true);
  ok('Menuden demo secilince sahte kart KURULUYOR',
     govdeIcinde(appKaynak, 'tasiyiciAdi', "this.demoVeri()"),
     'yoksa tasiyici degisir ama veri gelmez');

  /* 🔴 Headless render yakaladi: ?demo ile acilista demoVeri() hem
     mounted()'tan hem watch`tan cagriliyordu; ikisi de betigi beklerken
     gecti ve `sahte-kart.js` IKI KEZ indi -> "Identifier 'SahteKart' has
     already been declared" -> sayfanin o andan sonraki betikleri dustu.
     Kapi `await`ten ONCE kapanmali. */
  {
    const d = ornek();
    let inen = 0, kurulan = 0;
    d.betikYukle = async () => { inen++; };
    d.kaydet = () => {}; d.$nextTick = (f) => f && f();
    d.osiloOtomatik = () => {}; d.satirIsle = () => { kurulan++; };
    d.pilYokla = () => {};
    sandbox.SahteKart = {
      raporAralik: () => 200,
      dSatiri: () => ({ satir: 'D 1 0 0 0 0 0 96 0 0', w: 0 }),
      sinyaller: {}, komut: () => [],
    };
    SONRA.push(async () => {
      await Promise.all([d.demoVeri(), d.demoVeri()]);
      ok('demoVeri() IKI kez cagrilsa da betik BIR kez iniyor', inen === 1, `inen=${inen}`);
      ok('… ve akis bir kez kuruluyor (300 nokta, cift degil)',
         kurulan === 300, `satirIsle ${kurulan} kez`);
      delete sandbox.SahteKart;
    });
    /* 🔴 Headless render ikinci kusuru: `demoVeri()` once `tasiyiciAdi`yi
     'demo' yapip SONRA `bagli`yi aciyor; watch ondan sonra kosuyor ve
     acilan demo baglantisini "eski tasiyici" sanip KAPATIYORDU. Demo
     akisi ilk 300 noktadan sonra susuyor, rozet "bagli degil" diyordu.
     Bagli tasiyici artik acikca tutuluyor. */
  {
    const w = secenekler.watch.tasiyiciAdi;
    let kapanan = null;
    const T = vm.runInContext('TASIYICILAR', sandbox);
    const eskiKapat = T.demo.kapat;
    T.demo.kapat = async () => { kapanan = 'demo'; };
    const d = { ayarYaz() {}, kaydet() {}, bagli: true, bagliTasiyici: 'demo',
                demoVeri() { this.demoCagrildi = true; } };
    SONRA.push(async () => {
      await w.call(d, 'demo', 'seri');
      ok('demo kurulduktan sonra watch onu KAPATMIYOR (bagli kalir)',
         d.bagli === true && kapanan === null, `bagli=${d.bagli} kapanan=${kapanan}`);
      ok('… ve demoVeri ikinci kez cagrilmiyor', !d.demoCagrildi);

      const e2 = { ayarYaz() {}, kaydet() {}, bagli: true, bagliTasiyici: 'akis' };
      const eskiAkisKapat = T.akis.kapat;
      T.akis.kapat = async () => { kapanan = 'akis'; };
      await w.call(e2, 'seri', 'akis');
      ok('GERCEK tasiyici degisiminde ACIK olan kapaniyor',
         kapanan === 'akis' && e2.bagli === false && e2.bagliTasiyici === null);
      T.akis.kapat = eskiAkisKapat; T.demo.kapat = eskiKapat;
    });
  }
  ok('baglan() acik tasiyiciyi KAYDEDIYOR',
     govdeIcinde(appKaynak, 'baglan', 'this.bagliTasiyici = this.tasiyiciAdi'));
  ok('betikYukle ayni src`yi iki kez EKLEMIYOR',
       govdeIcinde(appKaynak, 'betikYukle', "querySelector('script[src=\"' + yol + '\"]')"),
       'const yeniden bildirimi SyntaxError verir');
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   14. TELEFON YERLESIMI + ACIL DURDURMA (B27 Asama 3)

   Iki sey civileniyor:
   (a) ACIL DURDURMA her gorunumde. Telefonda desarj surerken once dogru
       sekmeyi bulmak zorunda kalmak EMNIYET kusurudur. `p0` jeton ve
       parola istemeyen tek komut; serit de gorunumlerin DISINDA durmali,
       yoksa yalnizca acik sekmede gorunur.
   (b) Telefon kirilimi CSS'te var ve olcum kartlari orada yeniden
       diziliyor. "Telefonda basit surum" AYRI bir arayuz demek olurdu —
       bu proje arayuz ayrismasindan uc kez yandi; tek sablon, farkli
       yerlesim.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 14. Telefon yerlesimi + acil durdurma ---');
{
  const html = yorumsuz(htmlKaynak);
  const css = cssOku();

  /* (a) Acil serit: gorunumlerin DISINDA (ilk <main>'den once) ve
         kosulu "test calisiyor". */
  const acilIndeks = html.indexOf('class="acil"');
  const ilkMain = html.indexOf('<main ');
  ok('Acil durdurma seridi gorunumlerin DISINDA (her sekmede gorunur)',
     acilIndeks > 0 && ilkMain > 0 && acilIndeks < ilkMain,
     `acil@${acilIndeks} ilkMain@${ilkMain}`);
  ok('Acil serit YALNIZCA test calisirken gorunuyor',
     /v-if="pilDurum === 'CALISIYOR'"[\s\S]{0,120}class="acil"/.test(html) ||
     /class="acil"[\s\S]{0,120}v-if="pilDurum === 'CALISIYOR'"/.test(html));
  ok('Acil seritteki dugme `p0` gonderiyor (pilDurdurKomut)',
     /class="acil"[\s\S]{0,600}@click="pilDurdurKomut"/.test(html) &&
     govdeIcinde(appKaynak, 'pilDurdurKomut', "gonder('p0')"));
  /* Emniyet dugmesi ENGELLENMEMELI: `:disabled` konursa surucu olmayan
     oturumda ya da baglanti dalgalanmasinda durdurma kilitlenir. `p0`
     zaten jetonsuz gecen tek komut. */
  /* WIG (2026-10-02) yikici eylemlere iki asamali onay getirdi; p0 BILEREK disarida:
     deşarji kesen emniyet komutu TEK dokunusla ve aninda gitmeli. Her p0 dugmesi
     pilDurdurKomut'u DOGRUDAN cagirir ve govdesinde onay (onayIste/confirm) yok. */
  {
    const dogrudan = (html.match(/@click="pilDurdurKomut"/g) || []).length;
    const sarili = /onayIste\(\s*'(?:p0|pil[A-Za-z]*Dur[a-z]*)'/.test(html) || /onayIste\(\s*'(?:p0|pil[A-Za-z]*Dur[a-z]*)'/.test(appKaynak);
    const govde = (appKaynak.match(/pilDurdurKomut\(\)\s*\{([^}]*)\}/) || [])[1] || '';
    ok('[!] Emniyet: pil DURDUR (acil serit + Pil sekmesi) pilDurdurKomut\'u TEK tikla cagirir; p0 onaya sarilmaz, govdede onay yok',
       dogrudan >= 2 && !sarili && /gonder\('p0'\)/.test(govde) && !/onayIste|confirm\(|onay/.test(govde),
       `dogrudan=${dogrudan} sarili=${sarili} govde=${govde.trim()}`);
  }
  ok('Acil dugmede :disabled YOK (durdurma hicbir kosula bagli degil)',
     !/class="acil"[\s\S]{0,600}acil-dur[^>]*:disabled/.test(html));
  ok('Acil serit gorsel olarak uyari rengiyle ayirt ediliyor',
     /\.acil\s*\{[^}]*var\(--uyari\)/.test(css) &&
     /\.acil-dur\s*\{[^}]*var\(--uyari\)/.test(css));

  /* (b) Telefon kirilimi: olcum kartlari yeniden diziliyor ve cok dar
         ekranda tek sutuna donuyor. */
  const telefon = css.match(/@media \(max-width: 620px\)\s*\{([\s\S]*?)\n\}/);
  ok('Telefon kirilimi (<=620px) tanimli', !!telefon);
  if (telefon) {
    /* 3D (D2): dort okuma karti (V · A · W · Enerji) telefonda 2 x 2 — dordu de ilk
       ekranda. Eski uc kartta "guc tam genislik" kurali vardi; dort kartta 2 x 2. */
    const canliMain = html.match(/<main[^>]*v-show="gorunum === 'canli'"([\s\S]*?)<\/main>/);
    const kartlar = canliMain ? [...canliMain[1].matchAll(/class="olcum (v|i|w|e)"/g)].map((m) => m[1]) : [];
    ok('Telefonda dort okuma karti 2 x 2 (iki sutun)',
       /\.olcumler\s*\{[^}]*grid-template-columns:\s*1fr 1fr/.test(telefon[1])
       && kartlar.join('') === 'viwe', kartlar.join(' '));
  }
  ok('Cok dar ekranda (<=380px) olcumler tek sutuna donuyor',
     /@media \(max-width: 380px\)[\s\S]{0,200}grid-template-columns:\s*1fr;/.test(css));
  /* 3D (D1): <= 900 px serit CEKMECE. Kapaliyken `visibility: hidden` (yalniz gorunmez
     degil, SEKME ile de ulasilamaz); acikken gorunur; ust cubuk YALNIZ dar ekranda. */
  const dar = css.match(/@media \(max-width: 900px\)\s*\{([\s\S]*?)\n\}/);
  ok('[!] 3D: <=900 px serit cekmece — kapali: transform + visibility hidden, acik: gorunur; ust cubuk yalniz burada',
     !!dar && /\.serit\s*\{[^}]*transform:\s*translateX\(-100%\)[^}]*visibility:\s*hidden/.test(dar[1])
     && /\.cekmece-acik \.serit\s*\{[^}]*visibility:\s*visible/.test(dar[1])
     && /\.ust\s*\{[^}]*display:\s*flex/.test(dar[1])
     && /(^|\n)\.ust\s*\{\s*display:\s*none;\s*\}/.test(css.replace(/\/\*[\s\S]*?\*\//g, '')));

  /* Ust serit sadelesti: tasiyici secici ve adres AYARLAR'da. 3D: baglanti kumesi
     iki yerde (dar ekranin ust cubugu + sol serit), CSS her genislikte birini gosterir. */
  const ust = html.match(/<header class="ust">([\s\S]*?)<\/header>/);
  const serit = html.match(/<aside id="serit" class="serit"[^>]*>([\s\S]*?)<\/aside>/);
  ok('Ust cubukta ve seritte tasiyici secici ve adres kutusu YOK', !!ust && !!serit &&
     [ust[1], serit[1]].every((b) => !b.includes('v-model="tasiyiciAdi"') && !b.includes('v-model="kartTaban"')));
  ok('Ust cubukta ve seritte durum rozeti ve birincil eylem VAR', !!ust && !!serit &&
     [ust[1], serit[1]].every((b) => b.includes('class="rozet"') && b.includes('@click="baglan"')));
  const ayarBlok = html.match(/v-show="gorunum === 'ayar'"([\s\S]*?)<\/main>/);
  ok('Tasiyici secici ve kart adresi AYARLAR gorunumunde', !!ayarBlok &&
     ayarBlok[1].includes('v-model="tasiyiciAdi"') &&
     ayarBlok[1].includes('v-model="kartTaban"'));

  /* Telefonda `.local` tuzagi YAZILI olmali: Android mDNS cozmuyor ve
     kullanici "telefondan giremiyorum" diye takildi (2026-09-12). */
  ok('Baglanti karti Android `.local` tuzagini soyluyor',
     /Android/.test(html) && /\.local/.test(html) && /IP adresini/.test(html));
}

/* ═══════════════════════════════════════════════════════════════════════
   15. BUTCE VE DAYANIKLILIK (B27 Asama 4)

   Plandaki iki sayi (gzip < 250 KB, dosya <= 8) BELGEDE yaziyordu ama
   hicbir sey onlari sinamiyordu — yani butce degil temenniydi. Artik
   `_fs.json` (karta GERCEKTEN yazilan goruntunun kunyesi) uzerinden
   olculuyor.

   Dayaniklilik: kart yeniden baslarken sayfa acilirsa betiklerden biri
   gelmiyor ve ekranda ham `{{ }}` kaliyordu. `v-cloak` onu GIZLIYOR ama
   yerine bir sey KOYMUYOR — kullaniciya hicbir sey soylemeyen bos sayfa.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 15. Butce ve dayaniklilik ---');
{
  const html = yorumsuz(htmlKaynak);
  const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
  ok('LittleFS kunyesi (_fs.json) var', fs.existsSync(kunyeYolu));
  if (fs.existsSync(kunyeYolu)) {
    const kunye = JSON.parse(fs.readFileSync(kunyeYolu, 'utf8'));
    /* 3D — BUTCE KARARI (alt proje 3 yoneticisi, 2026-10-02): B27 A4'un 250 KB'si
       (3C'de goruntunun %97'si) artik ACILISTA INEN dosyalara uygulaniyor: index.html +
       sayfanin istedigi varliklar + app.js'in STATIK ice aktarma agaci. Ekran ilk acilinca
       inen moduller (dinamik `import()`; 3C Kayitlar) haric. Goruntunun TAMAMI P5 <= 600 KB
       (sim3_web.py 6m). Acilis kumesi ELLE listelenmiyor — asagida `acilis` kumesinden
       (html referanslari + iceAktarmaGrafigi) TURETILIYOR; yeni bir statik import
       kendiliginden sayilir. Bayt `_fs.json`dan (karta GERCEKTEN yazilan gzip boyu). */
    const BUTCE = 250 * 1024;
    const acilisK = new Set(['index.html']);
    for (const m of html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)) {
      if (!/^(https?:|data:|#|mailto:)/.test(m[1])) acilisK.add(m[1]);
    }
    for (const g of iceAktarmaGrafigi()) acilisK.add(g.goruntu);
    const baytlar = kunye.bayt || {};
    const topla = (k) => [...k].reduce((n, a) => n + (Number.isFinite(baytlar[a]) ? baytlar[a] : NaN), 0);
    const acilisBayt = topla(acilisK);
    ok(`[!] 3D: ACILIS kumesi gzip butcesi: ${acilisBayt} B <= ${BUTCE} B (statik agac; dinamik import haric)`,
       acilisBayt > 0 && acilisBayt <= BUTCE,
       `%${(100 * acilisBayt / BUTCE).toFixed(0)} dolu · ${acilisK.size} dosya · goruntu toplami ${kunye.icerik_bayt} B`
       + (kunye.bayt ? '' : ' — _fs.json`da dosya baytlari yok: python arayuz-uret.py'));
    /* 3D: Canli VARSAYILAN ekran ve grafigi (ekran/canli.js + ortak/grafik.js agaci) ekran
       ilk gorunur olunca `import()` ile iniyor — yani Canli ile acilan sayfada O DA aciliste
       iniyor. Gizlenmesin: o zincir de bu butceye SAYILIYOR (yoneticinin kuralindan SIKI). */
    const canliYol = govdeIcinde(appKaynak, 'canliYukle', "import('./ekran/canli.js')")
      && vm.runInContext('GORUNUM_VARSAYILAN', sandbox) === 'canli' ? path.join(ARAYUZ, 'ekran', 'canli.js') : null;
    const canliK = new Set(canliYol ? ['ekran/canli.js', ...iceAktarmaGrafigi(canliYol).map((g) => g.goruntu)] : []);
    for (const a of acilisK) canliK.delete(a);
    const canliBayt = acilisBayt + topla(canliK);
    ok(`[!] 3D: Canli ile acilis (statik + Canli grafik zinciri) gzip <= ${BUTCE} B`,
       canliK.size >= 2 && canliBayt <= BUTCE,
       `${canliBayt} B = %${(100 * canliBayt / BUTCE).toFixed(0)} · zincir: ${[...canliK].join(' ')}`);
    ok('[!] 3D: Canli ile acilista istenen TOPLAM dosya <= 12 (statik <= 8 + Canli zinciri <= 4)',
       canliK.size >= 2 && canliK.size <= 4 && acilisK.size + canliK.size <= 12,
       `${acilisK.size} + ${canliK.size}`);
    /* Dosya sayisi: her dosya karta ayri bir HTTP istegi demek ve her
       istek olcum dongusunu blokluyor (kartta olculdu: 6.5 KB'lik
       style.css bile 34 ms).
       3A: olculen sey ARTIK "goruntudeki dosya" degil "ACILISTA ISTENEN
       dosya". Goruntu `/ortak/*.js`yi de tasiyor (P4) ama onlar ancak bir
       ekran `import` edince iniyor. Sayilan: index.html + yerel varliklari +
       app.js'in (gecisli) statik ice aktarmalari. Eski hali VARLIKLAR'daki
       tirnaklari sayiyordu — goruntu 20 dosyayken "6" derdi. */
    const varliklar = fs.readFileSync(path.join(KOK, 'uretim', 'arayuz-uret.py'), 'utf8')
      .match(/VARLIKLAR = \[([\s\S]*?)\]/);
    const acilis = new Set(['index.html']);
    for (const m of html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)) {
      if (!/^(https?:|data:|#|mailto:)/.test(m[1])) acilis.add(m[1]);
    }
    for (const g of iceAktarmaGrafigi()) acilis.add(g.goruntu);
    ok('Acilista istenen dosya sayisi <= 8 (index + varliklar + statik import)',
       acilis.size > 1 && acilis.size <= 8, `${acilis.size}: ${[...acilis].join(' ')}`);
    /* Sayfanin istedigi her yerel varlik goruntude OLMALI: biri eksikse
       kart 404 doner ve arayuz acilmaz (B22.0'in ta kendisi). */
    const istenen = [...html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)]
      .map((m) => m[1]).filter((u) => !/^(https?:|data:|#|mailto:)/.test(u));
    const yazilan = varliklar ? [...varliklar[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]) : [];
    const eksik = istenen.filter((u) => !yazilan.includes(u));
    ok('Sayfanin istedigi her varlik LittleFS goruntusunde',
       eksik.length === 0, eksik.join(' ') || istenen.join(' '));
    /* 3A: app.js'in (gecisli) ice aktardigi her modul de goruntude olmali —
       biri eksikse kart 404 doner ve modul grafigi HIC yuklenmez. Kunye
       (`_fs.json`) GERCEKTEN uretilen goruntunun listesi. */
    const goruntude = new Set(Object.keys(kunye.kaynak || {}));
    const ithal = iceAktarmaGrafigi();
    const ithalEksik = ithal.filter((g) => !goruntude.has(g.goruntu)).map((g) => g.goruntu);
    ok('app.js`in ice aktardigi her modul LittleFS goruntusunde',
       ithal.length >= 1 && ithalEksik.length === 0,
       ithalEksik.join(' ') || ithal.map((g) => g.goruntu).join(' '));
  }

  /* Dayaniklilik: acilmama durumu. 3A: app.js `type="module"`; `onerror`
     modulun kendisi YA DA ice aktardigi bir dosya gelmezse tetikleniyor. */
  ok('Betik `onerror` ile acilmama durumu yakalaniyor',
     /<script src="vendor\/vue\.global\.prod\.js" onerror="arayuzHata\(/.test(html) &&
     /<script type="module" src="app\.js" onerror="arayuzHata\(/.test(html));
  ok('Zaman asimi kapisi da var (betik indi ama Vue baslamadi)',
     /setTimeout\([\s\S]{0,400}hasAttribute\('v-cloak'\)/.test(html));
  ok('Acilmama kutusu VARSAYILAN OLARAK gizli (hidden)',
     /<div id="acilmadi" hidden/.test(html));
  ok('Acilmama kutusunda YENILE eylemi var',
     /id="acilmadi"[\s\S]{0,400}location\.reload\(\)/.test(html));

  /* 3F (PL4): B27 A4'un "bosta 10 s, testte 2 s" yoklamasi KALKTI — surekli yoklama YALNIZ
     (bagli ∧ Pil sekmesi ∧ belge gorunur ∧ test suruyor). Davranis bolum 27'de. */
  const u = ornek();
  u.bagli = true; u.pilDurum = 'BEKLEMEDE'; u.gorunum = 'canli';
  const bos = u.pilYoklamaAcik;
  u.pilDurum = 'CALISIYOR';
  const baskaSekme = u.pilYoklamaAcik;
  u.gorunum = 'pil';
  const acik = u.pilYoklamaAcik;
  u.sayfaGorunur = false;
  const gizli = u.pilYoklamaAcik;
  ok('[!] PL4: bosta / baska sekmede / belge gizliyken pil YOKLANMIYOR; yalniz Pil sekmesinde test surerken',
     bos === false && baskaSekme === false && acik === true && gizli === false && u.pilYoklamaAralik === undefined,
     JSON.stringify({ bos, baskaSekme, acik, gizli }));
}

/* ═══════════════════════════════════════════════════════════════════════
   16. SKOP ARSIVI — GERIYE DONUK KAYIT (B35)

   🔴 BU BOLUM BIR CANLI KUSURDAN DOGDU. `TasiyiciAkis` (hem kart hem
      KOPRU bu tasiyiciyi kullaniyor) `skop: 'ikili'` ilan edip
      `/skop.bin` cekiyordu; sayfa kopruden geldiginde o istek KOPRUYE
      gidiyor ve kopruda boyle bir uc YOKTU -> 404. Yani osiloskop, tam
      da kullanicinin "sekilleri gormek + kayit almak" istedigi kipte
      olu bir dugmeydi. Zincir 18/18 yesilken.

   Buradaki iddialar iki seyi koruyor:
     1. TEK IKILI COZUCU — canli yakalama ile arsivden acilan kayit AYNI
        koddan gecmeli; iki cozucu olsaydi biri sessizce baska bir dalga
        cizerdi (bu projenin uc kez yandigi ayrisma sinifi).
     2. KULLANICI NEYE BAKTIGINI BILMELI — arsiv kaydi cizilirken tuval
        bunu SOYLEMELI, yoksa gecmis bir dalgaya bakip "kart su anda
        bunu olcuyor" sanilir.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 16. Skop arsivi (geriye donuk kayit) ---');
{
  const html = yorumsuz(htmlKaynak);

  ok('Arsiv listesi ucu cekiliyor (/skop/liste)',
     govdeIcinde(appKaynak, 'skopKayitlariYukle', '/skop/liste'));
  ok('Tek kayit ucu cekiliyor (/skop/al)',
     govdeIcinde(appKaynak, 'skopKayitAc', '/skop/al'));
  /* [!] ASIL IDDIA: arsiv kaydi CANLI YOLLA AYNI cozucuden geciyor. */
  ok('[!] Arsiv kaydi CANLI ile AYNI ikili cozucuden geciyor',
     govdeIcinde(appKaynak, 'skopKayitAc', 'this.skopIkiliCoz(') &&
     govdeIcinde(appKaynak, 'skopIkiliAl', 'this.skopIkiliCoz('),
     'iki cozucu olsaydi eski kayit baska cizilirdi');

  /* Kopru olup olmadigi `/durum` ucundan anlasiliyor — kart o ucu HIC
     acmiyor, yani yanit gelmesi zaten koprunun imzasi. */
  ok('Kopru varligi /durum ucundan anlasiliyor',
     govdeIcinde(appKaynak, 'kopruYokla', '/durum') &&
     govdeIcinde(appKaynak, 'kopruYokla', 'skop_arsiv'));
  ok('Kopru yoklamasi baglanmayi BLOKLAMIYOR (arsiv ek ozellik)',
     govdeIcinde(appKaynak, 'baglan', 'this.kopruYokla();') &&
     !govdeIcinde(appKaynak, 'baglan', 'await this.kopruYokla()'),
     'yoklama coksun, olcum yine aksin');

  /* [!] Olu dugme YOK: arsiv bolumu yalnizca kopru kipinde ciziliyor.
     DEVIR 4.15 tam olarak bunun tersiydi — calismayan bir dugme. */
  ok('[!] Kayit bolumu YALNIZCA kopru kipinde ciziliyor',
     /<section class="kart" v-if="skopArsivVar">/.test(html),
     'kart dogrudan bagliyken kayit yok — olu dugme gosterilmiyor');

  /* [!] Canli mi arsiv mi: tuvalde SOYLENMELI. */
  ok('[!] Arsiv kaydi cizilirken tuvalde ayirt edici serit var',
     /v-if="skopAcikKayit"[\s\S]{0,400}arsiv-serit|arsiv-serit[\s\S]{0,200}skopAcikKayit/
       .test(html) && html.includes('canlı değil'),
     'yoksa gecmis dalga canli sanilir');
  ok('Serit CANLIYA DONME yolu sunuyor',
     /arsiv-serit[\s\S]{0,600}osiloYakala/.test(html));

  /* Canli yakalama arsiv isaretini KALDIRMALI, yoksa serit yeni dalga
     cizildikten sonra da "arsiv" demeye devam ederdi. */
  ok('[!] Canli yakalama arsiv isaretini kaldiriyor',
     govdeIcinde(appKaynak, 'osiloYakala', 'this.skopAcikKayit = null') &&
     govdeIcinde(appKaynak, 'osiloOtomatik', 'this.skopAcikKayit = null'),
     'yoksa canli dalga "arsiv" etiketiyle gosterilirdi');
  /* Arsiv kaydi acilinca SUREKLI kip durmali: yoksa bir sonraki tur
     kaydin ustune canli dalga ciziyor. */
  ok('[!] Arsiv kaydi acilinca surekli yakalama duruyor',
     govdeIcinde(appKaynak, 'skopKayitAc', 'if (this.surekli) this.surekliDegis()'),
     'yoksa kayit aninda canli dalgayla degisirdi');
  /* Surekli kipte liste tazelenmiyor: saniyede birkac yakalamada her
     turda liste cekmek kopruyu bosuna mesgul eder. */
  ok('Surekli kipte arsiv listesi tazelenmiyor',
     govdeIcinde(appKaynak, 'skopListeTazeleGerekirse', '!this.surekli'));

  /* Kirpik kayit SESSIZ kalmiyor — eksik dalga "olculmus" gorunmemeli. */
  ok('[!] Kirpik kayit listede isaretleniyor',
     /v-if="!k\.tam"[\s\S]{0,120}kırpık/.test(html),
     'eksik dalga sessizce tam gorunmemeli');
  /* ⚠ `.uyari` bu projede emniyet uyarisinin KUTU stili; rozete
     uygulaninca rozet butona benziyor (tarayici goruntusunde yakalandi).
     Kayit rozetleri kendi degistiricisini kullaniyor. */
  ok('Kayit rozetleri emniyet-uyarisi sinifini KULLANMIYOR',
     !/class="kayit-etiket[^"]*\buyari\b/.test(html) &&
     !/kayit-etiket"[^>]*:class="\{ uyari/.test(html),
     'emniyet uyarisi stili rozete bulasmamali');
  /* Zaman damgasi DUVAR SAATI DEGIL; oyle gosterilip yanlis okunmasin. */
  ok('Zaman damgasinin ne oldugu yaziyor (duvar saati degil)',
     html.includes('köprü açıldıktan') &&
     govdeIcinde(appKaynak, 'skopZaman', 'Math.floor(ms / 1000)'));

  /* 🔴 KOPRUDE ASCII, KARTTA IKILI — AYNI VERIYI IKI KEZ TASIMA.
     Kopru karta USB'den bagli ve dokumu ZATEN seri porttan almak
     zorunda (arsive dusmesinin tek yolu; kartta ikili-seri dokum yok).
     O dokum SSE'den tarayiciya da geldigine gore ayrica `/skop.bin`
     cekmek ayni dalgayi ikinci kez tasimak ve IKI KEZ cizmek olurdu —
     B22.5 tam da bundan kaciniyordu. */
  ok('[!] Koprude ASCII yolu, kartta ikili yol seciliyor',
     govdeIcinde(appKaynak, 'osiloYakala', 'if (this.skopArsivVar) {') &&
     govdeIcinde(appKaynak, 'osiloYakala', "yetenek.skop === 'ikili'"),
     'koprude tB + /skop.bin ayni dalgayi ikinci kez tasirdi');
  /* Liste tazeleme TEK tamamlanma noktasinda: `skopIkiliAl` icinde
     kalsaydi koprudeki ASCII yakalamalari listeye hic dusmezdi. */
  ok('[!] Liste tazeleme TEK tamamlanma noktasinda (osiloBitir)',
     govdeIcinde(appKaynak, 'osiloBitir', 'skopListeTazeleGerekirse()') &&
     !govdeIcinde(appKaynak, 'skopIkiliAl', 'skopListeTazeleGerekirse'),
     'yoksa koprudeki ASCII yakalamalari listeye dusmezdi');

  /* 🔴 SUREKLI KIP: onceki yakalama bitmeden yenisi ISTENMEMELI.
     Eski tur kosulsuzdu (her 500 ms bir yakalama) — kartta dogrudan
     sorun degildi ama koprude dokum SERI PORTTAN geciyor ve 4000 ornek
     ~1.8 s suruyor. Kosulsuz tur kuyruk biriktirir, bloklar birbirini
     keser ve arsiv KIRPIK kayitlarla dolar. */
  ok('[!] Surekli kip onceki yakalamayi BEKLIYOR',
     govdeIcinde(appKaynak, 'surekliTur', 'if (this.osiloBekliyor) {'),
     'yoksa koprude komut kuyrugu birikir, bloklar birbirini keser');
  {
    /* Davranis sinamasi: mesgulken `osiloYakala` CAGRILMAMALI. */
    const v = ornek();
    let cagri = 0;
    v.osiloYakala = () => { cagri++; };
    v.surekli = true;
    v.osiloBekliyor = true;
    v.surekliZaman = null;
    const eskiST = globalThis.setTimeout;
    globalThis.setTimeout = () => 0;          // tur zincirini kurma
    try {
      v.surekliTur();
      ok('[!] Mesgulken yeni yakalama ISTENMIYOR', cagri === 0, `${cagri} cagri`);
      v.osiloBekliyor = false;
      v.surekliTur();
      ok('Bos kalinca yakalama ISTENIYOR', cagri === 1, `${cagri} cagri`);
    } finally {
      globalThis.setTimeout = eskiST;
    }
  }

  /* Varsayilan durum: kopru yokken bolum kapali ve liste bos. */
  const u = ornek();
  ok('Varsayilan: arsiv KAPALI (kart dogrudan bagliyken)',
     u.skopArsivVar === false && u.skopKayitlar.length === 0
     && u.skopAcikKayit === null);
}

/* ═══════════════════════════════════════════════════════════════════════
   17. SKOP GERILIM EKSENI KALIBRASYONU (B36)

   B34 kartta olctu: skopun gerilim ekseni ham kodu SABIT bir carpanla
   ceviriyordu ve bu varsayim tutmuyordu. Cipin eFuse egrisi `CT` ile
   geliyor, duzeltme CIZIM ANINDA uygulaniyor.

   🔴 EN ONEMLI IDDIA: ceviri TEK NOKTADAN geciyor. Eskiden
      `kod * voltAdim - voltOfset` DORT ayri yerde yaziliydi (tetik
      seviyesi, tepe degeri, dikey olcek, cizim dongusu). Duzeltme
      eklenince dordunun de degismesi gerekirdi; biri unutulsa izgara
      etiketi bir sey, iz baska sey gosterirdi ve hata SESSIZ olurdu.

   ⚠ Buradaki tablo GERCEK KARTTAN alindi (2026-09-12). Uydurulsaydi
     test kendi uydurmasini dogrulardi.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 17. Skop gerilim ekseni kalibrasyonu ---');
{
  const html = yorumsuz(htmlKaynak);
  const CT_SATIR = 'CT 17 oran=38.037037 ofset=63.530090 tavan_mv=3100.0'
    + ' 0:0 256:229 512:452 768:667 1024:883 1280:1095 1536:1309'
    + ' 1792:1524 2048:1739 2304:1954 2560:2165 2816:2372 3072:2568'
    + ' 3328:2750 3584:2914 3840:3053 4095:3160';

  const v = ornek();
  v.satirIsle(CT_SATIR);
  ok('CT satiri ayristiriliyor',
     !!v.skopKal && v.skopKal.kod.length === 17,
     v.skopKal ? `${v.skopKal.kod.length} nokta` : 'tablo yok');
  ok('Metaveri (oran/ofset/tavan) okunuyor',
     v.skopKal && Math.abs(v.skopKal.oran - 38.037037) < 1e-4
     && Math.abs(v.skopKal.tavanMv - 3100) < 1e-3);

  /* Tablo noktalarinda aradeger TAM deger vermeli. */
  ok('Tablo noktasinda aradeger tam',
     Math.abs(v.kalMv(2048) - 1739) < 1e-6
     && Math.abs(v.kalMv(0) - 0) < 1e-6,
     `${v.kalMv(2048)} / ${v.kalMv(0)}`);
  /* Iki nokta ARASINDA dogrusal. */
  ok('Noktalar arasi dogrusal aradeger',
     Math.abs(v.kalMv(2176) - (1739 + 1954) / 2) < 1e-6,
     String(v.kalMv(2176)));
  /* 🔴 Tablo disi KIRPILMIYOR, uzatiliyor: kirpilsaydi doyuma giren bir
     sinyal DUZ bir cizgi gibi gorunur ve kirpildigi anlasilmazdi. */
  ok('[!] Tablo disi kod KIRPILMIYOR (uzatiliyor)',
     v.kalMv(4500) > v.kalMv(4095),
     `kod 4500 -> ${v.kalMv(4500).toFixed(1)} mV`);

  /* Kalibreli cevirinin GERCEK sayisi. Kart oran=38.037, ofset=63.530
     bildiriyor; kod 2048 -> 1739 mV -> 1.739*38.037 - 63.530 V. */
  {
    const u = ornek();
    u.satirIsle(CT_SATIR);
    u.osilo = { voltAdim: 3.10 / 4096 * 38.03703704, voltOfset: 63.530090,
                veri: [2048] };
    const beklenen = 1739 / 1000 * 38.037037 - 63.530090;
    ok('[!] Kalibreli kod->volt cevirisi DOGRU sayiyi veriyor',
       Math.abs(u.kodVolt(2048) - beklenen) < 1e-4,
       `${u.kodVolt(2048).toFixed(4)} V (beklenen ${beklenen.toFixed(4)})`);

    /* Duzeltmesiz deger FARKLI olmali — aksi halde tablo hicbir sey
       yapmiyor demektir ve "kalibre" etiketi bos bir vaat olurdu. */
    const w = ornek();
    w.osilo = u.osilo;                      // ayni yakalama, tablo YOK
    const fark = Math.abs(u.kodVolt(2048) - w.kodVolt(2048));
    ok('[!] Duzeltme GERCEKTEN bir sey degistiriyor',
       fark > 1.0, `${fark.toFixed(3)} V fark (kod 2048)`);
    /* Kartta olculen buyukluk: kod 2048'de +7.19 V (bkz. DEVIR B36). */
    ok('Fark kartta olculen buyuklukte (+-%10)',
       Math.abs(fark - 7.189) < 0.72, `${fark.toFixed(3)} V vs 7.189 V`);
  }

  /* 🔴 TEK CEVIRI NOKTASI — dort cagri yeri de `kodVolt` kullaniyor. */
  ok('[!] Tetik seviyesi `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'esikVolt', 'this.kodVolt(this.skopEsik)'));
  ok('[!] Tepe degeri `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'osiloTepe', 'this.kodVolt('));
  ok('[!] Cizim dongusu ve dikey olcek `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'osiloCiz', 'this.kodVolt(hmin)')
     && govdeIcinde(appKaynak, 'osiloCiz', 'this.kodVolt(v)'),
     'izgara etiketi ile iz AYNI cevirimden gelmeli');
  ok('Cizimde artik ham `voltAdim` carpimi KALMADI',
     !/\bveri\[i\]\s*\*\s*voltAdim/.test(appKaynak)
     && !govdeIcinde(appKaynak, 'osiloCiz', '* voltAdim'),
     'ikinci bir ceviri yolu kalsaydi ayrisirdi');

  /* Bozuk / eksik tablo SESSIZCE kullanilmamali. */
  {
    const z = ornek();
    z.satirIsle('CT 0 kaynak=YOK');
    ok('[!] `CT 0 kaynak=YOK` tabloyu KURMUYOR', z.skopKal === null);
    /* 🔴 Bozuk tablo SESSIZCE kullanilmamali. Onceki hali
       `y.skopKal === null || uzunluklar esit` idi ve MUTASYON KACTI:
       denetim silinince de gecen bir totolojiydi. Simdi her bozuk bicim
       AYRI AYRI reddediliyor ve eksen ESKI yola dusuyor. */
    const bozuklar = [
      ['oran YOK',        'CT 3 0:0 256:229 512:452'],
      ['tek nokta',       'CT 1 oran=38.0 0:0'],
      ['sayi degil (NaN)', 'CT 3 oran=38.0 0:0 256:abc 512:452'],
      ['oran NaN',        'CT 3 oran=elma 0:0 256:229 512:452'],
    ];
    for (const [ad, satir] of bozuklar) {
      const y = ornek();
      y.satirIsle(satir);
      ok(`[!] Bozuk tablo REDDEDILIYOR: ${ad}`, y.skopKal === null,
         JSON.stringify(y.skopKal));
    }
    /* Reddedilince eksen duzeltmesiz yola DUSMELI — yarim bir tabloyla
       cizmek yerine eski, bilinen davranis. */
    {
      const y = ornek();
      y.osilo = { voltAdim: 3.10 / 4096 * 38.03703704, voltOfset: 63.530090,
                  veri: [2048] };
      const ham = y.kodVolt(2048);
      y.satirIsle('CT 3 oran=38.0 0:0 256:abc 512:452');
      ok('[!] Bozuk tablodan sonra eksen ESKI yola dusuyor',
         Math.abs(y.kodVolt(2048) - ham) < 1e-9,
         `${y.kodVolt(2048).toFixed(4)} vs ${ham.toFixed(4)}`);
    }
  }

  /* 🔴 SUSMUYORUZ: eksenin kalibre olup olmadigi EKRANDA yaziyor.
     Yazmasaydi duzeltmesiz bir eksen "olculmus" gorunur ve sayilar
     sessizce yanlis okunurdu (B34: girisde 9 V'a varan sapma). */
  ok('[!] Eksenin kalibre olup olmadigi EKRANDA yaziyor',
     /v-if="skopKal"[\s\S]{0,200}eksen kalibre/.test(html) &&
     /v-else[\s\S]{0,200}eksen HAM/.test(html),
     'duzeltmesiz eksen "kalibre" sanilmamali');
  ok('Tablo yokken SEBEBI ve buyuklugu yaziliyor',
     /v-if="!skopKal"[\s\S]{0,400}9 V/.test(html),
     '"ham" demek yetmez — ne kadar saptigi soylenmeli');

  /* Sahte kart GERCEK kartin protokolunu konusmali. */
  ok('[!] Sahte kart da `CT` cevapliyor (demo gercek yoldan kosuyor)',
     /CT 17 oran=/.test(fs.readFileSync(
       path.join(KOK, 'arayuz3', 'sahte-kart.js'), 'utf8')),
     'ayrisirsa demo arayuzu gercek yolundan sinamaz');
}

/* ═══════════════════════════════════════════════════════════════════════
   18. HIZLI YOL OLCEKLEMESI KALIBRE MI (B39)

   Dogrusal ADC modeli sifir giriste -6.9 V / -397 mA ofset veriyordu ve
   `guc_olc` ortalamayi CIKARMADIGI icin bu dogrudan P, Vrms ve PF'ye
   giriyordu (1 W direncsel yukte P 3.56 W, PF 0.77). Firmware artik
   eFuse tablosuyla olcekliyor ve `W` satirinin 11. alaninda bunu
   SOYLUYOR. Arayuz susmamali.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 18. Hizli yol olceklemesi kalibre mi ---');
{
  const html = yorumsuz(htmlKaynak);
  const a = ornek();
  a.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313 1');
  ok('[!] `W` 11. alan 1 -> kalibre', a.hizli && a.hizli.kal === true,
     JSON.stringify(a.hizli && a.hizli.kal));
  const b = ornek();
  b.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313 0');
  ok('[!] `W` 11. alan 0 -> HAM (kalibre SANILMIYOR)', b.hizli && b.hizli.kal === false);
  const c = ornek();
  c.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313');
  ok('[!] eski 10 alanli `W` hala ayristiriliyor ama kal=BILINMIYOR (null)',
     c.hizli && c.hizli.kal === null && Math.abs(c.hizli.p - 0.36314) < 1e-9,
     'eski firmware bilinmiyor demek; "kalibre" sanmak YANLIS olurdu');
  ok('[!] Ekranda uc durum da ayri yaziyor (kalibre / HAM / bilinmiyor)',
     /hizli\.kal === true[\s\S]{0,160}olçekleme kalibre|hizli\.kal === true[\s\S]{0,160}ölçekleme kalibre/.test(html)
     && /hizli\.kal === false[\s\S]{0,160}ölçekleme HAM/.test(html)
     && /ölçekleme bilinmiyor/.test(html));
  ok('Kalibresizken ofsetin BUYUKLUGU yaziyor',
     /hizli\.kal !== true[\s\S]{0,200}-6\.9 V/.test(html),
     '"ham" demek yetmez — ne kadar yanlis oldugu soylenmeli');
  ok('Sifir kalibrasyonunun HALA gerektigi yaziyor',
     /sıfır[\s\S]{0,20}kalibrasyonu/.test(html),
     'eFuse duzeltmesi on ucun sifir ofsetini gidermez');
}

/* ═══════════════════════════════════════════════════════════════════════
   19. SKOP DOKUMU OLCUMLE IC ICE (B40)

   Kart dokumu olcum dongusunu bloklamamak icin turlara boluyor; aradaki
   `D`/`K` satirlari dokumun ICINE dusuyor (kartta goruldu). Eskiden
   ayristirici BUTUN satirlari ornek sayiyordu.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 19. Skop dokumu olcumle ic ice ---');
{
  const u = ornek();
  u.osiloBitir = function () { this.bitti = this.osiloTopla; this.osiloTopla = null; };
  u.satirIsle('S2 20 1000 0.028788 0 100 0 1 63.530090');
  u.satirIsle('M f=0.000 T=0.000000000 Vpp=1.0000 Vmax=1.0 Vmin=0.0 Vort=0.5 Vrms=0.5 Vac=0.1 duty=0.00 tr=0 tf=0 n=0');
  u.satirIsle('1 2 3 4 5 6 7 8 9 10');
  u.satirIsle('D 12.3456 0.891234 10.99881 1234.5678 0.3429355 3600000 133 0');
  u.satirIsle('K 0 2603 0');
  u.satirIsle('11 12 13 14 15 16 17 18 19 20');
  const beklenen = Array.from({ length: 20 }, (_, i) => i + 1);
  const veri = u.bitti ? u.bitti.veri : (u.osiloTopla ? u.osiloTopla.veri : []);
  ok('[!] Araya giren D/K satiri dalgaya ORNEK olarak girmiyor',
     JSON.stringify(veri) === JSON.stringify(beklenen),
     JSON.stringify(veri));
  ok('[!] Araya giren D satiri olcum gostergesine YINE ulasiyor',
     Math.abs(u.volt - 12.3456) < 1e-6, String(u.volt));

  /* WiFi: sabit 400 ms bekleme kaldirildi, onay satiri tetikliyor. */
  ok('[!] `tB` sonrasi sabit gecikmeli cekis YOK',
     !govdeIcinde(appKaynak, 'osiloYakala', 'setTimeout(() => this.skopIkiliAl()'),
     'tb7 ve ustunde yakalama 400 ms\'den uzun -> /skop.bin 503');
  const v = ornek();
  let cekildi = 0;
  v.skopIkiliAl = () => { cekildi++; };
  v.skopIkiliBekle = true;
  v.satirIsle('* skop yakalandi (ikili): 833 ornek @ 83333 Hz — /skop.bin');
  ok('[!] Onay satiri GELINCE govde cekiliyor', cekildi === 1, String(cekildi));
  v.satirIsle('* skop yakalandi (ikili): 833 ornek @ 83333 Hz — /skop.bin');
  ok('Beklenmeyen ikinci onay IKINCI cekis yapmiyor', cekildi === 1, String(cekildi));
  const y = ornek();
  let c2 = 0;
  y.skopIkiliAl = () => { c2++; };
  y.skopIkiliBekle = true;
  y.satirIsle('! tetiklenemedi');
  y.satirIsle('* skop yakalandi (ikili): 1 ornek @ 1 Hz — /skop.bin');
  ok('`!` satiri bekleyen ikili cekisi IPTAL ediyor', c2 === 0 && y.skopIkiliBekle === false);
}

/* ═══════════════════════════════════════════════════════════════════════
   20. IKILI YOLDA OLCUM SATIRI (B43)

   WiFi'deki (tB + /skop.bin) yakalamalarda `olcum` hep null'du: frekans,
   Vpp, duty satiri HIC cikmiyordu (panelde goruldu). Kart artik `M`yi
   onay satirindan hemen ONCE basiyor; arayuz onu o yakalamaya bagliyor.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 20. Ikili yolda olcum satiri (B43) ---');
{
  const M = 'M f=996.806 T=0.001003204 Vpp=4.6640 Vmax=0.7320 Vmin=-3.9320 '
          + 'Vort=-1.7390 Vrms=2.3000 Vac=1.5500 duty=45.88 tr=0.000540963 '
          + 'tf=0.000346482 n=8';
  const ONAY = '* skop yakalandi (ikili): 833 ornek @ 83333 Hz — /skop.bin';
  function skopBin(adet) {
    const b = new ArrayBuffer(32 + adet * 2);
    const d = new DataView(b);
    d.setUint8(0, 0x53); d.setUint8(1, 0x33); d.setUint8(2, 0x42); d.setUint8(3, 1);
    d.setUint16(4, adet, true); d.setUint32(8, 83333, true);
    d.setFloat32(12, 0.028788, true); d.setFloat32(16, 63.53009, true);
    d.setUint32(20, 1000, true); d.setUint16(24, 83, true);
    d.setUint8(26, 0); d.setUint8(27, 1);
    for (let i = 0; i < adet; i++) d.setUint16(32 + i * 2, 1900 + (i % 10), true);
    return b;
  }

  const w = ornek();
  let cek = 0;
  w.skopIkiliAl = () => { cek++; };
  w.skopIkiliBekle = true;
  w.satirIsle(M);
  w.satirIsle(ONAY);
  ok('[!] Onaydan once gelen M satiri TUTULUYOR ve govde cekiliyor',
     cek === 1 && !!w.skopIkiliOlcum && Math.abs(w.skopIkiliOlcum.Vpp - 4.664) < 1e-9);
  const cozuldu = w.skopIkiliCoz(skopBin(833));
  ok('[!] Ikili yakalama OLCUM SATIRINI gosteriyor (WiFi)',
     cozuldu && !!w.osilo && !!w.osilo.olcum
     && Math.abs(w.osilo.olcum.f - 996.806) < 1e-9 && w.skopOlcumler.length > 0,
     w.osilo && w.osilo.olcum ? `${w.skopOlcumler.length} oge` : 'olcum null — WiFi\'de satir cikmaz');
  ok('Olcum TEK kullanimlik (sonraki kayda yapismiyor)', w.skopIkiliOlcum === null);

  const a = ornek();
  a.skopIkiliOlcum = { f: 1, Vpp: 1 };
  a.skopArsivtenAciliyor = true;
  a.skopIkiliCoz(skopBin(100));
  ok('[!] Arsivden acilan kayda bekleyen olcum BAGLANMIYOR',
     !!a.osilo && a.osilo.olcum === null, 'baska bir dalganin olcumu yanlis kayitta gorunurdu');

  const c = ornek();
  c.skopIkiliAl = () => {};
  c.skopIkiliBekle = true;
  c.satirIsle(M);
  c.satirIsle('! tetiklenemedi');
  ok('`!` bekleyen olcumu de temizliyor', c.skopIkiliOlcum === null);

  const e = ornek();
  e.satirIsle(M);
  ok('Bekleme yokken gelen M satiri tutulmuyor', e.skopIkiliOlcum === null);

  ok('Yeni `tB` oncesi eski olcum temizleniyor',
     /skopIkiliOlcum = null;[^\n]*\n\s*this\.skopIkiliBekle = true;\s*\n\s*this\.gonder\('tB'\)/.test(appKaynak));

  /* ASCII yolu bozulmadi ve iki yol TEK ayristiricidan geciyor */
  const s = ornek();
  s.osiloBitir = function () { this.bitti = this.osiloTopla; this.osiloTopla = null; };
  s.satirIsle('S2 3 1000 0.028788 0 100 0 1 63.530090');
  s.satirIsle(M);
  s.satirIsle('1 2 3');
  ok('[!] ASCII dokumunde M satiri yine olcume giriyor',
     !!s.bitti && !!s.bitti.olcum && Math.abs(s.bitti.olcum.duty - 45.88) < 1e-9);
  /* ⚠ `alan.indexOf('=')` ARANMIYOR: CT ayristiricisi da ayni kalibi
     kullaniyor, iddia M'yle ilgisiz bir yerde kizariyordu. M'ye OZGU iz:
     iki yolun ikisi de skopMCoz'u cagiriyor ve eski satir ici atama yok. */
  const satirIsleGovde = (() => {
    const i = appKaynak.indexOf('\n    satirIsle(');
    const j = appKaynak.indexOf('{', i);
    let d = 0;
    for (let k = j; k < appKaynak.length; k++) {
      if (appKaynak[k] === '{') d++;
      else if (appKaynak[k] === '}' && --d === 0) return appKaynak.slice(j, k + 1);
    }
    return '';
  })();
  const mCagri = satirIsleGovde.split('this.skopMCoz(satir)').length - 1;
  ok('M satiri TEK ayristiricida (ASCII ve ikili dal ikisi de skopMCoz)',
     mCagri === 2 && !satirIsleGovde.includes('this.osiloTopla.olcum = o;'),
     `${mCagri} cagri`);
}

/* ═══════════════════════════════════════════════════════════════════════
   21. TARAYICI GEZISINDE BULUNANLAR (B45)

   Panel Claude in Chrome ile sekme sekme gezildi (2026-09-13). Dort
   mantik/gorunum hatasi: zaman grafigi negatifi cizemiyor ve gurultuyu
   tam ekrana yayiyor; skop olcum satirinda birimler karisik; `A`/`CT`
   satirlari konsola dusmuyor; arsiv kaydinin olcum satiri kullanilmiyor.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 21. Tarayici gezisinde bulunanlar (B45) ---');
{
  /* (a) negatif deger + sifir: 3D'de grafik.js'e gecti — "negatif tuvalin DISINA
     cizilmesin, sifir gorunsun" iddialari bolum 25'te GERCEK cizim planindan sinaniyor. */
  const g = ornek();
  g.kartSont = 0.1; g.menzil = 0;
  const pencere = [{ t: 0, v: 1.7, i: -0.5, w: 0.2 }, { t: 1, v: 1.7, i: 0.4, w: 0.1 }];
  const taban = g.olcekTabani(pencere);

  /* (b) gurultu tabani: 20 LSB, kartin sont'undan. Grafikte bu `enAzAralik`
     (2 x taban, ekran/canli.js K2); davranisi bolum 25. */
  const iLsb = 0.256 / 32768 / 0.1;           // 78.125 uA
  ok('Akim tabani = 20 LSB (kartin sont\'undan)', Math.abs(taban.i - 20 * iLsb) < 1e-12,
     `${(taban.i * 1e3).toFixed(4)} mA`);
  ok('Gerilim tabani = 20 x 1.042 mV (NORMAL)', Math.abs(taban.v - 20 * 1.042e-3) < 1e-12);
  g.menzil = 1;
  ok('YUKSEK menzilde gerilim tabani 20 x 18.78 mV', Math.abs(g.olcekTabani(pencere).v - 20 * 18.78e-3) < 1e-12);
  g.menzil = 0;
  const gurultu = Array.from({ length: 40 }, (_, k) => ({ t: k, v: 1.7156, i: (k % 2 ? 3e-6 : -3e-6), w: (k % 2 ? 5e-6 : -5e-6) }));
  const tg = g.olcekTabani(gurultu);
  ok('[!] Guc tabani |V|max x akim tabani + |I|max x gerilim tabani (1.7 V x 1.56 mA ~ 2.7 mW)',
     Math.abs(tg.w - (1.7156 * tg.i + 3e-6 * tg.v)) < 1e-12, `${(tg.w * 1e3).toFixed(3)} mW`);

  /* (c) skop olcum satirinda gerilimler TEK birimde */
  const s = ornek();
  s.osilo = { adet: 4, hz: 1000, veri: [1, 2, 3, 4], tetiklendi: true,
              olcum: { f: 1000, T: 1e-3, Vpp: 4.4404, Vmax: 0.3482, Vmin: -4.0922, Vort: -1.8082, Vrms: 2.3756, Vac: 1.5408, duty: 50, tr: 3e-4, tf: 3e-4, n: 1 } };
  const gerilimler = s.skopOlcumler.filter((m) => /^V/.test(m.ad));
  ok('[!] Skop olcum satirinda alti gerilim de "x.xxx V" biciminde',
     gerilimler.length === 6 && gerilimler.every((m) => /^-?\d+\.\d{3} V$/.test(m.d)),
     gerilimler.map((m) => m.d).join(' | '));
  ok('Vmax 0.3482 -> "0.348 V" (348.200 mV DEGIL)',
     gerilimler.find((m) => m.ad === 'Vmax').d === '0.348 V');
  ok('Zaman buyuklukleri hala SI onekli (999.861 us gibi)',
     s.skopOlcumler.find((m) => m.ad === 'Periyot').d === '1.000 ms');

  /* (d) `A` ve `CT` konsola dusuyor */
  const c = ornek();
  c.satirIsle('A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 y_sifir=0 sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200');
  ok('[!] `A` (ayarlar) satiri KONSOLA dusuyor — "Ayarlari goster" bunu gostermiyordu',
     c.gunluk.some((x) => x.metin.startsWith('A menzil=')) && c.kartSont === 0.1);
  c.satirIsle('CT 3 oran=38.037037 ofset=63.530090 tavan_mv=3100.0 0:0 2048:1790 4095:3100');
  ok('`CT` satiri konsola dusuyor ve tablo yine kuruluyor',
     c.gunluk.some((x) => x.metin.startsWith('CT 3')) && !!c.skopKal && c.skopKal.kod.length === 3);
  c.satirIsle('D 1.7156 0.000001 0.00000 0.0022 0.0000006 55167 93 0 0');
  ok('`D` satiri konsola DUSMUYOR (saniyede 20 kez, panelde)',
     !c.gunluk.some((x) => x.metin.startsWith('D ')));
  ok('Konsol aciklamasi disarida kalanlari SOYLUYOR',
     /her satır burada[\s\S]{0,200}<code>D<\/code>[\s\S]{0,120}hariç/.test(htmlKaynak),
     '"her satir burada" iddiasi D/W/skop dokumu icin dogru degildi');

  /* (e) arsiv kaydinin olcum satiri — GERCEK KART FIKSTURU ile */
  const fk = JSON.parse(fs.readFileSync(path.join(__dirname, 'olcum-skop-fikstur.json'), 'utf8'));
  const a = ornek();
  a.satirIsle(fk.ct);
  ok('Fikstur: CT tablosu gercek karttan, 17 dugum', !!a.skopKal && a.skopKal.kod.length === 17);
  a.osilo = { adet: fk.kodlar.length, hz: 83333, veri: fk.kodlar, voltOfset: 63.530090, voltAdim: 0.028788, tetiklendi: true, olcum: null };
  const kart = a.skopMCoz(fk.m);
  const ars = a.skopArsivOlcum(fk.m, fk.kodlar);
  const fark = Math.max(...['Vmax', 'Vmin', 'Vpp', 'Vort', 'Vrms', 'Vac'].map((k) => Math.abs(ars[k] - kart[k])));
  ok('[!] Arsiv gerilimleri (arayuz, kodVolt) == kartin M satiri (C, kal_mv) — GERCEK kayitta <= 1 mV',
     fark <= 1e-3, `en buyuk fark ${(fark * 1e3).toFixed(3)} mV (${fk.kodlar.length} kod)`);
  ok('[!] Zaman buyuklukleri kaydin M satirindan (f, duty, n)',
     ars.f === kart.f && ars.duty === kart.duty && ars.n === kart.n && ars.tr === kart.tr);
  const eski = 'M f=999.996 T=0.001000004 Vpp=4.3470 Vmax=-6.3000 Vmin=-10.6469 Vort=-8.4892 Vrms=8.6 Vac=1.39 duty=51.13 tr=0.000483203 tf=0.000320116 n=9';
  const ars2 = a.skopArsivOlcum(eski, fk.kodlar);
  ok('[!] B43 ONCESI (dogrusal) M satiri olan eski kayitta gerilimler EKSENDEN (7 V celiski geri gelmiyor)',
     Math.abs(ars2.Vmax - kart.Vmax) <= 1e-3 && ars2.f === 999.996,
     `Vmax ${ars2.Vmax.toFixed(4)} (M satiri -6.3000 diyordu)`);
  ok('M satiri olmayan kayitta gerilimler var, zaman buyuklukleri UYDURULMUYOR',
     (() => { const o = a.skopArsivOlcum('', fk.kodlar); return o && !('f' in o) && !('duty' in o) && Math.abs(o.Vpp - kart.Vpp) <= 1e-3; })());
  ok('Bos kayitta null', a.skopArsivOlcum(fk.m, []) === null);
  /* Kisa M satiri (kopru sahtesi 'M f=250.000 Vpp=24.0000 n=5' gonderiyor):
     eksik `duty` render'i dusurmemeli — tarayici testinde skop gorunumu
     komple kayboluyordu. */
  a.osilo.olcum = a.skopArsivOlcum('M f=250.000 Vpp=24.0000 n=5', fk.kodlar);
  let satirlar = null, patladi = null;
  try { satirlar = a.skopOlcumler; } catch (e) { patladi = e.message; }
  ok('[!] Kisa M satiri (duty/tr/tf yok) skop olcum satirini COKERTMIYOR, eksik alan UYDURULMUYOR',
     patladi === null && Array.isArray(satirlar) && satirlar.some((m) => m.ad === 'Frekans' && m.d === '250.000 Hz')
     && !satirlar.some((m) => m.ad === 'Duty' || m.ad === 'Periyot'),
     patladi || (satirlar && satirlar.map((m) => m.ad).join(',')));
  ok('skopKayitAc arsiv olcumunu BAGLIYOR (kaynak)',
     govdeIcinde(appKaynak, 'skopKayitAc', 'this.osilo.olcum = this.skopArsivOlcum(kyt.olcum, this.osilo.veri);'));
}

/* ═══════════════════════════════════════════════════════════════════════
   22. TETIK ONAYI — gurultu reddi (B47)

   Kart `T` satirinda `onay=1|2` bildiriyor; arayuz menusu `tn1`/`tn2`
   gonderiyor. Eski firmware `onay=` gondermez -> menu dokunulmaz.
   Davranisin kendisi (igne tetiklemez) KARTTA sinaniyor:
   `tezgah_blokaj.py --onay`. Burada protokol ve menu.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 22. Tetik onayi — gurultu reddi (B47) ---');
{
  const T = (onay) => 'T tdiv=5/11 (5000 us/bolme) hz=20000 adet=1000 pencere_ms=50.00 esik=2048 kenar=yukselen hist=40 on=25% kip=0'
                      + (onay === null ? '' : ' onay=' + onay);
  const u = ornek();
  ok('Varsayilan onay 2 (gurultu reddi) — kartin varsayilaniyla ayni', u.skopOnay === 2
     && /SkopAyar skop_ayar = \{ 5, 2048, 0, 40, 25, SKOP_KIP_OTO, 2, 1 \};/.test(fs.readFileSync(INO, 'utf8')));
  u.satirIsle(T(1));
  ok('[!] `T ... onay=1` menuyu tek ornege aliyor', u.skopOnay === 1);
  u.satirIsle(T(2));
  ok('`T ... onay=2` geri aliyor', u.skopOnay === 2);
  u.skopOnay = 1;
  u.satirIsle(T(null));
  ok('[!] Eski firmware (onay yok) menuye DOKUNMUYOR', u.skopOnay === 1,
     'yoksa arayuz kartta olmayan bir ayari "2" diye gosterirdi');
  u.satirIsle(T(7));
  ok('Gecersiz onay degeri yok sayiliyor', u.skopOnay === 1);
  ok('[!] Menu `tn<onay>` gonderiyor ve iki secenek var',
     /v-model\.number="skopOnay" @change="skopKomut\('tn' \+ skopOnay\)"/.test(htmlKaynak)
     && /<option :value="2">Gürültü reddi \(2 örnek\)<\/option>/.test(htmlKaynak)
     && /<option :value="1">Tek örnek<\/option>/.test(htmlKaynak));
  const SK2 = require(path.join(ARAYUZ, 'sahte-kart.js'));
  ok('Sahte kart `tn1` -> T satirinda onay=1, `tn2` -> onay=2',
     /\bonay=1\b/.test(SK2.komut('tn1')[0]) && /\bonay=2\b/.test(SK2.komut('tn2')[0]));
  ok('Sahte kart gecersiz `tn3` reddediyor', SK2.komut('tn3')[0].startsWith('!'));
  /* Firmware tarafi (tetik_w/kalan, komut, T satiri) sim3_skop.py 6m'de. */
}

/* ═══════════════════════════════════════════════════════════════════════
   22b. SKOP ON SUZGECI (SK1, 2026-10-10)

   Kart `T` satirinda `suz=0|1` bildiriyor; menu `tf0` / `tf1` gonderiyor.
   Eski firmware `suz=` gondermez -> menu dokunulmaz. Suzgecin kendisi
   test_skop_suz.py'de (gercek kod, AVR), baglantisi sim3_skop.py 6n'de,
   etkisi kartta (tezgah_blokaj.py --sinyal). Burada protokol, menu ve
   "suruculuk devralininca eksen tablosu yeniden istenir" kurali.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 22b. Skop on suzgeci (SK1) ---');
{
  const T = (suz) => 'T tdiv=5/11 (5000 us/bolme) hz=20161 adet=1000 pencere_ms=49.60 esik=2048 kenar=yukselen hist=40 on=25% kip=0 onay=2'
                     + (suz === null ? '' : ' suz=' + suz);
  const u = ornek();
  ok('SK1 Varsayilan suzgec ACIK — kartin varsayilaniyla ayni', u.skopSuz === 1);
  u.satirIsle(T(0));
  ok('[!] SK1 `T ... suz=0` menuyu HAM\'a aliyor', u.skopSuz === 0);
  u.satirIsle(T(1));
  ok('SK1 `T ... suz=1` geri aliyor', u.skopSuz === 1);
  u.skopSuz = 0;
  u.satirIsle(T(null));
  ok('[!] SK1 Eski firmware (suz yok) menuye DOKUNMUYOR', u.skopSuz === 0,
     'yoksa arayuz kartta olmayan suzgeci "acik" diye gosterirdi');
  u.satirIsle(T(5));
  ok('SK1 Gecersiz suz degeri yok sayiliyor', u.skopSuz === 0);
  ok('[!] SK1 Menu `tf<suz>` gonderiyor, iki secenek var, etiket sozlukten',
     /v-model\.number="skopSuz" @change="skopKomut\('tf' \+ skopSuz\)"/.test(htmlKaynak)
     && /<option :value="1">\{\{ os\.suzAcik \}\}<\/option>/.test(htmlKaynak)
     && /<option :value="0">\{\{ os\.suzHam \}\}<\/option>/.test(htmlKaynak)
     && /\{\{ os\.suzgec \}\}/.test(htmlKaynak) && /:title="os\.suzIpucu"/.test(htmlKaynak));
  const SK3 = require(path.join(ARAYUZ, 'sahte-kart.js'));
  ok('SK1 Sahte kart `tf0` -> T satirinda suz=0, `tf1` -> suz=1',
     /\bsuz=0\b/.test(SK3.komut('tf0')[0]) && /\bsuz=1\b/.test(SK3.komut('tf1')[0]));
  ok('SK1 Sahte kart ciplak `tf` ve `tf2` reddediyor (firmware gibi)',
     SK3.komut('tf')[0].startsWith('!') && SK3.komut('tf2')[0].startsWith('!'));
  /* Kartta bulundu (2026-10-10): izleyici olarak acilan sekmede CT 403 aliyordu; suruculuk
     sonradan devralinsa da eksen HAM kaliyor, 12 V'luk kaynak 4 V gibi ciziliyordu. */
  const dv = /async devral\(\) \{[\s\S]*?\n    \},/.exec(appKaynak);
  ok('[!] SK1 Suruculuk devralininca, tablo yoksa, CT YENIDEN isteniyor',
     !!dv && /this\.surucuyum = true;[^\n]*if \(!this\.skopKal\) this\.gonder\('CT'\)/.test(dv[0]),
     'yoksa sonradan surucu olan sekmede skop ekseni kalibresiz kalir');
}

/* ═══════════════════════════════════════════════════════════════════════
   23. GORUNUM + ES MODUL ALTYAPISI (3A — alt proje 3, P1/P4)

   Kullanici birden cok tasarim arasinda gecis istedi; karar (P1): TEK
   duzen, UC renk takimi (Koyu · Acik · On panel), Ayarlar'dan secilir,
   tarayicida hatirlanir. Ayni dilimde app.js ES modulu oldu (P4) ve
   `ekran/` acildi; ilk modul `ekran/tema.js`.

   Korunan seyler:
   (a) Koyu, 3A ONCESININ DEGERLERI — donmus kopyayla karsilastiriliyor.
       "Gorunum eklendi" bahanesiyle varsayilan gorunum sessizce degismesin.
   (b) Uc takim AYNI belirtecleri tanimliyor ve METIN OKUNUYOR (WCAG
       4.5:1, sayiyla). On panel maketinin alarm rengi metin olarak 2.99:1
       idi — bu iddia olmasaydi hata kutusu o temada okunmazdi.
   (c) <head> betigi ile modul AYNI karari veriyor (ilk boyama vs sonrasi);
       ayrisirlarsa sayfa acilista bir renkte, sonra baskasinda cizilir.
   (d) Saklama try/catch icinde; erisimin KENDISI atinca da gorunum degisir.
   (e) Renk degisince tuvaller yeniden ciziliyor (bit eslem; renk onbellekte
       degil ama cizim eskide kalir).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 23. Gorunum (Koyu/Acik/On panel) + ES modul altyapisi (3A) ---');
{
  const html = yorumsuz(htmlKaynak);
  const css = cssOku();
  const cssKod = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const TEMA = require(path.join(ARAYUZ, 'ekran', 'tema.js'));

  /* ── (a) modul yuklemesi ─────────────────────────────────────────── */
  ok('[!] app.js ES MODULU olarak yukleniyor (type="module"), klasik kopyasi yok',
     /<script type="module" src="app\.js"/.test(html) && !/<script src="app\.js"/.test(html));
  ok('Vue (klasik betik) app.js modulunden ONCE baglaniyor',
     html.indexOf('vendor/vue.global.prod.js') >= 0
     && html.indexOf('vendor/vue.global.prod.js') < html.indexOf('type="module" src="app.js"'));
  ok('app.js tema modulunu ekran/ altindan ice aktariyor',
     ICE_AKTARILAN.some((i) => i.yol === './ekran/tema.js' && i.adlar.includes('temaKur')),
     ICE_AKTARILAN.map((i) => i.yol + ' {' + i.adlar.join(',') + '}').join(' · '));
  const grafik = iceAktarmaGrafigi();
  ok('app.js`in statik ice aktarma grafigindeki her dosya DISKTE var',
     grafik.length >= 1 && grafik.every((g) => g.var),
     grafik.filter((g) => !g.var).map((g) => g.kimden + ' -> ' + g.yol).join(' ')
       || grafik.map((g) => g.goruntu).join(' '));
  /* file:// artik modulu YUKLEMIYOR (koken null). Kutu "kart yeniden
     basliyor" deyip yanlis yere baktirmamali. */
  ok('Acilmama kutusu file:// sebebini ve caresini soyluyor',
     /arayuzHata = function[\s\S]{0,400}location\.protocol === 'file:'[\s\S]{0,300}sunucu\.py/.test(html));

  /* ── (b) renk takimlari ──────────────────────────────────────────── */
  const kural = (ad) => {
    for (const m of cssKod.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      if (m[1].split(',').map((s) => s.trim()).includes(':root[data-tema="' + ad + '"]')) return m[2];
    }
    return null;
  };
  const degerler = (govde) => Object.fromEntries(
    [...(govde || '').matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)]
      .map((m) => [m[1], m[2].replace(/\s+/g, ' ').trim().toLowerCase()]));
  const TAKIM = { koyu: degerler(kural('koyu')), acik: degerler(kural('acik')),
                  onpanel: degerler(kural('onpanel')) };
  const adlar = (t) => Object.keys(TAKIM[t]).sort().join(' ');
  ok('[!] Uc gorunum AYNI belirtec adlarini tanimliyor',
     adlar('koyu').length > 0 && adlar('koyu') === adlar('acik') && adlar('koyu') === adlar('onpanel'),
     ['acik', 'onpanel'].map((t) => t + ': ' + (
       Object.keys(TAKIM.koyu).filter((b) => !(b in TAKIM[t])).map((b) => '-' + b)
         .concat(Object.keys(TAKIM[t]).filter((b) => !(b in TAKIM.koyu)).map((b) => '+' + b))
         .join(' ') || 'tam')).join(' | '));
  /* 3A ONCESI koyu (bare :root) degerleri — donmus kopya. */
  const KOYU_3A_ONCESI = {
    '--zemin': '#0b0f14', '--zemin-2': '#101821', '--kart': '#131c25',
    '--kenar-c': '#1f2b37', '--kenar-koyu': '#31414f', '--yazi': '#dee7ef',
    '--soluk': '#94a3b3', '--cok-soluk': '#6b7c8b', '--vurgu': '#4cc4e0',
    '--vurgu-yazi': '#05131a', '--vurgu-zemin': '#0d2a34', '--uyari': '#ff8f7a',
    '--uyari-zemin': '#2a1310', '--iyi': '#74d99b', '--iyi-zemin': '#0c2a1c',
    '--volt': '#6ea8fe', '--amper': '#f2a33c', '--watt': '#35d39a',
    '--golge-1': '0 1px 0 rgba(255, 255, 255, .02) inset',
    '--golge-2': '0 1px 2px rgba(0, 0, 0, .5), 0 8px 24px rgba(0, 0, 0, .35)',
  };
  const koyuFark = Object.entries(KOYU_3A_ONCESI).filter(([b, d]) => TAKIM.koyu[b] !== d)
    .map(([b, d]) => `${b} ${TAKIM.koyu[b]} != ${d}`)
    .concat(Object.keys(TAKIM.koyu).filter((b) => !(b in KOYU_3A_ONCESI)).map((b) => '+' + b));
  ok('[!] Koyu degerleri 3A oncesiyle BIREBIR ayni (varsayilan gorunum degismedi)',
     koyuFark.length === 0 && /color-scheme:\s*dark/.test(kural('koyu') || ''),
     koyuFark.join(' · ') || `${Object.keys(KOYU_3A_ONCESI).length} belirtec + color-scheme`);
  ok('Bicim belirtecleri (mono/govde/yuvarlak/gecis) TEK :root blogunda, temada degil',
     ['koyu', 'acik', 'onpanel'].every((t) => !/--(mono|govde|yuvarlak|gecis)\s*:/.test(kural(t) || ''))
     && /:root\s*\{[^}]*--mono:[^}]*--yuvarlak:\s*10px;[^}]*--gecis:/.test(cssKod));
  ok('color-scheme her temada dogru (form denetimleri ve kaydirma cubugu uyar)',
     /color-scheme:\s*dark/.test(kural('koyu') || '') && /color-scheme:\s*light/.test(kural('acik') || '')
     && /color-scheme:\s*dark/.test(kural('onpanel') || ''));
  ok('prefers-color-scheme CSS`te YOK (sistem tercihi tek yerde: tema.js + <head>)',
     !/prefers-color-scheme/.test(cssKod));
  ok('[hidden] { display: none !important } kurali DURUYOR',
     /\[hidden\]\s*\{\s*display:\s*none\s*!important;?\s*\}/.test(cssKod));

  /* WCAG goreli parlaklik ve karsitlik — sayiyla. */
  const parlaklik = (h) => {
    const m = /^#([0-9a-f]{6})$/i.exec((h || '').trim());
    if (!m) return NaN;
    const k = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255)
      .map((c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
    return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2];
  };
  const karsitlik = (a, b) => {
    const x = parlaklik(a), y = parlaklik(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  };
  const CIFTLER = [
    ['--yazi', ['--zemin', '--zemin-2', '--kart']],
    ['--soluk', ['--zemin', '--zemin-2', '--kart']],
    ['--uyari', ['--kart', '--uyari-zemin']],         // hata kutusu metni
    ['--iyi', ['--iyi-zemin']],                       // "bagli" rozeti
    ['--vurgu', ['--zemin', '--vurgu-zemin']],        // etkin sekme / etkin dugme
    ['--vurgu-yazi', ['--vurgu']],                    // birincil dugme
  ];
  /* --cok-soluk (kucuk etiketler) Koyu'da 4.5'in ALTINDA (4.00) ve Koyu
     degismiyor; olcut: hicbir temada Koyu'dan DAHA okunaksiz olmasin. */
  const ZEMINLER = ['--zemin', '--zemin-2', '--kart'];
  const cokSolukTaban = Math.min(...ZEMINLER.map((z) =>
    karsitlik(TAKIM.koyu['--cok-soluk'], TAKIM.koyu[z])));
  for (const t of ['koyu', 'acik', 'onpanel']) {
    const d = TAKIM[t];
    let enKotu = { k: Infinity, ad: '' };
    for (const [on, zeminler] of CIFTLER) {
      for (const z of zeminler) {
        const k = karsitlik(d[on], d[z]);
        if (!(k >= enKotu.k)) enKotu = { k, ad: `${on} / ${z}` };
      }
    }
    ok(`[!] ${t}: metin karsitligi >= 4.5:1 (yazi/soluk/uyari/iyi/vurgu, ${CIFTLER.reduce((n, c) => n + c[1].length, 0)} cift)`,
       enKotu.k >= 4.5, `en kotu ${enKotu.ad} = ${enKotu.k.toFixed(2)}:1`);
    const cs = Math.min(...ZEMINLER.map((z) => karsitlik(d['--cok-soluk'], d[z])));
    ok(`${t}: --cok-soluk en az Koyu kadar okunur (>= ${cokSolukTaban.toFixed(2)}:1)`,
       cs >= cokSolukTaban - 1e-9, `${cs.toFixed(2)}:1`);
  }

  /* ── (c) tema modulu: secim, cozme, saklama ──────────────────────── */
  ok('TEMALAR: sistem · koyu · acik · onpanel; her somut temanin CSS blogu var',
     TEMA.TEMALAR.map((t) => t.id).join(' ') === 'sistem koyu acik onpanel'
     && TEMA.TEMALAR.filter((t) => t.id !== 'sistem').every((t) => kural(t.id) !== null)
     && [...cssKod.matchAll(/data-tema="([a-z]+)"/g)].every((m) => TEMA.temaGecerli(m[1])),
     TEMA.TEMALAR.map((t) => t.id + (t.id === 'sistem' || kural(t.id) ? '' : '(CSS yok)')).join(' '));
  ok('[!] Acik secim sistem tercihini EZER; "sistem" tercihe uyar; gecersiz -> Koyu',
     TEMA.temaCoz('sistem', true) === 'acik' && TEMA.temaCoz('sistem', false) === 'koyu'
     && TEMA.temaCoz('koyu', true) === 'koyu' && TEMA.temaCoz('onpanel', true) === 'onpanel'
     && TEMA.temaCoz('acik', false) === 'acik' && TEMA.temaCoz('bozuk', true) === 'koyu');

  /* Sahte pencere/belge: localStorage (atabilen), matchMedia (degisebilen). */
  const ortam = ({ depo = {}, acik = false, atar = '' } = {}) => {
    const nitelik = {}, dinleyici = [];
    const mq = { matches: acik,
      addEventListener: (_, f) => dinleyici.push(f),
      removeEventListener: (_, f) => { const i = dinleyici.indexOf(f); if (i >= 0) dinleyici.splice(i, 1); } };
    const pencere = {
      get localStorage() {
        if (atar === 'erisim') throw new Error('SecurityError');
        return {
          getItem: (k) => { if (atar === 'okuma') throw new Error('okuma'); return k in depo ? depo[k] : null; },
          setItem: (k, v) => { if (atar === 'yazma') throw new Error('QuotaExceeded'); depo[k] = String(v); },
        };
      },
      matchMedia: () => mq,
    };
    const belge = { documentElement: { setAttribute: (k, v) => { nitelik[k] = v; } } };
    return { pencere, belge, nitelik, depo, dinleyici,
             sistem(a) { mq.matches = a; dinleyici.slice().forEach((f) => f({ matches: a })); } };
  };
  {
    const o = ortam();
    const cagri = [];
    const y = TEMA.temaKur({ pencere: o.pencere, belge: o.belge, degisti: (t) => cagri.push(t) });
    const ilk = y.secim === 'sistem' && o.nitelik['data-tema'] === 'koyu'
             && o.nitelik['data-tema-secim'] === 'sistem';
    const s1 = y.sec('onpanel');
    const kayit = o.depo[TEMA.TEMA_ANAHTAR];
    const s2 = y.sec('onpanel');
    ok('[!] temaKur: secim uygulanir, SAKLANIR (JSON, olcum.tema), tuval geri cagrisi BIR kez',
       ilk && s1 === true && s2 === false && kayit === '"onpanel"'
       && o.nitelik['data-tema'] === 'onpanel' && cagri.join(',') === 'onpanel',
       `ilk=${ilk} kayit=${kayit} cagri=${cagri.join(',')}`);
    o.sistem(true);
    const sabit = o.nitelik['data-tema'] === 'onpanel' && cagri.length === 1;
    y.sec('sistem');                     // sistem su an acik -> Acik
    o.sistem(false);                     // canli: koyuya gecmeli
    ok('[!] "sistem" isletim sistemini CANLI izliyor; acik secim izlemiyor',
       sabit && o.nitelik['data-tema'] === 'koyu' && cagri.join(',') === 'onpanel,acik,koyu',
       `sabit=${sabit} cagri=${cagri.join(',')} etkin=${o.nitelik['data-tema']}`);
    y.birak();
    ok('birak() isletim sistemi dinleyicisini kaldiriyor', o.dinleyici.length === 0);
    ok('Gecersiz secim reddediliyor (saklanmiyor, uygulanmiyor)',
       y.sec('mor') === false && o.depo[TEMA.TEMA_ANAHTAR] === '"sistem"');
  }
  {
    /* (d) Saklama ATARSA: gorunum yine degisir, istisna kacmaz. */
    let istisna = '';
    const sonuc = [];
    for (const atar of ['erisim', 'okuma', 'yazma']) {
      const o = ortam({ atar, depo: { 'olcum.tema': '"acik"' } });
      try {
        const y = TEMA.temaKur({ pencere: o.pencere, belge: o.belge });
        y.sec('onpanel');
        sonuc.push(atar + ':' + o.nitelik['data-tema']);
      } catch (e) { istisna = atar + ': ' + e.message; }
    }
    ok('[!] localStorage ATARSA (erisim/okuma/yazma) gorunum yine degisiyor, istisna yok',
       !istisna && sonuc.join(' ') === 'erisim:onpanel okuma:onpanel yazma:onpanel',
       istisna || sonuc.join(' '));
    ok('temaOku/temaYaz erisimi try/catch icinde (kaynak)',
       /export function temaOku[\s\S]{0,80}try \{[\s\S]{0,200}catch/.test(fs.readFileSync(
         path.join(ARAYUZ, 'ekran', 'tema.js'), 'utf8'))
       && /export function temaYaz[\s\S]{0,80}try \{[\s\S]{0,200}catch/.test(fs.readFileSync(
         path.join(ARAYUZ, 'ekran', 'tema.js'), 'utf8')));
  }

  /* <head> betigi: ilk boyamadan ONCE, ve modulle AYNI karar. */
  const bas = (htmlKaynak.match(/<head>([\s\S]*?)<\/head>/) || [])[1] || '';
  const basBetik = (bas.match(/<script>([\s\S]*?)<\/script>/) || [])[1] || '';
  ok('Gorunum <head> icinde, stil dosyasindan ONCE uygulaniyor (yanip sonme yok)',
     !!basBetik && /data-tema/.test(basBetik)
     && bas.indexOf('<script>') < bas.indexOf('rel="stylesheet"'));
  {
    const farklar = [];
    let say = 0;
    const DEGERLER = [null, '"sistem"', '"koyu"', '"acik"', '"onpanel"', '"mor"', '{bozuk', '42'];
    const durumlar = [];
    for (const d of DEGERLER) for (const acik of [false, true]) for (const mm of [true, false]) {
      durumlar.push({ d, acik, mm, atar: '' });
    }
    for (const atar of ['erisim', 'okuma']) durumlar.push({ d: '"acik"', acik: true, mm: true, atar });
    for (const { d, acik, mm, atar } of durumlar) {
      const depo = d === null ? {} : { 'olcum.tema': d };
      // <head> betigi
      const o1 = ortam({ depo, acik, atar });
      const ctx = { document: o1.belge, JSON };
      Object.defineProperty(ctx, 'localStorage', { get: () => o1.pencere.localStorage });
      if (mm) ctx.matchMedia = o1.pencere.matchMedia;
      ctx.window = ctx;
      try { vm.createContext(ctx); vm.runInContext(basBetik, ctx); } catch (e) { o1.nitelik.hata = e.message; }
      // modul
      const o2 = ortam({ depo, acik, atar });
      if (!mm) delete o2.pencere.matchMedia;
      TEMA.temaKur({ pencere: o2.pencere, belge: o2.belge });
      say++;
      const a = JSON.stringify(o1.nitelik), b = JSON.stringify(o2.nitelik);
      if (a !== b) farklar.push(`${d}/${acik ? 'acik' : 'koyu'}/${mm ? 'mm' : '-'}/${atar}: bas ${a} modul ${b}`);
    }
    ok('[!] <head> betigi ile ekran/tema.js HER girdide AYNI karari veriyor',
       !!basBetik && farklar.length === 0, farklar[0] || `${say} durum`);
  }

  /* ── (e) uygulamaya baglanti ─────────────────────────────────────── */
  {
    const d = secenekler.data();
    ok('Secenekler TEMALAR`dan (elle kopya degil); baslangic secimi mounted`ta',
       d.temaSecenekleri === sandbox.TEMALAR && d.temaSecim === null);
    const giden = [];
    secenekler.watch.temaSecim.call({ _tema: { sec: (v) => giden.push(v) } }, 'acik');
    ok('watch.temaSecim secimi tema modulune veriyor', giden.join(',') === 'acik', giden.join(','));
    const u = ornek();
    let g = 0, o = 0;
    u.grafikCiz = () => { g++; }; u.osiloCiz = () => { o++; };
    u.temaDegisti();
    ok('[!] temaDegisti iki tuvali de yeniden ciziyor', g === 1 && o === 1, `grafik=${g} skop=${o}`);
    ok('mounted() temaKur`u temaDegisti geri cagrisiyla kuruyor',
       govdeIcinde(appKaynak, 'mounted', 'temaKur({')
       && govdeIcinde(appKaynak, 'mounted', 'degisti: () => this.temaDegisti()')
       && govdeIcinde(appKaynak, 'mounted', 'this.temaSecim = this._tema.secim'));
    const ayar = html.match(/v-show="gorunum === 'ayar'"([\s\S]*?)<\/main>/);
    ok('Ayarlar`da Gorunum secici: TEMALAR`dan, temaSecim`e bagli, aria-pressed',
       !!ayar && /<h2>Görünüm<\/h2>/.test(ayar[1])
       && /v-for="t in temaSecenekleri"/.test(ayar[1])
       && /@click="temaSecim = t\.id"/.test(ayar[1])
       && /:class="\{ etkin: temaSecim === t\.id \}"/.test(ayar[1])
       && /:aria-pressed=/.test(ayar[1]));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   24. KAYITLAR + KAYIT GORUNUMU (3C — alt proje 3, C1-C8)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3C kararlari". Burada
   (a) KABLOLAMA: altinci gorunum, ekran modulu ilk acilista iner (acilis
       istekleri buyumez), `#/kayit/<no>` rotasi, adres ezilmiyor, `G`
       artik arayuzde (onay).
   (b) SAF MANTIK node'da, GERCEK ortak/ modulleriyle: liste birlesimi ve
       "nerede", Turkce duyarsiz arama, seri hazirlama, imlec okumasi ve
       enerjinin RAPORLA ayni sayi olmasi, disa aktarma = ortak/ ciktisi,
       C1/C3 kararlari, IndexedDB deposunun parca hesabi ve kilidi.
   Gercek tarayici (IndexedDB, CDP fare olaylari, indirme, uc gorunum)
   `tarayici_kayitlar.py` (T3C). Ekran modulleri `/ortak/x.js` istiyor:
   node'da bu yol bir cozumleme kancasiyla ortak/src'ye baglaniyor (kart,
   kopru ve sunucu.py'nin esleme kuraliyla ayni).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 24. Kayitlar + kayit gorunumu (3C) ---');
{
  const { registerHooks } = require('module');
  const { pathToFileURL } = require('url');
  registerHooks({
    resolve(belirtec, baglam, sonraki) {
      if (belirtec.startsWith('/ortak/')) {
        return { url: pathToFileURL(path.join(KOK, 'ortak', 'src', belirtec.slice('/ortak/'.length))).href,
                 shortCircuit: true };
      }
      return sonraki(belirtec, baglam);
    },
  });
  const src = (ad) => require(path.join(KOK, 'ortak', 'src', ad));
  const K = src('kayit.js');
  const D = src('disari.js');
  const R = src('rapor.js');
  const IM = src('imza.js');
  const SZ = sozlukTum();
  const ek = (ad) => require(path.join(ARAYUZ, 'ekran', ad));
  const KL = ek('kayitlar.js');
  const KG = ek('kayit_gorunum.js');
  const ES = ek('esitleme.js');
  const DP = ek('depo_idb.js');
  const html = yorumsuz(htmlKaynak);
  const kaynak = (ad) => fs.readFileSync(path.join(ARAYUZ, 'ekran', ad), 'utf8');

  /* ── (a) kablolama ───────────────────────────────────────────────── */
  const kayitlarMain = html.match(/<main class="gorunum" v-show="gorunum === 'kayitlar'">([\s\S]*?)<\/main>/);
  ok('[!] index.html: Kayitlar gorunumu v-show, ekran ILK acilista (v-if kayitlarAcik) kuruluyor',
     !!kayitlarMain && /<kayitlar-ekran v-if="kayitlarAcik"/.test(kayitlarMain[1]),
     kayitlarMain ? 'bulundu' : 'yok');
  ok('[!] Ekrana kartAdres (tek istek yolu), gonder (komut yolu), bagli, kartTaban, tasiyici, etkin veriliyor',
     !!kayitlarMain && [':kart-adres="kartAdres"', ':gonder="gonder"', ':bagli="bagli"',
       ':kart-taban="kartTaban"', ':tasiyici="tasiyiciAdi"', ':etkin="gorunum === \'kayitlar\'"']
       .every((x) => kayitlarMain[1].includes(x)));
  const bilesen = secenekler.components && secenekler.components['kayitlar-ekran'];
  const secenek = bilesen && bilesen.yukleyici && typeof bilesen.yukleyici === 'object' ? bilesen.yukleyici : {};
  ok('[!] kayitlar-ekran ASENKRON bilesen: yukleyici ./ekran/kayitlar.js`i istiyor ve modul KayitlarEkrani veriyor',
     !!bilesen && bilesen.__asenkron === true
     && /import\('\.\/ekran\/kayitlar\.js'\)\.then\(\(m\) => m\.KayitlarEkrani\)/.test(String(secenek.loader))
     && typeof KL.KayitlarEkrani === 'object' && typeof KL.KayitlarEkrani.template === 'string',
     String(secenek.loader));
  ok('[!] Modul inmezse sekme BOS kalmiyor: hata bileseni sebebi ve careyi (.hata) yaziyor',
     !!secenek.errorComponent && /class="hata"[^>]*>[^<]*yüklenemedi[^<]*yenileyin/.test(secenek.errorComponent.template || ''));
  ok('[!] Kayitlar modulu ACILISTA inmiyor (statik ice aktarma grafiginde yok)',
     !iceAktarmaGrafigi().some((g) => /ekran\/(kayitlar|kayit_gorunum|esitleme|depo_idb)\.js$/.test(g.goruntu)),
     iceAktarmaGrafigi().map((g) => g.goruntu).join(' '));
  {
    const hashten = vm.runInContext('hashtenGorunum', sandbox);
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('[!] hashtenGorunum: #/kayitlar, #/kayit/12, #/kayit/12@7/rapor -> kayitlar',
       dene('#/kayitlar') === 'kayitlar' && dene('#/kayit/12') === 'kayitlar'
       && dene('#/kayit/12@7/rapor') === 'kayitlar' && dene('#/kayitx') === 'canli');
    const w = secenekler.watch.gorunum;
    let yazilan = [];
    sandbox.history = { replaceState: (a, b, h) => yazilan.push(h) };
    const sahte = { $nextTick() {}, grafikCiz() {}, osiloCiz() {}, kayitlarAcik: false };
    sandbox.location = { hash: '#/kayit/12' };
    w.call(sahte, 'kayitlar');
    const korundu = yazilan.length === 0 && sahte.kayitlarAcik === true;
    yazilan = [];
    sandbox.location = { hash: '#/olcum' };
    w.call(sahte, 'kayitlar');
    ok('[!] watch.gorunum ACIK KAYDIN adresini (#/kayit/12) #/kayitlar`a EZMIYOR; ekran kuruluyor',
       korundu && yazilan.join() === '#/kayitlar', `korundu=${korundu} yazilan=${yazilan.join()}`);
    sandbox.location = { hash: '' };
    ok('Kayitlar ekrani varsayilan olarak KURULMUYOR (acilis yuku yok)', secenekler.data().kayitlarAcik === false);
    delete sandbox.location;
    delete sandbox.history;
  }
  ok('[!] `G` artik arayuzde (Go<sira> onayi, ekran/esitleme.js); ARAYUZSUZ listesinde DEGIL',
     gonderilenler.some((g) => g.k === 'Go' && g.nerede === 'ekran/esitleme.js') && !('G' in ARAYUZSUZ));

  /* ── (b) C1 / C3 karar fonksiyonlari ─────────────────────────────── */
  const U = ES.esitlemeUygunlugu;
  ok('[!] C1: kartTaban dolu / USB / demo -> esitleme YOK (sebebiyle); ayni koken akis -> on kosul tamam',
     U({ kartTaban: 'http://baska', tasiyici: 'akis' }).neden === 'taban'
     && U({ kartTaban: '', tasiyici: 'seri' }).neden === 'usb'
     && U({ kartTaban: '', tasiyici: 'demo' }).neden === 'demo'
     && U({ kartTaban: '', tasiyici: 'akis' }).uygun === true && U({ kartTaban: '  ', tasiyici: 'akis' }).uygun);
  const LY = ES.listeYanitiCoz;
  ok('[!] C1: /kayit/liste siniflandirma — kart JSON tamam, 401 imza, 404 kart degil, 503 mesgul, bicimsiz bozuk',
     LY(200, '{"kimlik":7,"oturumlar":[]}').durum === 'tamam' && LY(401, 'imza gerekli').durum === 'imza'
     && LY(404, '').durum === 'yok' && LY(503, 'kayit mesgul').durum === 'mesgul'
     && LY(200, '<html>').durum === 'bozuk' && LY(200, '{"oturumlar":[]}').durum === 'bozuk'
     && LY(403, 'Host reddedildi').durum === 'host' && LY(500, 'x').durum === 'hata');
  ok('[!] Esitleme sirasindaki HTTP 401 -> "imza" (kullaniciya eslestirme yolu soylenir)',
     ES.hataSinifla(new IM.HttpHatasi(401, null, '/kayit/veri')).durum === 'imza'
     && ES.hataSinifla(new IM.HttpHatasi(500, null, '/kayit/veri')).durum === 'hata'
     && ES.hataSinifla(new TypeError('Failed to fetch')).durum === 'ag');
  {
    /* EU32 (W3): kl. metinleri sozluk_kayit.js'e gecti; Kayitlar'in pc./kl. KARISIK haritalari (NEREDE_METIN,
       nedenMetni, kopya satiri) ceviriKlPc ile cevrilir — ceviriPc yalniz acilis sozlugune dustugu icin
       kl.nerede_kart ekrana HAM anahtar olarak cikardi. */
    const KY = src('sozluk_kayit.js');
    const PCs = src('sozluk_pc.js');
    const f = KG.ceviriKlPc || (() => '');
    const nm = Object.values(KG.NEREDE_METIN || {});
    ok('[!] EU32: ceviriKlPc — kl. metni sozluk_kayit.js, pc. metni sozluk_pc.js (iki dilde); NEREDE_METIN`in hicbiri ham anahtar degil',
       f('kl.nerede_kart', 'en') === KY.SOZLUK_KAYIT['kl.nerede_kart'].en && f('pc.nerede', 'tr') === PCs.SOZLUK_PC['pc.nerede'].tr
       && nm.length >= 4 && nm.every((a) => ['tr', 'en'].every((d) => f(a, d) && !/^(kl|pc)\./.test(f(a, d)))),
       nm.map((a) => f(a, 'en')).join(' | '));
  }
  {
    const metin = SZ.ceviri('kl.neden_imza', 'tr');
    /* WIG: eski metin olmayan bir ayara ("Ayarlar'da (3H)") gonderiyordu. 4D: 3H-2'den beri panel
       eslestirmesi VAR (Ayarlar → Eşleştirme) ve PC'de arsivi kopru (pc.py) tutuyor — "henüz
       eşleştirilemiyor" + kayit_esitle.py BAYATTI; metin bugunku iki yolu soyler. */
    const en = SZ.ceviri('kl.neden_imza', 'en');
    ok('[!] 401 metni (4D): "Kart imzalı istek istiyor ve bu tarayıcıyı tanımıyor" + Ayarlar → Eşleştirme + PC yolu (kopru/pc.py); bayat "henüz eşleştirilemiyor" / kayit_esitle.py YOK',
       metin.startsWith('Kart imzalı istek istiyor ve bu tarayıcıyı tanımıyor') && metin.includes('Ayarlar → Eşleştirme')
       && metin.includes('kopru/pc.py') && !/henüz eşleştirilemiyor|kayit_esitle/.test(metin)
       && en.includes('Settings → Pairing') && en.includes('kopru/pc.py') && !/cannot be paired yet|kayit_esitle/.test(en), metin);
  }
  {
    /* Gercek kartta (2026-10-02) esitleme tek bir ag zaman asimiyla durdu: ag hatasi artan
       beklemeyle yeniden denenir, baska hata (imza, mesgul, bozuk) HEMEN doner. */
    const bekleyenler = [];
    const bekle = (ms) => { bekleyenler.push(ms); return Promise.resolve(); };
    const sirayla = (dizi) => { let n = 0; return async () => dizi[Math.min(n++, dizi.length - 1)]; };
    SONRA.push(async () => {
      const a = await ES.agYenidenDene(sirayla([{ durum: 'ag' }, { durum: 'ag' }, { durum: 'tamam', x: 1 }]), { bekle });
      const b1 = bekleyenler.splice(0);
      const b = await ES.agYenidenDene(sirayla([{ durum: 'imza' }, { durum: 'tamam' }]), { bekle });
      const b2 = bekleyenler.splice(0);
      const c = await ES.agYenidenDene(sirayla([{ durum: 'ag', mesaj: 'son' }]), { bekle });
      const b3 = bekleyenler.splice(0);
      ok('[!] Ag hatasi yeniden denenir (artan bekleme), baska sonuc hemen doner, en fazla AG_DENEME kez',
         a.durum === 'tamam' && a.x === 1 && a.deneme === 3 && b1.join() === `${ES.AG_BEKLE_MS},${2 * ES.AG_BEKLE_MS}`
         && b.durum === 'imza' && b.deneme === 1 && b2.length === 0
         && c.durum === 'ag' && c.mesaj === 'son' && c.deneme === ES.AG_DENEME && b3.length === ES.AG_DENEME - 1
         && ES.AG_DENEME >= 3, JSON.stringify({ a, b1, b, c, b3 }));
    });
  }
  {
    /* Gercek kartta (2026-10-02, 3G sinamasi) eşitleme sonunda /kal/liste bir kez TimeoutError
       aldi; Esitleyici bunu kalibrasyon_hata'ya cevirip "tamam" dondugu icin ust katmanin
       agYenidenDene'si hic devreye girmiyordu ("Kalibrasyon geçmişi alınamadı"). /kal/liste
       cekimi ag hatasinda artan beklemeyle yeniden denenir; /kayit/veri'ninki DENENMEZ (ust
       katman eşitlemeyi kaldigi yerden yeniden kuruyor — iki kat yeniden deneme bekleme sisirir). */
    SONRA.push(async () => {
      const eskiFetch = globalThis.fetch;
      const bekleyenler = [];
      const cagri = [];
      let kalHata = 2;
      globalThis.fetch = async (url) => {
        cagri.push(url);
        if (url.startsWith('/kal/liste')) {
          if (kalHata-- > 0) { const h = new Error('signal timed out'); h.name = 'TimeoutError'; throw h; }
          return new Response('{"kayitlar":[]}', { status: 200 });
        }
        throw new TypeError('Failed to fetch');
      };
      try {
        const den = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y,
          bekle: (ms) => { bekleyenler.push(ms); return Promise.resolve(); } });
        let y = null;
        try { y = await den._istek('/kal/liste', []); } catch (h) { y = { status: `${h.name}: ${h.message}` }; }
        const kalCagri = cagri.splice(0).length;
        const kalBekle = bekleyenler.splice(0);
        let veriHata = null;
        try { await den._istek('/kayit/veri', [['sira', 5]]); } catch (h) { veriHata = h; }
        const veriCagri = cagri.splice(0).length;
        ok('[!] /kal/liste ag hatasinda (TimeoutError) artan beklemeyle yeniden denenir; /kayit/veri denenmez',
           y && y.status === 200 && kalCagri === 3 && kalBekle.join() === `${ES.AG_BEKLE_MS},${2 * ES.AG_BEKLE_MS}`
           && veriHata instanceof TypeError && veriCagri === 1 && bekleyenler.length === 0,
           JSON.stringify({ durum: y && y.status, kalCagri, kalBekle, veriCagri, bekleme: bekleyenler }));
      } finally {
        globalThis.fetch = eskiFetch;
      }
    });
  }
  {
    const giden = [];
    const gonder = (m) => { giden.push(m); return Promise.resolve(); };
    const yok1 = ES.onayIslevi({ arsiv: false, bagli: true, gonder });
    const yok2 = ES.onayIslevi({ arsiv: true, bagli: false, gonder });
    const var_ = ES.onayIslevi({ arsiv: true, bagli: true, gonder });
    SONRA.push(async () => {
      if (var_) await var_(42);
      ok('[!] C3: VARSAYILAN onay YOK (arsiv kapali ya da bagli degil -> null); arsivde `Go<sira>` komut yolundan',
         yok1 === null && yok2 === null && typeof var_ === 'function' && giden.join() === 'Go42', giden.join());
    });
  }
  {
    const depo = {};
    const sahteDepo = { getItem: (k) => (k in depo ? depo[k] : null), setItem: (k, v) => { depo[k] = String(v); },
      removeItem: (k) => { delete depo[k]; } };
    const atan = { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('Quota'); },
      removeItem() { throw new Error('x'); } };
    ES.arsivYaz(7, true, sahteDepo);
    const yedi = ES.arsivOku(7, sahteDepo);
    const sekiz = ES.arsivOku(8, sahteDepo);
    ES.arsivYaz(7, false, sahteDepo);
    let istisna = '';
    try { ES.arsivYaz(7, true, atan); ES.arsivOku(7, atan); } catch (e) { istisna = e.message; }
    ok('[!] C3: "arsiv" secimi KART (akis kimligi) basina; kapatinca silinir; depo atarsa istisna yok',
       yedi === true && sekiz === false && !('olcum.arsiv.7' in depo) && !istisna, istisna || JSON.stringify(depo));
  }

  /* ── (c) sentetik akis: ortak/ paketleyicileriyle gercek kayitlar ──── */
  const u32 = (...d) => { const b = new Uint8Array(4 * d.length); const v = new DataView(b.buffer); d.forEach((x, i) => v.setUint32(4 * i, x, true)); return b; };
  const bitir = (n, s) => { const b = new Uint8Array(8); const v = new DataView(b.buffer); v.setUint32(0, n, true); v.setUint8(4, s); return b; };
  const utf8 = (s) => new TextEncoder().encode(s);
  const kanal = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
  const KAL = { normal: kanal(21), yuksek: kanal(201), i_ofset: 5, i_pga: 0.256, sont_ohm: 0.1,
    i_duzeltme: 1, sebeke_hz: 0, faz_kal_us: [0, 0] };
  function akisKur() {
    let sira = 0;
    const ham = [];
    const ekle = (tur, ot, yuk) => { sira++; ham.push(K.kayitPaketle(tur, sira, ot, yuk)); return sira; };
    const basla = (tur, hiz, unix, kms, acilis) => ekle(K.T_BASLA, sira + 1, K.baslaPaketle({ oturum_turu: tur,
      kal_bicim: 1, hiz_ms: hiz, unix_s: unix, kart_ms: kms, acilis, surum: 'A3-3C', kal: KAL, kal_no: 2 }));
    const nokta = (ms, v, i, w, bayrak = 0) => K.noktaPaketle({ kart_ms: ms, n: 40, bayrak, v_ort_kod: v,
      v_min_kod: Math.round(v) - 30, v_maks_kod: Math.round(v) + 50, i_ort_kod: i, i_min_kod: Math.round(i) - 3,
      i_maks_kod: Math.round(i) + 4, w_ort: w, w_min: w - 0.25, w_maks: w + 0.5 });
    const noktalar = (ot, ilk, ns) => {
      for (let j = 0; j < ns.length; j += 5) {
        const p = ns.slice(j, j + 5);
        const y = new Uint8Array(4 + 36 * p.length);
        y.set(u32(ilk + j), 0);
        p.forEach((b, k) => y.set(b, 4 + 36 * k));
        ekle(K.T_NOKTA, ot, y);
      }
    };
    const o = {};
    // A: olcum, 200 ms, saatli; ad + etiket + iki not
    o.A = basla(1, 200, 1790000000, 5000, 3);
    noktalar(o.A, 0, Array.from({ length: 20 }, (_, k) => nokta(5000 + 200 * (k + 1),
      1500 + 40 * k + (k === 7 ? 900 : 0), 300 + 5 * k, 1.5 + 0.01 * k)));
    ekle(K.T_NOT, 0, K.notPaketle(o.A, K.KNT_AD, 0, 0, utf8('Akü şarj — deneme')));
    ekle(K.T_NOT, 0, K.notPaketle(o.A, K.KNT_ETIKET, 0, 0, utf8('akü, şarj, 12V')));
    ekle(K.T_NOT, 0, K.notPaketle(o.A, K.KNT_NOT, 0, 0, utf8('genel not')));
    ekle(K.T_NOT, 0, K.notPaketle(o.A, K.KNT_NOT, 5000 + 200 * 11, 0, utf8('dalgalanma başladı')));
    ekle(K.T_BITIR, o.A, bitir(20, 1));
    // B: pil testi, 500 ms
    o.B = basla(2, 500, 1790001000, 90000, 3);
    ekle(K.T_OLAY, o.B, K.olayPaketle({ tur: K.KO_PIL_AYAR, kart_ms: 90001, kesme_v: 3.0, ocv: 4.1,
      azami_s: 36000, dcir_aralik_ms: 3000, dcir_ms: 200, kayit_hz: 2 }));
    noktalar(o.B, 0, Array.from({ length: 10 }, (_, k) => nokta(90000 + 500 * (k + 1), 2000 - 20 * k, 400, 2 - 0.02 * k)));
    ekle(K.T_OLAY, o.B, K.olayPaketle({ tur: K.KO_DCIR, kart_ms: 92600, no: 1, v_once: 3.9, i_once: 1,
      v_ani: 3.8, v_oturmus: 3.75, r_ani: 0.1, r_oturmus: 0.15, mah: 1.2, wh: 0.004 }));
    ekle(K.T_OLAY, o.B, K.olayPaketle({ tur: K.KO_PIL_SONUC, kart_ms: 95100, durum: 2, hata: 0, mah: 1.4,
      wh: 0.005, ocv: 4.1, v_son: 3.0, sure_ms: 5000, dcir_sayisi: 1 }));
    ekle(K.T_BITIR, o.B, bitir(10, 4));
    // C: ayrintili (hiz 0)
    o.C = basla(1, 0, 1790002000, 200000, 3);
    ekle(K.T_AYRINTI, o.C, K.ayrintiPaketle({ ilk: 0, t0_ms: 200003, t0_us: 200003417, bayrak: 0,
      ornekler: Array.from({ length: 12 }, (_, k) => [1000 + 10 * k, 200 + k, k ? 500 : 0, 0]) }));
    ekle(K.T_AYRINTI, o.C, K.ayrintiPaketle({ ilk: 12, t0_ms: 200070, t0_us: 200070120, bayrak: K.KA_SILME,
      ornekler: Array.from({ length: 8 }, (_, k) => [1200 + 10 * k, 220 + k, k ? 500 : 0, k === 3 ? K.KAO_V_HATA : 0]) }));
    ekle(K.T_BITIR, o.C, bitir(20, 1));
    // D: osiloskop gunlugu, tek tam yakalama
    o.D = basla(3, 1000, 1790003000, 300000, 3);
    ekle(K.T_SKOP, o.D, K.skopPaketle({ no: 1, ilk: 0, toplam: 8, parca: 0, kodlar: [100, 200, 300, 400, 300, 200, 100, 0],
      meta: { t_ms: 300100, sure_ms: 9, hz: 1000, tdiv_us: 1000, adim: 0.03, ofset: 1.5, tetik: 2, esik: 2048,
        histerezis: 8, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 25, onay: 2 } }));
    ekle(K.T_BITIR, o.D, bitir(0, 1));
    // E: saatsiz + saatsiz DEVAM (ikinci parcanin baslangica uzakligi BILINMIYOR)
    o.E = basla(1, 1000, 0, 7000, 3);
    noktalar(o.E, 0, Array.from({ length: 5 }, (_, k) => nokta(7000 + 1000 * (k + 1), 1000, 100, 1)));
    ekle(K.T_DEVAM, o.E, u32(4, 0, 2000, 5));
    noktalar(o.E, 5, Array.from({ length: 4 }, (_, k) => nokta(2000 + 1000 * (k + 1), 1100, 100, 1.2)));
    ekle(K.T_BITIR, o.E, bitir(9, 5));
    // P: saatli DEVAM, yeniden baslama arasi (1 s) bosluk esiginden (2.5 s) KISA — enerji acilis
    // sinirinin ustunden integre EDILMEMELI (rapor.js kurali); tek parca sanan hesap ayrisir.
    o.P = basla(1, 1000, 1790004000, 50000, 3);
    noktalar(o.P, 0, Array.from({ length: 5 }, (_, k) => nokta(50000 + 1000 * (k + 1), 1000 + 50 * k, 100, 1 + 0.1 * k)));
    ekle(K.T_DEVAM, o.P, u32(4, 1790004005, 3000, 5));
    noktalar(o.P, 5, Array.from({ length: 4 }, (_, k) => nokta(3000 + 1000 * (k + 1), 1400, 300, 3)));
    ekle(K.T_BITIR, o.P, bitir(9, 1));
    let n = 0;
    for (const h of ham) n += h.length;
    const b = new Uint8Array(n);
    let a = 0;
    for (const h of ham) { b.set(h, a); a += h.length; }
    return { b, o };
  }
  const { b: AKIS, o: NO } = akisKur();
  const kayitlar = K.akisCoz(AKIS);
  const ot = K.oturumlariKur(kayitlar);
  const A = ot.get(NO.A);
  const B = ot.get(NO.B);
  const C = ot.get(NO.C);
  const Dk = ot.get(NO.D);
  const E = ot.get(NO.E);
  const P = ot.get(NO.P);
  const sonSira = ES.oturumSonSiralari(kayitlar);
  ok('Sentetik akis ortak/ ile cozuldu: alti oturum, A`nin adi/etiketi/notlari',
     ot.size === 6 && A.ad === 'Akü şarj — deneme' && A.etiketler.join('|') === 'akü|şarj|12V' && A.notlar.size === 2,
     `${ot.size} oturum`);

  /* ── (d) liste birlesimi, nerede, siralama ─────────────────────────── */
  const yerel = { kimlik: 7, oturumlar: ot, sonSira };
  const eski = { kimlik: 3, oturumlar: K.oturumlariKur(K.akisCoz(akisKur().b)), sonSira: new Map() };
  const kartListe = { kimlik: 7, aktif: 999, oturumlar: [
    { id: NO.A, tur: 1, hiz_ms: 200, unix_s: 1790000000, kart_ms: 5000, acilis: 3, ilk: NO.A,
      son: sonSira.get(NO.A) + 3, nokta: 20, durum: 2, basi_silindi: 0 },
    { id: NO.B, tur: 2, hiz_ms: 500, unix_s: 1790001000, kart_ms: 90000, acilis: 3, ilk: NO.B,
      son: sonSira.get(NO.B), nokta: 10, durum: 2, basi_silindi: 0 },
    { id: 999, tur: 1, hiz_ms: 0, unix_s: 1790009000, kart_ms: 1, acilis: 3, ilk: 1000, son: 1010, nokta: 77,
      durum: 1, basi_silindi: 0 },
  ] };
  const satirlar = KL.listeBirlestir({ kart: kartListe, yereller: [yerel, eski] });
  const bul = (k, o_) => satirlar.find((s) => s.kimlik === k && s.oturum === o_);
  ok('[!] C4 nerede: kartta+yerel -> ikisi, yalniz kart -> kart, yalniz yerel -> tarayici',
     bul(7, NO.A).nerede === 'ikisi' && bul(7, 999).nerede === 'kart' && bul(7, NO.E).nerede === 'tarayici'
     && bul(7, NO.C).nerede === 'tarayici',
     satirlar.map((s) => `${s.kimlik}:${s.oturum}=${s.nerede}`).join(' '));
  ok('[!] C4: yerel kopya karttan GERIDEYSE "eksik"; aktif oturum "kaydediliyor"; kartin turu (hiz 0 -> ayrintili)',
     bul(7, NO.A).eksik === true && bul(7, NO.B).eksik === false && bul(7, 999).durum === 'kayitta'
     && bul(7, 999).tur === 'ayrinti' && bul(7, NO.A).durum === 'bitti');
  ok('[!] C2: baska kimligin oturumu "eski kart kopyasi", adresi @kimlik tasiyor; guncel akis @siz',
     bul(3, NO.A).eskiKart === true && bul(3, NO.A).adres === `#/kayit/${NO.A}@3`
     && bul(7, NO.A).eskiKart === false && bul(7, NO.A).adres === `#/kayit/${NO.A}`);
  const sira = satirlar.map((s) => `${s.kimlik}:${s.oturum}`);
  const beklenenSira = [999, NO.P, NO.E, NO.D, NO.C, NO.B, NO.A].map((x) => `7:${x}`)
    .concat([NO.P, NO.E, NO.D, NO.C, NO.B, NO.A].map((x) => `3:${x}`));
  ok('[!] Siralama yeni -> eski: guncel akis once, akis icinde oturum no azalan',
     sira.join() === beklenenSira.join(), sira.join(' '));
  ok('Kart bilinmiyorsa (null) her yerel oturum "tarayici", eski kart isareti yok',
     KL.listeBirlestir({ kart: null, yereller: [yerel] }).every((s) => s.nerede === 'tarayici' && !s.eskiKart));
  ok('[!] Liste satiri adi, etiketleri, sureyi (son nokta - baslangic) ve nokta sayisini tasiyor',
     bul(7, NO.A).ad === 'Akü şarj — deneme' && bul(7, NO.A).sureMs === 4000 && bul(7, NO.A).nokta === 20
     && bul(7, NO.C).nokta === 20 && bul(7, NO.D).nokta === 1 && bul(7, NO.E).sureMs === null,
     `A sure=${bul(7, NO.A).sureMs} E sure=${bul(7, NO.E).sureMs}`);

  /* ── (e) arama ve suzgec ─────────────────────────────────────────── */
  ok('[!] metinSadele Turkce duyarsiz: "AKÜ ŞARJ İıI ÇĞÖ" -> "aku sarj iii cgo"',
     KL.metinSadele('AKÜ ŞARJ İıI ÇĞÖ') === 'aku sarj iii cgo', KL.metinSadele('AKÜ ŞARJ İıI ÇĞÖ'));
  const ara = (q, s = {}) => KL.satirSuz(satirlar, { arama: q, ...s }).map((x) => `${x.kimlik}:${x.oturum}`);
  ok('[!] Arama ad/etiket/not metninde Turkce duyarsiz ("aku", "SARJ", "12v", "dalgalanma")',
     ara('aku').join() === `7:${NO.A},3:${NO.A}` && ara('SARJ').length === 2 && ara('12v').length === 2
     && ara('dalgalanma').length === 2 && ara('aku dalga').length === 2 && ara('aku yok').length === 0,
     ara('aku').join(' '));
  ok('[!] Numara: "#N" yalniz o oturum; "N" numara ya da metin',
     ara('#' + NO.B).join() === `7:${NO.B},3:${NO.B}` && ara(String(999)).join() === '7:999'
     && ara('#9999').length === 0);
  ok('[!] Suzgec: tur (olcum ayrintiliyi da kapsar) ve nerede',
     ara('', { tur: 'olcum' }).includes(`7:${NO.C}`) && !ara('', { tur: 'olcum' }).includes(`7:${NO.B}`)
     && ara('', { tur: 'pil' }).join() === `7:${NO.B},3:${NO.B}` && ara('', { nerede: 'kart' }).join() === '7:999'
     && ara('', { nerede: 'ikisi' }).join() === `7:${NO.B},7:${NO.A}`);

  /* ── (f) rota ─────────────────────────────────────────────────────── */
  const rc = KL.rotaCoz;
  ok('[!] Rota: #/kayit/12, #/kayit/12@7, #/kayit/12/rapor; bicimsiz -> liste; rotaYaz tersi',
     JSON.stringify(rc('#/kayit/12')) === '{"oturum":12,"kimlik":null,"rapor":false}'
     && JSON.stringify(rc('#/kayit/12@7/rapor')) === '{"oturum":12,"kimlik":7,"rapor":true}'
     && rc('#/kayitlar').oturum === null && rc('#/kayit/x').oturum === null && rc('#/kayit/').oturum === null
     && ['#/kayit/12', '#/kayit/12@7', '#/kayit/12/rapor', '#/kayit/3@0/rapor', '#/kayitlar']
       .every((h) => KL.rotaYaz(rc(h)) === h));
  ok('Rotadaki oturumun akisi: kimlik verilmisse o, yoksa guncel akis',
     KL.rotaAkisi({ oturum: NO.A, kimlik: 3 }, satirlar) === 3 && KL.rotaAkisi({ oturum: NO.A, kimlik: null }, satirlar) === 7);

  /* ── (g) seri hazirlama, imlec, enerji ─────────────────────────────── */
  const hA = KG.grafikSerileri(A, { kayitlar });
  const nsA = D.noktaSerileri(A, { kayitlar });
  const artan = (t) => t.every((x, k) => k === 0 || x >= t[k - 1]);
  ok('[!] Nokta oturumu: 9 seri (V/I/W ort + min/maks zarfi), HEPSI ayni t; t = baslangictan gecen ms',
     hA.tur === 'nokta' && hA.seriler.length === 9 && hA.seriler.every((s) => s.t === hA.t)
     && hA.t.length === 20 && hA.t[0] === 200 && hA.t[19] === 4000 && artan(hA.t)
     && hA.seriler.filter((s) => s.zarf).length === 6,
     `${hA.tur} ${hA.seriler.map((s) => s.ad).join(',')}`);
  ok('[!] Seri degerleri ortak/disari.noktaSerileri ile AYNI (V ort, I min, W maks); bosluk = hiz x 2.5',
     hA.seriler[0].y === nsA.vOrt || hA.seriler[0].y.every((x, k) => Object.is(x, nsA.vOrt[k]))
     && hA.seriler.find((s) => s.ad === 'I min').y.every((x, k) => Object.is(x, nsA.iMin[k]))
     && hA.seriler.find((s) => s.ad === 'W maks').y.every((x, k) => Object.is(x, nsA.wMaks[k]))
     && hA.boslukMs === 500 && hA.seriler.every((s) => s.boslukMs === 500));
  const hC = KG.grafikSerileri(C, { kayitlar });
  ok('Ayrintili oturum: V/I/W (zarf yok), bosluk 16.38 ms; osiloskop oturumu grafiksiz (3E)',
     hC.tur === 'ayrinti' && hC.seriler.map((s) => s.ad).join() === 'V,I,W' && hC.boslukMs === D.AYRINTI_BOSLUK_MS
     && hC.t.length === 20 && artan(hC.t) && KG.grafikSerileri(Dk, { kayitlar }).tur === 'yok');
  const hE = KG.grafikSerileri(E, { kayitlar });
  ok('[!] K1: saatsiz DEVAM parcasi oncekinin ARDINA (3 x bosluk ara), "tahmini" isaretli; zaman azalmiyor',
     hE.tahmini.join() === '1' && artan(hE.t) && hE.t[4] === 5000 && hE.t[5] === 5000 + 3 * 2500 + 0,
     `tahmini=${hE.tahmini} t=${Array.from(hE.t).join(',')}`);
  const gor = KG.gorunurluk(hA.seriler, { v: true, sag: 'guc', zarf: false });
  ok('K4 gorunurluk: sag eksen tek birim (guc secilince akim gizli), zarf kapali',
     gor.filter((s) => !s.gizli).map((s) => s.ad).join() === 'V,W'
     && KG.gorunurluk(hA.seriler, {}).filter((s) => !s.gizli).length === 6);
  {
    const hP = KG.grafikSerileri(P, { kayitlar });
    ok('P: saatli DEVAM parcasi GERCEK yerinde (tahmini degil), ara bosluk esiginden kisa',
       hP.tahmini.length === 0 && hP.t[4] === 5000 && hP.t[5] === 6000 && hP.t[5] - hP.t[4] < hP.boslukMs,
       Array.from(hP.t).join(','));
  }
  for (const [ad, o_] of [['A (olcum)', A], ['B (pil)', B], ['E (DEVAM)', E], ['P (DEVAM, kisa ara)', P]]) {
    const h = KG.grafikSerileri(o_, { kayitlar });
    const e = KG.aralikEnerji(h, h.t[0], h.t[h.t.length - 1]);
    const r = R.oturumRaporu(o_, { kayitlar });
    ok(`[!] K3: tam aralikta okuma enerjisi RAPORLA bit bit ayni — ${ad}`,
       e.wh === r.enerji.wh && e.mah === r.enerji.mah && e.wh !== 0, `okuma ${e.wh}/${e.mah} rapor ${r.enerji.wh}/${r.enerji.mah}`);
  }
  {
    const e = KG.aralikEnerji(hC, hC.t[0], hC.t[hC.t.length - 1]);
    const r = R.oturumRaporu(C, { kayitlar });
    const yakin_ = (x, y) => Math.abs(x - y) <= 1e-12 * Math.max(1, Math.abs(y));
    ok('K3: ayrintili oturumda da okuma enerjisi raporla ayni (1e-12)', yakin_(e.wh, r.enerji.wh) && yakin_(e.mah, r.enerji.mah),
       `${e.wh} ~ ${r.enerji.wh}`);
  }
  {
    /* W1/Y7 (K3c): yakalama isaretleri ZAMANINDA (META t_ms) — yakalamanin kaydi SONRAKI
       orneklerden sonra yazilir (kayit sirasi zaman sirasi degil); DEVAM'dan sonraki yakalama
       KENDI acilisinin ofsetinde. */
    let sira = 0;
    const ham = [];
    const ekle = (tur, ot_, yuk) => { sira++; ham.push(K.kayitPaketle(tur, sira, ot_, yuk)); return sira; };
    const id = ekle(K.T_BASLA, 1, K.baslaPaketle({ oturum_turu: 1, kal_bicim: 1, hiz_ms: 0, unix_s: 1790005000,
      kart_ms: 400000, acilis: 3, surum: 'A3-W1', kal: KAL, kal_no: 2 }));
    const ayr = (ilk, ms, n) => ekle(K.T_AYRINTI, id, K.ayrintiPaketle({ ilk, t0_ms: ms, t0_us: ms * 1000, bayrak: 0,
      ornekler: Array.from({ length: n }, (_, k) => [1000 + k, 200 + k, k ? 500 : 0, 0]) }));
    const skop = (no, t) => ekle(K.T_SKOP, id, K.skopPaketle({ no, ilk: 0, toplam: 2, parca: 0, kodlar: [1, 2],
      meta: { t_ms: t, sure_ms: 30, hz: 1000, tdiv_us: 1000, adim: 0.03, ofset: 1.5, tetik: 0, esik: 2048,
        histerezis: 8, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 25, onay: 2 } }));
    ayr(0, 400010, 10);                  // 400010..400028 ms
    ayr(10, 400070, 10);                 // yakalama 400030 + 30 ms
    skop(1, 400030);                     // kaydi SONRAKI orneklerden sonra
    ekle(K.T_DEVAM, id, u32(4, 1790005002, 1000, 20));
    ayr(20, 1010, 10);
    ayr(30, 1070, 10);
    skop(2, 1035);
    ekle(K.T_BITIR, id, bitir(40, 1));
    const b2 = new Uint8Array(ham.reduce((x, h) => x + h.length, 0));
    ham.reduce((x, h) => { b2.set(h, x); return x + h.length; }, 0);
    const kay2 = K.akisCoz(b2);
    const o2 = K.oturumlariKur(kay2).get(id);
    const h2 = KG.grafikSerileri(o2, { kayitlar: kay2 });
    const is2 = KG.yakalamaIsaretleri(o2, h2);
    ok('[!] W1/Y7 K3c: yakalama isareti iki ornegin ARASINDA (META t_ms), DEVAM sonrasi kendi acilisinda; "S<no>"',
       is2.length === 2 && is2[0].metin === 'S1' && is2[1].metin === 'S2' && is2[0].t === 30 && is2[1].t === 2035
       && h2.t[9] < is2[0].t && is2[0].t < h2.t[10] && h2.t[29] < is2[1].t && is2[1].t < h2.t[30]
       && KG.yakalamaIsaretleri(A, hA).length === 0,
       JSON.stringify(is2) + ' t9..10=' + h2.t[9] + ',' + h2.t[10] + ' t29..30=' + h2.t[29] + ',' + h2.t[30]);
    /* W1 inceleme: ~1.9 M ornekli oturumda her yeniden kurulum saniyeler + yuzlerce MB. Sayac:
       ayrintiOrnekler kayit basina t0_us'u IKI kez okur, baska okuyan yok. */
    const o3 = K.oturumlariKur(kay2).get(id);
    let okuma = 0;
    o3.ayrinti = o3.ayrinti.map((r) => {
      const { t0_us: t0, ...g } = r;
      return Object.defineProperty(g, 't0_us', { get() { okuma++; return t0; }, enumerable: true });
    });
    const h3 = KG.grafikSerileri(o3, { kayitlar: kay2 });
    const kGrafik = okuma / (2 * o3.ayrinti.length);
    okuma = 0;
    const is3 = KG.yakalamaIsaretleri(o3, h3);
    ok('[!] W1 inceleme K3c: grafik ornek listesini BIR kez kurar, yakalama isaretleri onun yerlerini kullanir (yeniden KURMAZ)',
       kGrafik === 1 && okuma === 0 && JSON.stringify(is3) === JSON.stringify(is2),
       `grafik ${kGrafik} kurulum, isaretler ${okuma / (2 * o3.ayrinti.length)}`);
  }
  {
    const ok2 = KG.okumaHesapla(hA, 1450, 610);           // ters sirayla da
    const v = nsA.vOrt;
    const ort = (v[3] + v[4] + v[5] + v[6]) / 4;   // [610, 1450] icindeki ornekler: t 800..1400 (sira 3..6)
    ok('[!] Imlec okumasi: A <= B siralanir, deger EN YAKIN ham ornek, dV = B - A, ort aralik ortalamasi',
       ok2.tA === 610 && ok2.tB === 1450 && Object.is(ok2.v.a, v[2]) && Object.is(ok2.v.b, v[6])
       && ok2.dV === v[6] - v[2] && Math.abs(ok2.v.ort - ort) < 1e-12 && ok2.enerji && ok2.enerji.wh > 0,
       `A=${ok2.v.a} B=${ok2.v.b} ort=${ok2.v.ort}`);
    const vMin = nsA.vMin;
    ok('[!] K2: okumanin min/maks`i min/maks KODLARINDAN (sicrama ortalamada erir, burada kalir)',
       Object.is(KG.okumaHesapla(hA, 0, 5000).v.maks, Math.max(...nsA.vMaks))
       && Object.is(KG.okumaHesapla(hA, 0, 5000).v.min, Math.min(...vMin)));
  }
  {
    const notlar = KG.notListesi(A, hA);
    ok('[!] Notlar: genel not grafikte yer YOK; zamanli not grafikte kendi aninda (x = 2200 ms)',
       notlar.length === 2 && notlar[0].genel && notlar[0].x === null && notlar[1].x === 2200
       && notlar[1].metin === 'dalgalanma başladı', JSON.stringify(notlar));
    const d = { veriT0: 0, veriT1: 10000, t0: 0, t1: 10000 };
    const p = KG.notPenceresi(d, 2200);
    ok('Nota gitmek pencereyi ona ortalar (butun veri gorunuyorsa onda bire daralir)',
       p.t0 === 1700 && p.t1 === 2700 && KG.notPenceresi({ ...d, t0: 0, t1: 400 }, 2200).t1 === 2400);
  }

  /* ── (h) disa aktarma = ortak/ ciktisi ────────────────────────────── */
  {
    const es = (a, b) => a.length === b.length && a.every((x, k) => x === b[k]);
    const csvTr = KG.disariUret('csv_tr', A, kayitlar);
    const csvEn = KG.disariUret('csv_en', A, kayitlar);
    const beklenTr = D.csvBayt(D.oturumCsv(A, { ...D.BICIM_EXCEL_TR, kayitlar }));
    const beklenEn = D.csvBayt(D.oturumCsv(A, { ...D.BICIM_EN, kayitlar }));
    const ilkSatir = new TextDecoder().decode(csvTr.bayt).split('\r\n')[0];
    ok('[!] C6: CSV (Excel-TR) baytlari ortak/oturumCsv ile AYNI; BOM + `;` + ondalik virgul',
       es(csvTr.bayt, beklenTr) && csvTr.bayt[0] === 0xEF && csvTr.bayt[1] === 0xBB && csvTr.bayt[2] === 0xBF
       && ilkSatir.includes(';') && csvTr.mime.startsWith('text/csv')
       && /^\d+,\d{6}$/.test(new TextDecoder().decode(csvTr.bayt).split('\r\n')[1].split(';')[8]),
       ilkSatir.slice(0, 60));
    ok('[!] C6: CSV (EN) ortak/oturumCsv(BICIM_EN) ile AYNI; ad kayit-<no>-<ad>-en.csv',
       es(csvEn.bayt, beklenEn) && csvEn.ad === `kayit-${NO.A}-aku-sarj-deneme-en.csv`
       && KG.dosyaAdi(A, '', 'csv') === `kayit-${NO.A}-aku-sarj-deneme.csv`, csvEn.ad);
    const ham = KG.disariUret('ham', A, kayitlar);
    const geri = K.akisCoz(ham.bayt);
    ok('[!] C6: ham .kyt = hamDisari: kartin baytlari (oturumun kayitlari + hedefi o olan NOT`lar), yeniden okunur',
       es(ham.bayt, D.hamDisari(kayitlar, NO.A)) && ham.ad.endsWith('.kyt')
       && geri.length === kayitlar.filter((k) => k.oturum === NO.A
         || (k.tur === K.T_NOT && new DataView(k.yuk.buffer, k.yuk.byteOffset, 4).getUint32(0, true) === NO.A)).length
       && geri.every((k) => es(k.yuk, kayitlar.find((x) => x.sira === k.sira).yuk)), `${geri.length} kayit`);
    const pil = KG.disariUret('pil_tr', B, kayitlar);
    const ayr = KG.disariUret('ayrinti_tr', C, kayitlar);
    const y = Dk.skoplar.values().next().value;
    const sk = KG.disariUret('skop', Dk, kayitlar, y);
    ok('[!] C6: pil CSV, ayrintili CSV ve yakalama CSV`si ortak/ ile ayni; tur basina dogru secenekler',
       es(pil.bayt, D.csvBayt(D.pilCsv(B, { ...D.BICIM_EXCEL_TR, kayitlar })))
       && es(ayr.bayt, D.csvBayt(D.ayrintiCsv(C, { ...D.BICIM_EXCEL_TR, kayitlar })))
       && es(sk.bayt, D.csvBayt(D.skopCsv(y, D.BICIM_EXCEL_TR)))
       && KG.disariTurleri(A).join() === 'csv_tr,csv_en,ham' && KG.disariTurleri(B).join() === 'pil_tr,pil_en,ham'
       && KG.disariTurleri(C).join() === 'ayrinti_tr,ayrinti_en,ham' && KG.disariTurleri(Dk).join() === 'ham',
       `${pil.ad} ${ayr.ad} ${sk.ad}`);
  }

  /* ── (i) IndexedDB deposu: saf parca hesabi + kilit ────────────────── */
  {
    const kaynakB = Uint8Array.from({ length: 150 }, (_, k) => k);
    const p = DP.parcala(kaynakB, 64);
    kaynakB[0] = 99;
    ok('[!] parcala: en cok N baytlik KOPYALAR (kaynak degisse de parca degismez)',
       p.map((x) => x.length).join() === '64,64,22' && p[0][0] === 0 && p[2][21] === 149);
    const ps = [{ no: 0, bas: 0, veri: Uint8Array.from({ length: 10 }, (_, k) => k) },
      { no: 1, bas: 10, veri: Uint8Array.from({ length: 10 }, (_, k) => 10 + k) }];
    const oku = (bas, top) => Array.from(DP.parcalardanOku(ps, bas, top)).join(',');
    ok('[!] parcalardanOku: bas`tan sona birlestirir (parca icinden, sinirdan, sondan otede bos)',
       oku(5, 20) === '5,6,7,8,9,10,11,12,13,14,15,16,17,18,19' && oku(10, 20) === '10,11,12,13,14,15,16,17,18,19'
       && oku(20, 20) === '' && oku(25, 20) === '' && oku(0, 15) === '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14');
    const k1 = DP.kirpPlani(ps, 15, 20);
    const k2 = DP.kirpPlani(ps, 10, 20);
    const k3 = DP.kirpPlani(ps, 25, 20);
    ok('[!] kirpPlani: ortadan keser, sinirda parca siler, uzunsa SIFIRLA uzatir (Python truncate)',
       JSON.stringify(k1) === '{"sil":[],"kes":{"no":1,"boy":5},"uzat":0}'
       && JSON.stringify(k2) === '{"sil":[1],"kes":null,"uzat":0}'
       && JSON.stringify(k3) === '{"sil":[],"kes":null,"uzat":5}'
       && JSON.stringify(DP.kirpPlani(ps, 0, 20)) === '{"sil":[0,1],"kes":null,"uzat":0}');
    const t = new Date(2026, 9, 2, 14, 3, 5);
    const var_ = new Set(['kalibrasyon-20261002-140305.json']);
    ok('Kalibrasyon arsivi adi bellekDepo bicimi, ayni saniyede -1',
       DP.arsivAdi(t, () => false) === 'kalibrasyon-20261002-140305.json'
       && DP.arsivAdi(t, (a) => var_.has(a)) === 'kalibrasyon-20261002-140305-1.json');
    const dp = kaynak('depo_idb.js');
    const kod = dp.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    ok('[!] C2: BUTUN yazma islemleri `durability: \'strict\'` (tek islem yardimcisindan)',
       (kod.match(/'readwrite'/g) || []).length === 1
       && /'readwrite', \{ durability: 'strict' \}/.test(kod)
       && (kod.match(/\.transaction\(/g) || []).length === 2);
    /* Web Locks taklidi: ifAvailable — dolu kilit null verir. */
    let tutulan = false;
    const kilitler = { request(ad, s, fn) {
      if (tutulan) return Promise.resolve(fn(null));
      tutulan = true;
      return Promise.resolve(fn({ name: ad })).then((x) => { tutulan = false; return x; });
    } };
    SONRA.push(async () => {
      const b1 = await DP.kilitAl('olcum-kayit:7', kilitler);
      let ikinci = '';
      try { await DP.kilitAl('olcum-kayit:7', kilitler); } catch (e) { ikinci = e.name; }
      await b1();
      await new Promise((r) => setImmediate(r));
      const b2 = await DP.kilitAl('olcum-kayit:7', kilitler).catch((e) => e.name);
      ok('[!] Web Locks: ayni akisa ikinci esitleme CalismaHatasi; birakinca yeniden alinir',
         ikinci === 'CalismaHatasi' && typeof b2 === 'function', `ikinci=${ikinci} b2=${typeof b2}`);
      if (typeof b2 === 'function') await b2();
      const s1 = await DP.kilitAl('olcum-kayit:8', undefined);
      let s2 = '';
      try { await DP.kilitAl('olcum-kayit:8', undefined); } catch (e) { s2 = e.name; }
      await s1();
      const s3 = await DP.kilitAl('olcum-kayit:8', undefined).catch((e) => e.name);
      ok('[!] Web Locks YOKSA (kartin http:// koken`i) sekme ici kilit ayni kurali uyguluyor',
         s2 === 'CalismaHatasi' && typeof s3 === 'function', `s2=${s2}`);
      if (typeof s3 === 'function') await s3();
    });
  }

  /* ── (j) sablon siniflari ve renkler ──────────────────────────────── */
  {
    const css = cssOku();
    const siniflar = new Set();
    for (const ad of ['kayitlar.js', 'kayit_gorunum.js']) {
      for (const m of kaynak(ad).matchAll(/\sclass="([^"{}]+)"/g)) {
        for (const c of m[1].split(/\s+/)) if (/^[a-z][a-z0-9-]*$/.test(c)) siniflar.add(c);
      }
    }
    for (const c of ['kl-nerede-kart', 'kl-nerede-tarayici', 'kl-nerede-ikisi', 'kl-durum-kayitta',
      'kl-durum-acik', 'kl-durum-bitti', 'kl-dikkat', 'kg-rapor-kipi']) siniflar.add(c);
    const tanimsiz = [...siniflar].filter((c) => c !== 'kg-rapor-kipi'
      && !new RegExp('\\.' + c + '(?![A-Za-z0-9_-])').test(css));
    ok('[!] Ekran sablonlarindaki her sinif (dinamik nerede/durum dahil) CSS`te TANIMLI',
       siniflar.size >= 40 && tanimsiz.length === 0, tanimsiz.join(' ') || `${siniflar.size} sinif`);
    const bolum = css.slice(css.indexOf('3C — KAYITLAR'));
    ok('[!] 3C stilleri YALNIZ belirtecle: sabit renk (#hex / rgb) yok, uc gorunumde ayni kurallar',
       css.indexOf('3C — KAYITLAR') > 0 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(bolum.replace(/\/\*[\s\S]*?\*\//g, '')));
    const telefon = [...css.matchAll(/@media \(max-width: 620px\)\s*\{([\s\S]*?)\n\}/g)].map((m) => m[1]).join('\n');
    ok('[!] Telefonda (<=620px) liste satiri TEK sutuna iniyor (390 px`te yatay tasma yok)',
       /\.kl-satir\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(telefon));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   25. CANLI + KABUK + KAYIT DENETIMI (3D — alt proje 3, D1-D8)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3D kararlari". Burada:
   (a) KABUK: sol serit gezinmesi (3G'den beri Karsilastirma da), cekmece (Esc / secim
       kapatir, odak menu dugmesine doner), baglanti kipi, esitlenmemis orani.
   (b) PASIF DURUM: G / GA / GT / GP ayristiricilari — alan ADLARI firmware'in
       protokol yorumundan, SAYISI onun snprintf bicimindan TURETILIYOR (kart
       bir alan eklerse kirmizi); `G?` yalniz baglaninca + kayit komutundan
       sonra (YOKLAMA YOK — davranissal: zamanlayicilar elle kosturuluyor).
   (c) KOMUT URETICILERI: firmware'in sinirlariyla (hiz listesi, 175 BAYT,
       not 120 bayt, plan 30 gun / 1.7e9 / 1 yil) — sabitler firmware'den.
   (d) OKUMA + KALAN: son 10 s min/maks, "~X kaldi" yalniz >= 60 s gozlemle.
   (e) CANLI GRAFIK: ekran/canli.js + GERCEK ortak/grafik.js cizim plani —
       bolum 11/21'deki eski elle cizim iddialari burada yeni koda gore.
   Gercek tarayici (cekmece 390 px, CDP fare, SSE + /komut, uc gorunum):
   tarayici_canli.py (T3D).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 25. Canli + kabuk + kayit denetimi (3D) ---');
{
  const html = yorumsuz(htmlKaynak);
  const kod = yorumsuz(appKaynak);
  const css = cssOku();
  const SZ = sozlukTum();
  const GR = require(path.join(KOK, 'ortak', 'src', 'grafik.js'));
  const CN = require(path.join(ARAYUZ, 'ekran', 'canli.js'));
  const ESx = require(path.join(ARAYUZ, 'ekran', 'esitleme.js'));
  const al = (ad) => vm.runInContext(ad, sandbox);
  const YONET_H = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_yonet.h'), 'utf8');
  const PLAN_H = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_plan.h'), 'utf8');
  const BICIM_H = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_bicim.h'), 'utf8');
  const inoYorumsuz = ino.replace(/\/\*[\s\S]*?\*\//g, ' ');

  /* ── (a) KABUK ──────────────────────────────────────────────────── */
  const G = al('GORUNUMLER');
  /* 3G (KR6): Karsilastirma yazildi — D1'in "yazilmamis ekran seritte YOK" kurali onu artik GOSTERIR. */
  ok('[!] D1/KR6: serit gezinmesi Canli · Osiloskop · Pil testi · Kayitlar · Karsilastirma · Ayarlar · Konsol',
     G.map((g) => g.id).join(' ') === 'canli skop pil kayitlar karsilastir ayar konsol', G.map((g) => g.id).join(' '));
  ok('[!] D8: her gorunumun adi ve alt yazisi SOZLUKTE (tr + en, bos degil)',
     G.every((g) => [g.ad, g.alt].every((a) => a in SZ.SOZLUK && SZ.SOZLUK[a].tr && SZ.SOZLUK[a].en)),
     G.map((g) => g.ad).join(' '));
  const serit = html.match(/<aside id="serit" class="serit"[^>]*>([\s\S]*?)<\/aside>/);
  ok('[!] D1: serit = ad + alt satir (yer · surum) + baglanti + gezinme (v-for gorunumler) + alt bilgi (esitlenmemis)',
     !!serit && /\{\{ seritAlt \}\}/.test(serit[1]) && /class="gorunum-nav"/.test(serit[1])
     && /v-for="g in gorunumler"/.test(serit[1]) && /@click="gorunumSecildi"/.test(serit[1])
     && /\{\{ esitlenmemisYazi \}\}/.test(serit[1]));
  ok('[!] D1: menu dugmesi cekmeceyi denetliyor (aria-controls="serit", aria-expanded)',
     /<button[^>]*class="menu-dugme"[^>]*ref="menuDugme"[^>]*@click="cekmeceDegistir"[^>]*:aria-expanded="cekmeceAcik \? 'true' : 'false'"[^>]*aria-controls="serit"/.test(html));
  {
    const u = ornek();
    let odak = 0;
    u.$nextTick = (f) => f && f();
    u.$refs = { menuDugme: { focus() { odak++; } } };
    u.cekmeceDegistir();
    const acildi = u.cekmeceAcik === true;
    u.tusBasildi({ key: 'a', preventDefault() {} });
    const harfKapatmadi = u.cekmeceAcik === true;
    let engel = false;
    u.tusBasildi({ key: 'Escape', preventDefault() { engel = true; } });
    const escKapadi = u.cekmeceAcik === false && odak === 1 && engel;
    u.cekmeceAc();
    u.gorunumSecildi();
    ok('[!] D1: cekmece — dugme acar, Esc kapatir ve odagi menu dugmesine dondurur, secim kapatir; baska tus kapatmaz',
       acildi && harfKapatmadi && escKapadi && u.cekmeceAcik === false && odak === 2,
       `acildi=${acildi} harf=${harfKapatmadi} esc=${escKapadi} odak=${odak}`);
    u.tusBasildi({ key: 'Escape', preventDefault() { throw new Error('kapaliyken engellendi'); } });
    ok('Cekmece kapaliyken Esc sayfanin baska isine KARISMIYOR (grafik imleci vb.)', u.cekmeceAcik === false);
  }
  {
    const u = ornek();
    const kip = (t, b, k) => { u.tasiyiciAdi = t; u.bagliTasiyici = b; u.kopruda = k; return u.baglantiKipi; };
    ok('[!] D1: baglanti kipi USB / WiFi / kopru / demo (kopru `/durum` ile ayriliyor)',
       kip('seri', 'seri', false) === 'usb' && kip('akis', 'akis', false) === 'wifi'
       && kip('akis', 'akis', true) === 'kopru' && kip('demo', 'demo', false) === 'demo',
       [kip('seri', 'seri', false), kip('akis', 'akis', false), kip('akis', 'akis', true)].join(' '));
    u.tasiyiciAdi = 'seri'; u.bagliTasiyici = 'seri'; u.bagli = true;
    ok('Baglanti rozeti "Cevrimici · USB"; bagli degilken "Bagli degil"',
       u.baglantiYazi === 'Çevrimiçi · USB' && (u.bagli = false, u.baglantiYazi === 'Bağlı değil'), u.baglantiYazi);
    ok('Seritin "esitlenmemis" alt bilgisi G gelmeden "—"', u.esitlenmemisYazi.includes('—'), u.esitlenmemisYazi);
    u.satirIsle('G 2 61 24337 50012 49000 310 45 0 2900 1300 4 300 0');
    ok('[!] D1: alt bilgi = G satirinin `onaysiz` alani (binde 45 -> %4.5)', u.esitlenmemisYazi === 'Eşitlenmemiş: %4.5',
       u.esitlenmemisYazi);
  }
  {
    const depo = (v) => ({ getItem: (k) => (k === 'olcum.dil' ? v : null) });
    const atan = { getItem() { throw new Error('SecurityError'); } };
    const girdiler = [null, '"en"', '"tr"', 'en', '"EN"', '{bozuk', '42', '"de"'];
    const dilSec = al('dilSec');
    const fark = girdiler.filter((v) => dilSec(depo(v)) !== ESx.dilOku(depo(v)));
    ok('[!] D8: kabugun dil secimi ekran/esitleme.js dilOku ile HER girdide ayni (ve depo atarsa tr)',
       fark.length === 0 && dilSec(atan) === 'tr' && dilSec(null) === 'tr' && dilSec(depo('"en"')) === 'en',
       fark.join(' ') || `${girdiler.length} girdi`);
  }
  {
    const afisCoz = al('afisCoz');
    const fw = (inoYorumsuz.match(/Serial\.println\(F\("(Olcum Karti[^"]*)"\)\)/) || [])[1];
    const a = fw ? afisCoz(fw) : null;
    ok('[!] D1: firmware acilis afisi taniniyor (metin firmware kaynagindan), surum afisteki metin',
       !!a && a.surum === fw.replace(/^Olcum Karti\s*—\s*/, '') && a.fw === null
       && afisCoz('Olcum Karti — Asama 3 A3-1F').fw === 'A3-1F' && afisCoz('Kayit: 11648 KB') === null,
       fw || 'afis yok');
  }

  /* ── (b) PASIF DURUM: G / GA / GT / GP ─────────────────────────── */
  const KS = al('KAYIT_SATIRLARI');
  const kayitSatiriCoz = al('kayitSatiriCoz');
  const fwSatir = {};
  for (const [tur, islev] of [['G', 'kayit_durum_bas'], ['GA', 'kayit_ga_bas'], ['GT', 'kayit_gt_bas'], ['GP', 'kayit_gp_bas']]) {
    const bicim = (ino.match(new RegExp('snprintf\\(t, sizeof\\(t\\), "' + tur + ' ([^"]*)"')) || [])[1];
    const i = ino.indexOf('static void ' + islev + '(');
    const yorum = i > 0 ? (ino.slice(0, i).match(/\/\*((?:(?!\*\/)[\s\S])*)\*\/\s*$/) || [])[1] || '' : '';
    const adlar = [...yorum.replace(/^[\s\S]*?\b(G[ATP]?) </, '$1 <').matchAll(/<(\w+?)(?:%o)?>/g)].map((m) => m[1]);
    fwSatir[tur] = { bicim, n: bicim ? (bicim.match(/%/g) || []).length : -1, adlar };
  }
  ok('[!] D5: G / GA / GT / GP alan SAYISI firmware snprintf bicimiyle ayni',
     ['G', 'GA', 'GT', 'GP'].every((t) => KS[t].length === fwSatir[t].n && fwSatir[t].n > 0),
     ['G', 'GA', 'GT', 'GP'].map((t) => `${t}:${KS[t].length}/${fwSatir[t].n}`).join(' '));
  ok('[!] D5: alan ADLARI ve SIRASI firmware protokol yorumundaki adlar',
     ['G', 'GA', 'GT', 'GP'].every((t) => KS[t].join(',') === fwSatir[t].adlar.join(',')),
     ['G', 'GA', 'GT', 'GP'].map((t) => `${t}: ${fwSatir[t].adlar.join(',')}`).join(' | '));
  {
    /* firmware bicimini sayilarla doldur (snprintf benzetimi) ve geri coz */
    const doldur = (tur) => tur + ' ' + fwSatir[tur].bicim.replace(/%l?[ud]/g, (() => { let k = 0; return () => String(k++ * 7 + 1); })());
    const sonuc = ['G', 'GA', 'GT', 'GP'].map((t) => {
      const o = kayitSatiriCoz(doldur(t));
      return !!o && o.tur === t && KS[t].every((ad, k) => o[ad] === k * 7 + 1);
    });
    const negatif = kayitSatiriCoz('G 5 0 0 1 0 0 0 0 0 0 0 0 -3');
    ok('[!] D5: firmware bicimiyle uretilen satirlar alan alan cozuluyor; son_hata eksi olabilir',
       sonuc.every(Boolean) && !!negatif && negatif.son_hata === -3 && negatif.durum === 5, sonuc.join(' '));
    ok('[!] D5: KATI — eksik/fazla alan, tamsayi olmayan ya da yabanci satir DURUM SAYILMAZ',
       kayitSatiriCoz('G 2 61 24337') === null && kayitSatiriCoz('G 2 61 24337 50012 49000 310 45 0 2900 1300 4 300 0 9') === null
       && kayitSatiriCoz('G 2 61 x 50012 49000 310 45 0 2900 1300 4 300 0') === null
       && kayitSatiriCoz('GX 1 2 3 4') === null && kayitSatiriCoz('Gerilim 1') === null);
    /* W2 (A3-W2): G'ye son_not + mesaj_dusen SONA eklendi. Eski firmware'in 13 alanli satiri
       (kartta A3-4B) hala DURUM: kayit gostergesi yeni panel + eski kartta susmamali. */
    const ESKI = al('KAYIT_SATIR_ESKI');
    const eskiG = kayitSatiriCoz('G 2 61 24337 50012 49000 310 45 0 2900 1300 4 300 0');
    const yeniG = kayitSatiriCoz('G 2 61 24337 50012 49000 310 45 0 2900 1300 4 300 0 50020 3');
    const hataG = kayitSatiriCoz('G 2 61 24337 50012 49000 310 45 0 2900 1300 4 300 0 -1 0');
    ok('[!] W2: G GERIYE UYUMLU — eski firmware satiri (13 alan) cozulur, son_not/mesaj_dusen nesnede YOK; '
       + 'yeni satir (15) ikisini tasir, son_not eksi (KG_*) olabilir; aradaki 14 alan RET; eski sayi '
       + 'firmware alan sayisindan KUCUK (yeni alanlar SONDA)',
       !!eskiG && eskiG.son_hata === 0 && eskiG.nokta === 24337 && !('son_not' in eskiG) && !('mesaj_dusen' in eskiG)
       && !!yeniG && yeniG.son_not === 50020 && yeniG.mesaj_dusen === 3 && yeniG.son_hata === 0
       && !!hataG && hataG.son_not === -1
       && Array.isArray(ESKI.G) && ESKI.G.length > 0 && ESKI.G.every((n) => n > 0 && n < fwSatir.G.n)
       && KS.G.slice(0, 13).join(',') === 'durum,oturum,nokta,sonraki,onay,doluluk,onaysiz,dusen,yaz_azami_us,sil_azami_us,sil_adet,tarama_ms,son_hata'
       && ['GA', 'GT', 'GP'].every((t) => kayitSatiriCoz(t + ' 1') === null),
       JSON.stringify({ eskiG, yeniG, hataG, ESKI }));
  }
  {
    const KDR = al('KDR');
    const PLAN = al('PLAN');
    const def = (h, ad) => { const m = h.match(new RegExp('#define ' + ad + '\\s+(\\d+)u')); return m ? Number(m[1]) : NaN; };
    const kdrTamam = Object.entries(KDR).every(([a, v]) => def(YONET_H, 'KDR_' + a) === v);
    const planTamam = Object.entries(PLAN).every(([a, v]) => def(PLAN_H, 'PLAN_' + a) === v);
    ok('[!] D5/D6: kayit durumu (KDR_*) ve plan durumu (PLAN_*) kodlari firmware ile ayni',
       kdrTamam && planTamam && Object.keys(KDR).length === 6 && Object.keys(PLAN).length === 8);
  }
  {
    /* YOKLAMA YOK (D5): baglan() + zamanlayicilar elle (5 dk'lik pil yoklamasi esdegeri) */
    const u = ornek();
    const giden = [];
    u.gonder = async (k) => { giden.push(k); };
    u.kaydet = () => {};
    u.tasiyiciAdi = 'demo';
    SONRA.push(async () => {
      /* bu iddianin zamanlayicilari: baglan()dan ve G/D satirlarindan SONRA kurulan her
         setTimeout yakalanip elle kosturuluyor (5 dk'lik yoklama esdegeri) */
      const zaman = [];
      const eskiZ = sandbox.setTimeout;
      sandbox.setTimeout = (fn, ms) => { zaman.push(fn); return zaman.length; };
      await u.baglan();
      for (let tur = 0; tur < 150; tur++) {
        const bekleyen = zaman.splice(0);
        for (const f of bekleyen) await f();
      }
      for (let k = 0; k < 5; k++) u.satirIsle('G 2 61 ' + (100 + k) + ' 50012 49000 310 45 0 2900 1300 4 300 0');
      const gSoru = giden.filter((k) => k === 'G?').length;
      await u.kayitBaslat();
      const sonra = giden.filter((k) => k === 'G?').length;
      sandbox.setTimeout = eskiZ;
      ok('[!] D5: `G?` baglaninca BIR KEZ; zamanlayicilar ve gelen G satirlari yeni `G?` DOGURMUYOR (yoklama yok)',
         gSoru === 1 && giden.indexOf('G?') > giden.indexOf('CT'), giden.join(' '));
      ok('[!] D5: kayit komutundan SONRA tam bir `G?`', sonra === 2 && giden[giden.length - 2] === 'Gb200'
         && giden[giden.length - 1] === 'G?', giden.slice(-3).join(' '));
    });
    /* 3E (OS5): dorduncu yer osiloskop gunlugu komutu (Gt/Gtd) — o da bir KAYIT komutu (D5) */
    ok('[!] D5: app.js`te setInterval YOK ve `G?` yalniz baglan + demoVeri (sahte kartin baglanmasi) + kayitKomut + skopGunlukGonder govdesinde',
       !/setInterval\(/.test(kod) && (kod.match(/'G\?'/g) || []).length === 4
       && govdeIcinde(appKaynak, 'baglan', "this.gonder('G?')") && govdeIcinde(appKaynak, 'demoVeri', "this.gonder('G?')")
       && govdeIcinde(appKaynak, 'kayitKomut', "this.gonder('G?')")
       && govdeIcinde(appKaynak, 'skopGunlukGonder', "this.gonder('G?')"));
  }
  {
    /* Durum gecisleri -> olaylar (D7), ret satiri (D4), konsol */
    const u = ornek();
    u.satirIsle('G 1 0 0 120 0 300 30 0 0 0 0 300 0');
    const ilk = u.olaylar.length;
    u.satirIsle('G 2 61 0 121 0 300 30 0 0 0 0 300 0');
    u.satirIsle('G 2 61 5 121 0 300 30 2 0 0 0 300 0');
    u.satirIsle('G 1 0 0 122 0 301 31 2 0 0 0 300 0');
    const m = u.olaylar.map((o) => o.metin);
    ok('[!] D7: olaylar — ilk G olay DEGIL; baslama, dusen artisi, durma (durum metniyle), en yeni basta',
       ilk === 0 && m[0] === 'Kayıt durdu · oturum 61 (kayıt yok (hazır))' && m[1] === 'Kart 2 noktayı düşürdü'
       && m[2] === 'Kayıt başladı · oturum 61' && u.gunluk.some((x) => x.metin.startsWith('G 2 61')), m.join(' | '));
    u.kayitKomutZamani = Date.now();
    u.satirIsle('! G: pil testi suruyor — kaydi zaten acik; durdurmak icin p0');
    ok('[!] D4: kayit komutundan sonra gelen `! G:` satiri OLDUGU GIBI denetimin yaninda ve olaylarda',
       !!u.kayitUyari && u.kayitUyari.tur === 'kart'
       && u.kayitUyari.metin === 'Kart reddetti: ! G: pil testi suruyor — kaydi zaten acik; durdurmak icin p0'
       && u.olaylar[0].metin.startsWith('! G: pil testi') && u.olaylar[0].tur === 'unlem');
    const v = ornek();
    v.kayitKomutZamani = Date.now() - 60000;
    v.satirIsle('! G plan atlandi: o an baska kayit vardi');
    ok('Komuttan BAGIMSIZ `! G` (plan atlandi) ret kutusuna DUSMUYOR, olaylara dusuyor',
       v.kayitUyari === null && v.olaylar.length === 1);
    for (let k = 0; k < 30; k++) v.satirIsle('! akis: ' + k + ' satir dustu (kuyruk doldu)');
    ok('[!] D7: son olaylar EN FAZLA 20, en yeni basta', v.olaylar.length === 20
       && v.olaylar[0].metin.includes(' 29 ') && v.olaylar[19].metin.includes(' 10 '), String(v.olaylar.length));
    v.satirIsle('GP 1 1790000000 7200 1000 0');
    v.satirIsle('GP 2 1790000000 7200 1000 62');
    v.satirIsle('GT 0 0 0 0');
    v.satirIsle('GT 1 0 3 0');
    ok('D7: plan durum degisimi ve osiloskop gunlugu olay; GP/GT konsola da dusuyor',
       v.olaylar[1].metin === 'Plan: sürüyor' && v.olaylar[0].metin === 'Osiloskop günlüğü başladı'
       && v.gunluk.some((x) => x.metin.startsWith('GP 2')), v.olaylar.slice(0, 2).map((o) => o.metin).join(' | '));
  }
  {
    /* Kart yeniden basladi (D ms geri gitti) — t AZALMAZ, arada bosluk; kayit surduyse soylenir */
    const u = ornek();
    u.raporMs = 200;
    u.satirIsle('G 2 61 100 121 0 300 30 0 0 0 0 300 0');
    for (const ms of [50000, 50200, 50400]) u.satirIsle(`D 12.0 0.5 6.0 1.0 0.001 ${ms} 172 0 0`);
    u.satirIsle('D 12.0 0.5 6.0 1.0 0.001 3000 172 0 0');
    u.satirIsle('D 12.0 0.5 6.0 1.0 0.001 3200 172 0 0');
    const t = u.gecmis.map((x) => x.t);
    const artan = t.every((x, k) => k === 0 || x > t[k - 1]);
    const bosluk = (t[3] - t[2]) * 1000;
    u.satirIsle('G 2 61 105 121 0 300 30 0 0 0 0 300 0');
    const m = u.olaylar.map((o) => o.metin);
    ok('[!] 3D: kart yeniden baslayinca (D ms geri) gecmisin zamani AZALMIYOR, arada bosluk esiginden genis bosluk',
       artan && bosluk > CN.canliBoslukMs(200) && Math.abs((t[4] - t[3]) * 1000 - 200) < 1e-6,
       `t=${t.join(',')} bosluk=${bosluk}`);
    ok('[!] D7: "Kart yeniden basladi" + ayni oturum KAYITta surduyse "Kayit surdu"',
       m[0] === 'Kayıt sürdü · oturum 61' && m[1] === 'Kart yeniden başladı', m.join(' | '));
    const w = ornek();
    for (const ms of [4294967000, 4294967200]) w.satirIsle(`D 1 0 0 0 0 ${ms} 172 0 0`);
    w.satirIsle('D 1 0 0 0 0 104 172 0 0');
    const tw = w.gecmis.map((x) => x.t);
    ok('[!] millis 32 bit sarmasi yeniden baslama SAYILMIYOR, zaman surekli',
       w.olaylar.length === 0 && Math.abs((tw[2] - tw[1]) * 1000 - 200) < 1e-6, tw.join(','));
    const a = ornek();
    a.satirIsle('Olcum Karti — Asama 3 (CIFT YONLU on uc)');
    a.satirIsle('D 1 0 0 0 0 5000 172 0 0');
    a.satirIsle('D 1 0 0 0 0 300 172 0 0');
    ok('[!] D1/D7: afis surumu seritte; afis + ardindan gelen ms dususu TEK "yeniden basladi" olayi',
       a.afisSurum === 'Asama 3 (CIFT YONLU on uc)' && a.olaylar.length === 1
       && a.olaylar[0].metin === 'Kart yeniden başladı' && a.gunluk.some((x) => x.metin.startsWith('Olcum Karti')));
  }

  /* ── (c) KOMUT URETICILERI (D4) ─────────────────────────────────── */
  {
    const H = al('KAYIT_HIZLARI');
    const hizFw = [...((inoYorumsuz.match(/static bool kayit__hiz_gecerli\(long h\) \{([\s\S]*?)\n\}/) || [])[1] || '')
      .matchAll(/h == (\d+)/g)].map((m) => Number(m[1]));
    ok('[!] D4: kayit araliklari firmware kayit__hiz_gecerli listesiyle AYNI (0 = her ornek)',
       hizFw.length >= 5 && H.join(',') === hizFw.join(','), `panel ${H.join(',')} · firmware ${hizFw.join(',')}`);
    const b = al('kayitBaslatKomutu');
    ok('[!] D4: Baslat -> Gb<ms>, "her ornek" -> Gb0; listede olmayan aralik GONDERILMIYOR',
       b(200).komut === 'Gb200' && b(0).komut === 'Gb0' && b(60000).komut === 'Gb60000'
       && b(50).hata === 'cn.hata_hiz' && b(-1).hata && b(NaN).hata);
    const azamiFw = Number((ino.match(/#define KOMUT_AZAMI (\d+)u/) || [])[1]) - 1;
    const notFw = Number((BICIM_H.match(/#define KAYIT_NOT_METIN (\d+)u/) || [])[1]);
    ok('[!] D4: komut tavani 175 BAYT (KOMUT_AZAMI - 1) ve not metni 120 bayt (KAYIT_NOT_METIN) firmware`ten',
       al('KOMUT_AZAMI_BAYT') === azamiFw && azamiFw === 175 && al('NOT_METIN_AZAMI_BAYT') === notFw && notFw === 120);
    const d = al('kayitKomutuDenetle');
    const s2 = String.fromCharCode(0x15f);       // 'ş' = 2 bayt
    ok('[!] D4: tavan BAYT sayiyor (Turkce harf 2 bayt): 175 ASCII gecer, 176 ASCII ve 88 x "ş" (176 bayt) GECMEZ',
       d('G' + 'x'.repeat(174)).komut && d('G' + 'x'.repeat(175)).hata === 'cn.hata_komut_uzun'
       && d(s2.repeat(88)).hata && d(s2.repeat(87)).komut && al('utf8Bayt')(s2 + 'a') === 3);
    const n = al('kayitNotKomutu');
    const tirnak = String.fromCharCode(34);
    const tersBolu = String.fromCharCode(92);
    ok('[!] D4: Not -> Gn<oturum> <metin>; taze D varsa Gn<oturum>@<kart_ms> <metin> (grafikte aninda)',
       n(61, 'Oda 24 °C').komut === 'Gn61 Oda 24 °C' && n(61, '  hücre ılık ', 123456).komut === 'Gn61@123456 hücre ılık');
    ok('[!] D4: Not reddi — oturum yok, bos, kartin attigi karakter (cift tirnak, ters bolu, denetim), 120 bayt ustu',
       n(0, 'x').hata === 'cn.hata_oturum' && n(61, '   ').hata === 'cn.hata_not_bos'
       && n(61, 'a' + tirnak + 'b').hata === 'cn.hata_not_karakter' && n(61, 'a' + tersBolu + 'b').hata === 'cn.hata_not_karakter'
       && n(61, 'a' + String.fromCharCode(1) + 'b').hata === 'cn.hata_not_karakter'
       && n(61, 'x'.repeat(120)).komut && n(61, 'x'.repeat(121)).hata === 'cn.hata_not_uzun'
       && n(61, s2.repeat(60)).komut && n(61, s2.repeat(61)).bayt === 122);
    const p = al('kayitPlanKomutu');
    const simdi = 1790000000;
    const sureFw = (PLAN_H.match(/#define PLAN_SURE_AZAMI \((\d+)UL \* (\d+)UL\)/) || []).slice(1).reduce((a, x) => a * Number(x), 1);
    const altFw = Number((PLAN_H.match(/#define PLAN_UNIX_ALT\s+(\d+)UL/) || [])[1]);
    const ileriFw = (PLAN_H.match(/#define PLAN_ILERI_AZAMI \((\d+)UL \* (\d+)UL\)/) || []).slice(1).reduce((a, x) => a * Number(x), 1);
    ok('[!] D4: plan sinirlari firmware kayit_plan.h`ten (30 gun, 1.7e9, 366 gun)',
       al('PLAN_SURE_AZAMI_S') === sureFw && sureFw === 2592000 && al('PLAN_UNIX_ALT') === altFw
       && altFw === 1700000000 && al('PLAN_ILERI_AZAMI_S') === ileriFw && ileriFw === 366 * 86400);
    const g = (b_, s, h) => p({ basUnix: b_, sureS: s, hizMs: h, simdiUnix: simdi });
    ok('[!] D4: Zamanla -> Gp<unix>,<sure_s>,<hiz_ms>; sinirlar kartla AYNI (1.7e9 alti, 1 yil ileri, 30 gun, pencere gecmis, hiz)',
       g(simdi + 3600, 7200, 1000).komut === 'Gp1790003600,7200,1000'
       && g(simdi + 60, 0, 0).komut === 'Gp1790000060,0,0'
       && g(1699999999, 60, 1000).hata === 'cn.hata_plan_eski' && g(1700000000, 0, 1000).komut
       && g(simdi + ileriFw, 60, 1000).komut && g(simdi + ileriFw + 1, 60, 1000).hata === 'cn.hata_plan_ileri'
       && g(simdi, sureFw, 1000).komut && g(simdi, sureFw + 1, 1000).hata === 'cn.hata_plan_sure'
       && g(simdi - 100, 100, 1000).hata === 'cn.hata_plan_gecmis' && g(simdi - 100, 101, 1000).komut
       && g(simdi - 100, 0, 1000).komut && g(simdi, 60, 50).hata === 'cn.hata_hiz' && g(simdi, -1, 1000).hata
       && p({ basUnix: NaN, sureS: 60, hizMs: 1000, simdiUnix: simdi }).hata === 'cn.hata_plan_bas');
    const yu = al('yerelSaattenUnix');
    ok('Plan baslangici datetime-local (YEREL saat) -> unix; bicimsiz -> NaN',
       yu('2026-10-02T21:05') === Math.floor(new Date(2026, 9, 2, 21, 5).getTime() / 1000)
       && Number.isNaN(yu('')) && Number.isNaN(yu('02.10.2026 21:05')));
    /* davranis: komutlar panelin komut yolundan, ardindan G? */
    const u = ornek();
    const giden = [];
    u.gonder = async (k) => { giden.push(k); };
    u.bagli = true; u.surucuyum = true;
    u.satirIsle('G 2 61 100 121 0 300 30 0 0 0 0 300 0');
    u.satirIsle('D 12.0 0.5 6.0 1.0 0.001 77000 172 0 0');
    u.notMetni = 'deneme';
    const ileri = new Date(Date.now() + 7 * 86400000);
    ileri.setSeconds(0, 0);
    u.planBas = u.yerelSaatYaz(ileri); u.planSureSa = 2; u.planSureDk = 30; u.planHiz = 1000;
    SONRA.push(async () => {
      await u.kayitDurdur();
      await u.notEkle();
      await u.planKur();
      await u.planIptal();
      const beklenen = ['Gd', 'G?', 'Gn61@77000 deneme', 'G?',
        'Gp' + Math.floor(ileri.getTime() / 1000) + ',9000,1000', 'G?', 'Gp-', 'G?'];
      ok('[!] D4: Durdur / Not / Zamanla / Iptal panelin KOMUT YOLUNDAN dogru metni gonderiyor (her biri ardindan G?)',
         giden.join('|') === beklenen.join('|') && u.notMetni === '' && u.notAcik === false, giden.join(' '));
      u.bagli = false;
      giden.length = 0;
      const sonuc = await u.kayitDurdur();
      ok('Bagli degilken kayit komutu GITMIYOR ve sebebi yaziyor', sonuc === false && giden.length === 0
         && u.kayitUyari && u.kayitUyari.metin === 'Karta bağlı değil — önce “Karta bağlan”a basın.');
    });
  }

  /* ── (d) OKUMA + KALAN (D2, D6) ─────────────────────────────────── */
  {
    const mm = al('sonAralikMinMaks');
    const gc = Array.from({ length: 21 }, (_, k) => ({ t: k, v: 10 + k, i: k === 15 ? NaN : -k, w: NaN, e: k / 10 }));
    const r = mm(gc, 'v', 10);
    const ri = mm(gc, 'i', 10);
    ok('[!] D2: son 10 s (son noktaya gore) min/maks; NaN sayilmiyor; hepsi NaN ya da bos -> null',
       r.min === 20 && r.maks === 30 && r.say === 11 && ri.min === -20 && ri.maks === -10 && ri.say === 10
       && mm(gc, 'w', 10) === null && mm([], 'v', 10) === null, JSON.stringify([r, ri]));
    const u = ornek();
    for (let k = 0; k < 60; k++) {
      /* k = 0: 10 s PENCERESININ DISINDA bir sicrama (13 V) — pencere kaymazsa maks 13 olurdu */
      u.satirIsle(`D ${(k === 0 ? 13 : 12 + (k % 7) * 0.001).toFixed(4)} 0.0${50 + (k % 5)} 0.6 ${k}.0 ${(k * 1e-4).toFixed(7)} ${1000 + 200 * k} 172 0 0`);
    }
    ok('[!] D2: okuma kartlari V · A · W · Enerji altinda "10 s: min … maks" (canli orneklerden, kartin birimiyle)',
       u.onSaniye.v === '10 s: 12.000 V … 12.006 V' && u.onSaniye.i === '10 s: 50.00 mA … 54.00 mA'
       && /^10 s: .* mWh … .* mWh$/.test(u.onSaniye.e) && u.onSaniye.w === '10 s: 600.00 mW … 600.00 mW',
       JSON.stringify(u.onSaniye));
    const cm = html.match(/<main[^>]*v-show="gorunum === 'canli'"([\s\S]*?)<\/main>/);
    ok('[!] D2: dort kartin her birinde 10 s satiri (onSaniye.v/i/w/e) sablonda',
       !!cm && ['v', 'i', 'w', 'e'].every((a) => cm[1].includes('{{ onSaniye.' + a + ' }}')));
  }
  {
    const kt = al('kalanTahmin');
    const seri = (n, adim, d) => Array.from({ length: n }, (_, k) => ({ t: k * adim, d: d(k) }));
    const az = kt(seri(59, 1000, () => 310));
    const sabit = kt(seri(71, 1000, () => 310));
    const duz = kt(seri(121, 1000, (k) => 300 + Math.floor(k / 10)));
    const yavas = kt(seri(121, 1000, (k) => 300 + Math.floor(Math.min(k, 30) / 10)));
    ok('[!] D6: "kaldi" tahmini < 60 s gozlemde "hesaplaniyor"', az.durum === 'hesaplaniyor', JSON.stringify(az));
    ok('[!] D6: degisim yoksa (binde nicemleme) KALAN ALT SINIRI ("> X"): (1000-d-1) x sure / 1',
       sabit.durum === 'enaz' && Math.abs(sabit.ms - 689 * 70000) < 1e-6, JSON.stringify(sabit));
    const beklenen = (1000 - 312) * 10000;
    ok('[!] D6: duzenli artista (10 s`de binde 1) "~X" = (1000 - onaysiz) / olculen hiz',
       duz.durum === 'yaklasik' && Math.abs(duz.ms - beklenen) / beklenen < 0.02, `${duz.ms} ~ ${beklenen}`);
    ok('D6: artis durunca tahmin buyuyor (son degisimden sonraki sessizlik hesaba katiliyor)',
       yavas.durum === 'yaklasik' && yavas.ms > 2 * (1000 - 303) * 10000, JSON.stringify(yavas));
    const u = ornek();
    for (let k = 0; k < 500; k++) u.satirIsle('G 2 61 ' + k + ' 121 0 300 30 0 0 0 0 300 0');
    const sikisti = u.kayitGozlem.length;
    u.satirIsle('G 2 61 600 121 0 300 31 0 0 0 0 300 0');
    u.satirIsle('G 2 61 601 121 900 300 5 0 0 0 0 300 0');
    ok('[!] D6: ayni onaysiz degeri tek araliga sikisiyor (uzun kayitta dizi buyumez); onay gelip azalinca gozlem bastan',
       sikisti === 2 && u.kayitGozlem.length === 1 && u.kayitGozlem[0].d === 5, `${sikisti} -> ${u.kayitGozlem.length}`);
    ok('Kalan metni: hesaplaniyor / "~X sa kaldi" / "> X gun kaldi"',
       u.kayitKalanYazi.startsWith('kalan süre hesaplanıyor')
       && (u.kayitGozlem = [{ t: 0, d: 310 }, { t: 70000, d: 310 }], u.kayitKalanYazi === '> 13 sa kaldı'), u.kayitKalanYazi);
  }
  {
    const u = ornek();
    u.bagli = true; u.surucuyum = true;
    u.gonder = async () => {};
    u.satirIsle('G 1 0 0 120 0 300 30 0 0 0 0 300 0');
    u.baslatHiz = 200;
    SONRA.push(async () => {
      await u.kayitBaslat();
      u.satirIsle('G 2 62 50 121 0 300 30 0 0 0 0 300 0');
      const istek = u.kayitHiz;
      ok('[!] D6: aralik bu sekmenin Gb`sinden; sure = nokta x aralik; "her ornek" GA`dan; yoksa OLCULEN',
         istek && istek.hiz === 200 && istek.kaynak === 'istek' && u.kayitSureMs === 10000 && u.kayitSureYazi === '00:00:10',
         JSON.stringify(istek));
      const v = ornek();
      v.satirIsle('G 2 70 0 121 0 300 30 0 0 0 0 300 0');
      const bilinmiyor = v.kayitHiz === null && v.kayitSureMs === null;
      v.kayitNoktaGozlem = [{ t: 0, n: 0 }, { t: 20000, n: 100 }];
      const olculen = v.kayitHiz;
      v.satirIsle('GA 480 1234 0 0');
      ok('D6: panel baslangici GORMEDIYSE sure tahmin edilmiyor; olculen aralik "~200 ms (olculen)"; GA ayrintili -> her ornek',
         bilinmiyor && olculen.kaynak === 'olculen' && Math.abs(olculen.hiz - 200) < 1e-9
         && v.kayitHiz.hiz === 0 && v.kayitHizYazi === 'her örnek (~500/s)');
    });
    const ak = html.match(/data-ak="kart"([\s\S]*?)data-olaylar/);
    ok('[!] D6: aktif kayit karti — oturum, nokta, sure, aralik, doluluk cubugu, kalan, plan, dusen uyarisi',
       !!ak && ['kayitOturumYazi', 'kayitNoktaYazi', 'kayitSureYazi', 'kayitHizYazi', 'role="progressbar"',
         'kayitDolulukYazi', 'kayitKalanYazi', 'planYazi', 'kayitDusenYazi'].every((x) => ak[1].includes(x)));
    const w = ornek();
    w.satirIsle('G 2 61 100 121 0 310 45 3 0 0 0 300 0');
    ok('[!] D6: dusen > 0 ise uyari metni; 0 ise yok',
       w.kayitDusenYazi === 'Kart 3 noktayı yazamadı (kayıt kuyruğu doldu).'
       && (w.satirIsle('G 2 61 101 121 0 310 45 0 0 0 0 300 0'), w.kayitDusenYazi === ''));
    w.satirIsle('GP 1 1790000000 7200 1000 0');
    ok('D6: plan satiri durum + baslangic + sure + aralik', /^Plan: bekliyor · \d{4}-\d\d-\d\d \d\d:\d\d · 2 sa · 1 s$/.test(w.planYazi),
       w.planYazi);
  }

  /* ── (e) CANLI GRAFIK: ekran/canli.js + ortak/grafik.js ─────────── */
  {
    const veri = Array.from({ length: 50 }, (_, k) => ({ t: k * 0.2, v: 12 + k * 0.01, i: k === 20 ? NaN : 0.5, w: 6 }));
    const taban = { v: 0.02, i: 0.0015, w: 0.03 };
    const s = CN.canliSeriler(veri, { taban, boslukMs: 500, gosterV: true, sagEksen: 'akim' });
    ok('[!] D3: uc kanal AYNI t dizisini paylasiyor (ms), NaN korunuyor, en dar aralik 2 x taban (B45 K2)',
       s.length === 3 && s[0].t === s[1].t && s[1].t === s[2].t && s[0].t[1] === 200 && Number.isNaN(s[1].y[20])
       && s[0].enAzAralik === 0.04 && s[1].enAzAralik === 0.003 && s.every((x) => x.boslukMs === 500));
    const gor = (sec) => CN.canliSeriler(veri, { taban, ...sec }).filter((x) => !x.gizli).map((x) => x.ad).join(',');
    ok('[!] D3 (canli.js K1): sag eksen TEK birim — akim YA DA guc; V ayri kutu',
       gor({ gosterV: true, sagEksen: 'akim' }) === 'V,I' && gor({ gosterV: true, sagEksen: 'guc' }) === 'V,W'
       && gor({ gosterV: false, sagEksen: 'yok' }) === '' && gor({ gosterV: false, sagEksen: 'guc' }) === 'W');
    /* eski bolum 11 (a)/(b): lejant */
    const u = ornek();
    const yok = CN.canliLejant([{ t: 0, v: NaN, i: 0.001, w: NaN }, { t: 1, v: NaN, i: 0.002, w: NaN }],
      { v: 0.02, i: 0.0015, w: 0.03 }, { gosterV: true, sagEksen: 'akim' });
    const metinler = yok.map((l) => u.lejantMetni(l));
    ok('[!] V tamamen NaN: "veri yok", "tepe … V" YOK; I gecerli: "tepe … mA" (eski bolum 11, grafik.js ile)',
       metinler[0] === 'veri yok' && !/tepe .* V/.test(metinler[0]) && /^tepe 2\.0 mA/.test(metinler[1]), metinler.join(' | '));
    const gur = Array.from({ length: 40 }, (_, k) => ({ t: k, v: 1.7156, i: (k % 2 ? 3e-6 : -3e-6), w: (k % 2 ? 5e-6 : -5e-6) }));
    const gt = { v: 0.02084, i: 0.0015625, w: 0.0027 };
    const lg = CN.canliLejant(gur, gt, { gosterV: true, sagEksen: 'akim' });
    ok('[!] Taban devredeyken lejant olcegi de yaziyor ("tepe 0.0 mA" tek basina izi aciklamaz)',
       lg[1].tabanda === true && u.lejantMetni(lg[1]) === 'tepe 0.0 mA · ölçek ±1.6 mA', u.lejantMetni(lg[1]));

    /* cizim plani: gercek grafik.js */
    const planKur = (vr, tb, sec, boslukMs = 2500) => {
      const ss = CN.canliSeriler(vr, { taban: tb, boslukMs, ...sec }).map(GR.seriHazirla);
      return GR.cizimPlani(ss, GR.durumKur(ss), { w: 800, h: 280 });
    };
    const cizgiler = (plan, kanal) => plan.komutlar.filter((k) => k.rol === 'seri' && k.kanal === kanal);
    const duzVeri = veri.map((x) => ({ ...x, i: 0.5 + (x.t % 1) * 0.1 }));
    const p1 = planKur(duzVeri, taban, { sagEksen: 'akim' });
    const p2 = planKur(duzVeri.map((x, k) => (k === 20 ? { ...x, i: NaN } : x)), taban, { sagEksen: 'akim' });
    ok('[!] Ortadaki NaN akim cizgisini KOPARIYOR (eski bolum 11; grafik.js G2): 1 cizgi -> 2 cizgi',
       cizgiler(p1, 1).length === 1 && cizgiler(p2, 1).length === 2,
       `${cizgiler(p1, 1).length} -> ${cizgiler(p2, 1).length}`);
    const neg = [{ t: 0, v: 1.7, i: -0.5, w: 0.2 }, { t: 1, v: 1.7, i: 0.4, w: 0.1 }, { t: 2, v: 1.7, i: -0.1, w: 0 }];
    const p3 = planKur(neg, { v: 0.02, i: 0.0016, w: 0.003 }, { sagEksen: 'akim' });
    const ylar = (k) => (k.tur === 'nokta' ? [k.y] : Array.from(k.noktalar).filter((_, j) => j % 2 === 1));
    const icinde = cizgiler(p3, 1).every((k) => ylar(k).every((y) => y >= p3.alan.y - 0.5 && y <= p3.alan.y + p3.alan.h + 0.5));
    const sag = p3.eksenler.sag;
    ok('[!] Negatif akim TUVALIN ICINDE (eski bolum 21 a): eksen [-0.5, 0.4]`u kapsiyor, sifir izgara cizgisi var',
       icinde && sag.min <= -0.5 && sag.maks >= 0.4 && sag.degerler.includes(0) && cizgiler(p3, 1).length >= 1,
       `sag [${sag.min.toFixed(3)}, ${sag.maks.toFixed(3)}] cizgi ${sag.degerler.join(',')}`);
    const p4 = planKur(gur, gt, { sagEksen: 'akim' });
    const s4 = p4.eksenler.sag;
    ok('[!] Bostaki +-3 uA gurultusu ekrani DOLDURMUYOR (eski bolum 21 b): eksen >= 2 x taban, gurultu yuksekligin <%1`i',
       s4.maks - s4.min >= 2 * gt.i - 1e-12 && (6e-6 / (s4.maks - s4.min)) < 0.01, `${((s4.maks - s4.min) * 1e3).toFixed(3)} mA`);
    const dalgali = Array.from({ length: 40 }, (_, k) => ({ t: k, v: 12, i: 0.01 + 0.005 * Math.sin(k), w: 0.12 }));
    const p5 = planKur(dalgali, gt, { sagEksen: 'akim' });
    const l5 = CN.canliLejant(dalgali, gt, { gosterV: false, sagEksen: 'akim' });
    ok('Gercek 10 +- 5 mA sinyal tabanin USTUNDE: lejant tabanda DEGIL, eksen sinyalin tam min/maksi',
       l5[0].tabanda === false && p5.eksenler.sag.min < 0.0051 && p5.eksenler.sag.maks > 0.0149);
    /* yeniden baslama boslugu cizgiyi koparir */
    const yb = ornek();
    yb.raporMs = 200;
    for (const ms of [50000, 50200, 50400, 3000, 3200, 3400]) yb.satirIsle(`D 12.0 0.5 6.0 1.0 0.001 ${ms} 172 0 0`);
    const p6 = planKur(yb.gecmis, taban, { sagEksen: 'akim' }, CN.canliBoslukMs(200));
    ok('[!] Kart yeniden baslayinca grafikte cizgi KOPUYOR (zaman uydurulmuyor)', cizgiler(p6, 0).length === 2,
       String(cizgiler(p6, 0).length));
  }
  {
    /* CanliGrafik: sahte tuval, canli / donmus */
    const sahteTuval = () => {
      const baglam = new Proxy({}, { get: (_, ad) => (ad === 'measureText' ? () => ({ width: 6 }) : () => {}), set: () => true });
      return { clientWidth: 800, clientHeight: 280, width: 0, height: 0, style: {}, tabIndex: -1,
        getContext: () => baglam, addEventListener() {}, removeEventListener() {} };
    };
    const pen = { devicePixelRatio: 1, getComputedStyle: () => ({ getPropertyValue: () => '#123456' }) };
    const tv = sahteTuval();
    const bilgiler = [];
    const cg = new CN.CanliGrafik(tv, { pencere: pen, degisti: (b) => bilgiler.push(b) });
    const gc = Array.from({ length: 400 }, (_, k) => Object.freeze({ t: k / 5, v: 12, i: 0.5, w: 6, e: 0 }));
    const esit = (a, b) => Math.abs(a - b) < 1e-6;
    const d = { gecmis: gc, pencereS: 30, gosterV: true, sagEksen: 'akim', taban: () => ({ v: 0.02, i: 0.0015, w: 0.03 }),
      aralikMs: 200, donmus: false };
    const b1 = cg.ciz(d);
    ok('[!] D3: canli pencere = son `pencere` s (30 s), canlida etkilesim KAPALI (pointer-events none, sekmeye kapali)',
       esit(b1.pencere.t1 - b1.pencere.t0, 30000) && esit(b1.pencere.t1, 79800)
       && tv.style.pointerEvents === 'none' && tv.tabIndex === -1 && esit(b1.pencere.koken, 79800) && b1.okuma === null,
       JSON.stringify(b1.pencere));
    const b2 = cg.ciz({ ...d, donmus: true });
    const yeni = gc.concat(Array.from({ length: 50 }, (_, k) => Object.freeze({ t: 80 + k / 5, v: 13, i: 0.6, w: 7, e: 0 })));
    const b3 = cg.ciz({ ...d, gecmis: yeni, donmus: true });
    ok('[!] D3: DONDUR — pencere ayni, yeni D satirlari KOPYAYA GIRMIYOR, imlec/yakinlastirma acik',
       b2.donmus && b3.donmus && esit(b3.pencere.t1, 79800) && esit(cg.g.durum.veriT1, 79800) && cg.g.durum.veriT0 === 0
       && tv.style.pointerEvents === '' && tv.tabIndex === 0, JSON.stringify(b3.pencere));
    cg.g.durumAyarla({ imlecA: 60000, imlecB: 70000 });
    const ok3 = cg._bildir();
    ok('[!] D3: donmusken iki imlec okumasi (A/B, dt, V/I degerleri, enerji)',
       !!ok3.okuma && ok3.okuma.dt === 10000 && ok3.okuma.enerji && Math.abs(ok3.okuma.enerji.wh - 12 * 0.5 * 10 / 3600) < 1e-9,
       ok3.okuma ? JSON.stringify(ok3.okuma.enerji) : 'yok');
    const b4 = cg.ciz({ ...d, gecmis: yeni, donmus: false });
    ok('D3: Canliya don — yeni veri gorunur, etkilesim yine kapali', !b4.donmus && esit(b4.pencere.t1, 89800)
       && tv.style.pointerEvents === 'none');
    const u = ornek();
    u.pencere = 300;                     // varsayilan (60) DEGIL: secim grafige gidiyor mu
    const dd = u.canliDurumu();
    ok('[!] D3: bugunku pencere / yenileme davranisi grafige gidiyor (pencereS, aralik, taban = olcekTabani, sag eksen)',
       dd.pencereS === u.pencere && dd.aralikMs === u.raporMs && typeof dd.taban === 'function'
       && JSON.stringify(dd.taban([{ t: 0, v: 1, i: 0, w: 0 }])) === JSON.stringify(u.olcekTabani([{ t: 0, v: 1, i: 0, w: 0 }])));
    u.gecmis = [{ t: 0 }]; u.ilkMs = 5; u.msKaydir = 9; u.donmus = true;
    u.gecmisiTemizle();
    ok('[!] D3: "Grafigi temizle" gecmisi, zaman kaydirmasini ve dondurmayi sifirliyor',
       u.gecmis.length === 0 && u.ilkMs === null && u.msKaydir === 0 && u.donmus === false);
  }
  {
    const cm = html.match(/<main[^>]*v-show="gorunum === 'canli'"([\s\S]*?)<\/main>/);
    const b = cm ? cm[1] : '';
    ok('[!] D3: Canli`da tuval (ref grafik) + dondur + temizle + CSV + pencere (30 s … 30 dk) + yenileme',
       /<canvas ref="grafik" class="canli-grafik" role="img"/.test(b) && /@click="dondurDegistir"/.test(b)
       && /@click="gecmisiTemizle"/.test(b) && /@click="csvIndir"/.test(b) && /v-model\.number="pencere"/.test(b)
       && [30, 60, 300, 1800].every((x) => b.includes(':value="' + x + '"')) && /v-model\.number="raporMs"/.test(b));
    ok('[!] D4: baslikta kayit denetimi: hiz secimi (kayitHizlari), Baslat, Not ekle, Durdur, Zamanla; ret kutusu',
       /v-for="h in kayitHizlari"/.test(b) && /@click="kayitBaslat"/.test(b) && /@click="kayitDurdur"/.test(b)
       && /@click="notAcDegistir"/.test(b) && /@click="planAcDegistir"/.test(b) && /@submit\.prevent="notEkle"/.test(b)
       && /@submit\.prevent="planKur"/.test(b) && /@click="planIptal"/.test(b) && /v-if="kayitUyari"/.test(b));
    ok('[!] Kayit komutlari izleyicide (kopru, surucu degil) KAPALI',
       (() => { const u = ornek(); u.bagli = true; u.surucuyum = false; const a = u.kayitKomutAcik; u.surucuyum = true; return a === false && u.kayitKomutAcik; })()
       && (b.match(/:disabled="!kayitKomutAcik"/g) || []).length >= 4);
    ok('[!] Canli grafik modulu TEMBEL: ekran/canli.js statik ice aktarma grafiginde YOK, canliYukle import() ediyor',
       !iceAktarmaGrafigi().some((g) => g.goruntu === 'ekran/canli.js')
       && govdeIcinde(appKaynak, 'canliYukle', "import('./ekran/canli.js')")
       && govdeIcinde(appKaynak, 'canliYukle', "this.canliDurum = 'yuklenemedi'") && /m\.yuklenemedi/.test(b));
    const blok = css.slice(css.indexOf('3D — KABUK'), css.indexOf('gezinme (şerit)'))
      + css.slice(css.indexOf('3D — dar ekran'), css.indexOf('@media (max-width: 620px)'))
      + css.slice(css.indexOf('3D — CANLI'), css.indexOf('3C — KAYITLAR'));
    ok('[!] 3D stilleri YALNIZ belirtecle: sabit renk (#hex / rgb) yok',
       css.indexOf('3D — KABUK') > 0 && css.indexOf('3D — CANLI') > 0
       && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(blok.replace(/\/\*[\s\S]*?\*\//g, '')));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   26. WEB ARAYUZ KURALLARI (WIG, 2026-10-02) — kabuk, Canli, Pil, Ayarlar,
       Konsol, Kayitlar. Osiloskop bolumu BU BOLUMUN DISINDA (ayri is).
   Dogrulanmis bulgularin her biri burada DAVRANIS ya da sablon iddiasi:
   (a) her denetimin erisilebilir adi var (label for/sarmalama/aria-label),
       sahipsiz <label> yok; (b) eszamansiz durumlar duyuruluyor; (c) yikici
       eylemler IKI ASAMALI (onay kendiliginden ve gorunum degisince duser);
       (d) kod/ag adi/parola alanlari otomatik buyuk harf / duzeltme yapmiyor;
       (e) baglanti yokken okuma kartlari '0.000 V' YAZMIYOR; (f) metinler
       ekranda olani soyluyor; (g) cekmece arkasi inert, odak yonetimi.
   Gercek tarayici: tarayici_canli.py (iki asamali Durdur, inert cekmece),
   tarayici_kayitlar.py (arsiv onayi, kayit acilinca odak).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 26. Web arayuz kurallari (WIG): kabuk, Canli, Pil, Ayarlar, Konsol, Kayitlar ---');
{
  const htmlTam = yorumsuz(htmlKaynak);
  /* osiloskop <main>'i kapsam disi: cikarilip bakiliyor */
  const html = htmlTam.replace(/<main class="gorunum" v-show="gorunum === 'skop'">[\s\S]*?<\/main>/, '');
  const css = cssOku();
  const cssKod = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const kod = yorumsuz(appKaynak);
  const SZ = sozlukTum();
  const KLm = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
  const KGm = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
  const TEMAm = require(path.join(ARAYUZ, 'ekran', 'tema.js'));
  const al = (ad) => vm.runInContext(ad, sandbox);
  if (!sandbox.clearTimeout) sandbox.clearTimeout = () => {};
  const ana = (ad) => { const m = html.match(new RegExp(`<main class="gorunum" v-show="gorunum === '${ad}'">([\\s\\S]*?)</main>`)); return m ? m[1] : ''; };
  const etiketler = (s, ad) => [...s.matchAll(new RegExp(`<${ad}\\b((?:[^>"']|"[^"]*"|'[^']*')*)>`, 'g'))].map((m) => m[1]);
  const nit = (a, ad) => { const m = a.match(new RegExp(`(?:^|\\s)${ad}="([^"]*)"`)); return m ? m[1] : null; };
  const vmodel = (ad) => etiketler(html, 'input').find((a) => nit(a, 'v-model') === ad) || '';
  /** Bilesen ornegi (Vue'suz): data + methods + computed (ust = computed ezmesi). */
  const bilesen = (B, props = {}, ust = {}) => {
    const o = Object.assign({}, props);
    Object.assign(o, B.data ? B.data.call(o) : {});
    Object.assign(o, B.methods || {});
    o.$nextTick = (f) => { if (f) f(); return Promise.resolve(); };
    o.$refs = {};
    for (const [ad, fn] of Object.entries(B.computed || {})) {
      Object.defineProperty(o, ad, ad in ust ? { get: () => ust[ad], configurable: true }
        : { get: fn.bind(o), configurable: true });
    }
    return o;
  };
  /** sandbox setTimeout'u gecici yakala (onay zaman asimi). */
  const zamanlayicili = (f) => {
    const eski = sandbox.setTimeout;
    const kuyruk = [];
    sandbox.setTimeout = (fn, ms) => { kuyruk.push({ fn, ms }); return kuyruk.length; };
    try { f(kuyruk); } finally { sandbox.setTimeout = eski; }
    return kuyruk;
  };

  /* ── (a) erisilebilir ad: her input/select/textarea ───────────────── */
  const adsizlar = (s) => {
    const idler = new Set([...s.matchAll(/<label\b[^>]*\sfor="([^"]+)"/g)].map((m) => m[1]));
    const adsiz = [];
    const sahipsiz = [];
    let derin = 0;
    let acik = null;
    for (const m of s.matchAll(/<(\/?)(label|input|select|textarea)\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
      const [, kapat, ad, a] = m;
      if (ad === 'label') {
        if (kapat) { if (acik && !acik.denetim && !acik.for) sahipsiz.push(acik.metin); derin = Math.max(0, derin - 1); acik = null; } else { derin++; acik = { denetim: false, for: /\sfor="/.test(a), metin: s.slice(m.index, m.index + 70) }; }
        continue;
      }
      if (kapat) continue;
      if (acik) acik.denetim = true;
      const id = nit(a, 'id');
      const adli = derin > 0 || /(?:^|\s):?aria-label(?:ledby)?="/.test(a) || (id && idler.has(id));
      if (!adli) adsiz.push(s.slice(m.index, m.index + 80).replace(/\s+/g, ' '));
    }
    return { adsiz, sahipsiz };
  };
  const ha = adsizlar(html);
  ok('[!] WIG a: index.html`de (osiloskop disi) HER input/select/textarea adli (label for/sarmalama/aria-label)',
     ha.adsiz.length === 0 && etiketler(html, 'input').length >= 12, ha.adsiz.join(' | ') || `${etiketler(html, 'input').length} input`);
  ok('[!] WIG a: sahipsiz <label> yok (ne for= ne denetim saran) — "Gerilim menzili" artik grup adi',
     ha.sahipsiz.length === 0, ha.sahipsiz.join(' | '));
  const sk = adsizlar(yorumsuz(KLm.KayitlarEkrani.template) + yorumsuz(KGm.KayitGorunumu.template));
  ok('WIG a: Kayitlar + kayit gorunumu sablonlarinda da adsiz denetim / sahipsiz label yok',
     sk.adsiz.length === 0 && sk.sahipsiz.length === 0, sk.adsiz.concat(sk.sahipsiz).join(' | '));
  const menzil = ana('ayar').match(/<div class="dugme-grup" role="group" aria-labelledby="([^"]+)">([\s\S]*?)<\/div>/);
  ok('[!] WIG a: menzil dugmeleri role=group + aria-labelledby (gorunen ad) + aria-pressed; Otomatik menzil aria-pressed',
     !!menzil && new RegExp(`id="${menzil[1]}"[^>]*>Gerilim menzili<`).test(ana('ayar'))
     && /:aria-pressed="menzil === 0 \? 'true' : 'false'"/.test(menzil[2]) && /:aria-pressed="menzil === 1 \? 'true' : 'false'"/.test(menzil[2])
     && /@click="otoMenzilDegistir"[^>]*:aria-pressed="otoMenzil \? 'true' : 'false'"|:aria-pressed="otoMenzil \? 'true' : 'false'"[^>]*@click="otoMenzilDegistir"/.test(ana('ayar')));

  /* ── (d) alan turleri / otomatik duzeltme ─────────────────────────── */
  const kapali = (a) => nit(a, 'autocapitalize') === 'off' && nit(a, 'spellcheck') === 'false';
  const konsol = vmodel('elleKomut');
  ok('[!] WIG d: Konsol komut kutusu buyuk/kucuk harf KORUNUR (f50 != F50, z != Z): autocapitalize/autocorrect/spellcheck kapali, autocomplete off, ad',
     kapali(konsol) && nit(konsol, 'autocorrect') === 'off' && nit(konsol, 'autocomplete') === 'off'
     && nit(konsol, 'name') === 'komut' && nit(konsol, 'enterkeyhint') === 'send' && /aria-label="/.test(konsol), konsol);
  const ssid = vmodel('agSsid');
  ok('[!] WIG d: SSID birebir gider (teras != Teras): otomatik buyuk harf/duzeltme kapali, name, autocomplete off',
     kapali(ssid) && nit(ssid, 'autocorrect') === 'off' && nit(ssid, 'autocomplete') === 'off' && nit(ssid, 'name') === 'ssid', ssid);
  const p1 = vmodel('agSifre');
  const p2 = vmodel('agWebSifre');
  ok('[!] WIG d: iki parola alani parola yoneticisine "giris formu" degil: name + autocomplete=new-password, AYRI adlar',
     nit(p1, 'type') === 'password' && nit(p2, 'type') === 'password' && nit(p1, 'autocomplete') === 'new-password'
     && nit(p2, 'autocomplete') === 'new-password' && nit(p1, 'name') && nit(p2, 'name') && nit(p1, 'name') !== nit(p2, 'name'));
  const adr = vmodel('kartTaban');
  ok('WIG d: kart adresi type=url + inputmode=url, buyuk harf/yazim kapali; yer tutucu ornek (…), talimat alanin altinda',
     nit(adr, 'type') === 'url' && nit(adr, 'inputmode') === 'url' && kapali(adr)
     && /…$/.test(nit(adr, 'placeholder') || '') && !/boş = /.test(nit(adr, 'placeholder') || ''));
  ok('WIG d: kesme gerilimi inputmode=decimal; kalibrasyon/faz alanlarinda buyuk harf/yazim kapali; faz yer tutucusu talimat degil',
     nit(vmodel('pilKesmeGiris'), 'inputmode') === 'decimal' && ['kalibV', 'kalibA', 'fazKal'].every((v) => kapali(vmodel(v)))
     && !/PF en büyük/.test(nit(vmodel('fazKal'), 'placeholder') || ''));
  ok('WIG d: Kayitlar arama kutusu: autocomplete/autocorrect/spellcheck kapali, enterkeyhint=search',
     (() => { const a = etiketler(KLm.KayitlarEkrani.template, 'input').find((x) => /kl-ara/.test(x)) || '';
       return kapali(a) && nit(a, 'autocomplete') === 'off' && nit(a, 'autocorrect') === 'off' && nit(a, 'enterkeyhint') === 'search'; })());
  {
    const u = ornek();
    const adres = (t) => { u.kartTaban = t; return u.kartAdres('/akis'); };
    ok('[!] WIG d: semasiz kart adresi http:// alir (yoksa istek sayfanin KENDI sunucusuna gider); https korunur; bos = ayni koken',
       adres('192.168.1.50') === 'http://192.168.1.50/akis' && adres('olcum.local/') === 'http://olcum.local/akis'
       && adres('https://x.y') === 'https://x.y/akis' && adres('HTTP://A') === 'HTTP://A/akis' && adres('') === '/akis'
       && adres('  ') === '/akis', adres('192.168.1.50'));
    u.kartTaban = '192.168.1.50';
    u.tasiyiciAdi = 'akis';
    ok('WIG d: serit alt satiri semasiz adreste de karti gosteriyor', u.seritAlt.startsWith('192.168.1.50'), u.seritAlt);
  }

  /* ── (b) duyurular ────────────────────────────────────────────────── */
  ok('[!] WIG b: bildirim hatasi role=alert; desteksiz kip ve izleyici role=status',
     /<div v-if="hata" class="hata" role="alert">/.test(html) && /<div v-if="!destekli" class="hata" role="status">/.test(html)
     && /<div v-if="bagli && !surucuyum" class="uyari" role="status">/.test(html));
  ok('[!] WIG b: baglanti rozeti (iki kopya) role=status, nokta aria-hidden; acil serit noktasi aria-hidden, DURDUR baglamli ad',
     (html.match(/<span class="rozet" role="status"/g) || []).length === 2 && (html.match(/<span class="nokta" aria-hidden="true">/g) || []).length === 2
     && /<span class="acil-nokta" aria-hidden="true">/.test(html) && /class="acil-dur"[^>]*aria-label="Pil testini durdur"/.test(html));
  ok('[!] WIG b: kabuk duyurucusu (role=status) .icerik DISINDA ve kalici: pil testi baslayinca duyurulur',
     (() => { const k = html.indexOf('class="gorunmez" role="status"'); return k > 0 && k < html.indexOf('<div class="icerik"'); })()
     && (() => { const u = ornek(); const a = u.kabukDuyuru; u.pilDurum = 'CALISIYOR'; return a === '' && /Pil testi çalışıyor/.test(u.kabukDuyuru); })());
  ok('[!] WIG b: pil hata / veri alinamiyor role=alert',
     /v-if="pilHata && pilHata !== '-'" class="hata" role="alert"/.test(html) && /v-if="pilHataMetni" class="uyari" role="alert"/.test(html));
  ok('WIG b: Konsol gunlugu role=log, adli, klavyeyle odaklanir; bossa "henuz satir yok" (bos kutu degil)',
     /<div class="gunluk" ref="gunlukKutu" role="log" aria-live="off" :aria-label="'Kart satırları'" tabindex="0">/.test(html)
     && /<p v-if="!gunluk\.length" class="ipucu">/.test(ana('konsol')) && /\.gunluk:focus-visible\s*\{[^}]*outline:\s*2px/.test(cssKod));
  ok('[!] WIG b: Kayitlar esitleme sonucu/sebebi KALICI aria-live bolgede; esitle dugmesi aria-busy; disari aktarma hatasi role=alert',
     /<div class="kl-duyuru" aria-live="polite">\s*<p v-if="nedenMetni"[\s\S]*?<p v-if="sonuc"[\s\S]*?<\/div>/.test(KLm.KayitlarEkrani.template)
     && /kl-esitle"[^>]*:aria-busy="esitleniyor \? 'true' : 'false'"/.test(KLm.KayitlarEkrani.template)
     && /<p v-if="hata" class="hata" role="alert">/.test(KGm.KayitGorunumu.template));
  {
    /* imlec okumasi: kalici, gorunmez, polite bolge; ~300 ms sonra TEK satir ozet */
    const g = bilesen(KGm.KayitGorunumu, { dil: 'tr', rapor: false, etkin: true }, {
      okumaSatirlari: [{ a: 'ta', etiket: 'A', deger: '00:01' }, { a: 'tb', etiket: 'B', deger: '00:02' },
        { a: 'dt', etiket: 'Δt', deger: '00:01' }, { a: 'Va', etiket: 'V (A)', deger: '1.0000 V' },
        { a: 'Vb', etiket: 'V (B)', deger: '2.0000 V' }, { a: 'Ia', etiket: 'I (A)', deger: '0.1 A' }] });
    g.okuma = { tA: 1 };
    const eskiZ = globalThis.setTimeout;
    const kq = [];
    globalThis.setTimeout = (fn, ms) => { kq.push({ fn, ms }); return kq.length; };
    try { g.duyuruZamanla(); } finally { globalThis.setTimeout = eskiZ; }
    const once = g.duyuru;
    if (kq.length) kq[kq.length - 1].fn();
    ok('[!] WIG b: kayit gorunumu imlec okumasi aria-live polite GORUNMEZ bolgede, ~300 ms gecikmeli tek satir (her ok tusunda 20 deger degil)',
       /<p class="gorunmez" aria-live="polite">\{\{ duyuru \}\}<\/p>/.test(KGm.KayitGorunumu.template) && once === ''
       && kq.length === 1 && kq[0].ms >= 200 && kq[0].ms <= 600 && g.duyuru === 'A 00:01 · B 00:02 · Δt 00:01 · V (A) 1.0000 V · V (B) 2.0000 V',
       g.duyuru);
    const u = ornek();
    const q = zamanlayicili(() => { u.canliOkumaDegisti([{ ad: 'A', d: '−00:00:05.0' }, { ad: 'B', d: '—' }]); });
    if (q.length) q[q.length - 1].fn();
    ok('[!] WIG b: Canli donmus okuma da gorunmez polite bolgede (gecikmeli ozet)',
       /<p class="gorunmez" aria-live="polite">\{\{ canliDuyuru \}\}<\/p>/.test(ana('canli')) && q.length === 1
       && u.canliDuyuru === 'A −00:00:05.0 · B —', u.canliDuyuru);
  }
  ok('[!] WIG b: gorunmez sinif CSS`te (kirpilmis, 1 px) — display:none DEGIL (ekran okuyucu okur)',
     /\.gorunmez\s*\{[^}]*position:\s*absolute[^}]*clip-path:\s*inset\(50%\)/.test(cssKod)
     && !/\.gorunmez\s*\{[^}]*display:\s*none/.test(cssKod));

  /* ── (c) iki asamali yikici eylemler ─────────────────────────────── */
  /** onay kalibi: acan dugme v-if="onay !== X" @click=onayIste(X); eylem YALNIZ v-else'deki data-onay=X dugmesinde. */
  const onayli = (s, ad, eylem, kosul = '') => {
    const ac = new RegExp(`<button v-if="${kosul}onay !== '${ad}'"[^>]*data-onay-ac="${ad}"[^>]*@click="onayIste\\('${ad}'\\)"`);
    const es = new RegExp(`<button[^>]*data-onay="${ad}"[^>]*@click="${eylem.replace(/[()]/g, '\\$&')}"`);
    const tum = s.split(`@click="${eylem}"`).length - 1;
    return ac.test(s) && es.test(s) && tum === 1;
  };
  const yikici = [
    ['canli', 'durdur', 'kayitDurdur'], ['canli', 'grafikTemizle', 'gecmisiTemizle'],
    ['ayar', 'akimSifir', 'sifirlaA'], ['ayar', 'enerjiSifir', 'enerjiSifirla'], ['ayar', 'gerilimSifir', 'sifirlaV'],
    ['ayar', 'webKoruma', 'agWebKorumaKaldir'], ['pil', 'pilSil', 'pilTemizle'],
  ];
  const yanlis = yikici.filter(([g, ad, e]) => !onayli(ana(g), ad, e));
  ok('[!] WIG c: Durdur, Grafigi temizle, Akim/Enerji/Gerilim sifirla, web korumasini kaldir, pil noktalarini sil IKI ASAMALI (eylem yalniz onay dugmesinde)',
     yanlis.length === 0, yanlis.map((x) => x[1]).join(', ') || `${yikici.length} eylem`);
  ok('[!] WIG c: Plani iptal — plan SUREN kayda bagliysa iki asamali ("suren kayit da durur"); bekleyen plan tek tik',
     onayli(ana('canli'), 'planIptal', 'planIptal', 'planBagli && ')
     && (() => { const u = ornek(); const P = al('PLAN'); u.kayit.gp = { durum: P.BEKLIYOR, oturum: 0 }; const a = u.planBagli;
       u.kayit.gp = { durum: P.SURUYOR, oturum: 12 }; return a === false && u.planBagli === true; })());
  ok('[!] WIG c: Agi kapat — ag uzerinden bagliyken iki asamali (kendini kilitler), USB`de tek tik',
     onayli(ana('ayar'), 'agKapat', "komut('N0')", "tasiyiciAdi !== 'seri' && "));
  {
    const u = ornek();
    const giden = [];
    u.gonder = (k) => { giden.push(k); return Promise.resolve(); };
    const q = zamanlayicili(() => u.onayIste('durdur'));
    const silahli = u.onay;
    q[q.length - 1].fn();
    ok('[!] WIG c: onay ~6 s sonra KENDILIGINDEN duser (bayat "Eminim" tek tikla calismaz), komut gitmez',
       silahli === 'durdur' && u.onay === null && giden.length === 0 && q[q.length - 1].ms >= 3000 && q[q.length - 1].ms <= 10000,
       `${silahli} -> ${u.onay}, ${q.length ? q[q.length - 1].ms : '-'} ms`);
    zamanlayicili(() => u.onayIste('akimSifir'));
    secenekler.watch.gorunum.call(u, 'pil');
    const g1 = u.onay;
    zamanlayicili(() => u.onayIste('akimSifir'));
    secenekler.watch.bagli.call(u, false);
    ok('[!] WIG c: gorunum degisince ya da baglanti kopunca onay duser', g1 === null && u.onay === null);
    const v = ornek();
    v.tasiyiciAdi = 'demo';
    zamanlayicili(() => v.onayIste('enerjiSifir'));
    try { const p = v.gonder('?'); if (p && p.catch) p.catch(() => {}); } catch (e) { /* demo betigi yok */ }
    ok('[!] WIG c: karta giden herhangi bir komut silahli onayi dusurur (Eminim baska is yapildiktan sonra kalmaz)', v.onay === null);
    const f = ornek();
    f.gonder = () => Promise.resolve();
    const fq = zamanlayicili(() => f.fabrikaSifirla());
    const fs1 = f.sifirlaOnay;
    if (fq.length) fq[fq.length - 1].fn();
    const fs2 = f.sifirlaOnay;
    zamanlayicili(() => f.fabrikaSifirla());
    secenekler.watch.gorunum.call(f, 'canli');
    ok('[!] WIG c: fabrika sifirlama onayi da zaman asiminda ve gorunum degisince duser (saatler sonra tek tik R! YOK)',
       fs1 === true && fs2 === false && f.sifirlaOnay === false && fq.length >= 1);
    const w = ornek();
    const wg = [];
    w.gonder = (k) => { wg.push(k); return Promise.resolve(); };
    w.agWebSifre = ''; w.agWebSifreGonder();
    w.agSifre = ''; w.agSifreGonder();
    const h1 = w.hata;
    w.agWebKorumaKaldir();
    ok('[!] WIG c: bos web parolasi / bos ag parolasi GONDERILMEZ (sebep soylenir); koruma YALNIZ "Korumayi kaldir" ile (Ns)',
       wg.join(',') === 'Ns' && /boş/i.test(h1) && /:disabled="!bagli \|\| !agWebSifre"/.test(ana('ayar'))
       && /:disabled="!bagli \|\| !agSifre"/.test(ana('ayar')), wg.join(','));
  }
  ok('WIG c: pil "Kaydi sil" -> "Tarayicidaki noktalari sil" (kartin kaydini silmez), onayda neyin silinecegi yaziyor',
     /Tarayıcıdaki noktaları sil/.test(ana('pil')) && !/>Kaydı sil</.test(ana('pil')) && /v-if="onay === 'pilSil'"[^>]*class="uyari"/.test(ana('pil')));
  {
    const k = bilesen(KLm.KayitlarEkrani, { kartAdres: (y) => y, kartTaban: '', tasiyici: 'akis', bagli: true, gonder: null, etkin: true },
      { esitlenebilir: true });
    let esit = 0;
    k.esitle = () => { esit++; };
    k.kartKimlik = null;
    k.arsivDegisti(true);
    const a1 = { arsiv: k.arsiv, onay: k.arsivOnay, esit };
    k.arsivVazgec();
    const a2 = { arsiv: k.arsiv, onay: k.arsivOnay };
    k.arsivDegisti(true);
    k.arsivOnayla();
    const a3 = { arsiv: k.arsiv, onay: k.arsivOnay, esit };
    k.arsivDegisti(false);
    ok('[!] WIG c: "bu tarayici arsivdir" IKI ASAMALI: isaretlemek yazmaz/esitlemez; Eminim -> arsiv + esitle; kapatmak aninda',
       !a1.arsiv && a1.onay && a1.esit === 0 && !a2.arsiv && !a2.onay && a3.arsiv && !a3.onay && a3.esit === 1 && k.arsiv === false
       && /:checked="arsiv \|\| arsivOnay"/.test(KLm.KayitlarEkrani.template) && /class="kl-arsiv-eminim"[^>]*@click="arsivOnayla"/.test(KLm.KayitlarEkrani.template),
       JSON.stringify([a1, a2, a3]));
  }
  ok('WIG c: onay/vazgec odagi kaybetmiyor: onayIste onay dugmesine, onayVazgec acan dugmeye, kopya silme ayni kalip',
     govdeIcinde(appKaynak, 'onayIste', '[data-onay=') && govdeIcinde(appKaynak, 'onayVazgec', '[data-onay-ac=')
     && /@click="silBasla\(k\.kimlik\)"/.test(KLm.KayitlarEkrani.template) && /@click="silVazgec\(k\.kimlik\)"/.test(KLm.KayitlarEkrani.template));
  {
    const u = ornek();
    let n = 0;
    let coz;
    u.kayitKomut = () => { n++; return new Promise((r) => { coz = r; }); };
    u.kayit.g = { durum: al('KDR').KAYIT, oturum: 5 };
    u.notMetni = 'deneme';
    const p1n = u.notEkle();
    const p2n = u.notEkle();
    ok('[!] WIG c: not gonderilirken ikinci basis IKINCI Gn gondermez (dugme mesgul: disabled + aria-busy + "Ekleniyor…")',
       n === 1 && /type="submit" class="birincil"[^>]*:disabled="notGonderiliyor"[^>]*:aria-busy="notGonderiliyor \? 'true' : 'false'"/.test(ana('canli'))
       && /Ekleniyor…|m\.notGonderiliyor/.test(ana('canli')), `${n} cagri`);
    if (coz) coz(true);
    SONRA.push(async () => {
      await p1n; await p2n;
      ok('WIG c: not istegi bitince dugme yeniden acik', u.notGonderiliyor === false);
    });
  }

  /* ── (e) bos / bayat okuma ────────────────────────────────────────── */
  {
    const u = ornek();
    const a = u.veriYok;
    u.bagli = true;
    const b = u.veriYok;
    u.gecmis = [Object.freeze({ t: 0, v: 1, i: 0, w: 0, e: 0 })];
    const c = u.veriYok;
    ok('[!] WIG e: baglanti yokken / ilk D gelmeden okuma kartlari "0.000 V" DEGIL "—" (veriYok)',
       a === true && b === true && c === false && ['!voltGecersiz && !veriYok', '!amperGecersiz && !veriYok', '!gucGecersiz && !veriYok', '!veriYok']
         .every((x) => ana('canli').includes(`<div class="deger" v-if="${x}">`)));
    u.pilDcirN = 0;
    const d0 = u.pilDcirYazi;
    u.pilDcirN = 3; u.pilDcirAni = 0.0456;
    ok('WIG e: pil ic direnc olcum yokken "—" (0.0 mΩ degil)', d0 === '—' && u.pilDcirYazi === '45.6 mΩ' && /\{\{ pilDcirYazi \}\}/.test(ana('pil')), d0);
    const e = ornek();
    const e1 = e.esitlenmemisYazi;
    ok('WIG e: serit alt bilgisi bagli degilken "bagli degil" diyor (kart suclanmiyor)', /bağlı değil/.test(e1) && e1.includes('—'), e1);
  }

  /* ── (f) metinler ekranda olani soyluyor ──────────────────────────── */
  {
    const u = ornek();
    const durumlar = { BEKLEMEDE: 0, CALISIYOR: 1, BITTI: 2, DURDURULDU: 3, HATA: 4 };
    const dYanlis = Object.entries(durumlar).filter(([ad, k]) => { u.pilDurum = ad; return u.pilDurumYazi !== SZ.ceviri('pil.durum.' + k, 'tr'); });
    u.pilDurum = 'YENI';
    const bilinmeyen = u.pilDurumYazi;
    const fwHata = [...ino.matchAll(/case PILH_(\w+):\s*return "([^"]*)"\s*(?:"([^"]*)")?/g)];
    const kodlar = { GERILIM_DUSUK: 1, GERILIM_YUKSEK: 2, TERS: 3, BAYPAS: 4, SURE: 5, AKIM_YOK: 6 };
    const hYanlis = fwHata.filter((m) => { u.pilHata = m[2] + (m[3] || ''); return u.pilHataYazi !== SZ.ceviri('pil.hata.' + kodlar[m[1]], 'tr'); });
    ok('[!] WIG f: pil durumu ve hatasi SOZLUKTEN (CALISIYOR -> "çalışıyor", TERS POLARITE -> "ters polarite"); firmware`in 6 hata metninin hepsi eslesiyor',
       dYanlis.length === 0 && hYanlis.length === 0 && fwHata.length === 6 && /YENI/.test(bilinmeyen)
       && /\{\{ pilDurumYazi \}\}/.test(ana('pil')) && /\{\{ pilHataYazi \}\}/.test(ana('pil')),
       dYanlis.map((x) => x[0]).concat(hYanlis.map((m) => m[1])).join(',') || `${fwHata.length} hata`);
    /* 3F (PL3): ekran artik egriyi GERCEKTEN ciziyor — serit vaat ediyorsa sablonda tuval VAR */
    ok('[!] WIG f / PL3: serit "deşarj eğrisi" diyorsa Pil ekraninda egri tuvali VAR (vaat = icerik)',
       /eğri/.test(SZ.ceviri('kb.pil_alt', 'tr')) && /curve/.test(SZ.ceviri('kb.pil_alt', 'en'))
       && /<canvas ref="pilTuval" class="pil-grafik" role="img" :aria-label="pl\.grafikEtiket">/.test(ana('pil')));
    ok('WIG f: yaniti yalniz Konsol`a dusen dugmeler bunu soyluyor (Fazi / Ag durumunu ... Konsol)',
       /komut\('F'\)[^>]*>[^<]*Konsol/.test(ana('ayar')) && /komut\('N\?'\)[^>]*>[^<]*Konsol/.test(ana('ayar')));
    ok('WIG f: Konsol "Temizle" -> "Gunlugu temizle"; kopya silme "Kopyayi sil"',
       />Günlüğü temizle</.test(ana('konsol')) && SZ.ceviri('kl.sil', 'tr') === 'Kopyayı sil');
    ok('WIG f: ADC yanit vermiyor metinleri sozlukte ve sonraki adimi soyluyor (I²C tara)',
       /\{\{ m\.adcYokV \}\}/.test(ana('canli')) && /\{\{ m\.adcYokI \}\}/.test(ana('canli'))
       && /I²C tara/.test(SZ.ceviri('cn.adc_yok_v', 'tr')) && /I²C scan/.test(SZ.ceviri('cn.adc_yok_v', 'en')));
    ok('WIG f: izleyici bilgisi TEK yerde (bildirim + devral dugmesi); Canli`daki ikinci kopya yok',
       !/m\.izleyici/.test(ana('canli')) && /Sürücülüğü devral/.test(html));
    u.gecmis = [{ t: 3900 }];
    const s1 = u.sureGoster;
    u.gecmis = [{ t: 65 }];
    ok('[!] WIG f: gecen sure "1 sa 5 dk" ("1s 5dk" = 1 saniye 5 dakika okunuyordu); saniye "sn"',
       s1 === '1 sa 5 dk' && u.sureGoster === '1 dk 5 sn', `${s1} | ${u.sureGoster}`);
    const n = ornek();
    n.kayit.g = { durum: al('KDR').KAYIT, oturum: 1, nokta: 12345 };
    ok('[!] WIG f: nokta sayisi "12.345" DEGIL (panelde . ondalik ayraci): dar bosluklu gruplama',
       !/12\.345/.test(n.kayitNoktaYazi) && n.kayitNoktaYazi.startsWith('12\u202f345'), n.kayitNoktaYazi);
    ok('WIG f: plan tarihi ISO-benzeri YYYY-AA-GG (Kayitlar listesiyle ayni)', /^\d{4}-\d\d-\d\d \d\d:\d\d$/.test(n.tarihYazi(1767225600)),
       n.tarihYazi(1767225600));
  }
  {
    const u = ornek();
    const giden = [];
    u.gonder = (k) => { giden.push(k); return Promise.resolve(); };
    u.kalibV = 'abc'; u.kalibreV();
    const h1 = u.hata;
    u.hata = ''; u.kalibA = '0'; u.kalibreA();
    const h2 = u.hata;
    u.hata = ''; u.pilKesmeGiris = '40'; u.pilKesmeGonder();
    /* 3F (PU15): kesme hatasi ALANIN YANINDA (Pil ekraninin uyarisi), genel kutuda degil */
    const h3 = u.pilUyari ? u.pilUyari.metin : '';
    ok('[!] WIG f: kalibrasyon / kesme gecersizse SESSIZ degil: sebep + ornek yazilir, komut gitmez',
       giden.length === 0 && /sayı/.test(h1) && /sayı/.test(h2) && /0\.5 … 38\.5 V/.test(h3) && u.hata === ''
       && u.pilUyari.tur === 'panel', [h1, h2, h3].join(' | '));
    u.hata = ''; u.fazKal = 'x'; u.fazGonder();
    ok('[!] WIG f: faz hatasi alanin YANINDA (role=alert, aria-invalid + aria-describedby), en ustteki genel kutuda degil',
       /sayı girin/.test(u.fazHata) && u.hata === '' && /<p v-if="fazHata" class="hata" role="alert" id="faz-hata">/.test(ana('ayar'))
       && /v-model="fazKal"[^>]*:aria-invalid="fazHata \? 'true' : 'false'"[^>]*aria-describedby="faz-hata[ "]/.test(ana('ayar')), u.fazHata);
    const b = (ad, mesaj) => u.baglantiHatasiMetni(Object.assign(new Error(mesaj), { name: ad }));
    ok('[!] WIG f: baglanti hatalari sonraki adimi soyluyor (port baska programda -> kapatip yeniden baglanin)',
       /başka bir program/.test(b('InvalidStateError', 'The port is already open.')) && /başka bir program/.test(b('NetworkError', 'Failed to open serial port.'))
       && /Failed to open/.test(b('NetworkError', 'Failed to open serial port.')) && b('NotFoundError', 'x') === '');
    ok('WIG f: "Demo kipi açılamadı" Turkce; Devralinamadi (409) eylem oneriyor; okuma hatasi sonraki adim',
       /'Demo kipi açılamadı: '/.test(kod) && /Başka bir sürücü/.test(kod) && /Okuma hatası: ' \+ e\.message \+ ' — /.test(kod));
  }
  {
    const anah = (a) => SZ.ceviri(a, 'tr');
    ok('[!] WIG f: Kayitlar hata metinleri sonraki adimi soyluyor (ag/host/hata/depo/kal/disari)',
       /Yenile/.test(anah('kl.neden_ag')) && /adresinden/.test(anah('kl.neden_host')) && /Yenile/.test(anah('kl.neden_hata'))
       && /izin/.test(anah('kl.neden_depo')) && /Yenile/.test(anah('kl.kal_hata')) && /yeniden deneyin/.test(anah('kg.disari_hata'))
       && /Refresh/.test(SZ.ceviri('kl.neden_ag', 'en')) && /again/.test(SZ.ceviri('kg.disari_hata', 'en')));
    /* 4D: 3H-2'den beri Ayarlar → Eşleştirme VAR — imza hatasi oraya (ve PC'de kopru/pc.py'ye) gonderir;
       olmayan bir bolume ("Ayarlar (3H)") ve ic asama koduna gondermez. */
    const esVar = /id: 'eslestirme'/.test(appKaynak);
    ok('[!] WIG f: imza hatasi VAR OLAN ayara (Ayarlar → Eşleştirme, 3H-2) gonderiyor; ic asama kodu (3H/3E) kullaniciya gorunmuyor',
       !/\(3[A-Z]\)/.test(anah('kl.neden_imza') + anah('kg.skop_ipucu') + SZ.ceviri('kl.neden_imza', 'en') + SZ.ceviri('kg.skop_ipucu', 'en'))
       && esVar && /Ayarlar → Eşleştirme/.test(anah('kl.neden_imza')) && /Ayarlar → Eşleştirme/.test(anah('ay.kal_neden_imza'))
       && /kopru\/pc\.py/.test(anah('kl.neden_imza')) && !/henüz yok|not available yet/.test(anah('ay.kal_neden_imza') + SZ.ceviri('ay.kal_neden_imza', 'en')));
    ok('WIG f: plan / baglanti hatalari ne yapilacagini soyluyor',
       /seçin/.test(anah('cn.hata_plan_bas')) && /ileri alın|uzatın/.test(anah('cn.hata_plan_gecmis')) && /Karta bağlan/.test(anah('cn.hata_bagli_degil')));
    ok('WIG f: kayit gorunumunde veri yoksa NEDEN bos oldugu yaziyor (kirik sayfa degil)',
       /<section class="kart" v-if="!grafikVar && !notlar\.length && !pilOzet && !yakalamalar\.length">/.test(KGm.KayitGorunumu.template)
       && /\{\{ m\.veriYok \}\}/.test(KGm.KayitGorunumu.template) && SZ.ceviri('kg.veri_yok', 'tr').length > 20);
  }
  {
    /* Turkce harf sinirli (JS \b 'ı' gibi harfleri harf saymaz): 'bağlısın' YAKALANIR, 'bağlısınız' DEGIL */
    const harf = 'A-Za-zçğıöşüÇĞİÖŞÜ';
    const sen = new RegExp(['görüyorsun', 'gönderemezsin', 'bağlısın', 'yazacağın', 'şüphelenirsen', 'çalışırsan',
      'kullan[.]', 'bağla,', 'gir,', 'yap[.]', 'bağla ve'].map((x) => `(?<![${harf}])${x}(?![${harf}])`).join('|'));
    const metin = html.replace(/<[^>]+>/g, ' ');
    ok('WIG f: gomulu metinlerde hitap "siz" (sen bicimi yok)', !sen.test(metin) && sen.test('ağ üzerinden bağlısın.'),
       (metin.match(sen) || [''])[0]);
  }

  /* ── (g) baslik, odak, cekmece ─────────────────────────────────────── */
  ok('[!] WIG g: her gorunumde (osiloskop disi) h1 var; Kayitlar listesi ve kayit gorunumu h1; Canli grafik basligi h2',
     ['canli', 'ayar', 'pil', 'konsol'].every((g) => /<h1\b/.test(ana(g))) && /<h1\b/.test(KLm.KayitlarEkrani.template)
     && /<h1 class="kg-baslik" ref="baslik" tabindex="-1">/.test(KGm.KayitGorunumu.template)
     && /<h2 class="gosterge-baslik">\{\{ m\.grafik \}\}<\/h2>/.test(ana('canli')) && /\.kart > h1/.test(cssKod));
  {
    const u = ornek();
    const cagri = [];
    u.$refs.icerik = { setAttribute: (a, d) => cagri.push(a + '=' + d), focus: () => cagri.push('focus'),
      addEventListener: (t) => cagri.push('dinle:' + t), removeAttribute: () => {} };
    u.icerigeGec();
    ok('[!] WIG g: "Icerige gec" baglantisi kabugun ILK ogesi; odagi .icerik`e tasir (hash degistirmeden)',
       /<div class="kabuk"[^>]*>\s*<a class="atla" href="#icerik" @click\.prevent="icerigeGec">/.test(html)
       && /<div class="icerik" id="icerik" ref="icerik" :inert="cekmeceAcik">/.test(html)
       && cagri.join(',') === 'tabindex=-1,focus,dinle:blur' && /\.atla:focus-visible\s*\{[^}]*transform:\s*none/.test(cssKod), cagri.join(','));
  }
  ok('[!] WIG g: cekmece acikken arka plan INERT (.icerik + ust cubuk baglanti kumesi); aside`in adi yok (tek "Ana gezinme" = nav)',
     /<div class="baglanti" :inert="cekmeceAcik">/.test(html) && /<aside id="serit" class="serit">/.test(html)
     && (html.match(/:aria-label="m\.gezinme"/g) || []).length === 1);
  {
    const u = ornek();
    u.cekmeceAcik = true;
    const eskiW = sandbox.window;
    sandbox.window = Object.assign({}, eskiW, { matchMedia: () => ({ matches: true }) });
    try { u.genislikDegisti(); } finally { sandbox.window = eskiW; }
    ok('[!] WIG g: pencere genisleyince (> 900 px) acik cekmece kapanir — masaustunde icerik inert KALMAZ', u.cekmeceAcik === false);
  }
  {
    const u = ornek();
    secenekler.watch.gorunum.call(u, 'pil');
    const t1 = sandbox.document.title;
    secenekler.watch.gorunum.call(u, 'konsol');
    ok('[!] WIG g: sekme basligi gorunumu soyluyor (ekran okuyucu + gecmis)', t1 === 'Pil testi — Ölçüm Kartı'
       && sandbox.document.title === 'Konsol — Ölçüm Kartı', `${t1} | ${sandbox.document.title}`);
  }
  ok('[!] WIG g: kayit acilinca odak kayit basligina (etkinse), kayit_gorunum mounted',
     /this\.\$refs\.baslik/.test(String(KGm.KayitGorunumu.mounted)) && /focus\(/.test(String(KGm.KayitGorunumu.mounted)));
  {
    const u = ornek();
    u.$nextTick = (f) => f();
    u.gorunum = 'konsol';
    const kutu = { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 };
    u.$refs.gunlukKutu = kutu;
    u.kaydet('a');
    const yukarida = kutu.scrollTop;
    kutu.scrollTop = 795;
    u.kaydet('b');
    const dipte = kutu.scrollTop;
    u.gorunum = 'canli'; kutu.scrollTop = 795; kutu.scrollHeight = 1200;
    u.kaydet('c');
    ok('[!] WIG g: konsol yukari kaydirilmisken yeni satir DIBE ATMIYOR; dipteyse izliyor; gizliyken dokunulmuyor',
       yukarida === 0 && dipte === 1000 && kutu.scrollTop === 795, `${yukarida} ${dipte} ${kutu.scrollTop}`);
  }
  ok('WIG g: yakalama tablosu sinirli (rapor disi 100 + "daha fazla"), rapor tam',
     /v-for="y in gorunenYakalamalar"/.test(KGm.KayitGorunumu.template) && /@click="yakalamaSinir \+= 100"/.test(KGm.KayitGorunumu.template)
     && (() => { const y = Array.from({ length: 250 }, (_, i) => ({ sira: i }));
       const g = bilesen(KGm.KayitGorunumu, { dil: 'tr', rapor: false }, { yakalamalar: y });
       const r = bilesen(KGm.KayitGorunumu, { dil: 'tr', rapor: true }, { yakalamalar: y });
       return g.gorunenYakalamalar.length === 100 && r.gorunenYakalamalar.length === 250; })());

  /* ── (h) CSS: odak, guvenli alan, dokunma, tema ───────────────────── */
  ok('[!] WIG h: dondurulmus Canli tuvali (tabIndex 0) GORUNUR odak halkasi; kg tuvalleri de',
     /\.canli-tuval\.donmus canvas\.canli-grafik:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--vurgu\)/.test(cssKod)
     && /canvas\.kg-grafik:focus-visible[^{]*\{[^}]*outline:\s*2px/.test(cssKod));
  ok('[!] WIG h: suruklenen tuvallerde metin secimi kapali (user-select none)',
     /canvas\.kg-grafik,\s*canvas\.kg-gezgin,\s*\.canli-tuval\.donmus canvas\.canli-grafik\s*\{[^}]*-webkit-user-select:\s*none;\s*user-select:\s*none/.test(cssKod));
  const dar = (cssKod.match(/@media \(max-width: 900px\) \{([\s\S]*?)\n\}/) || [])[1] || '';
  ok('[!] WIG h: dar ekranda yapiskan ust cubuk odagi ortmuyor (scroll-padding-top), cekmece overscroll contain, perde touch-action none, govde kilidi',
     /html\s*\{[^}]*scroll-padding-top:\s*72px/.test(dar) && /\.serit\s*\{[^}]*overscroll-behavior:\s*contain/.test(dar)
     && /\.perde\s*\{[^}]*touch-action:\s*none/.test(dar) && /html:has\(\.cekmece-acik\)\s*\{[^}]*overflow:\s*hidden/.test(dar));
  const vp = (htmlTam.match(/<meta name="viewport" content="([^"]+)"/) || [])[1] || '';
  ok('[!] WIG h: iOS centik/durum cubugu: viewport-fit=cover YOK ya da env(safe-area-inset) VAR; durum cubugu saydam degil',
     (!/viewport-fit=cover/.test(vp) || /env\(safe-area-inset-/.test(cssKod))
     && !/apple-mobile-web-app-status-bar-style" content="black-translucent"/.test(htmlTam), vp);
  ok('WIG h: kullanici etiketleri (rozet) uzun boşluksuz metinde satiri tasirmiyor; 100dvh; parola/url alanlari temali',
     /\.kl-rozet,\s*\.kg-etiket\s*\{[^}]*overflow-wrap:\s*anywhere/.test(cssKod) && /min-height:\s*100dvh/.test(cssKod)
     && /height:\s*100dvh/.test(cssKod) && /input\[type=password\]/.test(cssKod) && /input\[type=url\]/.test(cssKod));
  {
    const zemin2 = {};
    for (const [ad, sec] of [['koyu', ':root[data-tema="koyu"]'], ['acik', ':root[data-tema="acik"]'], ['onpanel', ':root[data-tema="onpanel"]']]) {
      const k = cssKod.indexOf(sec);
      const blok = k >= 0 ? cssKod.slice(k, cssKod.indexOf('}', k)) : '';
      zemin2[ad] = (blok.match(/--zemin-2:\s*(#[0-9a-fA-F]{3,8})/) || [])[1];
    }
    const meta = { content: '', setAttribute(a, d) { if (a === 'content') this.content = d; } };
    const belge = { documentElement: { setAttribute() {} }, querySelector: (s) => (s === 'meta[name="theme-color"]' ? meta : null) };
    const sonuc = ['koyu', 'acik', 'onpanel'].map((t) => { TEMAm.temaUygula(belge, t, false); return meta.content.toLowerCase() === String(zemin2[t]).toLowerCase(); });
    TEMAm.temaUygula({ documentElement: { setAttribute() {} } }, 'acik', false);   // querySelector'suz belge atmaz
    ok('[!] WIG h: theme-color ETKIN temanin --zemin-2`si (Acik`ta adres cubugu koyu kalmiyor); ilk deger Koyu',
       sonuc.every(Boolean) && Object.values(zemin2).every(Boolean)
       && (htmlTam.match(/<meta name="theme-color" content="([^"]+)"/) || [])[1] === zemin2.koyu, JSON.stringify(zemin2));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   27. OSILOSKOP (3E — alt proje 3, OS1-OS8)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3E kararlari". Burada:
   (a) KABLOLAMA + DUZEN: rota, tembel modul (esitleme zinciri ancak kayitli
       yakalamada), sag sutun kumeleri ve DOM sirasi (dar ekranda denetimler
       dalganin altinda), erisilebilirlik ozellikleri, 3E stilleri belirtecle.
   (b) OS5 GUNLUK: Gt sinirlari FIRMWARE kaynagindan, komut uretici, `/komut`
       metni + `G?`, kartin `! G:` reddi oldugu gibi, GT / "durdu" satirlari.
   (c) OS4 OLCUM: kaynak etiketi; kayitli yakalama (ortak/kayit.js ile GERCEK
       kayitlar) panelde kartin hesabiyla — GERCEK KART fiksturunde M satiriyla
       basilan haneye kadar ayni.
   (d) OS3 SPEKTRUM: ham kodlarin TAMAMI, DC cizilmez, Hz yazisi, ust sinir (≤).
   (e) OS6 KAYITLI YAKALAMA: rota yaz/coz tersi, akis secimi, ac / canliya don.
   (f) OS2 IZGARA: 10 x 8 bolme (yatay = firmware SKOP_BOLME).
   Gercek tarayici (SSE + /skop.bin, IndexedDB, uc gorunum, 390 px):
   tarayici_skop.py (T3E).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 26. Osiloskop (3E) ---');
{
  const html = yorumsuz(htmlKaynak);
  const kod = yorumsuz(appKaynak);
  const css = cssOku();
  const al = (ad) => vm.runInContext(ad, sandbox);
  const OS = require(path.join(ARAYUZ, 'ekran', 'osiloskop.js'));
  const KGx = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
  const Kx = require(path.join(KOK, 'ortak', 'src', 'kayit.js'));
  const SKx = require(path.join(KOK, 'ortak', 'src', 'skop.js'));
  const SZx = sozlukTum();
  const osKaynak = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'osiloskop.js'), 'utf8');
  const skopMain = html.match(/<main class="gorunum" v-show="gorunum === 'skop'">([\s\S]*?)<\/main>/);
  const sm = skopMain ? skopMain[1] : '';

  /* ── (a) KABLOLAMA + DUZEN ──────────────────────────────────────── */
  {
    const hashten = al('hashtenGorunum');
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('[!] OS6: #/skop/kayit/<oturum>/<sira>[@kimlik] Osiloskop`u aciyor; #/skop da; bicimsiz adres varsayilana',
       dene('#/skop/kayit/12/5') === 'skop' && dene('#/skop/kayit/12/5@7') === 'skop' && dene('#/skop') === 'skop'
       && dene('#/skopx') === 'canli');
    const w = secenekler.watch.gorunum;
    const yazilan = [];
    sandbox.history = { replaceState: (a, b, h) => yazilan.push(h) };
    sandbox.location = { hash: '#/skop/kayit/12/5@7' };
    const sahte = { $nextTick() {}, grafikCiz() {}, osiloCiz() {}, spektrumCiz() {}, skopAcik: false };
    w.call(sahte, 'skop');
    ok('[!] OS6: watch.gorunum KAYITLI YAKALAMA adresini #/skop`a EZMIYOR; modul kuruluyor (skopAcik)',
       yazilan.length === 0 && sahte.skopAcik === true, yazilan.join());
    delete sandbox.location;
    delete sandbox.history;
    ok('Osiloskop modulu varsayilan (Canli) acilista KURULMUYOR', secenekler.data().skopAcik === false);
  }
  {
    const statik = iceAktarmaGrafigi().map((g) => g.goruntu);
    const osAgac = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'osiloskop.js')).map((g) => g.goruntu);
    ok('[!] Osiloskop modulu TEMBEL: acilis grafiginde YOK, skopYukle import() ediyor, inmezse sebep ekranda',
       !statik.includes('ekran/osiloskop.js')
       && govdeIcinde(appKaynak, 'skopYukle', "import('./ekran/osiloskop.js')")
       && govdeIcinde(appKaynak, 'skopYukle', "this.skopDurum = 'yuklenemedi'") && /os\.yuklenemedi/.test(sm),
       statik.join(' '));
    ok('[!] Esitleme zinciri (esitleme / depo_idb / ortak kayit, esitle, imza) osiloskobun STATIK agacinda YOK — yalniz kayitli yakalamada iner',
       osAgac.join(' ') === ['ortak/grafik.js', 'ortak/fft.js', 'ortak/skop.js', 'ortak/ozet.js', 'ortak/istatistik.js']
         .filter((x) => osAgac.includes(x)).join(' ')
       && !osAgac.some((g) => /esitleme|depo_idb|ortak\/(kayit|esitle|imza|disari)\.js/.test(g))
       && /import\('\.\/esitleme\.js'\)/.test(osKaynak) && /import\('\/ortak\/disari\.js'\)/.test(osKaynak),
       osAgac.join(' '));
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    if (fs.existsSync(kunyeYolu)) {
      const b = JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {};
      const zincir = ['ekran/osiloskop.js', ...osAgac];
      const top = zincir.reduce((n, a) => n + (Number.isFinite(b[a]) ? b[a] : NaN), 0);
      ok('Osiloskop zinciri (modul + statik agaci) gzip <= 48 KB, <= 6 dosya ve kunyede (goruntude) var',
         top > 0 && top <= 48 * 1024 && zincir.length <= 6, `${top} B · ${zincir.join(' ')}`);
      /* #/skop ile ACILIS: sayfanin statik kumesi + osiloskop zinciri (Canli inmez) — 3D'nin 250 KB kurali */
      const acilisK = new Set(['index.html']);
      for (const m of html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)) {
        if (!/^(https?:|data:|#|mailto:)/.test(m[1])) acilisK.add(m[1]);
      }
      for (const g of iceAktarmaGrafigi()) acilisK.add(g.goruntu);
      for (const a of zincir) acilisK.add(a);
      const skopAcilis = [...acilisK].reduce((n, a) => n + (Number.isFinite(b[a]) ? b[a] : NaN), 0);
      ok('[!] #/skop ile acilis (statik + osiloskop zinciri) gzip <= 250 KB ve <= 14 dosya',
         skopAcilis > 0 && skopAcilis <= 250 * 1024 && acilisK.size <= 14, `${skopAcilis} B · ${acilisK.size} dosya`);
    }
  }
  {
    const kumeler = [...sm.matchAll(/<fieldset class="kart skop-kume" data-kume="([a-z]+)">([\s\S]*?)<\/fieldset>/g)];
    const ad = kumeler.map((k) => k[1]);
    const ic = Object.fromEntries(kumeler.map((k) => [k[1], k[2]]));
    ok('[!] OS1: sag sutunda bes kume, sirayla Yakalama · Zaman tabani · Tetik · Gunluk · Kalibrasyon cikisi (fieldset + legend)',
       ad.join() === 'yakalama,taban,tetik,gunluk,cal' && kumeler.every((k) => /<legend>\{\{ os\.\w+ \}\}<\/legend>/.test(k[2])),
       ad.join());
    ok('[!] OS1: her denetim KENDI kumesinde (yakala/surekli/otomatik · tdiv · tm/te/tl/tp/tn · Gt · CAL)',
       !!ic.yakalama && /@click="osiloYakala"/.test(ic.yakalama) && /@click="surekliDegis"/.test(ic.yakalama)
       && /@click="osiloOtomatik"/.test(ic.yakalama) && /tabanDegistir\(-1\)/.test(ic.taban || '')
       && ['tm', 'te', 'tl', 'tp', 'tn'].every((k) => (ic.tetik || '').includes(`skopKomut('${k}' +`))
       && /@click="skopGunlukBaslat"/.test(ic.gunluk || '') && /@click="skopGunlukDurdur"/.test(ic.gunluk || '')
       && /@change="calGonder"/.test(ic.cal || ''));
    const iDalga = sm.indexOf('class="kart skop-dalga"');
    const iDenetim = sm.indexOf('<aside class="skop-denetim"');
    const iSpektrum = sm.indexOf('class="kart skop-spektrum"');
    ok('[!] OS1: DOM sirasi dalga -> denetimler -> spektrum (dar ekranda denetimler dalganin hemen altinda; klavye sirasi)',
       iDalga > 0 && iDalga < iDenetim && iDenetim < iSpektrum && /<div class="skop-duzen">/.test(sm));
    const blok = css.slice(css.indexOf('3E — OSİLOSKOP'), css.indexOf('/* Rapor YAZDIRILIRKEN'));
    const dar = [...blok.matchAll(/@media \(max-width: 900px\)\s*\{([\s\S]*?)\n\}/g)].map((m) => m[1]).join('\n');
    ok('[!] OS1: genis ekranda dalga >= 2/3 (7fr / 3fr), denetim sagda iki satir; <= 900 px TEK sutun: dalga, denetim, spektrum',
       /grid-template-columns:\s*minmax\(0, 7fr\) minmax\(220px, 3fr\)/.test(blok)
       && /grid-template-areas:\s*"dalga denetim" "spektrum denetim"/.test(blok)
       && /grid-template-columns:\s*minmax\(0, 1fr\)/.test(dar) && /grid-template-areas:\s*"dalga" "denetim" "spektrum"/.test(dar));
    ok('[!] 3E stilleri YALNIZ belirtecle: sabit renk (#hex / rgb) yok',
       blok.length > 500 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(blok.replace(/\/\*[\s\S]*?\*\//g, '')));
    ok('[!] OS8: olcum kutusu, gunluk durumu ve ret alanlari aria-live="polite"; tuvaller role=img + etiket; aside etiketli',
       /class="skop-olcum-kutu" aria-live="polite"/.test(sm) && /class="skop-gunluk-durum"[^>]*aria-live="polite"/.test(sm)
       && (sm.match(/class="kume-ret" role="status" aria-live="polite"/g) || []).length === 2
       && /class="spektrum-ozet" aria-live="polite"/.test(sm)
       && /ref="osiloTuval"[^>]*role="img" :aria-label="os\.tuvalEtiket"/.test(sm)
       && /ref="spektrumTuval"[^>]*role="img" :aria-label="os\.spektrumEtiket"/.test(sm)
       && /<aside class="skop-denetim" :aria-label="os\.denetimler">/.test(sm));
    ok('OS8: Surekli dugmesi durumu aria-pressed ile soyluyor; olcum sayilari tabular-nums',
       /@click="surekliDegis"[\s\S]{0,200}:aria-pressed="surekli \? 'true' : 'false'"/.test(sm)
       && /\.skop-olcum-deger\s*\{[^}]*tabular-nums/.test(css) && /\.skop-gunluk-durum\s*\{[^}]*tabular-nums/.test(css));
    const os = al('OS_METIN');
    ok('[!] OS8: osiloskobun metinleri sozlukten (OS_METIN, tr + en dolu); sablon `os.` kullaniyor',
       Object.values(os).every((k) => k in SZx.SOZLUK && SZx.SOZLUK[k].tr && SZx.SOZLUK[k].en)
       && Object.keys(os).length >= 60 && (sm.match(/\{\{ os\.\w+ \}\}/g) || []).length >= 40,
       `${Object.keys(os).length} anahtar`);
  }

  /* ── (b) OS5 GUNLUK ─────────────────────────────────────────────── */
  {
    const ar = (ino.match(/static bool kayit__skop_aralik\([\s\S]*?\n}/) || [])[0];
    const sinir = /x != 0 && \(x < (\d+)UL \|\| x > (\d+)UL\)/.exec(ar || '');
    ok('[!] OS5: Gt araligi kartin sinirindan (kayit__skop_aralik: 0 ya da 1000 … 3 600 000 ms, en cok 7 hane)',
       !!sinir && Number(sinir[1]) === al('SKOP_GUNLUK_ENAZ_MS') && Number(sinir[2]) === al('SKOP_GUNLUK_AZAMI_MS')
       && /strlen\(p\) > 7u/.test(ar), sinir ? `${sinir[1]} … ${sinir[2]}` : 'bulunamadi');
    const GK = al('skopGunlukKomutu');
    const k = (o) => { const r = GK(o); return r.komut || r.hata; };
    ok('[!] OS5: komut uretici — her tetik Gt0, N s -> Gt<ms> (virgul de), sinir disi / bos / sayi degil REDDEDILIR',
       k({ kip: 'tetik' }) === 'Gt0' && k({ kip: 'aralik', saniye: 5 }) === 'Gt5000' && k({ kip: 'aralik', saniye: '2,5' }) === 'Gt2500'
       && k({ kip: 'aralik', saniye: 1 }) === 'Gt1000' && k({ kip: 'aralik', saniye: 3600 }) === 'Gt3600000'
       && k({ kip: 'aralik', saniye: 0.999 }) === 'os.hata_aralik' && k({ kip: 'aralik', saniye: 3600.001 }) === 'os.hata_aralik'
       && k({ kip: 'aralik', saniye: '' }) === 'os.hata_aralik' && k({ kip: 'aralik', saniye: 'abc' }) === 'os.hata_aralik'
       && k({ kip: 'aralik', saniye: 0 }) === 'os.hata_aralik' && k({ kip: 'x' }) === 'os.hata_kip');
    /* kartin dogrulayicisinin JS esi: uretilen HER komut kartta gecerli */
    const kartKabul = (c) => /^Gt\d{1,7}$/.test(c) && (Number(c.slice(2)) === 0
      || (Number(c.slice(2)) >= 1000 && Number(c.slice(2)) <= 3600000));
    const uretilen = [{ kip: 'tetik' }, ...[1, 1.5, 7, 59.9, 600, 3599.9995, 3600].map((s) => ({ kip: 'aralik', saniye: s }))]
      .map((o) => GK(o).komut);
    ok('OS5: uretilen her Gt komutu kartin kabul kuralindan geciyor', uretilen.every(kartKabul), uretilen.join(' '));
    ok('[!] OS5: firmware Gt / Gtd alt komutunu taniyor (kayit_komut -> kayit_skop_komut)',
       /alt == 't'\) \{?\s*kayit_skop_komut\(s\)|else if \(alt == 't'\)[\s\S]{0,80}kayit_skop_komut/.test(ino)
       && /s\[2\] == 'd' && !s\[3\]/.test(ino));

    const u = ornek();
    const giden = [];
    u.gonder = async (m) => { giden.push(m); };
    u.gunlukKip = 'aralik'; u.gunlukSaniye = 5;
    const v = ornek();
    v.bagli = false;
    const gidenV = [];
    v.gonder = async (m) => { gidenV.push(m); };
    SONRA.push(async () => {
      u.bagli = true;
      await u.skopGunlukBaslat();
      const bas = giden.splice(0);
      await u.skopGunlukDurdur();
      const dur = giden.splice(0);
      u.gunlukKip = 'tetik';
      await u.skopGunlukBaslat();
      const tet = giden.splice(0);
      u.gunlukKip = 'aralik'; u.gunlukSaniye = 0.2;
      await u.skopGunlukBaslat();
      const red = giden.splice(0);
      const panelUyari = u.skopGunlukUyari;
      await v.skopGunlukBaslat();
      ok('[!] OS5: Baslat -> `Gt5000` + `G?`; Durdur -> `Gtd` + `G?`; her tetikte -> `Gt0`; sinir disi GONDERILMIYOR (sebep ekranda)',
         bas.join() === 'Gt5000,G?' && dur.join() === 'Gtd,G?' && tet.join() === 'Gt0,G?' && red.length === 0
         && panelUyari && panelUyari.tur === 'panel' && /1 … 3600 s/.test(panelUyari.metin),
         JSON.stringify({ bas, dur, tet, red, panelUyari }));
      ok('OS5: bagli degilken komut gitmiyor, sebep ekranda', gidenV.length === 0 && v.skopGunlukUyari
         && v.skopGunlukUyari.metin === 'Karta bağlı değil.');
      u.skopGunlukZamani = Date.now();
      u.satirIsle('! G: osiloskop gunlugu zaten suruyor (Gtd)');
      const ret = u.skopGunlukUyari;
      u.skopGunlukUyari = null;
      u.skopGunlukZamani = Date.now() - 6000;
      u.satirIsle('! G: osiloskop gunlugu zaten suruyor (Gtd)');
      ok('[!] OS5 (E9): komuttan sonraki 5 s icinde gelen `! G:` gunluk kumesinde OLDUGU GIBI; 6 s sonra gelen o komutun reddi sayilmiyor',
         ret && ret.tur === 'kart' && ret.metin === 'Kart reddetti: ! G: osiloskop gunlugu zaten suruyor (Gtd)'
         && u.skopGunlukUyari === null, JSON.stringify(ret));
    });
    const g = ornek();
    ok('OS5: GT gorulmeden durum "bilinmiyor"', g.skopGunlukDurumYazi === 'Günlük durumu bilinmiyor (bağlanınca kart söyler).'
       && g.skopGunlukAktif === false);
    g.satirIsle('GT 0 0 0 0');
    const kapali = g.skopGunlukDurumYazi;
    g.satirIsle('GT 1 5000 3 1');
    const aralik = g.skopGunlukDurumYazi;
    const aktif = g.skopGunlukAktif;
    g.satirIsle('GT 1 0 7 0');
    const tetik = g.skopGunlukDurumYazi;
    const n0 = g.olaylar.length;
    g.satirIsle('* G osiloskop gunlugu durdu: 9 yakalama, 2 yazilamayan');
    ok('[!] OS5: durum PASIF GT satirindan; kartin "gunlugu durdu" satiri durumu kapatiyor (sayilarla), olay yaziyor',
       kapali === 'Günlük kapalı' && aralik === 'Sürüyor: her 5 s · 3 yakalama · 1 yakalama yazılamadı' && aktif
       && tetik === 'Sürüyor: her tetikte · 7 yakalama' && g.skopGunlukAktif === false && g.kayit.gt.yakalama === 9
       && g.kayit.gt.yazilamayan === 2 && g.olaylar.length === n0 + 1,
       JSON.stringify({ kapali, aralik, tetik }));
    ok('OS5: "gunlugu durdu" ve "oturumu acilamadi" metinleri FIRMWARE`de birebir',
       ino.includes('Serial.print(F("* G osiloskop gunlugu durdu: "));') && ino.includes('Serial.print(F(" yakalama, "));')
       && ino.includes('Serial.println(F(" yazilamayan"));') && ino.includes('"! G: osiloskop gunlugu oturumu acilamadi — durdu"'));
    ok('[!] OS5: gunluk surerken elle yakalama dugmeleri KAPALI (kart reddeder), Surekli durdurulabilir',
       /@click="osiloYakala" data-skop="yakala"\s*:disabled="!bagli \|\| osiloBekliyor \|\| surekli \|\| skopGunlukAktif"/.test(sm)
       && /:disabled="!bagli \|\| \(skopGunlukAktif && !surekli\)"/.test(sm)
       && /@click="osiloOtomatik" :disabled="!bagli \|\| osiloBekliyor \|\| skopGunlukAktif"/.test(sm));
    ok('OS5: gunluk komutlari izleyicide (kopru, surucu degil) KAPALI', /data-gunluk="baslat"/.test(sm)
       && (sm.match(/:disabled="!kayitKomutAcik/g) || []).length === 2);
    const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
    const bas = SK.komut('Gt5000');
    const durum = SK.komut('G?');
    const elle = SK.komut('t');
    const iki = SK.komut('Gt0');
    const dur = SK.komut('Gtd');
    const kotu = SK.komut('Gt999');
    ok('[!] E12: demo karti Gt / Gtd: GT satiri, elle yakalama reddi, ret metinleri FIRMWARE`in metni',
       /basladi: 5000 ms'de bir/.test(bas[0]) && durum.includes('GT 1 5000 0 0')
       && elle[0] === '! skop: osiloskop gunlugu suruyor — elle yakalama yok (once Gtd)' && ino.includes(elle[0])
       && iki[0] === '! G: osiloskop gunlugu zaten suruyor (Gtd)' && ino.includes(iki[0])
       && /durdu: 0 yakalama, 0 yazilamayan/.test(dur[0])
       && kotu[0] === '! G: Gt<ms> — 0 (her tetik) ya da 1000..3600000; Gtd durdurur' && ino.includes(kotu[0]),
       JSON.stringify({ bas, elle, iki, dur, kotu }));
  }

  /* ── (c) OS4 OLCUM: kaynak + kayitli yakalamada kartin hesabi ────── */
  const fk = JSON.parse(fs.readFileSync(path.join(__dirname, 'olcum-skop-fikstur.json'), 'utf8'));
  const egri = fk.ct.split(' ').filter((p) => /^\d+:\d+$/.test(p)).map((p) => Number(p.split(':')[1]));
  function skopOturumu({ olay = true, mv = egri, parcali = true } = {}) {
    let sira = 0;
    const ham = [];
    const ekle = (tur, ot, yuk) => { sira++; ham.push(Kx.kayitPaketle(tur, sira, ot, yuk)); return sira; };
    const kanal = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
    const ot = ekle(Kx.T_BASLA, 1, Kx.baslaPaketle({ oturum_turu: 3, kal_bicim: 1, hiz_ms: 0, unix_s: 1790003000,
      kart_ms: 300000, acilis: 3, surum: 'A3-3E', kal: { normal: kanal(21), yuksek: kanal(201), i_ofset: 5, i_pga: 0.256,
        sont_ohm: 0.1, i_duzeltme: 1, sebeke_hz: 0, faz_kal_us: [0, 0] }, kal_no: 2 }));
    if (olay) ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_SKOP_KAL, kart_ms: 300001, mv }));
    const meta = { t_ms: 302000, sure_ms: 12, hz: 83333, tdiv_us: 1000, adim: SKx.KART_VOLT_ADIM, ofset: SKx.KART_VOLT_OFSET,
      tetik: 208, esik: 1916, histerezis: 14, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 25, onay: 2 };
    const kodlar = fk.kodlar;
    const bolum = parcali ? 400 : kodlar.length;
    const s0 = ekle(Kx.T_SKOP, ot, Kx.skopPaketle({ no: 1, ilk: 0, toplam: kodlar.length, parca: 0, meta, kodlar: kodlar.slice(0, bolum) }));
    if (parcali) ekle(Kx.T_SKOP, ot, Kx.skopPaketle({ no: 1, ilk: bolum, toplam: kodlar.length, parca: 1, kodlar: kodlar.slice(bolum) }));
    const eksik = ekle(Kx.T_SKOP, ot, Kx.skopPaketle({ no: 2, ilk: 0, toplam: kodlar.length, parca: 0,
      meta: { ...meta, t_ms: 303000 }, kodlar: kodlar.slice(0, 100) }));
    let n = 0;
    for (const h of ham) n += h.length;
    const b = new Uint8Array(n);
    let a = 0;
    for (const h of ham) { b.set(h, a); a += h.length; }
    const kayitlar = Kx.akisCoz(b);
    return { o: Kx.oturumlariKur(kayitlar).get(ot), kayitlar, s0, eksik, ot };
  }
  const mSatiri = (o) => `M f=${o.f.toFixed(3)} T=${o.T.toFixed(9)} Vpp=${o.Vpp.toFixed(4)} Vmax=${o.Vmax.toFixed(4)} `
    + `Vmin=${o.Vmin.toFixed(4)} Vort=${o.Vort.toFixed(4)} Vrms=${o.Vrms.toFixed(4)} Vac=${o.Vac.toFixed(4)} n=${o.n}`;
  const alanlar = (s) => Object.fromEntries(s.slice(2).trim().split(/\s+/).map((x) => x.split('=')));
  {
    const u = ornek();
    const kart = u.skopOlcumKaynak;
    u.skopAcikKayit = { gun: 'x', ms: 1 };
    const arsiv = u.skopOlcumKaynak;
    u.skopKayitli = { oturum: 1, no: 1 };
    const panel = u.skopOlcumKaynak;
    ok('[!] OS4: olcum kutusu KAYNAGINI yaziyor — canli kart (M), kopru arsivi, panel (kayitli)',
       kart === 'kart' && arsiv === 'arsiv' && panel === 'panel'
       && u.skopOlcumKaynakYazi === 'Kaynak: panel, kaydın ham kodlarından — kartın hesabıyla (skopOlcKart)'
       && /:data-kaynak="skopOlcumKaynak">\{\{ skopOlcumKaynakYazi \}\}/.test(sm));
  }
  {
    const { o, s0, eksik } = skopOturumu();
    const r = OS.yakalamaKur(o, s0);
    const kartM = alanlar(fk.m);
    const panelM = alanlar(mSatiri(r.olcum));
    const esit = ['f', 'T', 'Vpp', 'Vmax', 'Vmin', 'Vort', 'Vrms', 'Vac', 'n'].filter((a) => panelM[a] !== kartM[a]);
    ok('[!] OS4 GERCEK KART: kayitli yakalama (ortak/kayit.js ile paketlenip cozulen 2 parca + egri OLAYI) panelde kartin M satiriyla AYNI',
       !r.hata && r.osilo.olcumKaynak === 'panel' && r.bilgi.egri === true && esit.length === 0,
       esit.length ? `farkli: ${esit.map((a) => `${a} ${panelM[a]}/${kartM[a]}`).join(' ')}` : mSatiri(r.olcum));
    const u = ornek();
    u.satirIsle(fk.ct);
    u.osilo = { voltAdim: 0.028788, voltOfset: SKx.KART_VOLT_OFSET, veri: [2048] };
    const canliEksen = u.kodVolt(2048);
    u.osilo = r.osilo;
    const kayitEksen = u.kodVolt(2048);
    u.skopKal = null;
    const ctsiz = u.kodVolt(2048);
    ok('[!] OS6: kayitli yakalamanin ekseni KENDI egrisiyle (canli CT olmasa da) — CT`li canli eksenle ayni',
       Math.abs(kayitEksen - canliEksen) < 1e-6 && Math.abs(ctsiz - canliEksen) < 1e-6 && r.osilo.kal.kod.length === 17,
       `${kayitEksen} / ${canliEksen} / ${ctsiz}`);
    ok('OS6: eksik yakalama (parca eksik) CIZILMIYOR, sebebi soyleniyor', OS.yakalamaKur(o, eksik).hata === 'os.hata_yakalama_eksik'
       && OS.yakalamaKur(o, 999).hata === 'os.hata_yakalama_yok');
    const e2 = skopOturumu({ olay: false });
    const r2 = OS.yakalamaKur(e2.o, e2.s0);
    const u2 = ornek();
    u2.satirIsle(fk.ct);                         // canli kartin CT'si VAR — ama kayit egrisiz olculmus
    u2.osilo = r2.osilo;
    const beklenen = 2048 * r2.osilo.voltAdim - r2.osilo.voltOfset;
    ok('[!] OS4/OS6: egri OLAYI yoksa (ya da gecersizse) kart o yakalamayi EGRISIZ olcmustu: olcum skopOlc + ofset, eksen HAM',
       r2.osilo.kal === null && r2.bilgi.egri === false
       && Object.is(r2.olcum.Vpp, SKx.skopOlc(fk.kodlar, undefined, SKx.KART_VOLT_ADIM, 83333).Vpp)
       && Math.abs(u2.kodVolt(2048) - beklenen) < 1e-9
       && OS.yakalamaKur(skopOturumu({ mv: new Array(17).fill(0) }).o, e2.s0 + 1).osilo.kal === null,
       `${u2.kodVolt(2048)} vs ${beklenen}`);
    const oturum = { olaylar: [{ tur: 4, sira: 2, mv: egri.map((x) => x + 1) }, { tur: 4, sira: 10, mv: egri },
      { tur: 4, sira: 30, mv: egri.map((x) => x + 2) }, { tur: 1, sira: 5 }] };
    ok('OS6 (S3): egri = yakalamadan ONCEKI en son KO_SKOP_KAL; hic yoksa ilki',
       OS.yakalamaEgrisi(oturum, 20)[0] === egri[0] && OS.yakalamaEgrisi(oturum, 1)[0] === egri[0] + 1
       && OS.yakalamaEgrisi({ olaylar: [] }, 5) === null);
  }

  /* ── (d) OS3 SPEKTRUM ───────────────────────────────────────────── */
  {
    const hz = 10000;
    const veri = Array.from({ length: 1000 }, (_, i) => 2000 + Math.round(1000 * Math.sin(2 * Math.PI * 437.5 * i / hz)));
    const sp = OS.spektrumHesapla(veri, hz, { kodVolt: (k) => k * 0.01 - 20 });
    ok('[!] OS3: tepe frekansi Hann ile <= 0.05 kutu; genlik volt (kodVolt), DC cikarildi (dc = ortalama)',
       Math.abs(sp.tepe.f - 437.5) <= 0.05 * sp.df && Math.abs(sp.tepe.genlik - 10) < 0.4 && Math.abs(sp.dc - 0) < 0.05
       && sp.pencere === 'hann' && sp.nfft === 1024 && sp.harmonik.harmonikler.length === 5,
       `${sp.tepe.f} Hz ${sp.tepe.genlik} V dc ${sp.dc}`);
    const dik = OS.spektrumHesapla(veri, hz, { kodVolt: (k) => k, pencere: 'dikdortgen' });
    ok('OS3: pencere secimi gidiyor (dikdortgen); bilinmeyen pencere -> hann', dik.pencere === 'dikdortgen'
       && OS.spektrumHesapla(veri, hz, { pencere: 'blackman' }).pencere === 'hann' && OS.spektrumHesapla([1], hz) === null);
    const s = OS.spektrumSerisi(sp, 'v');
    const d = OS.spektrumSerisi(sp, 'dbv');
    ok('[!] OS3 (S1): grafik serisi DC kutusunu ICERMIYOR (x = f[1] …), dBV = 20 log10(V), birim etiketi',
       s.t[0] === sp.f[1] && s.t.length === sp.f.length - 1 && s.y[0] === sp.genlik[1] && s.birim === 'V'
       && d.birim === 'dBV' && Math.abs(d.y[44] - 20 * Math.log10(sp.genlik[45])) < 1e-9);
    ok('[!] OS3: spektrum yakalamanin TAMAMINDAN (osilo.veri), zoom penceresinden DEGIL; eksenle ayni ceviri (kodVolt)',
       govdeIcinde(appKaynak, 'spektrumCiz', 'o.veri') && govdeIcinde(appKaynak, 'spektrumCiz', 'this.kodVolt(k)')
       && !govdeIcinde(appKaynak, 'spektrumCiz', 'gorunurAralik'));
    ok('OS2: x ekseni Hz/kHz (grafik.js xEksen), adima gore ondalik',
       OS.hzYazi(12500, 500) === '12.5 kHz' && OS.hzYazi(500, 100) === '500 Hz' && OS.hzYazi(2000, 1000) === '2 kHz'
       && OS.hzYazi(12.5, 0.5) === '12.5 Hz' && OS.hzYazi(1500, 100) === '1.5 kHz' && OS.hzYazi(NaN, 1) === '' && /xEksen: \{ tur: 'sayi', yazi: hzYazi \}/.test(osKaynak));
    const u = ornek();
    u.spektrumBilgi = { var: true, n: 1000, nfft: 1024, df: 9.765625, dc: 12, tepe: { f: 50, genlik: 9 }, thd: 0.0123,
      harmonikler: [{ n: 1, f: 50, genlik: 9 }, { n: 2, f: 97.6, genlik: 0.013, taban: true }, null, { n: 4, f: 200, genlik: 0.01 }, null] };
    const st = u.spektrumSatirlari;
    ok('[!] OS3: harmonik tablosu — yerel tepe yoksa (sizinti tabani) genlik "≤" ile UST SINIR; Nyquist otesi "—"; THD %',
       st.length === 5 && st[1].v === '≤ 0.0130 V' && st[1].db.startsWith('≤ ') && st[0].v === '9.0000 V'
       && st[2].f === '—' && u.spektrumOzet.thd === '1.23 %' && u.spektrumOzet.tepe === '50.000 Hz', JSON.stringify(st));
    ok('OS3: pencere / birim tercihi saklaniyor, bilinmeyen kayitli deger varsayilana dusuyor',
       /spektrumPencere\(v\) \{ this\.ayarYaz\('spektrumPencere', v\)/.test(kod) && /spektrumBirim\(v\) \{ this\.ayarYaz\('spektrumBirim', v\)/.test(kod)
       && govdeIcinde(appKaynak, 'tercihleriYukle', "['hann', 'dikdortgen'].includes(sp)"));
  }

  /* ── (e) OS6 KAYITLI YAKALAMA ───────────────────────────────────── */
  {
    const rc = OS.skopRotaCoz;
    const ry = KGx.skopRotaYaz;
    ok('[!] OS6: rota yaz/coz birbirinin TERSI (kayit_gorunum yaziyor, osiloskop cozuyor); bicimsiz -> null',
       JSON.stringify(rc('#/skop/kayit/12/5')) === '{"oturum":12,"sira":5,"kimlik":null}'
       && JSON.stringify(rc('#/skop/kayit/12/5@7')) === '{"oturum":12,"sira":5,"kimlik":7}'
       && rc('#/skop') === null && rc('#/skop/kayit/12') === null && rc('#/skop/kayit/x/5') === null && rc('#/skop/kayit/0/5') === null
       && ['#/skop/kayit/12/5', '#/skop/kayit/12/5@7', '#/skop/kayit/3/1@0'].every((h) => ry(rc(h)) === h));
    const kg = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'), 'utf8');
    ok('[!] OS6: 3C yakalama tablosunda tam yakalamaya "Osiloskopta ac" baglantisi (kimlikli adres)',
       /<a v-if="y\.tam" :href="skopAdresi\(y\.sira\)" class="kg-skop-ac" data-skop-ac>\{\{ m\.osiloskoptaAc \}\}<\/a>/.test(kg)
       && govdeIcinde(kg, 'skopAdresi', 'kimlik: this.veri.kimlik'));
    const { o, kayitlar, s0, ot } = skopOturumu();
    const akis = (kimlik, olusma) => ({ kimlik, olusma });
    const veriler = { 3: { kimlik: 3, oturumlar: new Map([[ot, o]]), kayitlar }, 7: { kimlik: 7, oturumlar: new Map([[ot, o]]), kayitlar },
      9: { kimlik: 9, oturumlar: new Map(), kayitlar: [] } };
    const istenen = [];
    const denetci = { akislar: async () => [akis(3, 10), akis(7, 20), akis(9, 30)],
      akisVerisi: async (k) => { istenen.push(k); return veriler[k]; } };
    SONRA.push(async () => {
      const a = await OS.kayitliYakalamaAc({ oturum: ot, sira: s0, kimlik: null }, { denetciKur: async () => denetci });
      const ia = istenen.splice(0);
      const b = await OS.kayitliYakalamaAc({ oturum: ot, sira: s0, kimlik: 3 }, { denetciKur: async () => denetci });
      const ib = istenen.splice(0);
      const c = await OS.kayitliYakalamaAc({ oturum: ot, sira: s0, kimlik: 5 }, { denetciKur: async () => denetci });
      ok('[!] OS6 (S4): @kimlik yoksa oturumu TASIYAN en yeni akis (9 tasimiyor -> 7); @3 -> 3; olmayan akis -> "yok"',
         !a.hata && a.bilgi.kimlik === 7 && ia.join() === '9,7' && !b.hata && b.bilgi.kimlik === 3 && ib.join() === '3'
         && c.hata === 'os.hata_yakalama_yok' && a.bilgi.oturum === ot && a.bilgi.no === 1
         && a.bilgi.unixMs === 1790003000 * 1000 + 2000, JSON.stringify({ a: a.bilgi, ia, ib, c }));
      const u = ornek();
      u._skopMod = { kayitliYakalamaAc: async () => a };
      u.surekli = true;
      u.surekliZaman = null;
      u.skopAcikKayit = { gun: 'x', ms: 1 };
      await u.skopKayitliAc({ oturum: ot, sira: s0, kimlik: null });
      const acik = { osilo: u.osilo === a.osilo, kayitli: !!u.skopKayitli, surekli: u.surekli, ark: u.skopAcikKayit,
        yazi: u.skopKayitliYazi };
      u.gonder = async () => {};
      u.osiloYakala();
      ok('[!] OS6: kayitli yakalama ACILIYOR (surekli durur, kopru arsivi isareti kalkar, serit "canli degil"); canli yakalama onu KAPATIYOR',
         acik.osilo && acik.kayitli && acik.surekli === false && acik.ark === null
         && acik.yazi === `Kayıt #${ot} · yakalama 1 · ${u.tarihYazi(1790003002)} — canlı değil` && u.skopKayitli === null,
         JSON.stringify(acik));
      const w = ornek();
      w._skopMod = { kayitliYakalamaAc: async () => ({ hata: 'os.hata_yakalama_yok', d: { oturum: 4, sira: 9 } }) };
      await w.skopKayitliAc({ oturum: 4, sira: 9, kimlik: null });
      ok('OS6: bulunamayan yakalama SEBEBIYLE (Kayitlar`dan esitle)', w.skopKayitliHata
         === 'Bu tarayıcıda oturum #4 içinde 9 sıralı yakalama yok — Kayıtlar\'dan eşitleyin.' && w.osilo === null);
    });
    ok('[!] OS6: ARSIV seridi (kayitli), "Kayda don" baglantisi ve "Canliya don" dugmesi sablonda',
       /<div v-if="skopKayitli" class="arsiv-serit" data-skop-kayitli>[\s\S]{0,300}\{\{ skopKayitliYazi \}\}[\s\S]{0,200}:href="skopKayitAdresi"[\s\S]{0,200}@click="skopCanliyaDon"/.test(sm));
  }

  /* ── (f) OS2 IZGARA ─────────────────────────────────────────────── */
  {
    const bolme = /static const uint8_t\s+SKOP_BOLME\s*=\s*(\d+);/.exec(ino);
    const u = ornek();
    const cizgi = [];
    let renk = '';
    let bas = null;
    const ctx = { set strokeStyle(v) { renk = v; }, get strokeStyle() { return renk; }, lineWidth: 1,
      beginPath() {}, stroke() {}, moveTo(x, y) { bas = [x, y]; }, lineTo(x, y) { cizgi.push({ renk, d: bas[0] === x, x, y }); } };
    u.renk = (ad) => ad;
    u.izgara(ctx, 500, 300, 50, 10, 400, 280);
    const dikey = cizgi.filter((c) => c.d);
    const yatay = cizgi.filter((c) => !c.d);
    ok('[!] OS2: dalga izgarasi 10 x 8 BOLME (11 dikey + 9 yatay cizgi; yatay bolme = firmware SKOP_BOLME); orta eksenler --kenar-koyu',
       !!bolme && Number(bolme[1]) === al('SKOP_BOLME_X') && dikey.length === 11 && yatay.length === 9
       && dikey.filter((c) => c.renk === '--kenar-koyu').length === 1 && yatay.filter((c) => c.renk === '--kenar-koyu').length === 1
       && cizgi.every((c) => c.renk === '--kenar-c' || c.renk === '--kenar-koyu'),
       `${dikey.length} dikey, ${yatay.length} yatay`);
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   28. PIL TESTI (3F — alt proje 3, PL1-PL7; uygulama kararlari PU1-PU16)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3F kararlari". Burada:
   (a) KABLOLAMA + DUZEN: PL1 DURDUR (Pil sekmesinde de tek tik, ASLA :disabled), tembel
       modul (ekran/pil.js; esitleme zinciri yalniz kayit kaynaginda), #/pil acilis butcesi,
       3F stilleri belirtecle, PL7 metinler sozlukten + erisilebilirlik.
   (b) PL4 YOKLAMA: kosul tablosu; zamanlayici yalniz kosul dogruyken; kartin satirlari
       PASIF (basladi / bitti) — gizli sekmede istek yok, bitince BIR son hal; USB / koprude
       `p` (B satiri); halka sifirlaninca (yeni test) yerel kopya bastan; `kalan=` dolgusu.
   (c) FIRMWARE ile ayni metinler ve alanlar: pil satirlari, `/pil` anahtarlari, B satiri
       sirasi, P siniri, DCIR sabitleri (pil_test.h).
   (d) KOMUT URETICILERI + PL5/PU4 akisi: P<v> onayi beklenir, onaysiz p1 GITMEZ; kart baska
       kesmeyle baslatirsa p0; ad `Ga<oturum>` G'den sonra.
   (e) PU6 oturum numarasi G'den; PL6 "Kayitlar'da ac" adresi.
   (f) PU8 okuma kartlari: mAh / Wh KARTIN sayaci (kaynak yazili); kayit gelince kayittan.
   (g) PU10 DCIR tablosu; PU9 mAh ekseni (tarayici, yamuk); ekran/pil.js saf fonksiyonlari;
       kayit kaynagi GERCEK ortak/kayit.js ile paketlenip cozulen PIL oturumundan.
   (h) Demo karti (sahte-kart.js) firmware'in metinleriyle.
   Gercek tarayici (SSE, istek sayisi, IndexedDB, uc gorunum, 390 px): tarayici_pil.py (T3F).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 28. Pil testi (3F) ---');
{
  const html = yorumsuz(htmlKaynak);
  const kod = yorumsuz(appKaynak);
  const css = cssOku();
  const al = (ad) => vm.runInContext(ad, sandbox);
  const PL = require(path.join(ARAYUZ, 'ekran', 'pil.js'));
  const Kx = require(path.join(KOK, 'ortak', 'src', 'kayit.js'));
  const Dx = require(path.join(KOK, 'ortak', 'src', 'disari.js'));
  const SZx = sozlukTum();
  const pilKaynak = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'pil.js'), 'utf8');
  const pilH = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'pil_test.h'), 'utf8');
  const pm = (html.match(/<main class="gorunum" v-show="gorunum === 'pil'">([\s\S]*?)<\/main>/) || [])[1] || '';
  const pilBlok = css.slice(css.indexOf('3F — PİL TESTİ'), css.indexOf('/* Rapor YAZDIRILIRKEN'));
  /** Tanim govdesinin METNI (govdeIcinde ile ayni bulucu). */
  const govdeMetni = (kaynak, ad) => {
    let i = kaynak.indexOf('\n    async ' + ad + '(');
    if (i < 0) i = kaynak.indexOf('\n    ' + ad + '(');
    if (i < 0) return '';
    const j = kaynak.indexOf('{', i);
    let d = 0;
    for (let k = j; k < kaynak.length; k++) {
      if (kaynak[k] === '{') d++;
      else if (kaynak[k] === '}') { d--; if (d === 0) return kaynak.slice(j, k + 1); }
    }
    return '';
  };

  /* ── (a) KABLOLAMA + DUZEN ──────────────────────────────────────── */
  {
    const dur = (pm.match(/<button[^>]*data-pil="durdur"[^>]*>/) || [])[0] || '';
    /* 5P (K9): telefonun "bilinmiyor" seridi acil seridin v-else-if'i (yalniz ORTAM varken) — ucuncu DURDUR
       YALNIZ orada ve onaysiz; PC'nin iki DURDUR'u (acil serit + Pil sekmesi) AYNEN sayilir. */
    const telSerit = (html.match(/<div v-if="pilDurum === 'CALISIYOR'" class="acil">[\s\S]*?<\/button>\s*<\/div>\s*(<div v-else-if="acilTelefon" class="acil" data-acil-telefon>[\s\S]*?<\/button>\s*<\/div>)/) || [])[1] || '';
    ok('[!] EMNIYET-P0 (PL1): Pil sekmesinin DURDUR`u pilDurdurKomut`u TEK tikla cagirir; :disabled YOK, v-if/v-show YOK (her zaman gorunur)',
       /@click="pilDurdurKomut"/.test(dur) && !/:disabled|disabled|v-if|v-show|onayIste/.test(dur)
       && (html.replace(telSerit, '').match(/@click="pilDurdurKomut"/g) || []).length === 2
       && (telSerit.match(/@click="pilDurdurKomut"/g) || []).length === 1 && !/disabled|onayIste/.test(telSerit), dur);
    ok('[!] EMNIYET-P0 (PU1): `p0` yolu modulu BEKLEMEZ — pilDurdurKomut ve acil serit app.js`te; ekran/pil.js `p0` gondermez',
       /pilDurdurKomut\(\) \{ this\.gonder\('p0'\); \}/.test(appKaynak) && !/p0/.test(yorumsuz(pilKaynak).replace(/'pl\.[a-z_]+'/g, ''))
       && govdeIcinde(appKaynak, 'pilModYukle', "import('./ekran/pil.js')"));
    const statik = iceAktarmaGrafigi().map((g) => g.goruntu);
    const pilAgac = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'pil.js')).map((g) => g.goruntu);
    ok('[!] Pil modulu TEMBEL: acilis grafiginde YOK, pilModYukle import() ediyor, inmezse sebep ekranda; varsayilan acilista kurulmuyor',
       !statik.includes('ekran/pil.js') && govdeIcinde(appKaynak, 'pilModYukle', "this.pilModDurum = 'yuklenemedi'")
       && /pilModDurum === 'yuklenemedi'" class="hata tuval-ust">\{\{ pl\.yuklenemedi \}\}/.test(pm) && secenekler.data().pilAcik === false,
       statik.join(' '));
    ok('[!] PU11: esitleme zinciri (esitleme / depo_idb / ortak kayit, esitle, imza, disari) pil modulunun STATIK agacinda YOK — yalniz kayit kaynaginda iner',
       pilAgac.every((g) => ['ortak/grafik.js', 'ortak/sozluk.js', 'ortak/ozet.js', 'ortak/istatistik.js'].includes(g))
       && /import\('\.\/esitleme\.js'\)/.test(pilKaynak) && /import\('\/ortak\/disari\.js'\)/.test(pilKaynak), pilAgac.join(' '));
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    if (fs.existsSync(kunyeYolu)) {
      const b = JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {};
      /* zincir = Pil sekmesinin acilisa EKLEDIGI dosyalar (sozluk.js zaten acilista iner). PT7: + ortak/sozluk_pil.js
         (PilPt'nin metin + hesabi; pil.js PilPt kurulunca DINAMIK indirir — Pil sekmesinde hep iner, sayilir) */
      const zincir = ['ekran/pil.js', ...pilAgac, 'ortak/sozluk_pil.js'].filter((a) => !statik.includes(a));
      const top = zincir.reduce((n, a) => n + (Number.isFinite(b[a]) ? b[a] : NaN), 0);
      ok('Pil zinciri (modul + acilista inmeyen statik agaci + PT7 sozlugu) gzip <= 40 KB, <= 5 dosya ve kunyede (goruntude) var; sozluk_pil.js <= 5 KB',
         top > 0 && top <= 40 * 1024 && zincir.length <= 5 && b['ortak/sozluk_pil.js'] > 0 && b['ortak/sozluk_pil.js'] <= 5120,
         `${top} B · ${zincir.join(' ')} · sozluk_pil ${b['ortak/sozluk_pil.js']} B`);
      const acilisK = new Set(['index.html']);
      for (const m of html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)) {
        if (!/^(https?:|data:|#|mailto:)/.test(m[1])) acilisK.add(m[1]);
      }
      for (const g of iceAktarmaGrafigi()) acilisK.add(g.goruntu);
      for (const a of zincir) acilisK.add(a);
      const pilAcilis = [...acilisK].reduce((n, a) => n + (Number.isFinite(b[a]) ? b[a] : NaN), 0);
      ok('[!] #/pil ile acilis (statik + pil zinciri) gzip <= 250 KB ve <= 13 dosya',
         pilAcilis > 0 && pilAcilis <= 250 * 1024 && acilisK.size <= 13, `${pilAcilis} B · ${acilisK.size} dosya`);
    }
    {
      const hashten = al('hashtenGorunum');
      sandbox.location = { hash: '#/pil' };
      const g = hashten();
      delete sandbox.location;
      const w = secenekler.watch.gorunum;
      let tazele = 0;
      const sahte = { $nextTick() {}, pilAcik: false, bagli: true, pilBayat: true, pilCalisiyor: false,
        pilGorundu: secenekler.methods.pilGorundu, pilTazele() { tazele++; }, pilKayitIste() {} };
      sandbox.history = { replaceState() {} };
      w.call(sahte, 'pil');
      delete sandbox.history;
      ok('[!] #/pil Pil ekranini aciyor; gorunum izleyicisi modulu kuruyor (pilAcik) ve durum BAYATSA bir kez tazeliyor',
         g === 'pil' && sahte.pilAcik === true && tazele === 1);
    }
    ok('[!] 3F stilleri YALNIZ belirtecle: sabit renk (#hex / rgb) yok; DURDUR uyari renginde',
       pilBlok.length > 500 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(pilBlok.replace(/\/\*[\s\S]*?\*\//g, ''))
       && /\.pil-dur\s*\{[^}]*var\(--uyari\)/.test(pilBlok));
    ok('[!] 390 px (T3F olctu): .iki-sutun telefon kurali TABAN kuralindan SONRA (ayni ozgulukte sonraki kazanir)',
       css.lastIndexOf('.iki-sutun { grid-template-columns: minmax(0, 1fr); }') > css.indexOf('.iki-sutun {\n  display: grid;'));
    const pl = al('PL_METIN');
    ok('[!] PL7: Pil ekraninin metinleri sozlukten (PL_METIN, tr + en dolu); sablon `pl.` kullaniyor',
       Object.values(pl).every((k) => k in SZx.SOZLUK && SZx.SOZLUK[k].tr && SZx.SOZLUK[k].en)
       && Object.keys(pl).length >= 50 && (pm.match(/\{\{ pl\.\w+ \}\}/g) || []).length >= 30, `${Object.keys(pl).length} anahtar`);
    ok('[!] PL7 (WIG): ret role=alert (pilUyari), durum degisimi aria-live, tablo th scope=col + caption, tuval role=img + etiket, form alanlari etiketli',
       /<p v-if="pilUyari" class="hata" data-pil="uyari" role="alert" :data-tur="pilUyari\.tur">/.test(pm)
       && /<p class="gorunmez" aria-live="polite">\{\{ pilDuyuru \}\}<\/p>/.test(pm)
       && (pm.match(/<th scope="col">/g) || []).length === 5 && /<caption class="gorunmez">/.test(pm)
       && /ref="pilTuval" class="pil-grafik" role="img" :aria-label="pl\.grafikEtiket"/.test(pm)
       && ['pil-kesme', 'pil-ad', 'pil-ad-surerken'].every((id) => pm.includes(`<label for="${id}">`) && pm.includes(`id="${id}"`)));
    ok('PL2: alti okuma karti (v-for pilOkumalar, her birinin altinda KAYNAK) + sonuc karti + egri + DCIR + parametreler sirasiyla',
       /v-for="o in pilOkumalar"[\s\S]{0,400}data-pil="kaynak">\{\{ o\.kaynak \}\}/.test(pm)
       && pm.indexOf('pil-okumalar') < pm.indexOf('data-pil="sonuc"') && pm.indexOf('data-pil="sonuc"') < pm.indexOf('pilTuval')
       && pm.indexOf('pilTuval') < pm.indexOf('data-pil="dcir"') && pm.indexOf('data-pil="dcir"') < pm.indexOf('data-pil="parametre"'));
  }

  /* ── (b) PL4 YOKLAMA ────────────────────────────────────────────── */
  {
    const K = al('pilYoklamaKosulu');
    const tablo = [[true, 'pil', true, 'CALISIYOR', true], [false, 'pil', true, 'CALISIYOR', false],
      [true, 'canli', true, 'CALISIYOR', false], [true, 'pil', false, 'CALISIYOR', false], [true, 'pil', true, 'BITTI', false],
      [true, 'pil', true, 'BEKLEMEDE', false]];
    ok('[!] PL4: surekli yoklama YALNIZ bagli ∧ Pil sekmesi ∧ belge gorunur ∧ test suruyor',
       tablo.every(([bagli, gorunum, gorunur, durum, b]) => K({ bagli, gorunum, gorunur, durum }) === b) && al('PIL_YOKLAMA_MS') === 2000);
    const u = ornek();
    u.bagli = true; u.gorunum = 'pil'; u.pilDurum = 'CALISIYOR';
    let n = 0;
    u.pilTazele = async () => { n++; };
    SONRA.push(async () => {
      const eskiZ = sandbox.setTimeout;
      const q = [];
      sandbox.setTimeout = (fn, ms) => { q.push({ fn, ms }); return q.length; };
      u.pilYoklamaKur(true);
      await new Promise((r) => setImmediate(r));
      const ilk = n;
      const kuruldu = q.length;
      const ms = q.length ? q[q.length - 1].ms : null;
      u.gorunum = 'canli';
      const once = q.length;
      if (q.length) await q[q.length - 1].fn();
      await new Promise((r) => setImmediate(r));
      const q2 = q.slice(once);
      /* kosul ISTEK SURERKEN duserse (yanit beklenirken baska sekmeye gecildi) de yeni zamanlayici YOK */
      u.gorunum = 'pil';
      u.pilTazele = async () => { n++; u.gorunum = 'canli'; };
      const once2 = q.length;
      u.pilYoklamaKur(true);
      await new Promise((r) => setImmediate(r));
      const q3 = q.slice(once2);
      sandbox.setTimeout = eskiZ;
      ok('[!] PL4: zamanlayici acilinca HEMEN bir yokla, sonra PIL_YOKLAMA_MS; kosul dusunce (baska sekme; istek surerken de) yeni istek ve yeni zamanlayici YOK',
         ilk === 1 && kuruldu === 1 && ms === 2000 && q2.length === 0 && n === 2 && q3.length === 0,
         `n=${n} kuruldu=${kuruldu} ms=${ms} q2=${q2.length} q3=${q3.length}`);
    });
    /* kartin satirlari: basladi -> durum, acil serit, oturum beklemesi; gizli sekmede istek YOK */
    const v = ornek();
    v.bagli = true; v.gorunum = 'canli';
    let tz = 0;
    v.pilTazele = () => { tz++; };
    v.kayit.g = { durum: 2, oturum: 5 };
    v.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.200 V');
    const b1 = { d: v.pilDurum, k: v.pilKesme, o: v.pilOcv, bek: v.pilOturumBekle && v.pilOturumBekle.onceki, tz, kb: v.kabukDuyuru };
    v.satirIsle('* pil testi BITTI — 123.45 mAh, 0.4567 Wh');
    const b2 = { d: v.pilDurum, mah: v.pilMah, bayat: v.pilBayat, tz };
    v.pilGorundu();
    ok('[!] PL4: kartin BASLADI satiri durumu, kesmeyi, OCV`yi verir (yoklama yok); BITTI gizli sekmede istek YAPMAZ (bayat), Pil sekmesi acilinca BIR kez',
       b1.d === 'CALISIYOR' && b1.k === 3.2 && b1.o === 4.1 && b1.bek === 5 && b1.tz === 0 && /çalışıyor/.test(b1.kb)
       && b2.d === 'BITTI' && b2.mah === 123.45 && b2.bayat === true && b2.tz === 0 && tz === 1, JSON.stringify({ b1, b2, tz }));
    const w = ornek();
    w.bagli = true; w.gorunum = 'pil';
    let tw = 0;
    w.pilTazele = () => { tw++; };
    w.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.000 V');
    w.satirIsle('* pil testi DURDURULDU, yuk kesildi');
    ok('PL4: Pil sekmesi gorunurken bitis BIR son hal ister; DURDURULDU / sure asimi durumu kartin satirindan',
       tw === 1 && w.pilDurum === 'DURDURULDU' && (() => { const x = ornek(); x.satirIsle('* pil testi BASLADI — OCV 4.1 V, kesme 3.0 V');
         x.satirIsle('! pil testi: azami sure asildi, yuk kesildi'); return x.pilDurum === 'HATA' && x.pilHata === 'azami sure asildi'; })());
    /* USB / kopru: /pil yok -> `p` (surucuyse) */
    const s = ornek();
    const giden = [];
    s.gonder = async (k) => { giden.push(k); };
    s.bagli = true; s.tasiyiciAdi = 'seri'; s.bagliTasiyici = 'seri';
    const izleyici = ornek();
    const g2 = [];
    izleyici.gonder = async (k) => { g2.push(k); };
    izleyici.bagli = true; izleyici.tasiyiciAdi = 'akis'; izleyici.bagliTasiyici = 'akis'; izleyici.kopruda = true; izleyici.surucuyum = false;
    const fetchler = [];
    SONRA.push(async () => {
      const eskiF0 = sandbox.fetch;
      sandbox.fetch = async (url) => { fetchler.push(url); return { ok: true, status: 200, text: async () => 'yok' }; };
      await s.pilYokla();
      await izleyici.pilYokla();
      sandbox.fetch = eskiF0;
      s.satirIsle('B CALISIYOR 12.345 0.04567 4.1000 3.9000 3.200 77 0.04500 0.06000 1 77 -');
      ok('[!] PU13: USB`de / koprude `/pil` YOK — durum `p` komutunun B satirindan (surucuyse; izleyici komut gondermez)',
         giden.join() === 'p' && g2.length === 0 && !fetchler.some((x) => String(x).includes('/pil')) && s.pilKaynak === 'satir' && izleyici.pilKaynak === 'satir'
         && s.pilDurum === 'CALISIYOR' && s.pilMah === 12.345 && s.pilSonMs === 77000 && s.pilDcirListe.length === 1,
         JSON.stringify({ giden, g2, fetchler }));
    });
    /* /pil: yeni test (halka sifirlandi) + kalan dolgusu */
    const y = ornek();
    y.bagli = true; y.tasiyiciAdi = 'akis'; y.bagliTasiyici = 'akis';
    y.pilNokta = [Object.freeze({ sira: 0, ms: 1000, v: 4, i: 1 }), Object.freeze({ sira: 1, ms: 2000, v: 4, i: 1 })];
    y.pilYerelSira = 500;
    const yanit = (sira, ilk, kalan, n) => ['durum=CALISIYOR', 'hata=-', 'mah=1.0000', 'wh=0.004000', 'ocv=4.1000', 'vson=4.0000',
      'kesme=3.000', 'dcir_ani=0.00000', 'dcir_otr=0.00000', 'dcir_n=0', `sira=${sira}`, `ilk_sira=${ilk}`, `kalan=${kalan}`,
      'coulomb=3.600', '--', ...Array.from({ length: n }, (_, k) => `${1000 * (ilk + k + 1)},4.0000,1.000000`)].join(String.fromCharCode(10)) + String.fromCharCode(10);
    const istenen = [];
    SONRA.push(async () => {
      const eskiF = sandbox.fetch;
      sandbox.fetch = async (url) => {
        istenen.push(url);
        const sira = Number(url.split('sira=')[1]);
        if (sira === 500) return { ok: true, status: 200, text: async () => yanit(200, 200, 0, 0) };
        return { ok: true, status: 200, text: async () => yanit(200, sira, 200 - sira - Math.min(150, 200 - sira), Math.min(150, 200 - sira)) };
      };
      await y.pilYokla();
      sandbox.fetch = eskiF;
      ok('[!] PU12: kartin `sira`si bizdekinden kucuk (yeni test) -> yerel kopya BASTAN, 0`dan istenir; `kalan=` varken AYNI yoklamada devam (150 + 50)',
         istenen.join(' ') === '/pil?sira=500 /pil?sira=0 /pil?sira=150' && y.pilNokta.length === 200 && y.pilYerelSira === 200
         && y.pilSonMs === 200000 && Object.isFrozen(y.pilNokta[0]), istenen.join(' '));
    });
  }

  {
    const u = ornek();
    let yuk = 0;
    u._pilMod = {};
    u.pilKayitYukle = () => { yuk++; };
    u.gorunum = 'pil';
    u.pilOturum = { no: 7, gorulmedi: false };
    u.pilBayat = true;
    u.pilKayitIste();
    const bayatken = yuk;
    u.pilBayat = false;
    u.pilKayitIste();
    u.pilKayitIste();
    u.pilKayitOzet = { oturum: 7, dcir: [] };
    u._pilKayit = { ozet: u.pilKayitOzet };
    u.pilDurumAyarla('CALISIYOR');
    ok('[!] PU11: kayit kaynagi durum BILINMEDEN (yenileme sonrasi ilk /pil gelmeden) ACILMAZ, sonra bir kez; test yeniden surerse kayit kaynagi BIRAKILIR (canli kopya)',
       bayatken === 0 && yuk === 1 && u.pilKayitOzet === null && u._pilKayit === null, `bayatken=${bayatken} yuk=${yuk}`);
  }

  /* ── (c) FIRMWARE ile ayni metinler ve alanlar ──────────────────── */
  {
    const O = al('pilSatirOlayi');
    const metinler = ['* pil testi BASLADI — OCV ', ' V, kesme ', '* pil testi BITTI — ', ' mAh, ', '* pil testi DURDURULDU, yuk kesildi',
      '* pil testi zaten calismiyor; yuk kapali', '! pil testi: azami sure asildi, yuk kesildi', '! pil testi REDDEDILDI: ',
      '! pil testi KAYDEDILMIYOR — ', '* pil kesme gerilimi ', '! P: 0.5 ile ', '! pil: skop yakalamasi suruyor',
      '! pil testi zaten suruyor — yeniden baslatmak icin once p0'];
    const yok = metinler.filter((m) => !ino.includes(m));
    ok('[!] Panelin tanidigi pil satirlari FIRMWARE`de birebir (BASLADI / BITTI / DURDURULDU / sure / REDDEDILDI / KAYDEDILMIYOR / kesme / ret)',
       yok.length === 0, yok.join(' | ') || `${metinler.length} metin`);
    const ornekler = {
      basladi: O('* pil testi BASLADI — OCV 4.1523 V, kesme 3.000 V'), bitti: O('* pil testi BITTI — 2034.56 mAh, 7.4321 Wh'),
      dur: O('* pil testi DURDURULDU, yuk kesildi'), red: O('! pil testi REDDEDILDI: TERS POLARITE'),
      kay: O('! pil testi KAYDEDILMIYOR — kayit bellegi dolu (esitle + onayla)'), kes: O('* pil kesme gerilimi 10.500 V'),
      kesP: O('* pil kesme gerilimi 3.000 V · kayit 1.00 Hz · azami sure 24 saat · DCIR kapali'), ret: O('! pil: osiloskop gunlugu suruyor — once Gtd'),
      retP: O("! P: 0.5 ile 38.5 V arasi olmali (ust sinir MOSFET Vdss'inden)"), yabanci: O('* pil'), g: O('G 2 5 1 2 3 4 5 6 7 8 9 10 11'),
    };
    ok('[!] pilSatirOlayi: firmware bicimindeki satirlar dogru turde ve sayida; yabanci satir null',
       ornekler.basladi.tur === 'basladi' && ornekler.basladi.ocv === 4.1523 && ornekler.basladi.kesme === 3
       && ornekler.bitti.mah === 2034.56 && ornekler.bitti.wh === 7.4321 && ornekler.dur.tur === 'durduruldu'
       && ornekler.red.hata === 'TERS POLARITE' && ornekler.kay.neden === 'kayit bellegi dolu (esitle + onayla)'
       && ornekler.kes.v === 10.5 && ornekler.kesP.v === 3 && ornekler.ret.tur === 'ret' && ornekler.retP.tur === 'ret'
       && ornekler.yabanci === null && ornekler.g === null, JSON.stringify(ornekler));
    /* B satiri: `p` govdesindeki Serial.print SIRASI */
    const pGovde = (ino.match(/\/\* durum raporu \*\/[\s\S]*?pil_hata_metni\(pil\.hata\)\);/) || [''])[0];
    const sira = [...pGovde.matchAll(/Serial\.print(?:ln)?\(([^;]*?)\);/g)].map((m) => m[1].trim()).filter((a) => a !== "' '");
    const beklenen = ['F("B ")', 'pil_durum_metni(pil.durum)', 'yuk_mAh3(pil.yuk_pC), 3', 'enerji_wh3(pil.enerji_pJ), 5',
      'pil.v_bas, 4', 'pil.v_son, 4', 'ayar.pil_kesme_v, 3', null, 'pil.dcir_ani, 5', 'pil.dcir_oturmus, 5', 'pil.dcir_sayisi',
      'pil_halka.sira', 'pil_hata_metni(pil.hata)'];
    const B = al('pilBSatiriCoz')('B CALISIYOR 1.234 0.00456 4.1000 3.9000 3.000 3600 0.04500 0.06000 12 3600 -');
    ok('[!] PU13: B satiri alan SIRASI firmware`in `p` durum raporuyla ayni (13 alan; sure saniye); ayristirici her alani yerine koyuyor',
       sira.length === 13 && beklenen.every((b, k) => b === null || sira[k] === b) && /\(millis\(\) - pil\.baslama_ms\)/.test(sira[7])
       && B && B.durum === 'CALISIYOR' && B.mah === 1.234 && B.wh === 0.00456 && B.ocv === 4.1 && B.vson === 3.9 && B.kesme === 3
       && B.sureS === 3600 && B.dcirAni === 0.045 && B.dcirOtr === 0.06 && B.dcirN === 12 && B.sira === 3600 && B.hata === '-'
       && al('pilBSatiriCoz')('B 1 2 3') === null, sira.join(' | '));
    const sayfa = (ino.match(/void pil_sayfa\(\) \{[\s\S]*?\n\}/) || [''])[0];
    const fwAlan = [...sayfa.matchAll(/F\("(?:\\n)?([a-z_]+)="\)/g)].map((m) => m[1]);
    const okunan = [...new Set([...govdeMetni(appKaynak, 'pilYokla').matchAll(/\ba\.([a-z_]+)\b/g)].map((m) => m[1]))];
    ok('[!] /pil: pilYokla`nin okudugu HER anahtar firmware`in pil_sayfa`sinda var (durum, mah, dcir_n, sira, ilk_sira, kalan …; PT6: evre, kayit_hz, dcir; HT2: hat_mohm, v_ham SONDA)',
       fwAlan.length === 19 && okunan.length >= 17 && okunan.every((a) => fwAlan.includes(a))
       && fwAlan.slice(14, 17).join() === 'evre,kayit_hz,dcir' && ['evre', 'kayit_hz', 'dcir', 'hat_mohm'].every((a) => okunan.includes(a))
       && fwAlan.slice(17).join() === 'hat_mohm,v_ham',
       `fw: ${fwAlan.join(',')} · okunan: ${okunan.join(',')}`);
    const dA = Number((/#define PIL_DCIR_ARALIK_MS (\d+)u/.exec(pilH) || [])[1]);
    const dD = Number((/#define PIL_DCIR_MS\s+(\d+)u/.exec(pilH) || [])[1]);
    const an = al('pilDcirAniMs');
    const ocvMs = Number((/#define PIL_OCV_MS\s+(\d+)u/.exec(pilH) || [])[1]);
    ok('[!] PU5/PU10 + PT2: DCIR araligi, darbesi ve OCV evresi pil_test.h derleme sabitleriyle ayni; n. anin zamani [OCV +] n x (aralik + darbe) (kartin kurali: darbe son darbenin BITISINDEN sonra, zamanlayici YUK ACILINCA baslar)',
       dA === al('PIL_DCIR_ARALIK_MS') && dD === al('PIL_DCIR_DARBE_MS') && ocvMs === al('PIL_OCV_MS') && ocvMs === 5000
       && an(1) === 300200 && an(3) === 900600 && Number.isNaN(an(0)) && an(1, ocvMs) === 305200 && an(3, ocvMs) === 905600
       && /p->son_dcir_ms = ms;\s*\/\* DCIR zamanlayicisi yuk acilinca baslar/.test(pilH)
       && /ms - p->son_dcir_ms >= \(uint32_t\)\(PIL_DCIR_ARALIK_MS\)/.test(pilH), `${dA} ${dD} ${ocvMs}`);
    ok('[!] PU5: DCIR araligi icin firmware`de KOMUT YOK (derleme sabiti) — panel salt okur gosterir, gonderen kod yok',
       !/case 'D'[\s\S]{0,200}PIL_DCIR/.test(ino) && !/pil_dcir_aralik\s*=/.test(ino) && /\{\{ pilDcirAralikYazi \}\}/.test(pm)
       && /\{\{ pl\.dcirSabit \}\}/.test(pm));
  }

  /* ── (d) KOMUT URETICILERI + PL5 / PU4 akisi ───────────────────── */
  {
    const K = al('pilKesmeKomutu');
    const k = (x) => { const r = K(x); return r.komut || r.hata; };
    ok('[!] PL5: kesme uretici — `P<v>`, virgul ondalik; 0.5 … 38.5 disi, bos, sayi olmayan, eksi, ussel REDDEDILIR',
       k('3') === 'P3' && k('3,2') === 'P3.2' && k(' 10.5 ') === 'P10.5' && k('0.5') === 'P0.5' && k('38.5') === 'P38.5'
       && ['0.49', '38.6', '', 'abc', '-3', '1e1', '3.2.1', '40'].every((x) => k(x) === 'pl.hata_kesme'));
    const kartKabul = (c) => { const v = parseFloat(c.slice(1)); return c[0] === 'P' && v >= 0.5 && v <= 38.5; };
    ok('PL5: uretilen her P komutu kartin kabul kuralindan geciyor', ['0.5', '1', '3.0', '3,7', '10.5', '12.0001', '38.5'].every((x) => kartKabul(K(x).komut)));
    const A = al('pilAdKomutu');
    const uzun = 'ş'.repeat(61);
    ok('[!] PU7: ad uretici — `Ga<oturum> <ad>`; oturum yok / bos / tirnak / ters bolu / denetim / 120 bayti asan (Turkce 2 bayt) REDDEDILIR',
       A(7, ' 18650 #3 ').komut === 'Ga7 18650 #3' && A(0, 'x').hata === 'pl.hata_ad_oturum' && A(7, '  ').hata === 'pl.hata_ad_bos'
       && A(7, 'a' + String.fromCharCode(34)).hata === 'pl.hata_ad_karakter' && A(7, 'a' + String.fromCharCode(92)).hata === 'pl.hata_ad_karakter'
       && A(7, 'a' + String.fromCharCode(7)).hata === 'pl.hata_ad_karakter' && A(7, uzun).hata === 'pl.hata_ad_uzun' && A(7, uzun).bayt === 122
       && A(7, 'ş'.repeat(60)).komut === 'Ga7 ' + 'ş'.repeat(60));
    /* akis: kesme kartinkiyle ayni -> yalniz p1; farkli -> P + ONAY -> p1; onay gelmezse p1 GITMEZ */
    /* PT7: Pr / Pd'ye kartin (A3-PT1) onay satirlari — metinler FIRMWARE'IN (c bolumu ino'da arar) */
    const ptOnay = (c) => (c[1] === 'r' ? (c === 'Pr0' ? '* pil kayit hizi her ornek (ayrintili kayit + 1/s nokta)' : `* pil kayit hizi ${c.slice(2)} /s`)
      : c === 'Pd1' ? "* pil DCIR olcumu ACIK (5 dk'da bir 200 ms yuk kesilir)" : '* pil DCIR olcumu KAPALI');
    const yap = (kesmeKart, giris, onaylar = true) => {
      const u = ornek();
      const giden = [];
      u.bagli = true; u.pilKesmeBilinen = true; u.pilKesme = kesmeKart; u.pilKesmeGiris = giris;
      u.gonder = async (c) => {
        giden.push(c);
        if (c[0] === 'P' && (c[1] === 'r' || c[1] === 'd')) u.satirIsle(ptOnay(c));
        else if (onaylar && c[0] === 'P') u.satirIsle(`* pil kesme gerilimi ${Number(c.slice(1)).toFixed(3)} V`);
      };
      return { u, giden };
    };
    const a1 = yap(3.0, '');
    const a2 = yap(3.0, '3.2');
    const a3 = yap(3.0, '3.2', false);
    SONRA.push(async () => {
      const r1 = await a1.u.pilBaslat();
      const r2 = await a2.u.pilBaslat();
      const eskiZ = sandbox.setTimeout;
      const VD = vm.runInContext('Date', sandbox);
      const eskiN = VD.now;
      let saat = eskiN.call(VD);
      VD.now = () => saat;
      sandbox.setTimeout = (fn) => { saat += 100; Promise.resolve().then(fn); return 1; };
      const r3 = await a3.u.pilBaslat();
      sandbox.setTimeout = eskiZ;
      VD.now = eskiN;
      ok('[!] PL5 + PU4: bos giris = kartin kesmesi (yalniz p1); farkli kesme -> `P3.2`, kartin ONAYINDAN sonra `p1`; onay gelmezse p1 GITMEZ, sebep yazili',
         r1 === true && a1.giden.join() === 'Pr1,Pd0,p1' && r2 === true && a2.giden.join() === 'Pr1,Pd0,P3.2,p1' && r3 === false
         && a3.giden.join() === 'Pr1,Pd0,P3.2'
         && /onaylamadı/.test(a3.u.pilUyari.metin) && a3.u.pilUyari.tur === 'panel',
         JSON.stringify([a1.giden, a2.giden, a3.giden, a3.u.pilUyari]));
      /* PU4: kart baska kesmeyle baslattiysa p0 */
      a2.u.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.000 V');
      ok('[!] PU4: kart testi ISTENENDEN farkli kesmeyle baslattiysa panel HEMEN `p0` yollar ve soyler (yanlis kesmeyle desarj pili bitirir)',
         a2.giden.join() === 'Pr1,Pd0,P3.2,p1,p0' && a2.u.pilUyari.tur === 'panel' && /3\.000 V/.test(a2.u.pilUyari.metin) && /3\.200 V/.test(a2.u.pilUyari.metin),
         a2.giden.join());
      a1.u.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.000 V');
      ok('PU4: istenenle ayni kesmede p0 GITMEZ', a1.giden.join() === 'Pr1,Pd0,p1' && a1.u.pilUyari === null);
    });
    const b = yap(3.0, '40');
    const c = yap(3.0, '3.0');
    c.u.pilAd = 'x' + String.fromCharCode(34);
    const d = yap(3.0, '3.0');
    d.u.bagli = false;
    SONRA.push(async () => {
      await b.u.pilBaslat();
      await c.u.pilBaslat();
      await d.u.pilBaslat();
      ok('[!] PL5: gecersiz kesme / gecersiz ad / bagli degil -> HICBIR komut gitmez, sebep alanin yaninda (panel)',
         b.giden.length === 0 && c.giden.length === 0 && d.giden.length === 0 && b.u.pilUyari.tur === 'panel'
         && /0\.5 … 38\.5/.test(b.u.pilUyari.metin) && /tırnak/.test(c.u.pilUyari.metin) && /bağlı değil/.test(d.u.pilUyari.metin));
    });
    /* E9: komuttan sonraki 5 s icindeki `! pil` / `! P:` OLDUGU GIBI; disindaki degil */
    const e = ornek();
    e.pilKomutZamani = Date.now();
    e.satirIsle('! pil: skop yakalamasi suruyor (ADS susuyor) — tekrar dene');
    const r1 = e.pilUyari;
    e.pilUyari = null;
    e.pilKomutZamani = Date.now() - 6000;
    e.satirIsle('! pil: skop yakalamasi suruyor (ADS susuyor) — tekrar dene');
    e.satirIsle('! pil testi REDDEDILDI: yuk baglanmadi (akim akmadi)');
    ok('[!] PL5 (E9): komuttan sonraki 5 s icinde `! pil…` o komutun reddi — OLDUGU GIBI; REDDEDILDI her zaman (durum HATA, hata sozlukten)',
       r1 && r1.tur === 'kart' && r1.metin === 'Kart reddetti: ! pil: skop yakalamasi suruyor (ADS susuyor) — tekrar dene'
       && e.pilUyari.metin === 'Kart reddetti: ! pil testi REDDEDILDI: yuk baglanmadi (akim akmadi)' && e.pilDurum === 'HATA'
       && e.pilHataYazi === 'yük bağlanmadı (akım akmadı)', JSON.stringify(r1));
  }

  /* ── (e) PU6 oturum numarasi G'den; PL6 adres ──────────────────── */
  {
    const u = ornek();
    const giden = [];
    u.gonder = async (c) => { giden.push(c); };
    u.bagli = true;
    u.satirIsle('G 2 5 120 30 0 120 45 0 2900 1300 4 300 0');
    u.pilAdBekleyen = '18650 #3';
    u.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.000 V');
    u.satirIsle('G 2 5 121 30 0 120 45 0 2900 1300 4 300 0');
    const ara = u.pilOturum;
    u.satirIsle('G 2 6 0 30 0 120 45 0 2900 1300 4 300 0');
    ok('[!] PU6: PIL oturumu = BASLADI`dan sonra KAYIT durumlu ve ONCEKINDEN FARKLI ilk G (acik olcum oturumu 5 sayilmaz); ad `Ga6 …` o an gider',
       ara === null && u.pilOturum && u.pilOturum.no === 6 && u.pilOturum.gorulmedi === false && giden.join() === 'Ga6 18650 #3'
       && u.pilKayitAdresi === '#/kayit/6', JSON.stringify(u.pilOturum));
    const v = ornek();
    v.pilDurum = 'CALISIYOR';
    v.satirIsle('G 2 9 300 30 0 120 45 0 2900 1300 4 300 0');
    const w = ornek();
    w.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.000 V');
    w.satirIsle('! pil testi KAYDEDILMIYOR — kayit bellegi dolu (esitle + onayla)');
    w.satirIsle('G 2 11 0 30 0 120 45 0 2900 1300 4 300 0');
    ok('[!] PU6: test surerken acilan sayfa ilk KAYIT G`sini alir ve "baslangici gorulmedi" der; KAYDEDILMIYOR -> oturum YOK, kartin uyarisi ekranda',
       v.pilOturum && v.pilOturum.no === 9 && v.pilOturum.gorulmedi === true && v.pilOturumYazi === 'Kayıt #9 (başlangıcı görülmedi)'
       && w.pilOturum === null && /KAYDEDILMIYOR/.test(w.pilUyari.metin) && /KAYDEDİLMİYOR/.test(w.pilKayitYokYazi));
    const x = ornek();
    x.pilOturum = { no: 12, gorulmedi: false };
    const a = x.pilKayitAdresi;
    x.pilKayitOzet = { oturum: 12, kimlik: 21, dcir: [] };
    ok('[!] PL6: "Kayitlar`da ac" -> #/kayit/<oturum>; kayit acildiysa kimlikli (#/kayit/<oturum>@<kimlik>); sablonda bagli',
       a === '#/kayit/12' && x.pilKayitAdresi === '#/kayit/12@21'
       && /<a v-if="pilOturum && !pilCalisiyor" :href="pilKayitAdresi" class="pil-kayit-ac" data-pil="kayitlarda-ac">/.test(pm));
    const KLm = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
    ok('PL6: adres Kayitlar`in rota cozucusuyle o kaydi aciyor', JSON.stringify(KLm.rotaCoz('#/kayit/12@21')) === '{"oturum":12,"kimlik":21,"rapor":false}');
  }

  /* ── (f) PU8 okuma kartlari ────────────────────────────────────── */
  {
    const u = ornek();
    const bos = u.pilOkumalar.map((o) => o.deger);
    u.bagli = true; u.gecmis = [Object.freeze({ t: 0, v: 3.9, i: 1, w: 3.9, e: 0 })];
    u.volt = 3.9123; u.amper = 0.9876;
    u.satirIsle('* pil testi BASLADI — OCV 4.1000 V, kesme 3.200 V');
    u.pilDurumYaz({ durum: 'CALISIYOR', hata: '-', mah: 123.456, wh: 0.4567, ocv: 4.1, vson: 3.9, kesme: 3.2, dcirAni: 0, dcirOtr: 0, dcirN: 0, sira: 10 }, true);
    u.pilSonMs = 3723000;
    const o = Object.fromEntries(u.pilOkumalar.map((x) => [x.a, x]));
    ok('[!] PU8: okuma kartlari — V/I CANLI (D satiri), mAh/Wh KARTIN sayaci (tarayici hesaplamaz), sure kartin son noktasi, kesme kartin ayari; her birinin KAYNAGI yazili',
       bos.every((d) => d === '—') && o.v.deger === '3.912' && o.v.kaynak === 'canlı (kartın D satırı)' && o.i.deger === '0.9876'
       && o.mah.deger === '123.5' && o.mah.kaynak === 'kartın sayacı (her örnek)' && o.wh.deger === '0.457' && o.sure.deger === '01:02:03'
       && o.sure.kaynak === 'kartın saati (son nokta)' && o.kesme.deger === '3.20' && o.kesme.kaynak === 'kartın ayarı',
       JSON.stringify(o));
    u.pilKayitOzet = { oturum: 4, kimlik: 1, dcir: [], ayar: { kesme_v: 3.0, ocv: 4.15, dcir_aralik_ms: 300000, dcir_ms: 200 },
      sonuc: { mah: 2000.04, wh: 7.4, v_son: 2.999, sure_ms: 7200000, durumMetin: 'bitti', hata: 0 } };
    u.pilDurum = 'BITTI';
    const k = Object.fromEntries(u.pilOkumalar.map((x) => [x.a, x]));
    ok('[!] PL4/PU8: test bitip kayit yuklenince kartlar KAYITTAN (PIL_SONUC / PIL_AYAR), akim "yuk kesik"',
       k.mah.deger === '2000.0' && k.mah.kaynak === 'kayıt (PİL oturumu)' && k.v.deger === '2.999' && k.i.deger === '—'
       && k.i.kaynak === 'yük kesik' && k.sure.deger === '02:00:00' && k.kesme.deger === '3.00' && u.pilSonucYazi === 'bitti');
    const a = ornek();
    a.pilKesmeBilinen = true; a.pilMah = 55.55; a.pilTazeZaman = 1000000; a.saatTik = 1000000 + 125000;
    const eski = a.acilMahYazi;
    a.saatTik = 1000000 + 3000;
    ok('[!] PL4: acil seritteki mAh — Pil sekmesi disinda yoklama yok, degerin YASI yaziliyor (bayat sayi taze gorunmuyor)',
       eski === '55.5 mAh (00:02:05 önce)' && a.acilMahYazi === '55.5 mAh' && /\{\{ acilMahYazi \}\}/.test(html), eski);
  }

  /* ── (g) DCIR tablosu, ekran/pil.js saf fonksiyonlari, kayit kaynagi ── */
  {
    const u = ornek();
    u.pilDcirGozle(1, 0.0456, 0.0612, 80.26);
    u.pilDcirGozle(1, 0.0456, 0.0612, 81);
    u.pilDcirGozle(4, 0.05, 0.07, 400);
    const t = u.pilDcirTablo;
    ok('[!] PU10: DCIR gozlemi — dcir_n artinca son olcum; atlanan numaralar "gorulmedi" (—); an kartin kuralindan; mAh yoklama aninda (≈)',
       t.length === 4 && JSON.stringify(t[0]) === JSON.stringify({ no: 1, zaman: '00:05:00', rAni: '45.6 mΩ', rOtr: '61.2 mΩ', mah: '≈ 80.3', gorulmedi: false })
       && t[1].rAni === '—' && t[1].gorulmedi && t[2].zaman === '00:15:00' && t[3].mah === '≈ 400.0' && u.pilDcirGorulmeyen === true,
       JSON.stringify(t));
    ok('PU10: sablonda tablo pilDcirTablo`dan; son olcum karti pilDcirYazi', /v-for="d in pilDcirTablo"/.test(pm) && /\{\{ pilDcirYazi \}\}/.test(pm));
    ok('[!] ekran/pil.js sabitleri ortak/kayit.js ile ayni (OTURUM_PIL, KO_PIL_AYAR, KO_DCIR, KO_PIL_SONUC)',
       PL.OTURUM_PIL === Kx.OTURUM_PIL && PL.KO_PIL_AYAR === Kx.KO_PIL_AYAR && PL.KO_DCIR === Kx.KO_DCIR && PL.KO_PIL_SONUC === Kx.KO_PIL_SONUC);
    const c = PL.canliSeri([{ sira: 0, ms: 1000, v: 4, i: 1 }, { sira: 1, ms: 2000, v: 3.9, i: 1 }, { sira: 2, bosluk: true, adet: 5 },
      { sira: 7, ms: 8000, v: 3.8, i: 0.9 }, { sira: 8, ms: 7000, v: 9, i: 9 }]);
    ok('[!] canliSeri: bosluk isareti NaN nokta (cizgi KOPAR, ara deger YOK); azalan ms atilir',
       Array.from(c.t).join() === '1000,2000,2000,8000' && Number.isNaN(c.v[2]) && Number.isNaN(c.i[2]) && c.v[3] === 3.8);
    const t1 = Float64Array.from({ length: 3601 }, (_, k) => k * 1000);
    const i1 = new Float64Array(3601).fill(1);
    const m1 = PL.mahEkseni(t1, i1, 2500);
    const m2 = PL.mahEkseni(Float64Array.of(0, 1000, 2000), Float64Array.of(1, NaN, 1));
    const m3 = PL.mahEkseni(Float64Array.of(0, 1000), Float64Array.of(1, -0.01));
    const m4 = PL.mahEkseni(Float64Array.of(0, 1000, 9000), Float64Array.of(1, 1, 1), 2500);
    const m5 = PL.mahEkseni(Float64Array.of(0, 1000, 2000), Float64Array.of(1, 2, 3));
    ok('[!] PU9: mAh ekseni (tarayici) — 1 A x 1 sa = 1000 mAh, yamuk; NaN / eksi akim / bosluk -> eksen KURULMAZ (sebep)',
       Math.abs(m1.x[3600] - 1000) < 1e-9 && m1.hata === null && m2.x === null && m2.hata === 'pl.mah_bosluk' && m3.hata === 'pl.mah_eksi'
       && m4.hata === 'pl.mah_bosluk' && Math.abs(m5.x[2] - (1.5 + 2.5) * 1000 / 3600) < 1e-12);
    const seri = { t: Float64Array.of(0, 1000, 2000, 3000), v: Float64Array.of(4, 3.9, 3.8, 3.7), i: Float64Array.of(1, 1, 1, 1) };
    const sz = PL.pilSerileri(seri, { eksen: 'zaman' });
    const sm = PL.pilSerileri(seri, { eksen: 'mah' });
    const sb = PL.pilSerileri({ ...seri, i: Float64Array.of(1, NaN, 1, 1) }, { eksen: 'mah' });
    ok('[!] PL3: seriler V (sol) + I (sag), V USTTE (sirada son); mAh ekseninde x = yamuk mAh; kurulamazsa ZAMAN eksenine duser ve sebebi tasir',
       sz.seriler.map((s) => s.ad + ':' + s.eksen).join() === 'I:sag,V:sol' && sz.eksen === 'zaman' && sz.seriler[0].t === seri.t
       && sm.eksen === 'mah' && Math.abs(sm.seriler[1].t[3] - 3000 / 3600) < 1e-12 && sm.x === sm.seriler[0].t
       && sb.eksen === 'zaman' && sb.eksenUyari === 'pl.mah_bosluk');
    const dcir = [{ no: 1, tMs: 1000 }, { no: 2, tMs: 2600 }, { no: 3, tMs: NaN }];
    ok('[!] PL3/PU10: DCIR isaretleri — zaman ekseninde t = an; mAh ekseninde EN YAKIN ornegin x`i (ara deger yok); etiket R<no>; ani bilinmeyen atlanir',
       JSON.stringify(PL.dcirIsaretleri(dcir, seri)) === '[{"t":1000,"metin":"R1"},{"t":2600,"metin":"R2"}]'
       && JSON.stringify(PL.dcirIsaretleri(dcir, seri, sm.x).map((x) => x.t)) === JSON.stringify([sm.x[1], sm.x[3]]));
    ok('PU9: mAh ekseni sonu kartin sayaciyla yan yana yazili (ayrisirsa gorunur)',
       (() => { const v = ornek(); v.pilEksen = 'mah'; v.pilBilgi = { xSon: 245.92 }; v.pilKesmeBilinen = true; v.pilMah = 246.24;
         return v.pilMahKarsilastirma === 'Eksen sonu 245.9 mAh (tarayıcı, 1 Hz noktalardan) · kartın sayacı 246.2 mAh (her örnek)'; })());
    const ok1 = PL.okumaSatirlari({ tA: 1000, tB: 61000, dt: 60000, dV: -0.1, kanallar: [{ ad: 'V', a: { deger: 4 }, b: { deger: 3.9 } },
      { ad: 'I', a: { deger: 1 }, b: { deger: 0.98 } }], enerji: { mah: 16.5, wh: 0.065 } }, 'zaman');
    ok('PL3: imlec okumasi — A/B zamani, Δt, V/I A→B, ΔV, A–B mAh/Wh (tarayici, HAM)',
       ok1.map((s) => s.ad + '=' + s.d).join(' | ') === 'A=00:00:01 | B=00:01:01 | Δt=00:01:00 | V A/B=4.000 V → 3.900 V | I A/B=1.0000 A → 0.9800 A | ΔV=-0.1000 V | A–B mAh (tarayıcı)=16.50 mAh | A–B Wh (tarayıcı)=0.0650 Wh',
       ok1.map((s) => s.ad + '=' + s.d).join(' | '));
    /* kayit kaynagi: GERCEK ortak/kayit.js ile paketlenip cozulen PIL oturumu */
    let sira = 0;
    const ham = [];
    const ekle = (tur, ot, yuk) => { sira++; ham.push(Kx.kayitPaketle(tur, sira, ot, yuk)); return sira; };
    const kanal = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
    const kal = { normal: kanal(21), yuksek: kanal(201), i_ofset: 5, i_pga: 0.256, sont_ohm: 0.1, i_duzeltme: 1, sebeke_hz: 0, faz_kal_us: [0, 0] };
    const ot = ekle(Kx.T_BASLA, 1, Kx.baslaPaketle({ oturum_turu: 2, kal_bicim: 1, hiz_ms: 1000, unix_s: 1790300000, kart_ms: 100000,
      acilis: 3, surum: 'A3-3F', kal, kal_no: 2 }));
    ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_PIL_AYAR, kart_ms: 100001, kesme_v: 3.2, ocv: 4.1, azami_s: 86400,
      dcir_aralik_ms: 300000, dcir_ms: 200, kayit_hz: 1 }));
    const nk = (ms, v, i) => Kx.noktaPaketle({ kart_ms: 100000 + ms, n: 40, bayrak: 0, v_ort_kod: v / 0.002625 + 12, v_min_kod: 0,
      v_maks_kod: 0, i_ort_kod: i / 7.8125e-5 + 5, i_min_kod: 0, i_maks_kod: 0, w_ort: v * i, w_min: 0, w_maks: 0 });
    const u32 = (x) => { const b = new Uint8Array(4); new DataView(b.buffer).setUint32(0, x, true); return b; };
    const noktalar = (ilk, ns) => { const y = new Uint8Array(4 + 36 * ns.length); y.set(u32(ilk), 0); ns.forEach((b, k) => y.set(b, 4 + 36 * k)); ekle(Kx.T_NOKTA, ot, y); };
    noktalar(0, [nk(1000, 4.0, 1.0), nk(2000, 3.99, 0.99), nk(3000, 3.98, 0.98)]);
    ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_DCIR, kart_ms: 100000 + 300200, no: 1, v_once: 3.9, i_once: 1, v_ani: 3.85,
      v_oturmus: 3.83, r_ani: 0.05, r_oturmus: 0.07, mah: 83.4, wh: 0.33 }));
    ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_PIL_SONUC, kart_ms: 100000 + 400000, durum: 2, hata: 0, mah: 99.5, wh: 0.39,
      ocv: 4.1, v_son: 3.2, sure_ms: 400000, dcir_sayisi: 1 }));
    ekle(Kx.T_BITIR, ot, (() => { const b = new Uint8Array(8); new DataView(b.buffer).setUint32(0, 3, true); b[4] = 4; return b; })());
    const otOlcum = ekle(Kx.T_BASLA, sira + 1, Kx.baslaPaketle({ oturum_turu: 1, kal_bicim: 1, hiz_ms: 200, unix_s: 1790300500, kart_ms: 500000,
      acilis: 3, surum: 'A3-3F', kal, kal_no: 2 }));
    let n = 0;
    for (const h of ham) n += h.length;
    const bayt = new Uint8Array(n);
    let a0 = 0;
    for (const h of ham) { bayt.set(h, a0); a0 += h.length; }
    const kayitlar = Kx.akisCoz(bayt);
    const oturumlar = Kx.oturumlariKur(kayitlar);
    const r = PL.pilKayitKur(oturumlar.get(ot), { disari: Dx, kayitlar, kimlik: 21 });
    ok('[!] PU11: kayit kaynagi — egri kaydin noktalarindan (kalibrasyonla V/A, x = relMs), DCIR OLAY`in KENDI zamani ve degerleri, sonuc PIL_SONUC, ayar PIL_AYAR, sebep BITIR',
       !r.hata && Array.from(r.seri.t).join() === '1000,2000,3000' && Math.abs(r.seri.v[0] - 4.0) < 1e-6 && Math.abs(r.seri.i[2] - 0.98) < 1e-6
       && r.ozet.dcir.length === 1 && r.ozet.dcir[0].tMs === 300200 && Math.abs(r.ozet.dcir[0].rAni - 0.05) < 1e-7
       && Math.abs(r.ozet.dcir[0].mah - 83.4) < 1e-4 && r.ozet.dcir[0].yaklasik === false && Math.abs(r.ozet.sonuc.mah - 99.5) < 1e-4
       && r.ozet.sonuc.durumMetin === 'bitti (kesme gerilimine ulaşıldı)' && r.ozet.sebepMetin === 'pil testi bitti'
       && Math.abs(r.ozet.ayar.kesme_v - 3.2) < 1e-6 && r.ozet.kimlik === 21 && r.boslukMs === 2500
       && PL.pilKayitKur(oturumlar.get(otOlcum), { disari: Dx }).hata === 'pl.hata_kayit_tur', JSON.stringify(r.ozet && r.ozet.dcir));
    const veriler = { 3: { kimlik: 3, oturumlar: new Map([[ot, oturumlar.get(ot)]]), kayitlar },
      7: { kimlik: 7, oturumlar: new Map([[ot, oturumlar.get(otOlcum)]]), kayitlar } };
    const istenen = [];
    const denetci = { akislar: async () => [{ kimlik: 3, olusma: 10 }, { kimlik: 7, olusma: 20 }],
      akisVerisi: async (k) => { istenen.push(k); return veriler[k]; } };
    SONRA.push(async () => {
      const a = await PL.pilKaydiAc({ oturum: ot, kimlik: null }, { denetciKur: async () => denetci });
      const sira1 = istenen.splice(0);
      const yok = await PL.pilKaydiAc({ oturum: 77, kimlik: null }, { denetciKur: async () => denetci });
      ok('[!] PU11 (3E S4 kurali): @kimlik yoksa oturumu TASIYAN ve turu PIL olan en yeni akis — daha yeni akistaki ayni numarali OLCUM oturumu ATLANIR; yoksa "yok"',
         !a.hata && a.ozet.kimlik === 3 && sira1.join() === '7,3' && typeof a.csv === 'function' && yok.hata === 'pl.hata_kayit_yok'
         && Dx.csvBayt(Dx.pilCsv(oturumlar.get(ot), { ...Dx.BICIM_EXCEL_TR, kayitlar })).length === a.csv('tr').length,
         JSON.stringify({ k: a.ozet && a.ozet.kimlik, sira1 }));
      const esit = [];
      const den2 = { kartListesi: async () => ({ durum: 'tamam', liste: { kimlik: 21, oturumlar: [] } }),
        esitle: async (x) => { esit.push(x); return { durum: 'tamam' }; } };
      const u1 = await PL.pilKaydiEsitle({ kartTaban: 'http://192.168.1.50', tasiyici: 'akis', denetciKur: async () => den2 });
      const u2 = await PL.pilKaydiEsitle({ tasiyici: 'akis', kopruda: true, denetciKur: async () => den2 });
      const u3 = await PL.pilKaydiEsitle({ tasiyici: 'akis', bagli: true, gonder: () => {}, denetciKur: async () => den2 });
      ok('[!] PU11 (C1/C3): esitleme yalniz kartin KENDI adresinden (baska koken / kopru -> yok, istek yok); kimlik dizinden, onay VARSAYILAN gitmez',
         u1.durum === 'uygun_degil' && u2.durum === 'uygun_degil' && u3.durum === 'tamam' && esit.length === 1 && esit[0].kimlik === 21
         && esit[0].onay === null, JSON.stringify({ u1, u2, esit }));
    });
  }

  /* ── (h) demo karti ───────────────────────────────────────────── */
  {
    const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
    const O = al('pilSatirOlayi');
    const kes = SK.komut('P40');
    const ayar = SK.komut('P2.8');
    const bas = SK.komut('p1');
    const iki = SK.komut('p1');
    const gb = SK.komut('Gb200');
    SK.pilTik(1);
    SK.pilTik(5000);
    const sayfa = SK.pilSayfa(0);
    const b = SK.komut('p');
    const dur = SK.komut('p0');
    const zaten = SK.komut('p0');
    ok('[!] E12: demo karti pil testi — P / p1 / p0 / p metinleri FIRMWARE`in; BASLADI ve B satiri panelin ayristiricisindan geciyor; /pil govdesi pil_sayfa bicimi; pil surerken Gb reddi',
       kes[0] === "! P: 0.5 ile 38.5 V arasi olmali (ust sinir MOSFET Vdss'inden)" && O(ayar[0]).v === 2.8
       && O(bas[0]).tur === 'basladi' && O(bas[0]).kesme === 2.8 && bas.some((x) => /^G 2 /.test(x))
       && iki[0] === '! pil testi zaten suruyor — yeniden baslatmak icin once p0' && ino.includes(iki[0])
       && gb[0] === '! G: pil testi suruyor — kaydi zaten acik; durdurmak icin p0' && ino.includes(gb[0])
       && sayfa.indexOf('durum=CALISIYOR') === 0 && /\n--\n\d+,\d+\.\d{4},\d+\.\d{6}\n/.test(sayfa)
       && O(b[0]).tur === 'durum' && O(dur[0]).tur === 'durduruldu' && O(zaten[0]).tur === 'calismiyor',
       JSON.stringify({ kes, bas, b }));
  }

  /* ── (i) PT — PIL TESTI IYILESTIRMESI (tasarim/2026-10-07-pil-iyilestirme.md, PT2–PT7) ──────────
     app.js durumu tutar ve Pr -> Pd -> P -> p1 gonderir; form, OCV / DCIR gosterimi ekran/pil.js PilPt (sablonu
     telefon paketinde derlenir); metin + hesap ortak/sozluk_pil.js (PilPt DINAMIK indirir). Acilis (EU31 / #/skop),
     KU1 ve #/pil 13 dosya sinirlari tasmiyor. */
  {
    const SP = require(path.join(KOK, 'ortak', 'src', 'sozluk_pil.js'));
    const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
    const O = al('pilSatirOlayi');
    /* PilPt'nin Vue'suz ornegi (sozluk inmis gibi: s = ortak/sozluk_pil.js) */
    const ptOrnek = (kip, d) => {
      const o = { kip, d, s: SP, olaylar: [], $emit(a, v) { this.olaylar.push([a, v]); } };
      for (const [ad, f] of Object.entries(PL.PilPt.computed)) {
        Object.defineProperty(o, ad, { get: (typeof f === 'function' ? f : f.get).bind(o), set: f.set ? f.set.bind(o) : undefined });
      }
      return o;
    };
    /* firmware metinleri: panelin tanidigi PT satirlari ino'da birebir */
    const ptMetin = ['* pil kayit hizi ', "* pil DCIR olcumu ACIK (5 dk'da bir 200 ms yuk kesilir)", '* pil DCIR olcumu KAPALI',
      '! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali', '! Pd: Pd1 (ac) ya da Pd0 (kapat)', '! P: pil testi suruyor — once p0',
      'her ornek (ayrintili kayit + 1/s nokta)', ' s yuksuz (OCV), sonra yuk'];
    const ptYok = ptMetin.filter((m) => !ino.includes(m));
    ok('[!] PT7: Pr / Pd onay ve ret satirlari FIRMWARE`de birebir; panel onaylari `ayar`, retleri `ret` sayiyor (kesme / test satirlari karismiyor)',
       ptYok.length === 0 && O('* pil kayit hizi 20 /s').tur === 'ayar' && O('* pil kayit hizi her ornek (ayrintili kayit + 1/s nokta)').tur === 'ayar'
       && O('* pil DCIR olcumu KAPALI').tur === 'ayar' && O('! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali').tur === 'ret'
       && O('! Pd: Pd1 (ac) ya da Pd0 (kapat)').tur === 'ret' && O('! P: pil testi suruyor — once p0').tur === 'ret'
       && O('* pil kesme gerilimi 3.000 V').tur === 'kesme' && O('* pil testi kaydi istendi (oturum turu PIL)') === null
       && O('* pil testi BASLADI — OCV 4.1100 V, kesme 3.000 V; once 5 s yuksuz (OCV), sonra yuk').tur === 'basladi',
       ptYok.join(' | ') || `${ptMetin.length} metin`);
    /* A3-PT1 `P` (argumansiz) satiri: panel yalniz KESMEYI okur — `ayar` (Pr/Pd onayi) sanmaz; bicim firmware'den */
    const pGovdePT = (ino.match(/Serial\.print\(F\("\* pil kesme gerilimi "\)\);[\s\S]{0,700}?F\("kapali"\)\);/) || [''])[0];
    const pSat = (hz, dc) => `* pil kesme gerilimi 3.250 V · kayit ${hz.toFixed(2)} Hz${hz ? '' : ' (her ornek)'} · azami sure 24 saat · DCIR ${dc}`;
    ok('[!] PT: A3-PT1 `P` satiri (`kayit <hz> Hz[ (her ornek)] · azami sure <s> saat · DCIR acik|kapali`) firmware`in sirasiyla; panel KESMEYI dogru okur, Pr/Pd onayi SAYMAZ',
       /F\(" V · kayit "\)[\s\S]*F\(" Hz \(her ornek\)"\)[\s\S]*F\(" · azami sure "\)[\s\S]*F\(" saat · DCIR "\)/.test(pGovdePT)
       && O(pSat(0, 'kapali')).tur === 'kesme' && O(pSat(0, 'kapali')).v === 3.25 && O(pSat(20, 'acik')).v === 3.25
       && (() => { const u = ornek(); u.pilKomutZamani = Date.now(); u.satirIsle(pSat(0, 'kapali'));
         return u.pilKesme === 3.25 && u.pilKesmeBilinen === true && u._pilAyarYanit === undefined && u.pilUyari === null; })(),
       pGovdePT.replace(/\s+/g, ' ').slice(0, 200));
    /* hiz secenekleri: firmware'in pil_hz_izinli kumesi; sabitler firmware'den */
    const izin = (/static uint8_t pil_hz_izinli\(uint32_t hz\)\s*\{\s*return \(uint8_t\)\(([^;]*)\);/.exec(pilH) || ['', ''])[1];
    const prKabul = [...izin.matchAll(/hz == (\d+)u/g)].map((m) => Number(m[1])).sort((a, b) => a - b);
    const N = SP.kayitHizNormal;
    ok('[!] PT3: hiz secenekleri firmware`in pil_hz_izinli kumesiyle AYNI (1 · 5 · 20 · 50 · 0 = her ornek); bos / bozuk / listede olmayan tercih -> 1/s ("" ve null "her ornek" DEGIL); PIL_OCV_MS pil_test.h`le ayni',
       [...SP.PIL_KAYIT_HIZLARI].join() === '1,5,20,50,0' && [...SP.PIL_KAYIT_HIZLARI].sort((a, b) => a - b).join() === prKabul.join()
       && N(0) === 0 && N('20') === 20 && N(50) === 50 && ['', null, undefined, 'x', 7, -1, 0.2, true, '  '].every((x) => N(x) === 1)
       && SP.PIL_OCV_MS === Number((/#define PIL_OCV_MS\s+(\d+)u/.exec(pilH) || [])[1]) && SP.PIL_OCV_MS === al('PIL_OCV_MS'),
       `fw: ${prKabul.join(',')}`);
    const u0 = ornek();
    ok('[!] PT5/PT7: app.js VARSAYILANI 1/s ve DCIR KAPALI (bilesen inmese de bu gider); PT durumu bos',
       u0.pilKayitHz === 1 && u0.pilDcirAcik === false && u0.pilPtDestek === null && u0.pilEvre === '' && u0.pilIstenen === null);
    /* kayit yeri tahmini: sabitler firmware'in bolum ve kayit boylarindan */
    const part = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'partitions.csv'), 'utf8');
    const bolum = parseInt((/^kayit,\s*data,\s*0x40,\s*0x[0-9A-Fa-f]+,\s*(0x[0-9A-Fa-f]+)/m.exec(part) || [])[1], 16);
    const kot = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_oturum.h'), 'utf8');
    const kbh = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_bicim.h'), 'utf8');
    const azYuk = Number((/#define KAYIT_AZAMI_YUK (\d+)u/.exec(kot) || [])[1]);
    const nB = Number((/#define KAYIT_NOKTA_BAYT\s+(\d+)u/.exec(kbh + kot) || [])[1]) || 36;
    const aB = Number((/#define KAYIT_AYRINTI_ORNEK\s+(\d+)u/.exec(kbh) || [])[1]);
    const aBas = Number((/#define KAYIT_AYRINTI_BAS\s+(\d+)u/.exec(kbh) || [])[1]);
    const S = SP.kayitSuresiS;
    const sHer = S(0, bolum) / 3600;
    const s1 = S(1, bolum) / 3600;
    const s50 = S(50, bolum) / 3600;
    ok('[!] PT4/PT7: tahmini azami sure — bolum partitions.csv`den, nokta / ayrinti kayit boylari kayit_oturum.h + kayit_bicim.h`den; her ornek ~1 sa (0.9…1.6), 1/s > 24 sa, hiz arttikca kisalir; bos yer G`nin onaysiz payindan',
       bolum === SP.KAYIT_BOLUM_BAYT && azYuk === 1012 && aB === 6 && aBas === 16
       && Math.abs(SP.PIL_NOKTA_BAYT - (azYuk + 16) / Math.floor((azYuk - 4) / nB)) < 1e-12
       && Math.abs(SP.PIL_AYRINTI_BAYT - (azYuk + 16) / Math.floor((azYuk - aBas) / aB)) < 1e-12
       && sHer > 0.9 && sHer < 1.6 && s1 > 24 && s50 < s1 / 40 && s50 > sHer && S(1, 0) === 0
       && SP.bosKayitBayt({ onaysiz: 500 }) === bolum / 2 && SP.bosKayitBayt(null) === null && SP.bosKayitBayt({}) === null
       && SP.bosKayitBayt({ onaysiz: 1200 }) === 0 && JSON.stringify(SP.sureKisa(4739)) === '{"anahtar":"pt.saat","n":"1.3"}'
       && SP.sureKisa(1800).n === '30' && SP.sureKisa(400000).n === '111',
       `her ornek ${sHer.toFixed(2)} sa · 1/s ${s1.toFixed(0)} sa · 50/s ${s50.toFixed(2)} sa`);
    /* form (PilPt kip form): etiketler, sure yazisi, her ornek uyarisi, kalicilik, olaylar */
    const d1 = ornek();
    d1.kayit.g = null;
    d1.pilKayitHz = 0;
    const f1 = ptOrnek('form', d1);
    const yaziBolum = f1.g.sure;
    const uyariHer = f1.g.uyariHer;
    d1.kayit.g = { onaysiz: 250 };
    d1.pilKayitHz = 1;
    const yaziKart = f1.g.sure;
    const sec = f1.g.hizlar;
    const ls = new Map();
    const sahteLS = { getItem: (k) => (ls.has(k) ? ls.get(k) : null), setItem: (k, v) => ls.set(k, String(v)) };
    const eskiD = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    Object.defineProperty(globalThis, 'localStorage', { value: sahteLS, configurable: true, writable: true });
    f1.hz = '20';
    f1.dcir = 1;
    const yazilan = [ls.get('olcum.pilKayitHz'), ls.get('olcum.pilDcir')];
    if (eskiD) Object.defineProperty(globalThis, 'localStorage', eskiD);
    else delete globalThis.localStorage;
    const sab = PL.PilPt.template;
    const yok = ptOrnek('form', d1);
    yok.s = null;
    ok('[!] PT7 (form): secenekler 1/s … "Her ornek (~400/s)"; sure yazisi dayanagini soyler (kartin bos yeri / bolum); her ornek UYARISI yalniz her ornekte; secim app.js`e olayla gider ve tarayicida hatirlanir; sozluk inmeden form YOK; alanlar etiketli',
       sec.map((x) => x.v).join() === '1,5,20,50,0' && sec[1].ad === '5/s' && sec[4].ad === 'Her örnek (~400/s)'
       && /^Bu hızda en çok ~1\.\d sa kayıt \(11\.9 MB kayıt bölümüne göre/.test(yaziBolum) && /~\d+ sa kayıt \(kartın boş kayıt yeri ~8\.9 MB\)\.$/.test(yaziKart)
       && /1 saatte/.test(uyariHer) && f1.g.uyariHer === '' && yok.g === null
       && JSON.stringify(f1.olaylar) === '[["hz",20],["dcir",true]]' && yazilan.join() === '20,true'
       && /<p v-if="g\.uyariHer" class="uyari" data-pil="hiz-uyari">/.test(sab) && /<label for="pil-hiz">\{\{ g\.hizEtiket \}\}<\/label>/.test(sab)
       && /<select id="pil-hiz" v-model="hz" data-pil="hiz">/.test(sab) && /<template v-if="g && kip === 'form'">/.test(sab)
       && /<input id="pil-dcir" type="checkbox" v-model="dcir" data-pil="dcir-ac"[^>]*>\s*<label for="pil-dcir"[^>]*>\{\{ g\.dcirEtiket \}\}<\/label>/.test(sab)
       && /<pil-pt kip="form" :d="\$data" @hz="pilKayitHz = \$event" @dcir="pilDcirAcik = \$event"><\/pil-pt>/.test(pm)
       && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(sab), `${yaziBolum} · ${yaziKart}`);
    /* sira: Pr -> Pd -> P -> p1; ret -> p1 YOK; eski firmware -> Pr/Pd YOK */
    const pt = (ayar = {}) => {
      const u = ornek();
      const giden = [];
      u.bagli = true; u.pilKesmeBilinen = true; u.pilKesme = 3.0; u.pilKesmeGiris = '3.2';
      Object.assign(u, ayar);
      u.gonder = async (c) => {
        giden.push(c);
        if (c === u._ret) { u.satirIsle(u._retSatir); return; }
        if (c[0] === 'P' && (c[1] === 'r' || c[1] === 'd')) u.satirIsle(c[1] === 'r' ? `* pil kayit hizi ${c.slice(2)} /s` : '* pil DCIR olcumu KAPALI');
        else if (c[0] === 'P') u.satirIsle(`* pil kesme gerilimi ${Number(c.slice(1)).toFixed(3)} V`);
      };
      return { u, giden };
    };
    const v1 = pt();
    const v2 = pt({ pilKayitHz: 0, pilDcirAcik: true });
    const v3 = pt({ _ret: 'Pr20', _retSatir: '! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali', pilKayitHz: 20 });
    const v4 = pt({ pilPtDestek: false, pilKayitHz: 50 });
    SONRA.push(async () => {
      const r1 = await v1.u.pilBaslat();
      const r2 = await v2.u.pilBaslat();
      const r3 = await v3.u.pilBaslat();
      const r4 = await v4.u.pilBaslat();
      ok('[!] PT7: Baslat -> `Pr1`, `Pd0` (VARSAYILAN), sonra `P3.2` + onay, sonra `p1`; her ornek + DCIR acik -> `Pr0`, `Pd1`; istenen ayar saklanir',
         r1 === true && v1.giden.join() === 'Pr1,Pd0,P3.2,p1' && r2 === true && v2.giden.join() === 'Pr0,Pd1,P3.2,p1'
         && JSON.stringify(v1.u.pilIstenen) === '{"hz":1,"dcir":false}' && JSON.stringify(v2.u.pilIstenen) === '{"hz":0,"dcir":true}',
         JSON.stringify([v1.giden, v2.giden]));
      ok('[!] PT7: kart `Pr`yi reddederse `Pd`, `P`, `p1` GITMEZ; kartin satiri OLDUGU GIBI (pl.kart_reddetti)',
         r3 === false && v3.giden.join() === 'Pr20' && v3.u.pilUyari.tur === 'kart' && v3.u.pilIstenen === null
         && v3.u.pilUyari.metin === 'Kart reddetti: ! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali', JSON.stringify([v3.giden, v3.u.pilUyari]));
      ok('[!] PT7: `/pil` PT alanlarini tasimayan (A3-PT1 oncesi) karta Pr / Pd GITMEZ (eski kart `Pr`yi `P` sanip reddederdi); test kesmeyle baslar',
         r4 === true && v4.giden.join() === 'P3.2,p1' && v4.u.pilIstenen === null, v4.giden.join());
    });
    /* /pil basligi, OCV evresi */
    const e = ornek();
    e.bagli = true; e.tasiyiciAdi = 'akis'; e.bagliTasiyici = 'akis';
    const yanitPt = (ek, n = 2) => ['durum=CALISIYOR', 'hata=-', 'mah=0.0000', 'wh=0.000000', 'ocv=4.1100', 'vson=4.1100', 'kesme=3.000',
      'dcir_ani=0.00000', 'dcir_otr=0.00000', 'dcir_n=0', `sira=${n}`, 'ilk_sira=0', `kalan=0`, 'coulomb=0.000', ...ek, '--',
      ...Array.from({ length: n }, (_, k) => `${1000 * (k + 1)},4.1100,0.000000`)].join(String.fromCharCode(10)) + String.fromCharCode(10);
    SONRA.push(async () => {
      const eskiF = sandbox.fetch;
      sandbox.fetch = async () => ({ ok: true, status: 200, text: async () => yanitPt(['evre=ocv', 'kayit_hz=1.00', 'dcir=0']) });
      e.satirIsle('* pil testi BASLADI — OCV 4.1100 V, kesme 3.000 V; once 5 s yuksuz (OCV), sonra yuk');
      const basta = { evre: e.pilEvre, destek: e.pilPtDestek };
      await e.pilYokla();
      const ocv1 = { evre: e.pilEvre, gor: e.pilOcvEvresi, destek: e.pilPtDestek, hz: e.pilKartHz, dcir: e.pilKartDcir, kapali: e.pilDcirKapali };
      sandbox.fetch = async () => ({ ok: true, status: 200, text: async () => yanitPt(['evre=yuk', 'kayit_hz=0.00', 'dcir=1'], 6) });
      await e.pilYokla();
      const ocv2 = { evre: e.pilEvre, gor: e.pilOcvEvresi, hz: e.pilKartHz, dcir: e.pilKartDcir, kapali: e.pilDcirKapali };
      const eski = ornek();
      eski.bagli = true; eski.tasiyiciAdi = 'akis'; eski.bagliTasiyici = 'akis';
      sandbox.fetch = async () => ({ ok: true, status: 200, text: async () => yanitPt([]) });
      await eski.pilYokla();
      sandbox.fetch = eskiF;
      const okumalar = govdeMetni(appKaynak, 'pilYokla');
      ok('[!] PT2/PT6: BASLADI`daki "yuksuz (OCV)" A3-PT1`i tanitir ve evreyi OCV yapar (yoklama beklenmez); /pil evre=ocv -> OCV seridi GORUNUR, evre=yuk -> kalkar; kayit_hz / dcir okunur; PT alansiz /pil -> eski firmware',
         basta.evre === 'ocv' && basta.destek === true && ocv1.evre === 'ocv' && ocv1.gor === true && ocv1.hz === 1 && ocv1.dcir === 0
         && ocv1.kapali === true && ocv2.evre === 'yuk' && ocv2.gor === false && ocv2.hz === 0 && ocv2.dcir === 1 && ocv2.kapali === false
         && eski.pilPtDestek === false && /a\.evre/.test(okumalar) && /a\.kayit_hz/.test(okumalar) && /a\.dcir\b/.test(okumalar)
         && /<pil-pt v-if="pilOcvEvresi" kip="evre" :d="\$data"><\/pil-pt>/.test(pm),
         JSON.stringify({ basta, ocv1, ocv2 }));
    });
    const w = ornek();
    w.satirIsle('* pil testi BASLADI — OCV 4.1100 V, kesme 3.000 V');
    const eskiBas = { evre: w.pilEvre, destek: w.pilPtDestek };
    const z = ornek();
    z.pilPtDestek = true;
    z.satirIsle('* pil testi BASLADI — OCV 4.1100 V, kesme 3.000 V; once 5 s yuksuz (OCV), sonra yuk');
    z.pilSonMs = 6000;
    const usbGecti = z.pilOcvEvresi;
    z.satirIsle('* pil testi DURDURULDU, yuk kesildi');
    ok('[!] PT2: eski BASLADI evreyi OCV YAPMAZ; USB`de (yalniz B satiri) OCV seridi kartin saati PIL_OCV_MS`i gecince kalkar; test bitince evre ve istenen ayar duser',
       eskiBas.evre === '' && eskiBas.destek === null && usbGecti === false && z.pilEvre === '' && z.pilIstenen === null);
    /* farkli ayar uyarisi + evre / lejant / DCIR metinleri (PilPt) */
    const fd = ornek();
    fd.pilDurum = 'CALISIYOR';
    fd.pilIstenen = { hz: 20, dcir: true };
    const fk = ptOrnek('fark', fd);
    fd.pilKartHz = 1; fd.pilKartDcir = 1;
    const fark1 = fk.g.fark;
    fd.pilKartHz = 20; fd.pilKartDcir = 0;
    const fark2 = fk.g.fark;
    fd.pilKartDcir = 1;
    const fark3 = fk.g.fark;
    fd.pilKartHz = 0; fd.pilIstenen = { hz: 1, dcir: true };
    const fark4 = fk.g.fark;
    fd.pilDurum = 'BITTI';
    const fark5 = fk.g.fark;
    ok('[!] PT7: kart istenenden farkli hiz / DCIR`la calisiyorsa (yalniz test surerken) uyari — test DURDURULMAZ (emniyet degil); sablonda yeri var',
       fark1 === 'Kart testi istenenden farklı ayarla sürdürüyor: kayıt 1/s (istenen 20/s).'
       && fark2 === 'Kart testi istenenden farklı ayarla sürdürüyor: DCIR kapalı (istenen açık).' && fark3 === ''
       && fark4 === 'Kart testi istenenden farklı ayarla sürdürüyor: kayıt Her örnek (~400/s) (istenen 1/s).' && fark5 === ''
       && SP.ayarFarki(null, 1, 0) === null && /<pil-pt v-if="pilCalisiyor && pilIstenen" kip="fark" :d="\$data"><\/pil-pt>/.test(pm)
       && /<p v-else-if="g && kip === 'fark' && g\.fark" class="uyari" data-pil="ayar-fark">\{\{ g\.fark \}\}<\/p>/.test(sab),
       JSON.stringify({ fark1, fark2, fark4 }));
    const ld = ornek();
    const lj = ptOrnek('lejant', ld);
    const lej0 = lj.g.lejant;
    ld.pilPtDestek = true; ld.pilNokta = [{ sira: 0, ms: 1000, v: 4, i: 0 }];
    const lej1 = lj.g.lejant;
    ld.pilKayitOzet = { oturum: 3, ocv: null };
    const lej2 = lj.g.lejant;
    ld.pilKayitOzet = { oturum: 3, ocv: [0, 5000] };
    ok('[!] PT7: egrinin OCV lejanti yalniz bant varken (canlida A3-PT1 + nokta, kayitta KN_OCV araligi); OCV seridi metni sozluk_pil`den',
       lej0 === '' && lej1 === 'OCV · yük kapalı ilk 5 s' && lej2 === '' && lj.g.lejant === lej1
       && ptOrnek('evre', ld).g.evre === 'OCV ölçülüyor (yük kapalı) — ilk 5 s'
       && /<p v-else-if="g && kip === 'evre'" data-pil="evre" role="status"/.test(sab) && /\{\{ g\.evre \}\}/.test(sab)
       && /<pil-pt kip="lejant" :d="\$data"><\/pil-pt>/.test(pm) && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(sab));
    /* DCIR kapali gosterimi */
    const g = ornek();
    const once = g.pilDcirKapali;
    g.pilKartDcir = 0;
    const canli = g.pilDcirKapali;
    g.pilKayitOzet = { oturum: 4, kimlik: 1, dcir: [], ayar: { kesme_v: 3, ocv: 4.1, dcir_aralik_ms: 300000, dcir_ms: 200 } };
    const kayitAcik = g.pilDcirKapali;
    g.pilKayitOzet = { oturum: 4, kimlik: 1, dcir: [], ayar: { kesme_v: 3, ocv: 4.1, dcir_aralik_ms: 0, dcir_ms: 200 } };
    ok('[!] PT5: DCIR KAPALI — canlida /pil dcir=0, kayitta PIL_AYAR dcir_aralik_ms 0 -> tablo YERINE "kapali" metni (PilPt), aralik "kapalı"; bilinmiyorsa eski gorunum',
       once === false && canli === true && kayitAcik === false && g.pilDcirKapali === true
       && /<pil-pt v-if="pilDcirKapali" kip="dcir" :d="\$data"><\/pil-pt>\s*<template v-else>/.test(pm)
       && /<pil-pt v-if="pilDcirKapali" kip="kapali" :d="\$data"><\/pil-pt><template v-else>\{\{ pilDcirAralikYazi \}\}<\/template>/.test(pm)
       && ptOrnek('dcir', g).g.dcirKapali === 'Bu testte iç direnç ölçümü kapalı — yük hiç kesilmiyor.'
       && ptOrnek('kapali', g).g.kapali === 'kapalı');
    /* yerlesim: PilPt ekran/pil.js'te (sablon telefon paketinde derlenir), metin + hesap ortak/sozluk_pil.js'te — PilPt kurulunca DINAMIK */
    ok('[!] PT7 (EU32 / KU1 / acilis butcesi): PilPt ekran/pil.js`te (app.js defineAsyncComponent, Pil sekmesinde); metin + hesabi ortak/sozluk_pil.js — YALNIZ PilPt DINAMIK indirir (Karsilastirma pil.js`i indirir, sozlugu degil); acilis grafiginde ve app.js`te YOK; her pt. anahtari sozlugun kendi hesabinda',
       /'pil-pt': defineAsyncComponent\(\{ loader: \(\) => import\('\.\/ekran\/pil\.js'\)\.then\(\(m\) => m\.PilPt\) \}\)/.test(appKaynak)
       && /import\('\/ortak\/sozluk_pil\.js'\)/.test(pilKaynak) && !/from '\/ortak\/sozluk_pil\.js'/.test(pilKaynak)
       && !/sozluk_pil/.test(yorumsuz(appKaynak)) && !iceAktarmaGrafigi().map((x) => x.goruntu).includes('ortak/sozluk_pil.js')
       && !iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'pil.js')).map((x) => x.goruntu).includes('ortak/sozluk_pil.js')
       && (() => { const k = fs.readFileSync(path.join(KOK, 'ortak', 'src', 'sozluk_pil.js'), 'utf8'); const h = k.slice(k.indexOf('// ── hesap'));
         return Object.keys(SP.SOZLUK_PIL).every((a) => h.includes(`'${a}'`) || h.includes(`"${a}"`)); })());
    /* OCV bandi (pil.js) */
    ok('[!] PT2/PT7: ekran/pil.js KN_OCV ortak/kayit.js ile ayni; OCV bandi zaman ekseninde [t0, t1], mAh ekseninde en yakin orneklerin x`i; canlida A3-PT1 kartinda [0, PIL_OCV_MS]',
       PL.KN_OCV === Kx.KN_OCV && Kx.KN_OCV === 0x80
       && JSON.stringify(PL.ocvBantlari([0, 5000], { t: Float64Array.of(1000, 5000, 6000) })) === '[{"t0":0,"t1":5000,"metin":"OCV"}]'
       && JSON.stringify(PL.ocvBantlari([0, 5000], { t: Float64Array.of(1000, 5000, 6000) }, Float64Array.of(0, 0.5, 1))) === '[{"t0":0,"t1":0.5,"metin":"OCV"}]'
       && PL.ocvBantlari(null, { t: Float64Array.of(1) }).length === 0 && PL.ocvBantlari([5, 5], { t: Float64Array.of(1) }).length === 0
       && govdeIcinde(appKaynak, 'pilCiz', 'ocv: !k && this.pilPtDestek ? [0, PIL_OCV_MS] : null'));
    {
      /* kayit kaynagi: KN_OCV noktalari -> ozet.ocv / r.ocv; DCIR kapali */
      let sira = 0;
      const ham = [];
      const ekle = (tur, ot, yuk) => { sira++; ham.push(Kx.kayitPaketle(tur, sira, ot, yuk)); return sira; };
      const kanal = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
      const kal = { normal: kanal(21), yuksek: kanal(201), i_ofset: 5, i_pga: 0.256, sont_ohm: 0.1, i_duzeltme: 1, sebeke_hz: 0, faz_kal_us: [0, 0] };
      const ot = ekle(Kx.T_BASLA, 1, Kx.baslaPaketle({ oturum_turu: 2, kal_bicim: 1, hiz_ms: 1000, unix_s: 1790300000, kart_ms: 100000,
        acilis: 3, surum: 'A3-PT1', kal, kal_no: 2 }));
      ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_PIL_AYAR, kart_ms: 100001, kesme_v: 3, ocv: 4.1, azami_s: 86400,
        dcir_aralik_ms: 0, dcir_ms: 200, kayit_hz: 1 }));
      const nk = (ms, b) => Kx.noktaPaketle({ kart_ms: 100000 + ms, n: 40, bayrak: b, v_ort_kod: 4.1 / 0.002625 + 12, v_min_kod: 0,
        v_maks_kod: 0, i_ort_kod: 5, i_min_kod: 0, i_maks_kod: 0, w_ort: 0, w_min: 0, w_maks: 0 });
      const ns = [1000, 2000, 3000, 4000, 5000, 6000, 7000].map((ms) => nk(ms, ms <= 5000 ? Kx.KN_OCV : 0));
      const y = new Uint8Array(4 + 36 * ns.length);
      ns.forEach((b, k) => y.set(b, 4 + 36 * k));
      ekle(Kx.T_NOKTA, ot, y);
      let n = 0;
      for (const h of ham) n += h.length;
      const bayt = new Uint8Array(n);
      let a0 = 0;
      for (const h of ham) { bayt.set(h, a0); a0 += h.length; }
      const kayitlar = Kx.akisCoz(bayt);
      const r = PL.pilKayitKur(Kx.oturumlariKur(kayitlar).get(ot), { disari: Dx, kayitlar, kimlik: 21 });
      ok('[!] PT2/PT5: kayit kaynagi — OCV bandi KN_OCV noktalarindan (ilk nokta hiz_ms once basladi: [0, 5000]), ozette de; PIL_AYAR dcir_aralik_ms 0 -> dcirKapali',
         !r.hata && JSON.stringify(r.ocv) === '[0,5000]' && JSON.stringify(r.ozet.ocv) === '[0,5000]' && r.ozet.dcirKapali === true,
         JSON.stringify({ ocv: r.ocv, dk: r.ozet.dcirKapali }));
      /* PT4: her ornek pil oturumu (BASLA hiz_ms 0, noktalar PIL_AYR_NOKTA_MS'de bir + AYRINTI) — kayit gorunumu */
      const KG = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
      const ot2 = ekle(Kx.T_BASLA, sira + 1, Kx.baslaPaketle({ oturum_turu: 2, kal_bicim: 1, hiz_ms: 0, unix_s: 1790300100, kart_ms: 200000,
        acilis: 3, surum: 'A3-PT1', kal, kal_no: 2 }));
      ekle(Kx.T_OLAY, ot2, Kx.olayPaketle({ tur: Kx.KO_PIL_AYAR, kart_ms: 200001, kesme_v: 3, ocv: 4.1, azami_s: 86400,
        dcir_aralik_ms: 300000, dcir_ms: 200, kayit_hz: 0 }));
      for (let p = 0; p < 5; p++) {
        ekle(Kx.T_AYRINTI, ot2, Kx.ayrintiPaketle({ ilk: p * 140, t0_ms: 200000 + p * 1400, t0_us: (200000 + p * 1400) * 1000, bayrak: 0,
          ornekler: Array.from({ length: 140 }, (_, j) => [1574, p * 140 + j < 500 ? 5 : 1200, j ? 2500 : 0, 0]) }));
      }
      const ns2 = [1000, 2000, 3000, 4000, 5000, 6000, 7000].map((ms) => Kx.noktaPaketle({ kart_ms: 200000 + ms, n: 400,
        bayrak: ms <= 5000 ? Kx.KN_OCV : 0, v_ort_kod: 1574, v_min_kod: 0, v_maks_kod: 0, i_ort_kod: 5, i_min_kod: 0, i_maks_kod: 0,
        w_ort: 0, w_min: 0, w_maks: 0 }));
      const y2 = new Uint8Array(4 + 36 * ns2.length);
      ns2.forEach((b2, k) => y2.set(b2, 4 + 36 * k));
      ekle(Kx.T_NOKTA, ot2, y2);
      let n2 = 0;
      for (const h of ham) n2 += h.length;
      const bayt2 = new Uint8Array(n2);
      let a2 = 0;
      for (const h of ham) { bayt2.set(h, a2); a2 += h.length; }
      const kayitlar2 = Kx.akisCoz(bayt2);
      const o2 = Kx.oturumlariKur(kayitlar2).get(ot2);
      const h2 = KG.grafikSerileri(o2, { kayitlar: kayitlar2 });
      const hn = KG.grafikSerileri(Kx.oturumlariKur(kayitlar2).get(ot), { kayitlar: kayitlar2 });
      ok('[!] PT4/PT7 (kayit gorunumu): her ornek pil oturumunun grafigi AYRINTI orneklerinden (700 ornek, 1/s noktalar degil), OCV bandi KN_OCV noktalarindan [0, 5000] (hiz_ms 0: PIL_AYR_NOKTA_MS); disari aktarmada ayrintili CSV de var; nokta pil oturumunda bant [0, 5000], ayrintili CSV yok',
         Kx.PIL_AYR_NOKTA_MS === 1000 && Dx.noktaAralikMs(o2) === 1000 && Dx.noktaBoslukMs(o2) === 2500
         && h2.tur === 'ayrinti' && h2.adet === 700 && JSON.stringify(h2.ocv) === '[[0,5000]]'
         && JSON.stringify(KG.ocvBantlari(h2)) === '[{"t0":0,"t1":5000,"metin":"OCV"}]'
         && KG.disariTurleri(o2).join() === 'pil_tr,pil_en,ayrinti_tr,ayrinti_en,ham'
         && hn.tur === 'nokta' && JSON.stringify(hn.ocv) === '[[0,5000]]' && KG.disariTurleri(Kx.oturumlariKur(kayitlar2).get(ot)).join() === 'pil_tr,pil_en,ham'
         && /bantlar: ocvBantlari\(this\._h\)/.test(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'), 'utf8')),
         JSON.stringify({ tur: h2.tur, adet: h2.adet, ocv: h2.ocv, hn: hn.ocv }));
    }
    /* demo karti: PT komutlari ve /pil alanlari, OCV evresi */
    const pr = SK.komut('Pr20');
    const prX = SK.komut('Pr7');
    const pd = SK.komut('Pd1');
    const pdX = SK.komut('Pd2');
    const pn = SK.komut('P');
    SK.komut('Pd0');
    SK.komut('Pr1');
    SK.komut('p0');
    const bas = SK.komut('p1');
    SK.pilTik(100000);
    SK.pilTik(100050);                    // 50 ms x 30 = 1.5 s: OCV evresinde
    const sOcv = SK.pilSayfa(0);
    const prSur = SK.komut('Pr5');
    SK.pilTik(100300);                    // +7.5 s: yuk acildi
    const sYuk = SK.pilSayfa(0);
    SK.komut('p0');
    const alan = (s, a) => (new RegExp('(?:^|\\n)' + a + '=([^\\n]*)').exec(s) || [])[1];
    ok('[!] PT (demo karti): Pr / Pd / P / BASLADI metinleri FIRMWARE`in; test surerken Pr reddi; /pil evre=ocv -> yuk, kayit_hz, dcir; OCV evresinde akim 0',
       pr[0] === '* pil kayit hizi 20 /s' && prX[0] === '! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali' && ino.includes(prX[0])
       && pd[0] === "* pil DCIR olcumu ACIK (5 dk'da bir 200 ms yuk kesilir)" && pdX[0] === '! Pd: Pd1 (ac) ya da Pd0 (kapat)' && ino.includes(pdX[0])
       && /· DCIR acik · hat 0 mOhm$/.test(pn[0]) && O(pn[0]).tur === 'kesme' && O(bas[0]).tur === 'basladi' && /; once 5 s yuksuz \(OCV\), sonra yuk$/.test(bas[0])
       && prSur[0] === '! P: pil testi suruyor — once p0' && ino.includes(prSur[0])
       && alan(sOcv, 'evre') === 'ocv' && alan(sOcv, 'kayit_hz') === '1.00' && alan(sOcv, 'dcir') === '0' && /\n1000,\d\.\d{4},0\.000000\n/.test(sOcv)
       && alan(sYuk, 'evre') === 'yuk', JSON.stringify({ pr, pd, pn, sOcv: sOcv.slice(0, 400) }));
  }
  /* ── (j) HT — HAT DIRENCI TELAFISI (tasarim/2026-10-07-pil-iyilestirme.md HT1–HT5) ──────────────────────────
     Kart pil testinin gerilimini V + I x R ile duzeltir; D satiri (Canli), olcum oturumlari, skop ve akim HAM.
     Panel: app.js yalniz `/pil` hat_mohm'u (pilHat) tutar ve Pil sekmesinin V kartini AYNI formulle duzeltir (R = 0
     iken HAM AYNEN); ozet + "ham" PilPt (sozluk_pil), duzeltici ekran/pil_hat.js + ortak/sozluk_hat.js ("Ayarla…"ya
     basinca iner). Kayit: KO_PIL_HAT (ortak/kayit.js + disari.hatDuzeltV) -> grafik / rapor / CSV pil kutuplarindan. */
  {
    const SH = require(path.join(KOK, 'ortak', 'src', 'sozluk_hat.js'));
    const SP = require(path.join(KOK, 'ortak', 'src', 'sozluk_pil.js'));
    const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
    const KG = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
    const O = al('pilSatirOlayi');
    const hatKaynak = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'pil_hat.js'), 'utf8');
    const sab = PL.PilPt.template;
    /* firmware metinleri + sinirlar */
    const htMetin = ['* pil hat direnci ', '! Ph: 0..1000 mOhm', 'F(" · hat ")', 'F("\\nhat_mohm=")', 'F("\\nv_ham=")'];
    const htYok = htMetin.filter((m) => !ino.includes(m));
    const azami = Number((/#define PIL_HAT_AZAMI_MOHM\s+(\d+)u/.exec(pilH) || [])[1]);
    const onay = O('* pil hat direnci 85 mOhm');
    const ret = O('! Ph: 0..1000 mOhm');
    ok('[!] HT1: `Ph` onay / ret satirlari, `P` satirinin ` · hat` eki ve /pil `hat_mohm=` `v_ham=` FIRMWARE`de; panel onayi `ayar` (satiriyla), reddi `ret` (satiriyla) sayar; ` · hat` ekli P satiri KESMEYI verir; azami 1000 mΩ pil_test.h ile ayni',
       htYok.length === 0 && onay.tur === 'ayar' && onay.s === '* pil hat direnci 85 mOhm' && ret.tur === 'ret' && ret.s === '! Ph: 0..1000 mOhm'
       && O('* pil kesme gerilimi 3.000 V · kayit 1.00 Hz · azami sure 24 saat · DCIR kapali · hat 85 mOhm').v === 3
       && azami === 1000 && SH.PIL_HAT_AZAMI_MOHM === azami,
       htYok.join(' | ') || JSON.stringify({ onay, ret }));
    /* elle giris: kartin pil_ph_ayir kurali (rakam, bastaki sifir yok, en cok 4 hane, <= 1000) */
    const G = SH.hatGiris;
    ok('[!] HT1: elle giris kartin pil_ph_ayir kuraliyla — 0 · 7 · 85 · 1000 gecer; 1001 · 050 · 00 · -5 · 8.5 · 85mΩ · bos · null REDDEDILIR (karta GITMEZ)',
       [['0', 0], ['7', 7], [' 85 ', 85], ['1000', 1000], [85, 85]].every(([x, n]) => G(x).mohm === n)
       && ['1001', '050', '00', '-5', '8.5', '85mΩ', '', '  ', null, undefined, '10000', {}].every((x) => G(x).hata === 'ht.hata_giris')
       && /static uint8_t pil_ph_ayir\(const char \*s, uint16_t \*mohm\)/.test(pilH) && /if \(s\[0\] == '0' && s\[1\]\) return 1u;/.test(pilH));
    /* R = 0 iken Pil sekmesinin V karti BIT BIT eskisi; R > 0: V + I x R (kartin pil_v_duzelt'i); I gecersizse — */
    const vKart = (hat, volt, amper, ads = 0) => {
      const u = ornek();
      u.bagli = true; u.pilDurum = 'CALISIYOR'; u.pilHat = hat; u.volt = volt; u.amper = amper; u.adsDurum = ads; u.gecmis = [1];
      return u.pilOkumalar[0].deger;
    };
    const ornekler = [[3.793, 1.128], [4.1, -0.002], [0, 0], [-0, 0.5], [12.3456, NaN], [3.7, Infinity], [1e-9, 2]];
    const eski = (v) => (Number.isFinite(v) ? v.toFixed(3) : '—');
    const sifirAyni = ornekler.every(([v, i]) => [undefined, null, '0', '', 'x'].every((h) => vKart(h, v, i) === eski(v)));
    const sifirGecersiz = [undefined, '0'].every((h) => vKart(h, 3.8, 1, 2) === '3.800' && vKart(h, 3.8, 1, 1) === '—');
    ok('[!] HT2 (R = 0 AYNI): hat_mohm yok / 0 / bozuk iken V karti BIT BIT eskisi (I NaN / sonsuz / gecersiz olsa bile; -0 dahil)',
       sifirAyni && sifirGecersiz, JSON.stringify(ornekler.map(([v, i]) => vKart('0', v, i))));
    ok('[!] HT2: R > 0 iken V karti pil kutuplarindan V + I x R (3.793 V, 1.128 A, 153 mΩ -> 3.966 V); I gecersizse "—"; kayit / son V (kartin duzeltilmis vson) dokunulmaz',
       vKart('153', 3.793, 1.128) === '3.966' && vKart('153', 3.793, 1.128, 2) === '—' && vKart('1000', 3.0, 0.5) === '3.500'
       && (() => { const u = ornek(); u.pilHat = '153'; u.pilDurum = 'BITTI'; u.pilKesmeBilinen = true; u.pilVson = 3.9;
         return u.pilOkumalar[0].deger === '3.900'; })()
       && Math.abs(SH.hatDuzelt(3.793, 1.128, 153) - Kx.pilVDuzelt(3.793, 1.128, 153)) === 0 && SH.hatDuzelt(4, NaN, 0) === 4);
    /* Canli / olcum / skop R'YI KULLANMAZ: pilHat yalniz pilOkumalar'da (+ veri + pilYokla); Canli'nin V'si HAM */
    const kod = yorumsuz(appKaynak);
    const hatYer = [...kod.matchAll(/pilHat\b/g)].length;
    const cu = ornek();
    cu.pilHat = '500'; cu.pilDurum = 'CALISIYOR';
    cu.satirIsle('D 3.7930 1.128000 4.27850 1.2340 0.0003428 45678 172 0');
    const ekranlar = ['canli.js', 'osiloskop.js', 'karsilastir.js', 'kayitlar.js'].map((a) => fs.readFileSync(path.join(ARAYUZ, 'ekran', a), 'utf8'));
    ok('[!] HT2: Canli / olcum / skop R`YI KULLANMAZ — app.js`te pilHat YALNIZ veri + pilYokla + pilOkumalar (3 yer); D satirindan sonra `volt` / `watt` HAM (3.793 V, 4.2785 W), Canli / Osiloskop / Karsilastirma / Kayitlar ekranlari hat_mohm / pilHat okumaz',
       hatYer === 3 && govdeIcinde(appKaynak, 'pilOkumalar', 'this.pilHat / 1e3') && govdeIcinde(appKaynak, 'pilYokla', 'this.pilHat = a.hat_mohm')
       && Math.abs(cu.volt - 3.793) < 1e-12 && Math.abs(cu.amper - 1.128) < 1e-12 && Math.abs(cu.watt - 4.2785) < 1e-12
       && ekranlar.every((k) => !/pilHat|hat_mohm|hatDuzelt|KO_PIL_HAT/.test(k)), `pilHat ${hatYer} yer`);
    /* PilPt ozet + ham: eski firmware (hat_mohm yok) -> HICBIR SEY; R 0 -> "telafi yok", ham yok; R > 0 + test -> ham */
    const kok = (o) => ({ dil: 'tr', pilHat: undefined, pilDurum: 'CALISIYOR', volt: 3.793, amper: 1.128, voltGecersiz: false,
      amperGecersiz: false, veriYok: false, ...o });
    const g0 = SP.htGorunum(kok({}));
    const g1 = SP.htGorunum(kok({ pilHat: '0' }));
    const g2 = SP.htGorunum(kok({ pilHat: '153' }));
    const g3 = SP.htGorunum(kok({ pilHat: '153', pilDurum: 'BITTI' }));
    ok('[!] HT5: eski firmware / USB (hat_mohm yok) -> ozet, "Ayarla…" ve "ham" YOK (Ph gonderilecek yer yok); R 0 -> "0 mΩ — telafi yok", ham yok; R > 0 + test -> "ham 3.793 V" (D satirinin HAM V`si); test bitince ham yok; sablon ve yerlesim',
       g0.hat === null && g0.ham === '' && g1.hat.deger === '0 mΩ — telafi yok' && g1.ham === '' && g1.hat.ac === 'Ayarla…'
       && g2.hat.deger === '153 mΩ' && g2.hat.r === 153 && g2.ham === 'ham 3.793 V' && g3.ham === ''
       && SP.htGorunum(kok({ pilHat: '153', dil: 'en' })).hat.etiket === 'Lead resistance'
       && SP.hatMohm('1001') === null && SP.hatMohm('85') === 85 && SP.hatMohm(85) === null
       && /<div v-else-if="g && kip === 'hat' && g\.hat" class="pil-form" data-pil="hat">/.test(sab)
       && /<component v-if="duz" :is="duz" :r="g\.hat\.r"><\/component>\s*<button v-else type="button" @click="duzAc" data-pil="hat-ac">/.test(sab)
       && /<div v-else-if="g && kip === 'ham' && g\.ham" class="alt-bilgi" data-pil="ham">\{\{ g\.ham \}\}<\/div>/.test(sab)
       && /<pil-pt v-if="o\.a === 'v'" kip="ham"><\/pil-pt>/.test(pm) && /\{\{ pl\.dcirSabit \}\}<\/p>\s*<pil-pt kip="hat"><\/pil-pt>/.test(pm),
       JSON.stringify({ g1: g1.hat, g2: g2.ham }));
    /* duzeltici TEMBEL: acilista, #/pil acilisinda ve Karsilastirmada YOK; yalniz PilPt'nin "Ayarla…"si indirir */
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const by = fs.existsSync(kunyeYolu) ? JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {} : {};
    const hatZ = ['ekran/pil_hat.js', ...iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'pil_hat.js')).map((g) => g.goruntu)];
    const pilAgacHt = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'pil.js')).map((g) => g.goruntu);
    const hatBayt = ['ekran/pil_hat.js', 'ortak/sozluk_hat.js'].reduce((n, a) => n + (by[a] || NaN), 0);
    ok('[!] HT5 (butce): duzeltici (ekran/pil_hat.js + ortak/sozluk_hat.js) acilis grafiginde, pil.js`in statik agacinda ve app.js`te YOK; YALNIZ PilPt "Ayarla…" ile DINAMIK; kendi agaci yalniz sozluk_hat + sozluk; <= 6 KB gzip (kunyede)',
       /import\('\.\/pil_hat\.js'\)/.test(yorumsuz(pilKaynak)) && !pilAgacHt.includes('ekran/pil_hat.js') && !pilAgacHt.includes('ortak/sozluk_hat.js')
       && !iceAktarmaGrafigi().map((x) => x.goruntu).some((x) => /pil_hat|sozluk_hat/.test(x)) && !/pil_hat|sozluk_hat/.test(kod)
       && hatZ.slice(1).sort().join() === 'ortak/sozluk.js,ortak/sozluk_hat.js' && hatBayt > 0 && hatBayt <= 6144
       && /from '\/ortak\/sozluk_hat\.js'/.test(hatKaynak) && !/sozluk_pil/.test(yorumsuz(hatKaynak)),
       `${hatZ.join(' ')} · ${hatBayt} B`);
    /* multimetre: R_yeni = R_eski + (V_mm − V_gosterilen) / I, 0…1000'e kirpilir; I >= 0.1 A */
    const Or = SH.hatOneri;
    ok('[!] HT5: multimetre formulu R_yeni = R_eski + (V_mm − V_gosterilen) / I (mΩ, yuvarlanir): 50 mΩ, 3.9475 V gosterilen, 3.976 V multimetre, 0.95 A -> 80 mΩ; 0…1000`e KIRPILIR (kirpildi isaretli); I < 0.1 A ya da sayi olmayan -> null',
       Or(50, 3.976, 3.9475, 0.95).yeni === 80 && Or(50, 3.976, 3.9475, 0.95).kirpildi === false
       && Or(0, 3.966, 3.793, 1.128).yeni === 153 && Or(900, 5.0, 3.8, 1.0).yeni === 1000 && Or(900, 5.0, 3.8, 1.0).kirpildi === true
       && Or(900, 5.0, 3.8, 1.0).ham === 2100 && Or(10, 3.0, 3.5, 1.0).yeni === 0 && Or(10, 3.0, 3.5, 1.0).ham === -490
       && Or(50, 3.976, 3.9475, 0.099) === null && Or(50, NaN, 3.9, 1) === null && Or(50, 3.9, 3.9, Infinity) === null
       && SH.mmGiris('3,966') === 3.966 && SH.mmGiris('3.9660') === 3.966 && ['', '0', '-3', '39', 'abc', '3,9,6', null].every((x) => SH.mmGiris(x) === null));
    /* akis (sahte $root): elle Ph, multimetre (tek onay), ret, sessizlik, bagli degil, kosul */
    const kokAkis = (yanit, o = {}) => {
      const giden = [];
      const u = { dil: 'tr', bagli: true, pilHat: '50', pilDurum: 'CALISIYOR', volt: 3.9, amper: 0.95, voltGecersiz: false,
        amperGecersiz: false, veriYok: false, pilBaslatiliyor: false, ...o,
        async pilAyarGonder(c) { giden.push(c); return yanit(c); } };
      return { u, giden };
    };
    const y0 = () => ({ hatGiris: '', mmGiris: '', oneri: null, mesgul: false, sonuc: null });
    const kabul = (c) => ({ tur: 'ayar', s: `* pil hat direnci ${c.slice(2)} mOhm` });
    SONRA.push(async () => {
      const a = kokAkis(kabul);
      const y = y0();
      y.hatGiris = '050';
      const r0 = await SH.hatIslem(a.u, y, 'yaz', 50);
      const s0 = y.sonuc && y.sonuc.a;
      y.hatGiris = '120';
      const r1 = await SH.hatIslem(a.u, y, 'yaz', 50);
      const m1 = SH.hatGorunum(a.u, y).sonuc;
      y.mmGiris = '3,976';
      await SH.hatIslem(a.u, y, 'oner', 50);
      const oneri = SH.hatGorunum(a.u, y).oneri;
      const gitmedi = a.giden.length;
      const r2 = await SH.hatIslem(a.u, y, 'gonder', 50);
      ok('[!] HT5: elle `Ph` — gecersiz (050) GITMEZ, sebep yazilir; 120 -> `Ph120`, kart onayi -> "Kart onayladı" ve app`in pilHat`i hemen 120; multimetre (3,976 V, gosterilen = V + I x R = 3.9475 V, 0.95 A) -> oneri 80 mΩ, TEK onaydan once GITMEZ, "Gönder" -> `Ph80`',
         r0 === false && s0 === 'ht.hata_giris' && r1 === true && a.giden[0] === 'Ph120' && m1 === 'Kart onayladı: hat direnci 120 mΩ.'
         && a.u.pilHat === '80' && gitmedi === 1 && /^Yeni hat direnci 80 mΩ \(şimdi 50 mΩ\): gösterilen 3\.947 V, multimetre 3\.976 V, akım 0\.950 A\. Karta gönderilsin mi\?$/.test(oneri)
         && r2 === true && a.giden.join() === 'Ph120,Ph80' && y.oneri === null && y.mmGiris === '',
         JSON.stringify({ giden: a.giden, oneri, m1 }));
      const b = kokAkis(() => ({ tur: 'ret', s: '! Ph: 0..1000 mOhm' }));
      const yb = y0();
      yb.hatGiris = '900';
      const rb = await SH.hatIslem(b.u, yb, 'yaz', 50);
      const c = kokAkis(() => ({}));
      const yc = y0();
      yc.hatGiris = '70';
      const rc = await SH.hatIslem(c.u, yc, 'yaz', 50);
      const d = kokAkis(() => ({ tur: 'ayar', s: '* pil kayit hizi 20 /s' }));
      const yd = y0();
      yd.hatGiris = '70';
      const rd = await SH.hatIslem(d.u, yd, 'yaz', 50);
      const e = kokAkis(kabul, { bagli: false });
      const ye = y0();
      ye.hatGiris = '70';
      const re = await SH.hatIslem(e.u, ye, 'yaz', 50);
      ok('[!] HT5: kartin reddi OLDUGU GIBI ("Kart reddetti: ! Ph: …"), sessizlik ve BASKA onay (Pr) "yanıt vermedi" (pilHat DEGISMEZ), bagli degilken GITMEZ',
         rb === false && SH.hatGorunum(b.u, yb).sonuc === 'Kart reddetti: ! Ph: 0..1000 mOhm' && b.u.pilHat === '50'
         && rc === false && yc.sonuc.a === 'ht.yanitsiz' && c.u.pilHat === '50' && rd === false && yd.sonuc.a === 'ht.yanitsiz' && d.u.pilHat === '50'
         && re === false && e.giden.length === 0 && ye.sonuc.a === 'ht.bagli_degil' && SH.hatGorunum(b.u, yb).sonucHata === true);
      const f1 = kokAkis(kabul, { amper: 0.05 });
      const f2 = kokAkis(kabul, { pilDurum: 'BITTI' });
      const f3 = kokAkis(kabul, { amperGecersiz: true });
      const kosul = [];
      for (const f of [f1, f2, f3]) {
        const yf = y0();
        yf.mmGiris = '3.9';
        await SH.hatIslem(f.u, yf, 'oner', 50);
        kosul.push(yf.oneri === null && yf.sonuc.a === 'ht.kosul' && f.giden.length === 0 && SH.hatGorunum(f.u, yf).mmAcik === false);
      }
      const yk = y0();
      yk.mmGiris = 'abc';
      await SH.hatIslem(kokAkis(kabul).u, yk, 'oner', 50);
      ok('[!] HT5: "Multimetreyle düzelt" yalniz test surerken ve I >= 0.1 A (0.05 A / bitmis test / akim gecersiz -> kapali, oneri YOK, gonderim YOK); gecersiz multimetre degeri sebebiyle reddedilir; sablonda alan etiketli, dugme mmAcik`a bagli',
         kosul.every(Boolean) && yk.sonuc.a === 'ht.hata_mm' && yk.oneri === null
         && SH.hatGorunum(kokAkis(kabul).u, y0()).mmAcik === true
         && /<label for="pil-mm">\{\{ g\.mm \}\}<\/label>/.test(hatKaynak) && /:disabled="!g\.mmAcik \|\| g\.mesgul" @click="ht\('oner'\)"/.test(hatKaynak)
         && /<label for="pil-hat">\{\{ g\.giris \}\}<\/label>/.test(hatKaynak) && /@click="ht\('gonder'\)"/.test(hatKaynak),
         JSON.stringify(kosul));
    });
    /* /pil: hat_mohm -> pilHat; eski /pil (alan yok) -> undefined (ozellik gizli) */
    SONRA.push(async () => {
      const eskiF = sandbox.fetch;
      const bas = (ek) => ['durum=CALISIYOR', 'hata=-', 'mah=0.0000', 'wh=0.000000', 'ocv=4.1100', 'vson=4.1100', 'kesme=3.000',
        'dcir_ani=0.00000', 'dcir_otr=0.00000', 'dcir_n=0', 'sira=0', 'ilk_sira=0', 'kalan=0', 'coulomb=0.000',
        'evre=yuk', 'kayit_hz=1.00', 'dcir=0', ...ek, '--'].join(String.fromCharCode(10)) + String.fromCharCode(10);
      const yeni = ornek();
      yeni.bagli = true; yeni.tasiyiciAdi = 'akis'; yeni.bagliTasiyici = 'akis';
      sandbox.fetch = async () => ({ ok: true, status: 200, text: async () => bas(['hat_mohm=153', 'v_ham=3.7930']) });
      await yeni.pilYokla();
      const eskiK = ornek();
      eskiK.bagli = true; eskiK.tasiyiciAdi = 'akis'; eskiK.bagliTasiyici = 'akis';
      sandbox.fetch = async () => ({ ok: true, status: 200, text: async () => bas([]) });
      await eskiK.pilYokla();
      sandbox.fetch = eskiF;
      ok('[!] HT2/HT5: /pil hat_mohm=153 -> pilHat "153" (ozet + V karti); A3-PT3 oncesi /pil (alan yok) -> pilHat undefined: ozellik GIZLI, V karti HAM',
         yeni.pilHat === '153' && eskiK.pilHat === undefined && SP.htGorunum({ ...kok({}), pilHat: eskiK.pilHat }).hat === null,
         JSON.stringify({ yeni: yeni.pilHat, eski: eskiK.pilHat }));
    });
    /* kayit: KO_PIL_HAT -> egri / grafik / ozet pil kutuplarindan; olay yoksa HAM AYNEN; olcum oturumunda HIC */
    {
      let sira = 0;
      const ham = [];
      const ekle = (tur, ot, yuk) => { sira++; ham.push(Kx.kayitPaketle(tur, sira, ot, yuk)); return ot; };
      const kanal = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
      const kal = { normal: kanal(21), yuksek: kanal(201), i_ofset: 5, i_pga: 0.256, sont_ohm: 0.1, i_duzeltme: 1, sebeke_hz: 0, faz_kal_us: [0, 0] };
      const nk = (ms) => Kx.noktaPaketle({ kart_ms: ms, n: 40, bayrak: 0, v_ort_kod: 1500, v_min_kod: 1490, v_maks_kod: 1510,
        i_ort_kod: 30000, i_min_kod: 29000, i_maks_kod: 31000, w_ort: 0, w_min: 0, w_maks: 0 });   // ~2.3 A: I^2 x R Wh'de gorunur
      const oturumKur = (ot, tur, olaylar) => {
        ekle(Kx.T_BASLA, ot, Kx.baslaPaketle({ oturum_turu: tur, kal_bicim: 1, hiz_ms: 1000, unix_s: 1790300000,
          kart_ms: 100000, acilis: 3, surum: 'A3-PT3', kal, kal_no: 2 }));
        for (const [ms, mohm] of olaylar) ekle(Kx.T_OLAY, ot, Kx.olayPaketle({ tur: Kx.KO_PIL_HAT, kart_ms: ms, hat_mohm: mohm }));
        const ns = [101000, 102000, 103000, 104000].map(nk);
        const y = new Uint8Array(4 + 36 * ns.length);
        ns.forEach((b, k) => y.set(b, 4 + 36 * k));
        ekle(Kx.T_NOKTA, ot, y);
        return ot;
      };
      const otHat = oturumKur(31, 2, [[100000, 50], [102500, 80]]);
      const otYok = oturumKur(32, 2, []);
      const otOlc = oturumKur(33, 1, [[100000, 50]]);
      let n = 0;
      for (const h of ham) n += h.length;
      const bayt = new Uint8Array(n);
      let a0 = 0;
      for (const h of ham) { bayt.set(h, a0); a0 += h.length; }
      const kayitlar = Kx.akisCoz(bayt);
      const ots = Kx.oturumlariKur(kayitlar);
      const s = Dx.noktaSerileri(ots.get(otHat), { kayitlar });
      const bek = Array.from(s.vOrt, (v, k) => Kx.pilVDuzelt(v, s.iOrt[k], [50, 50, 80, 80][k]));
      const r = PL.pilKayitKur(ots.get(otHat), { disari: Dx, kayitlar, kimlik: 21 });
      const rYok = PL.pilKayitKur(ots.get(otYok), { disari: Dx, kayitlar, kimlik: 21 });
      const h = KG.grafikSerileri(ots.get(otHat), { kayitlar });
      const hYok = KG.grafikSerileri(ots.get(otYok), { kayitlar });
      const hOlc = KG.grafikSerileri(ots.get(otOlc), { kayitlar });
      const vSeri = (x) => x.seriler.find((q) => q.ad === 'V');
      const sYok = Dx.noktaSerileri(ots.get(otYok), { kayitlar });
      const sOlc = Dx.noktaSerileri(ots.get(otOlc), { kayitlar });
      const ayni = (p, q) => p.length === q.length && Array.from(p).every((x, k) => Object.is(x, q[k]));
      const okuma = KG.okumaHesapla(h, h.t[0], h.t[3]);
      const gor = KG.gorunurluk(h.seriler, { v: true, sag: 'akim', zarf: true }).find((q) => q.ad === 'V ham');
      ok('[!] HT3 (kayit): KO_PIL_HAT (12 B, u32 hat_mohm — kayit_bicim.h ile ayni) -> her nokta o ANDA gecerli R ile V + I x R (50 mΩ, 102.5 s`den sonra 80 mΩ); Pil sekmesinin kayit egrisi + kayit gorunumu grafigi duzeltilmis, "V ham" yalniz okumada (cizilmez); ozet {ilk 50, son 80, 1 kez}',
         Kx.olayPaketle({ tur: Kx.KO_PIL_HAT, kart_ms: 1, hat_mohm: 85 }).length === 12 && /#define KO_PIL_HAT\s+6u/.test(fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_bicim.h'), 'utf8'))
         && ayni(r.seri.v, bek) && ayni(vSeri(h).y, bek) && ayni(h.seriler.find((q) => q.ad === 'V ham').y, s.vOrt)
         && gor && gor.gizli === true && okuma.vHam && Object.is(okuma.vHam.a, s.vOrt[0])
         && JSON.stringify(r.ozet.hat) === '{"ilk":50,"son":80,"degisim":1}' && JSON.stringify(h.hat) === '{"ilk":50,"son":80,"degisim":1}'
         && KG.hatYazi(h.hat) === '80 mΩ (1 kez değişti; başta 50 mΩ)' && KG.hatYazi({ ilk: 50, son: 50, degisim: 0 }, 'en') === '50 mΩ',
         JSON.stringify({ bek, hat: h.hat }));
      const wBek = Array.from(s.wOrt, (w, k) => Kx.pilWDuzelt(w, s.iOrt[k], [50, 50, 80, 80][k]));
      const wSeri = (x) => x.seriler.find((q) => q.ad === 'W');
      const okW = KG.okumaHesapla(h, h.t[0], h.t[3]).enerji;
      const okWY = KG.okumaHesapla(hYok, hYok.t[0], hYok.t[3]).enerji;
      ok('[!] HT2 (W / Wh, butunlestirici karari): KO_PIL_HAT`li PIL oturumunda W pilin VERDIGI guc W + I^2 x R (kartin pil Wh kurali, kayit.js pilWDuzelt); imlec Wh`i de ondan (artar), mAh AYNI; olaysiz pil ve OLCUM oturumunda W HAM AYNEN',
         ayni(wSeri(h).y, wBek) && !ayni(wBek, s.wOrt) && okW.wh > okWY.wh && okW.mah === okWY.mah
         && ayni(wSeri(hYok).y, sYok.wOrt) && ayni(wSeri(hOlc).y, sOlc.wOrt)
         && Kx.pilWDuzelt(3.0, 1.0, 200) === 3.2 && Kx.pilWDuzelt(3.0, NaN, 0) === 3.0 && Object.is(Kx.pilWDuzelt(-0, 2, 0), -0),
         JSON.stringify({ wBek, wh: okW.wh, whY: okWY.wh }));
      ok('[!] HT3 (R = 0 / olay yok AYNI): olaysiz pil oturumunda egri, grafik, ozet ve okuma HAM AYNEN (V ham serisi YOK, hat null); OLCUM oturumuna (olay olsa bile) telafi UYGULANMAZ',
         ayni(rYok.seri.v, sYok.vOrt) && rYok.ozet.hat === null && ayni(vSeri(hYok).y, sYok.vOrt) && !hYok.seriler.some((q) => q.ad === 'V ham')
         && hYok.hat === null && ayni(vSeri(hOlc).y, sOlc.vOrt) && hOlc.hat === null && !hOlc.seriler.some((q) => q.ad === 'V ham')
         && KG.okumaHesapla(hYok, hYok.t[0], hYok.t[3]).vHam === null);
      const cH = Dx.pilCsv(ots.get(otHat), { ...Dx.BICIM_EXCEL_TR, kayitlar });
      const cY = Dx.pilCsv(ots.get(otYok), { ...Dx.BICIM_EXCEL_TR, kayitlar });
      const satir = cH.split('\r\n');
      const sY = cY.split('\r\n');
      ok('[!] HT3 (CSV): KO_PIL_HAT varsa SONA `v_pil_V;w_pil_W;hat_mohm` (EN: v_cell_V, p_cell_W, lead_mohm), enerji_Wh pilin verdigi gucten (Wh artar); HAM V/W sutunlari AYNEN; olay yoksa baslik KOLONLAR.pil`in kendisi (yeni sutun YOK)',
         satir[0].endsWith(';not;v_pil_V;w_pil_W;hat_mohm') && sY[0].endsWith(';not') && satir[0].startsWith(sY[0])
         && satir[1].endsWith(';50') && satir[4].endsWith(';80') && satir[1].split(';').length === sY[1].split(';').length + 3
         && (() => { const j = sY[0].split(';').indexOf('enerji_Wh'); const w = sY[0].split(';').indexOf('w_ort_W');
           const a = satir[4].split(';'); const b = sY[4].split(';');
           return j > 0 && w > 0 && Number(a[j].replace(',', '.')) > Number(b[j].replace(',', '.')) && a[w] === b[w]; })()
         && Dx.pilCsv(ots.get(otHat), { ...Dx.BICIM_EN, kayitlar }).split('\r\n')[0].endsWith(',note,v_cell_V,p_cell_W,lead_mohm'),
         satir[0].slice(-60));
      const rp = require(path.join(KOK, 'ortak', 'src', 'rapor.js')).oturumRaporu(ots.get(otHat), { kayitlar });
      const rpY = require(path.join(KOK, 'ortak', 'src', 'rapor.js')).oturumRaporu(ots.get(otYok), { kayitlar });
      ok('[!] HT3 (rapor): gerilim ve GUC istatistigi + Wh pilden (V + I x R, W + I^2 x R), HAM `vHam` / `wHam`da, `pil.hat` ozeti; mAh HAM (iki oturumda ayni); olaysiz oturumda alanlar YOK',
         Math.abs(rp.istatistik.v.ort - bek.reduce((x, y) => x + y, 0) / 4) < 1e-12 && rp.istatistik.vHam && Math.abs(rp.istatistik.vHam.ort - rpY.istatistik.v.ort) < 1e-12
         && Math.abs(rp.istatistik.w.ort - wBek.reduce((x, y) => x + y, 0) / 4) < 1e-12 && Math.abs(rp.istatistik.wHam.ort - rpY.istatistik.w.ort) < 1e-12
         && JSON.stringify(rp.pil.hat) === '{"ilk":50,"son":80,"degisim":1}' && !('vHam' in rpY.istatistik) && !('wHam' in rpY.istatistik) && !('hat' in rpY.pil)
         && rp.enerji.wh > rpY.enerji.wh && rp.enerji.mah === rpY.enerji.mah);
    }
    /* demo karti: Ph (test surerken de), P eki, /pil alanlari, duzeltilmis vson */
    SK.komut('p0');
    const p1 = SK.komut('Ph150');
    const pX = SK.komut('Ph1001');
    const p0X = SK.komut('Ph050');
    const pP = SK.komut('P');
    SK.komut('p1');
    SK.pilTik(200000);
    SK.pilTik(200400);                    // 400 ms x 30 = 12 s: yuk acik
    const sur = SK.komut('Ph80');
    SK.pilTik(200420);
    const sayfaHt = SK.pilSayfa(0);
    SK.komut('p0');
    SK.komut('Ph0');
    const alanHt = (a) => (new RegExp('(?:^|\\n)' + a + '=([^\\n]*)').exec(sayfaHt) || [])[1];
    const vHam = Number(alanHt('v_ham'));
    const vson = Number(alanHt('vson'));
    ok('[!] HT (demo karti): `Ph` onay / ret metinleri FIRMWARE`in, test SURERKEN de kabul; `P` satiri ` · hat <n> mOhm` ile biter; /pil sonda hat_mohm, v_ham; vson = v_ham + I x R (pil kutuplari)',
       p1[0] === '* pil hat direnci 150 mOhm' && pX[0] === '! Ph: 0..1000 mOhm' && p0X[0] === pX[0] && ino.includes(pX[0])
       && / · hat 150 mOhm$/.test(pP[0]) && sur[0] === '* pil hat direnci 80 mOhm'
       && /\ndcir=\d\nhat_mohm=80\nv_ham=\d+\.\d{4}\n--\n/.test(sayfaHt) && vson > vHam && vson - vHam < 0.2,
       JSON.stringify({ p1, pP, sur, vHam, vson }));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   29. KARSILASTIRMA (3G — alt proje 3, KR1-KR8; uygulama kararlari KU1-KU10)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3G kararlari". Burada:
   (a) KABLOLAMA: yedinci gorunum (KR6 seritte), tembel modul (Kayitlar zincirine
       en cok iki dosya ekler), `#/karsilastir/...` rotasi ve adres ezilmiyor.
   (b) ROTA (KR1): coz/yaz birbirinin tersi; en cok 6; kip/kanal sorguda (KU2).
   (c) SECIM (KR1/KR5): secilebilir() — kartta / osiloskop / bos / dolu sebepleri;
       Kayitlar bileseni: kutu baglantinin DISINDA, kimlik HER ZAMAN adreste.
   (d) X KIPLERI (KR3) GERCEK ortak/kayit.js ile paketlenip cozulen oturumlarda:
       baslangic = K1 ekseni (tahmini isaretli), saat = unix (saatsiz / kismi /
       geri -> disarida + sebep), mah = PU9 (pil degil / bosluk / eksi -> disarida).
   (e) OKUMA (KR4/KU4): kayit BASINA, bagimsiz dongulerle; imlec disarida -> "—".
   (f) BIRLESIK CSV (KR7): sutunlar kayit basina, satir = ornek sirasi, ara deger YOK.
   (g) RENK (KR2/KU3): yalniz tema belirteclerinden, 3 gorunumde kart'a >= 3:1 ve
       renk korlugu benzetiminde ayni desenli her cift ayri (CIELAB dE >= 15).
   Gercek tarayici (IndexedDB, CDP fare, indirme, uc gorunum, 390 px):
   tarayici_karsilastir.py (T3G).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 29. Karsilastirma (3G) ---');
{
  const html = yorumsuz(htmlKaynak);
  const css = cssOku();
  const al = (ad) => vm.runInContext(ad, sandbox);
  const KR = require(path.join(ARAYUZ, 'ekran', 'karsilastir.js'));
  const KLx = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
  const KGx = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
  const PLx = require(path.join(ARAYUZ, 'ekran', 'pil.js'));
  const Kx = require(path.join(KOK, 'ortak', 'src', 'kayit.js'));
  const Dx = require(path.join(KOK, 'ortak', 'src', 'disari.js'));
  const SZx = sozlukTum();
  const GRx = require(path.join(KOK, 'ortak', 'src', 'grafik.js'));
  const krKaynak = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'karsilastir.js'), 'utf8');
  const klKaynak = fs.readFileSync(path.join(ARAYUZ, 'ekran', 'kayitlar.js'), 'utf8');

  /* ── (a) KABLOLAMA ──────────────────────────────────────────────── */
  {
    const G = al('GORUNUMLER');
    const ids = G.map((g) => g.id);
    const g = G.find((x) => x.id === 'karsilastir');
    ok('[!] KR6: Karsilastirma seritte, Kayitlar`in hemen ardinda; adi ve alt yazisi sozlukte (tr + en)',
       !!g && ids.indexOf('karsilastir') === ids.indexOf('kayitlar') + 1
       && [g.ad, g.alt].every((a) => a in SZx.SOZLUK && SZx.SOZLUK[a].tr && SZx.SOZLUK[a].en)
       && SZx.SOZLUK['kb.karsilastir'].tr === 'Karşılaştırma', ids.join(' '));
    const km = html.match(/<main class="gorunum" v-show="gorunum === 'karsilastir'">([\s\S]*?)<\/main>/);
    ok('[!] index.html: Karsilastirma gorunumu v-show, ekran ILK acilista (v-if karsilastirAcik); kartAdres + etkin veriliyor',
       !!km && /<karsilastir-ekran v-if="karsilastirAcik"/.test(km[1]) && km[1].includes(':kart-adres="kartAdres"')
       && km[1].includes(":etkin=\"gorunum === 'karsilastir'\""), km ? 'bulundu' : 'yok');
    const b = secenekler.components && secenekler.components['karsilastir-ekran'];
    const sec = b && b.yukleyici && typeof b.yukleyici === 'object' ? b.yukleyici : {};
    ok('[!] karsilastir-ekran ASENKRON bilesen: ./ekran/karsilastir.js`i istiyor (KarsilastirEkrani); inmezse sebep + care',
       !!b && b.__asenkron === true
       && /import\('\.\/ekran\/karsilastir\.js'\)\.then\(\(m\) => m\.KarsilastirEkrani\)/.test(String(sec.loader))
       && typeof KR.KarsilastirEkrani === 'object' && typeof KR.KarsilastirEkrani.template === 'string'
       && !!sec.errorComponent && /class="hata"[^>]*>[^<]*yüklenemedi[^<]*yenileyin/.test(sec.errorComponent.template || ''),
       String(sec.loader));
    const statik = iceAktarmaGrafigi().map((x) => x.goruntu);
    ok('[!] Karsilastirma modulu ACILISTA inmiyor (statik ice aktarma grafiginde yok)',
       !statik.some((x) => /ekran\/(karsilastir|kayitlar|pil)\.js$/.test(x)), statik.join(' '));
    const hashten = al('hashtenGorunum');
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('[!] hashtenGorunum: #/karsilastir, #/karsilastir/12@7,15, #/karsilastir?x=saat -> karsilastir; #/karsilastirx -> canli',
       dene('#/karsilastir') === 'karsilastir' && dene('#/karsilastir/12@7,15') === 'karsilastir'
       && dene('#/karsilastir?x=saat&k=I') === 'karsilastir' && dene('#/karsilastir/3?x=mah') === 'karsilastir'
       && dene('#/karsilastirx') === 'canli');
    const w = secenekler.watch.gorunum;
    let yazilan = [];
    sandbox.history = { replaceState: (a, b2, h) => yazilan.push(h) };
    const sahte = { $nextTick() {}, grafikCiz() {}, osiloCiz() {}, karsilastirAcik: false };
    sandbox.location = { hash: '#/karsilastir/12@7,15@7' };
    w.call(sahte, 'karsilastir');
    sandbox.location = { hash: '' };
    ok('[!] watch.gorunum secimli adresi (#/karsilastir/12@7,…) EZMIYOR ve ekrani kuruyor; varsayilan acilista kurulmuyor',
       yazilan.length === 0 && sahte.karsilastirAcik === true && secenekler.data().karsilastirAcik === false,
       `yazilan=${yazilan.join()} acik=${sahte.karsilastirAcik}`);
    delete sandbox.location;
    delete sandbox.history;
    /* KU1: Kayitlar'dan gelinince zincirin geri kalani zaten inmis: Karsilastirma YALNIZ kendi
       modulunu ve pil.js'i (PU9 mAh ekseni) ekler. Bayt `_fs.json`dan (karta yazilan gzip). */
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const agac = (ad) => [ad, ...iceAktarmaGrafigi(path.join(ARAYUZ, ad)).map((x) => x.goruntu)];
    const klAgac = new Set(agac('ekran/kayitlar.js'));
    const ek = agac('ekran/karsilastir.js').filter((x) => !statik.includes(x) && !klAgac.has(x));
    const by = fs.existsSync(kunyeYolu) ? JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {} : {};
    const ekBayt = ek.reduce((n, a) => n + (Number.isFinite(by[a]) ? by[a] : NaN), 0);
    ok('[!] KU1: Karsilastirma Kayitlar zincirine YALNIZ ekran/karsilastir.js + ekran/pil.js ekler, gzip <= 20 KB (kunyede)',
       ek.slice().sort().join(' ') === 'ekran/karsilastir.js ekran/pil.js' && ekBayt > 0 && ekBayt <= 20 * 1024,
       `${ek.join(' ')} · ${ekBayt} B`);
  }

  /* ── (b) ROTA ───────────────────────────────────────────────────── */
  {
    const C = KR.karsilastirRotaCoz;
    const Y = KLx.karsilastirRotaYaz;
    const r1 = C('#/karsilastir/12@7,15,3@7,0,x,12@7?x=saat&k=I');
    ok('[!] KR1: rota cozucu — (no, kimlik) ciftleri, tekrar bir kez, gecersiz parca sayilir; kip ve kanal sorgudan',
       JSON.stringify(r1.secim) === '[{"oturum":12,"kimlik":7},{"oturum":15,"kimlik":null},{"oturum":3,"kimlik":7}]'
       && r1.kip === 'saat' && r1.kanal === 'I' && r1.gecersiz === 2 && r1.fazla === 0, JSON.stringify(r1));
    const r2 = C('#/karsilastir/1,2,3,4,5,6,7,8?x=bozuk&k=Z');
    ok('[!] KR1: en cok KR_AZAMI (6) kayit — fazlasi atilir ve SAYILIR; bilinmeyen kip/kanal varsayilana duser',
       KLx.KR_AZAMI === 6 && r2.secim.length === 6 && r2.fazla === 2 && r2.kip === 'baslangic' && r2.kanal === 'V'
       && C('#/karsilastir').secim.length === 0 && C('#/kayitlar').secim.length === 0, JSON.stringify(r2));
    ok('[!] KU2: adres yazici varsayilan kip/kanali YAZMAZ, digerlerini sorguya yazar; kimlik yoksa @ yok',
       Y({ secim: [{ oturum: 12, kimlik: 7 }, { oturum: 15, kimlik: null }] }) === '#/karsilastir/12@7,15'
       && Y({ secim: [{ oturum: 12, kimlik: 7 }], kip: 'saat', kanal: 'I' }) === '#/karsilastir/12@7?x=saat&k=I'
       && Y({ secim: [{ oturum: 3, kimlik: 1 }], kip: 'mah' }) === '#/karsilastir/3@1?x=mah' && Y({}) === '#/karsilastir');
    let ters = true;
    let ornek_ = '';
    for (let n = 0; n < 200 && ters; n++) {
      const secim = [];
      for (let k = 0; k < 1 + (n % 6); k++) {
        const o = { oturum: 1 + ((n * 37 + k * 11) % 500), kimlik: (n + k) % 3 ? (n * 7 + k) % 40 : null };
        if (!secim.some((s) => s.oturum === o.oturum && s.kimlik === o.kimlik)) secim.push(o);
      }
      const kip = KR.KIPLER[n % 3];
      const kanal = ['V', 'I', 'W'][(n >> 1) % 3];
      const a = Y({ secim, kip, kanal });
      const r = C(a);
      ters = JSON.stringify(r.secim) === JSON.stringify(secim) && r.kip === kip && r.kanal === kanal && !r.gecersiz && !r.fazla;
      ornek_ = a;
    }
    ok('[!] KR1: coz(yaz(x)) = x — 200 rastgele secim / kip / kanal', ters, ornek_);
  }

  /* ── (c) SECIM ──────────────────────────────────────────────────── */
  {
    const S = KLx.secilebilir;
    const sat = (o) => ({ yerelde: true, tur: 'olcum', nokta: 5, ...o });
    ok('[!] KR5: yalniz kartta olan oturum SECILEMEZ ("once esitleyin"); osiloskop gunlugu ve noktasiz kopya da (sebepleriyle)',
       S(sat({ yerelde: false })).sebep === 'kr.sec_kartta' && S(sat({ tur: 'skop' })).sebep === 'kr.sec_skop'
       && S(sat({ tur: 'bilinmeyen' })).sebep === 'kr.sec_bos' && S(sat({ nokta: 0 })).sebep === 'kr.sec_bos'
       && S(sat({})).uygun === true && S(sat({ tur: 'ayrinti' })).uygun && S(sat({ tur: 'pil' })).uygun
       && /önce eşitleyin/.test(SZx.ceviri('kr.sec_kartta', 'tr')));
    ok('[!] KR1: 6 secimden sonra yeni satir eklenemez (sebep "en çok 6"); secili satir her zaman cikarilabilir',
       S(sat({}), { adet: 6 }).sebep === 'kr.sec_dolu' && S(sat({}), { adet: 5 }).uygun
       && S(sat({}), { adet: 6, seciliMi: true }).uygun);
    /* Bilesen: sahte `this` ile GERCEK computed/methods */
    const E = KLx.KayitlarEkrani;
    const satirlar = Array.from({ length: 8 }, (_, k) => ({ anahtar: `3:${k + 1}`, kimlik: 3, oturum: k + 1, tur: k === 7 ? 'skop' : 'olcum',
      nokta: 4, yerelde: true, ad: k === 0 ? 'Akü' : null }));
    satirlar.push({ anahtar: '3:20', kimlik: 3, oturum: 20, tur: 'olcum', nokta: 9, yerelde: false, ad: null });
    const u = { secim: [], satirlar, dil: 'tr' };
    for (const [ad, fn] of Object.entries(E.computed)) {
      if (['secimDurumlari', 'secimBilgi', 'secimAdresi', 'km'].includes(ad)) Object.defineProperty(u, ad, { get: fn.bind(u) });
    }
    for (const s of satirlar) E.methods.secimDegistir.call(u, s, true);
    const d = u.secimDurumlari;
    ok('[!] KR1: listeden secim — 6`da durur (7. olcum eklenmez), osiloskop ve yalniz-kartta satirin kutusu KAPALI ve etiketinde SEBEP',
       u.secim.length === 6 && u.secim.map((x) => x.oturum).join() === '1,2,3,4,5,6'
       && d['3:7'].uygun === false && d['3:7'].sebep === 'kr.sec_dolu' && d['3:8'].sebep === 'kr.sec_skop'
       && d['3:20'].sebep === 'kr.sec_kartta' && d['3:20'].etiket.includes('önce eşitleyin')
       && d['3:1'].secili && d['3:1'].uygun && d['3:1'].etiket.startsWith('Karşılaştırmadan çıkar: Akü'),
       JSON.stringify(u.secim.map((x) => x.oturum)));
    ok('[!] KR1 (3E S4): "Karsilastir" adresi kimligi HER ZAMAN yaziyor; secim sirasi = adres sirasi',
       u.secimAdresi === '#/karsilastir/1@3,2@3,3@3,4@3,5@3,6@3', u.secimAdresi);
    E.methods.secimDegistir.call(u, satirlar[2], false);
    ok('Secimden cikarilan satir adresten de cikar; 7. satir artik eklenebilir', u.secim.length === 5
       && !u.secimAdresi.includes('3@3') && u.secimDurumlari['3:7'].uygun === true);
    const sarmal = klKaynak.match(/<div v-for="s in gorunenSatirlar"[^>]*class="kl-satir-sarmal">([\s\S]*?)<\/div>\s*<\/div>/);
    const link = sarmal ? (sarmal[1].match(/<a class="kl-satir"[\s\S]*?<\/a>/) || [''])[0] : '';
    ok('[!] KR1/WIG: secim kutusu satir baglantisinin DISINDA (ic ice etkilesimli oge yok); :disabled ve aria-label secimDurumlari`ndan',
       !!sarmal && /<input type="checkbox" :data-kl-sec="s\.anahtar"/.test(sarmal[1]) && link.length > 0 && !/<input|<button/.test(link)
       && sarmal[1].indexOf('<input') < sarmal[1].indexOf('<a class="kl-satir"')
       && sarmal[1].includes(':disabled="!secimDurumlari[s.anahtar].uygun"')
       && sarmal[1].includes(':aria-label="secimDurumlari[s.anahtar].etiket"'));
    ok('KR1: "Karsilastir" en az 2 secimde BAGLANTI (secimAdresi), azinda kapali dugme; secim bilgisi canli bolgede',
       /<a v-if="secim\.length >= 2" class="kl-karsilastir-git" :href="secimAdresi"/.test(klKaynak)
       && /<button v-else type="button" class="birincil" disabled data-kl-karsilastir>/.test(klKaynak)
       && /class="kl-secim-bilgi" aria-live="polite"/.test(klKaynak));
  }

  /* ── (d) X KIPLERI: GERCEK ortak/kayit.js ile oturumlar ─────────── */
  const kanal_ = (n) => ({ n, pga: 4.096, kazanc: 1, sifir_ham: 12, tau: 0 });
  const KAL = { normal: kanal_(21), yuksek: kanal_(201), i_ofset: 5, i_pga: 0.256, sont_ohm: 0.1, i_duzeltme: 1,
    sebeke_hz: 0, faz_kal_us: [0, 0] };
  const VK = 4.096 / 32768 * 21;            // volt / kod (kayit.js formulu; bagimsiz yazildi)
  const IK = 0.256 / 32768 / 0.1;           // amper / kod
  let sira = 0;
  const ham = [];
  const ekle = (tur, ot, yuk) => { sira++; ham.push(Kx.kayitPaketle(tur, sira, ot, yuk)); return sira; };
  const u32 = (...d) => { const b = new Uint8Array(4 * d.length); const v = new DataView(b.buffer); d.forEach((x, i) => v.setUint32(4 * i, x, true)); return b; };
  const basla = (tur, hiz, unix, kms) => ekle(Kx.T_BASLA, sira + 1, Kx.baslaPaketle({ oturum_turu: tur, kal_bicim: 1, hiz_ms: hiz,
    unix_s: unix, kart_ms: kms, acilis: 3, surum: 'A3-3G', kal: KAL, kal_no: 2 }));
  const nk = (ms, v, i, w = v * i) => Kx.noktaPaketle({ kart_ms: ms, n: 40, bayrak: 0, v_ort_kod: v / VK + 12, v_min_kod: 0,
    v_maks_kod: 0, i_ort_kod: i / IK + 5, i_min_kod: 0, i_maks_kod: 0, w_ort: w, w_min: 0, w_maks: 0 });
  const noktalar = (ot, ilk, ns) => {
    for (let j = 0; j < ns.length; j += 5) {
      const p = ns.slice(j, j + 5);
      const y = new Uint8Array(4 + 36 * p.length);
      y.set(u32(ilk + j), 0);
      p.forEach((b, k) => y.set(b, 4 + 36 * k));
      ekle(Kx.T_NOKTA, ot, y);
    }
  };
  const O = {};
  O.A = basla(1, 200, 1790000000, 5000);                                  // olcum, saatli
  noktalar(O.A, 0, Array.from({ length: 20 }, (_, k) => nk(5000 + 200 * (k + 1), 12 + 0.1 * k, 0.5 + 0.01 * (k % 4))));
  O.E = basla(1, 1000, 0, 7000);                                          // saatsiz + saatsiz DEVAM
  noktalar(O.E, 0, Array.from({ length: 5 }, (_, k) => nk(7000 + 1000 * (k + 1), 5, 0.1)));
  ekle(Kx.T_DEVAM, O.E, u32(4, 0, 2000, 5));
  noktalar(O.E, 5, Array.from({ length: 5 }, (_, k) => nk(2000 + 1000 * (k + 1), 6, 0.1)));
  O.P = basla(1, 1000, 0, 9000);                                          // kismi saat: BASLA saatsiz, DEVAM saatli
  noktalar(O.P, 0, Array.from({ length: 3 }, (_, k) => nk(9000 + 1000 * (k + 1), 7, 0.2)));
  ekle(Kx.T_DEVAM, O.P, u32(5, 1790004000, 1000, 3));
  noktalar(O.P, 3, Array.from({ length: 4 }, (_, k) => nk(1000 + 1000 * (k + 1), 7, 0.2)));
  O.B = basla(2, 1000, 1790001000, 90000);                                // pil, kesintisiz
  const BI = [1.0, 0.98, 0.97, 0.99, 0.95, 0.93, 0.94, 0.9, 0.88, 0.87];
  noktalar(O.B, 0, BI.map((i, k) => nk(90000 + 1000 * (k + 1), 4.1 - 0.05 * k, i)));
  O.G = basla(2, 1000, 1790002000, 50000);                                // pil, BOSLUKLU (3 s > 2.5 x 1000)
  noktalar(O.G, 0, [1, 2, 5, 6].map((s) => nk(50000 + 1000 * s, 3.9, 0.5)));
  O.N = basla(2, 1000, 1790003000, 60000);                                // pil, EKSI akim
  noktalar(O.N, 0, [0.5, 0.4, -0.1, 0.3].map((i, k) => nk(60000 + 1000 * (k + 1), 3.8, i)));
  O.C = basla(1, 0, 1790005000, 200000);                                  // ayrintili, saatli
  ekle(Kx.T_AYRINTI, O.C, Kx.ayrintiPaketle({ ilk: 0, t0_ms: 200003, t0_us: 200003417, bayrak: 0,
    ornekler: Array.from({ length: 12 }, (_, k) => [1000 + 10 * k, 200 + k, k ? 500 : 0, 0]) }));
  let n_ = 0;
  for (const h of ham) n_ += h.length;
  const bayt = new Uint8Array(n_);
  let a0 = 0;
  for (const h of ham) { bayt.set(h, a0); a0 += h.length; }
  const kayitlar = Kx.akisCoz(bayt);
  const OT = Kx.oturumlariKur(kayitlar);
  const H = Object.fromEntries(Object.entries(O).map(([ad, no]) => [ad, KGx.grafikSerileri(OT.get(no), { kayitlar })]));
  const tur = Object.fromEntries(Object.entries(O).map(([ad, no]) => [ad, KGx.oturumTuru(OT.get(no))]));
  const KS = (ad, kip, kanal = 'V') => KR.kipSerisi(H[ad], { kip, kanal, tur: tur[ad] });
  const azalmaz = (x) => { for (let k = 1; k < x.length; k++) if (!(x[k] >= x[k - 1])) return false; return x.length > 0; };
  {
    const a = KS('A', 'baslangic');
    const e = KS('E', 'baslangic');
    ok('[!] KR3 baslangic: x = K1 ekseni (grafikSerileri.t AYNI dizi), y secili kanal; saatsiz yeniden baslama "tahmini" isaretli',
       a.x === H.A.t && a.y === H.A.s.vOrt && a.tahmini === false && e.tahmini === true && !a.sebep && !e.sebep
       && a.x[0] === 200 && a.x[19] === 4000 && e.x[4] === 5000 && e.x[5] === e.x[4] + 3 * 2500 && azalmaz(e.x) && KS('A', 'baslangic', 'I').y === H.A.s.iOrt && KS('A', 'baslangic', 'W').y === H.A.s.wOrt,
       `A ${a.x[0]}…${a.x[19]} · E ${Array.from(e.x).join(',')}`);
    const s = KS('A', 'saat');
    let saatTamam = s.x && s.x.length === 20;
    for (let k = 0; saatTamam && k < 20; k++) saatTamam = s.x[k] === 1790000000 * 1000 + 200 * (k + 1);
    const c = KS('C', 'saat');
    ok('[!] KR3 saat: x = unix ms (BASLA unix + acilis ici fark, bagimsiz hesapla AYNI); ayrintilida unixUs/1000, azalmayan',
       saatTamam && s.y === H.A.s.vOrt && !c.sebep && c.x.length === 12 && azalmaz(c.x)
       && Math.abs(c.x[0] - (1790005000 * 1000 + (200003417 - 200000 * 1000) / 1000)) < 1e-3 && c.y === H.C.s.v,
       `A ${s.x && s.x[0]} · C ${c.x && c.x[0]}`);
    const e2 = KS('E', 'saat');
    const p = KS('P', 'saat');
    ok('[!] KR3 saat: saatsiz kayit DISARIDA (sebep "saat yok"), kismen saatli kayit DISARIDA ve kac noktanin bilinmedigini soyluyor',
       e2.sebep === 'kr.disari_saatsiz' && !e2.x && p.sebep === 'kr.disari_saat_kismi' && p.d.eksik === 3 && p.d.toplam === 7
       && /saat yok/.test(SZx.ceviri('kr.disari_saatsiz', 'tr'))
       && SZx.ceviri('kr.disari_saat_kismi', 'tr', p.d) === '3 / 7 noktanın saati bilinmiyor', JSON.stringify({ e2, p: { sebep: p.sebep, d: p.d } }));
    const geri = KR.kipSerisi({ tur: 'nokta', adet: 3, t: Float64Array.of(0, 1, 2), tahmini: [], seriler: [],
      s: { vOrt: Float64Array.of(1, 2, 3), unixMs: Float64Array.of(5000, 4000, 6000) } }, { kip: 'saat' });
    ok('[!] KR3 saat: saati GERI giden kayit disarida (zaman uydurulmaz, grafik.js azalmayan x ister)', geri.sebep === 'kr.disari_saat_geri');
    const m = KS('B', 'mah');
    const bag = [];
    let top = 0;
    const iB = Array.from(H.B.s.iOrt);
    for (let k = 0; k < iB.length; k++) {
      if (k) top += (iB[k - 1] + iB[k]) / 2 * 1000 / 3600;
      bag.push(top);
    }
    const ref = PLx.mahEkseni(H.B.t, H.B.s.iOrt, H.B.boslukMs);
    ok('[!] KR3 mah (PU9): pil oturumunun x`i yamuk integral (bagimsiz dongu, 1e-12) ve pil.js mahEkseni`nin AYNI sonucu; eksen sonu yazilir',
       !m.sebep && m.x.length === 10 && bag.every((v, k) => Math.abs(m.x[k] - v) <= 1e-12 * Math.max(1, v))
       && Array.from(m.x).join() === Array.from(ref.x).join() && m.mahSon === m.x[9] && m.y === H.B.s.vOrt
       && Math.abs(iB[0] - 1.0) < 1e-6 && azalmaz(m.x), `son ${m.x && m.x[9]} ~ ${bag[9]}`);
    ok('[!] KR3 mah: pil DISI (olcum, ayrintili), BOSLUKLU ve EKSI akimli pil kaydi DISARIDA, sebebiyle; zaman eksenine DUSMEZ',
       KS('A', 'mah').sebep === 'kr.disari_pil_degil' && KS('C', 'mah').sebep === 'kr.disari_pil_degil'
       && KS('G', 'mah').sebep === 'kr.disari_mah_bosluk' && KS('N', 'mah').sebep === 'kr.disari_mah_eksi'
       && !KS('G', 'mah').x && !KS('N', 'mah').x && !KS('G', 'baslangic').sebep,
       ['A', 'C', 'G', 'N'].map((x) => x + ':' + KS(x, 'mah').sebep).join(' '));
  }

  /* ── (e) OKUMA kayit basina ─────────────────────────────────────── */
  {
    const ks = KS('B', 'baslangic');
    const t = Array.from(H.B.t);
    const v = Array.from(H.B.s.vOrt);
    const i = Array.from(H.B.s.iOrt);
    const w = Array.from(H.B.s.wOrt);
    const tA = 2400;
    const tB = 7600;
    const yakin = (x) => { let e = 0; for (let k = 1; k < t.length; k++) if (Math.abs(t[k] - x) < Math.abs(t[e] - x)) e = k; return e; };
    const ic = t.map((x, k) => k).filter((k) => t[k] >= tA && t[k] <= tB);
    let mah = 0;
    let wh = 0;
    for (let j = 1; j < ic.length; j++) {
      const p = ic[j - 1];
      const q = ic[j];
      mah += (i[p] + i[q]) * (t[q] - t[p]) / 2;
      wh += (w[p] + w[q]) * (t[q] - t[p]) / 2;
    }
    mah /= 3600;
    wh /= 3600000;
    const ort = ic.reduce((n, k) => n + v[k], 0) / ic.length;
    const r = KR.kayitOkuma(ks, tA, tB, { kip: 'baslangic', kanal: 'V' });
    const yak = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(b));
    ok('[!] KR4: kayit okumasi — A/B en yakin ornek, Δ = B − A, ort A–B ornek ortalamasi, mAh/Wh yamuk (K3: Wh kartin W`sinden) BAGIMSIZ hesapla (1e-9)',
       r.a === v[yakin(tA)] && r.b === v[yakin(tB)] && yak(r.fark, v[yakin(tB)] - v[yakin(tA)]) && yak(r.ort, ort)
       && yak(r.mah, mah) && yak(r.wh, wh) && r.aIcinde && r.bIcinde, JSON.stringify(r));
    const kg = KGx.okumaHesapla(H.B, tA, tB);
    ok('KR4: okuma kayit gorunumunun okumasiyla AYNI (tek hesap: okumaHesapla)',
       r.a === kg.v.a && r.b === kg.v.b && r.ort === kg.v.ort && r.mah === kg.enerji.mah && r.wh === kg.enerji.wh);
    const disari = KR.kayitOkuma(ks, tA, 50000, { kip: 'baslangic', kanal: 'V' });
    const ikiDisari = KR.kayitOkuma(ks, -5000, 50000, { kip: 'baslangic', kanal: 'V' });
    ok('[!] KU4: imlec kaydin DISINDAYSA o deger "—" (NaN; en yakin ornege YAPISMAZ), Δ/ort/mAh/Wh yalniz ikisi de icerdeyse',
       disari.a === v[yakin(tA)] && Number.isNaN(disari.b) && Number.isNaN(disari.fark) && Number.isNaN(disari.ort)
       && Number.isNaN(disari.mah) && Number.isNaN(disari.wh) && disari.bIcinde === false
       && Number.isNaN(ikiDisari.a) && Number.isNaN(ikiDisari.b), JSON.stringify(disari));
    const mk = KS('B', 'mah');
    const rm = KR.kayitOkuma(mk, mk.x[2], mk.x[7], { kip: 'mah', kanal: 'V' });
    ok('[!] KR4: mAh kipinde A/B mAh ekseninde, mAh / Wh YOK (yalniz zaman kiplerinde)',
       rm.a === v[2] && rm.b === v[7] && Number.isNaN(rm.mah) && Number.isNaN(rm.wh) && Number.isFinite(rm.ort));
    const ri = KR.kayitOkuma(KS('A', 'baslangic', 'I'), 1000, 3000, { kip: 'baslangic', kanal: 'I' });
    ok('KR4: kanal I -> akim degerleri', ri.a === H.A.s.iOrt[4] && ri.b === H.A.s.iOrt[14]);
    /* KU4/KR4: bilesenin okumasi her kayit icin KENDI serisinden (sahte this ile gercek yontem) */
    const u = { rota: { kip: 'baslangic', kanal: 'V' }, _cizilen: [{ g: { anahtar: '9:1', no: 1 }, ks: KS('A', 'baslangic') },
      { g: { anahtar: '9:2', no: 2 }, ks: KS('B', 'baslangic') }] };
    const ok2 = KR.KarsilastirEkrani.methods.okumaKur.call(u, 1000, 3000);
    ok('[!] KR4: bilesen okumasi KAYIT BASINA — her satir kendi kaydinin kayitOkuma`si (biri digerinin degerini almaz)',
       ok2.kayitlar.length === 2 && ok2.kayitlar[0].a === H.A.s.vOrt[4] && ok2.kayitlar[1].a === H.B.s.vOrt[0]
       && ok2.kayitlar[1].b === H.B.s.vOrt[2] && ok2.dt === 2000 && ok2.kayitlar[0].anahtar === '9:1', JSON.stringify(ok2));
  }

  /* ── (f) BIRLESIK CSV ───────────────────────────────────────────── */
  {
    const a = KS('A', 'baslangic');
    const b = KS('B', 'baslangic');
    const g = [{ no: O.A, kimlik: 3, ayrinti: false, x: a.x, y: a.y }, { no: O.B, kimlik: 3, ayrinti: false, x: b.x, y: b.y }];
    const tr = KR.birlesikCsv(g, { kip: 'baslangic', kanal: 'V', bicim: Dx.BICIM_EXCEL_TR });
    const sat = tr.split('\r\n');
    const hucre = (s) => s.split(';');
    const sy = (x, n) => Dx.sayiYaz(x, n, ',');
    let satirTamam = true;
    for (let j = 0; j < 20 && satirTamam; j++) {
      const h = hucre(sat[1 + j]);
      satirTamam = h.length === 4 && h[0] === sy(a.x[j], 3) && h[1] === sy(a.y[j], 6)
        && (j < 10 ? h[2] === sy(b.x[j], 3) && h[3] === sy(b.y[j], 6) : h[2] === '' && h[3] === '');
    }
    ok('[!] KR7: birlesik CSV (Excel-TR) — BOM, ";", ondalik virgul, CRLF; baslik kayit basina x + kanal; satir j = her kaydin j. ORNEGI, kisa kayit BOS hucre (ara deger yok)',
       tr.startsWith('﻿') && sat[0] === `﻿kayit${O.A}_gecen_ms;kayit${O.A}_v_ort_V;kayit${O.B}_gecen_ms;kayit${O.B}_v_ort_V`
       && sat.length === 22 && sat[21] === '' && satirTamam && sat[1].split(';')[0] === '200,000' && sat[1].split(';')[2] === '1000,000',
       sat.slice(0, 3).join(' | '));
    const gW = [{ no: O.A, kimlik: 3, ayrinti: false, x: a.x, y: KS('A', 'baslangic', 'W').y },
      { no: O.B, kimlik: 3, ayrinti: false, x: b.x, y: KS('B', 'baslangic', 'W').y }];
    const en = KR.birlesikCsv(gW, { kip: 'baslangic', kanal: 'W', bicim: Dx.BICIM_EN }).split('\r\n');
    ok('KR7: EN bicimi "," ayrac, "." ondalik, rec<no>_elapsed_ms / p_avg_W',
       en[0] === `﻿rec${O.A}_elapsed_ms,rec${O.A}_p_avg_W,rec${O.B}_elapsed_ms,rec${O.B}_p_avg_W`
       && en[1].split(',')[0] === '200.000' && en[1].split(',')[1] === Dx.sayiYaz(H.A.s.wOrt[0], 6));
    const s = KS('A', 'saat');
    const m = KS('B', 'mah');
    const c = KS('C', 'saat');
    const saat = KR.birlesikCsv([{ no: O.A, kimlik: 3, ayrinti: false, x: s.x, y: s.y }, { no: O.C, kimlik: 3, ayrinti: true, x: c.x, y: c.y }],
      { kip: 'saat', kanal: 'I' }).split('\r\n');
    const mah = KR.birlesikCsv([{ no: O.B, kimlik: 3, ayrinti: false, x: m.x, y: m.y }], { kip: 'mah', kanal: 'V' }).split('\r\n');
    ok('KR7: saat kipinde unix_s (3 ondalik), mAh kipinde yuk_mAh (6 ondalik); ayrintili kayitta kanal sutunu ornek adi (i_A)',
       saat[0] === `﻿kayit${O.A}_unix_s;kayit${O.A}_i_ort_A;kayit${O.C}_unix_s;kayit${O.C}_i_A`
       && saat[1].split(';')[0] === '1790000000,200' && saat[1].split(';')[2] === sy(c.x[0] / 1000, 3)
       && mah[0] === `﻿kayit${O.B}_yuk_mAh;kayit${O.B}_v_ort_V` && mah[2].split(';')[0] === sy(m.x[1], 6), saat[1]);
    const iki = KR.birlesikCsv([{ no: 5, kimlik: 3, x: Float64Array.of(1), y: Float64Array.of(NaN) },
      { no: 5, kimlik: 9, x: Float64Array.of(2), y: Float64Array.of(1) }], {}).split('\r\n');
    ok('KR7: ayni numara iki akistan -> baslikta @kimlik; NaN deger BOS hucre',
       iki[0] === '﻿kayit5@3_gecen_ms;kayit5@3_v_ort_V;kayit5@9_gecen_ms;kayit5@9_v_ort_V' && iki[1] === '1,000;;2,000;1,000000', iki.join(' | '));
    ok('KR7: dosya adi karsilastirma-<kip>-<kanal>[-en].csv',
       KR.karsilastirDosyaAdi('saat', 'I', 'en') === 'karsilastirma-saat-i-en.csv' && KR.karsilastirDosyaAdi('baslangic', 'V') === 'karsilastirma-baslangic-v.csv');
  }

  /* ── (g) RENK: tema belirteclerinden, renk korlugune dayanikli ─── */
  {
    const cssKod = css.replace(/\/\*[\s\S]*?\*\//g, '');
    const kural = (ad) => {
      for (const m of cssKod.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
        if (m[1].split(',').map((s) => s.trim()).includes(':root[data-tema="' + ad + '"]')) return m[2];
      }
      return '';
    };
    const takim = (ad) => Object.fromEntries([...kural(ad).matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim().toLowerCase()]));
    const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
    const gam = (c) => { c = Math.min(1, Math.max(0, c)); return 255 * (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055); };
    const rgb = (h) => [1, 3, 5].map((k) => parseInt(h.slice(k, k + 2), 16));
    /* Machado, Oliveira, Fernandes 2009 — siddet 1.0 (dogrusal RGB'de) */
    const MAT = {
      normal: [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
      protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
      deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
      tritan: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
    };
    const sim = (c, M) => { const l = c.map(lin); return M.map((r) => gam(r[0] * l[0] + r[1] * l[1] + r[2] * l[2])); };
    const lab = (c) => {
      const [r, g, b] = c.map(lin);
      const f = (x) => (x > 216 / 24389 ? Math.cbrt(x) : (24389 / 27 * x + 16) / 116);
      const X = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047);
      const Y = f(0.2126 * r + 0.7152 * g + 0.0722 * b);
      const Z = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
      return [116 * Y - 16, 500 * (X - Y), 200 * (Y - Z)];
    };
    const dE = (a, b) => Math.hypot(...lab(a).map((x, k) => x - lab(b)[k]));
    const lum = (c) => { const [r, g, b] = c.map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const kon = (a, b) => { const x = lum(a); const y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    const rapor = [];
    let tamam = true;
    let enKotuDE = Infinity;
    let enKotuKon = Infinity;
    let enKotuImlec = Infinity;
    for (const t of ['koyu', 'acik', 'onpanel']) {
      const d = takim(t);
      const renk = KR.KR_RENKLER.map((_, k) => KR.krRenk(k, (ad) => d['--' + ad]));
      if (!renk.every((h) => /^#[0-9a-f]{6}$/.test(h)) || new Set(renk).size !== 6) { tamam = false; rapor.push(t + ' gecersiz ' + renk); continue; }
      const c = renk.map(rgb);
      for (let k = 0; k < 6; k++) {
        enKotuKon = Math.min(enKotuKon, kon(c[k], rgb(d['--kart'])));
        enKotuImlec = Math.min(enKotuImlec, dE(c[k], rgb(d['--yazi'])));
        for (let j = k + 1; j < 6; j++) {
          const desen = (x) => (KR.KR_RENKLER[x].desen || []).join();
          if (desen(k) !== desen(j)) continue;
          for (const M of Object.values(MAT)) enKotuDE = Math.min(enKotuDE, dE(sim(c[k], M), sim(c[j], M)));
        }
      }
      rapor.push(`${t}: ${renk.join(' ')}`);
    }
    ok('[!] KR2/KU3: alti cizgi rengi YALNIZ tema belirteclerinden (Koyu takima yeni belirtec eklenmedi), uc gorunumde gecerli ve farkli',
       tamam && KR.KR_RENKLER.every((r) => ['volt', 'amper', 'watt', 'vurgu'].includes(r.belirtec) && (!r.kutup || ['yazi', 'kart'].includes(r.kutup)))
       && !/#[0-9a-fA-F]{6}\b|['"]#[0-9a-fA-F]{3}['"]/.test(yorumsuz(krKaynak)), rapor.join(' · '));
    ok('[!] KR2: her cizgi her gorunumde kart zeminine karsi >= 3:1 (WCAG 1.4.11) ve imlec renginden (--yazi, K5) ayri (dE >= 20)',
       enKotuKon >= 3 && enKotuImlec >= 20, `en kotu karsitlik ${enKotuKon.toFixed(2)}:1, imlece dE ${enKotuImlec.toFixed(1)}`);
    ok('[!] KR2: renk korlugu (protan / deutan / tritan, Machado 2009) dahil AYNI desenli her cift ayri: CIELAB dE >= 15; 4.-6. kayit KESIK (imlec B deseninden ayri)',
       enKotuDE >= 15 && KR.KR_RENKLER.slice(0, 3).every((r) => !r.desen) && KR.KR_RENKLER.slice(3).every((r) => r.desen === KR.KR_DESEN)
       && KR.KR_DESEN.join() !== '6,4', `en kotu dE ${enKotuDE.toFixed(1)}`);
    ok('KR2: renkKar karisimi kanal basina Math.round (sRGB); cozulemezse taban rengi',
       KR.renkKar('#000000', '#ffffff', 0.5) === '#808080' && KR.renkKar('#6ea8fe', '#dee7ef', 0.5) === '#a6c8f7'
       && KR.renkKar('#6ea8fe', null, 0) === '#6ea8fe' && KR.renkKar('red', '#fff', 0.5) === 'red' && KR.renkKar('#abc', '#000', 0) === '#aabbcc');
    const t = Float64Array.from({ length: 30 }, (_, k) => k * 1000);
    const y = Float64Array.from({ length: 30 }, (_, k) => Math.sin(k));
    const s = [GRx.seriHazirla({ ad: 'K0', t, y, renk: 'kr0' }), GRx.seriHazirla({ ad: 'K3', t, y, renk: 'kr3', desen: KR.KR_DESEN })];
    const plan = GRx.cizimPlani(s, GRx.durumKur(s), { w: 600, h: 200 }, {});
    const cz = plan.komutlar.filter((k) => k.rol === 'seri' && k.tur === 'cizgi');
    ok('[!] KR2: kesik desen grafik.js planina geciyor (seri.desen -> komut.desen), duz seride desen yok',
       cz.some((k) => k.renk === 'kr3' && k.desen === KR.KR_DESEN) && cz.filter((k) => k.renk === 'kr0').every((k) => !k.desen));
    ok('KR2: lejant ornegi tuvaldeki desenle ayni (stroke-dasharray KR_RENKLER`den); renk SECIM SIRASINA bagli (kr + pos)',
       /:stroke-dasharray="l\.desen"/.test(KR.KarsilastirEkrani.template) && /renk: 'kr' \+ g\.pos/.test(krKaynak)
       && /desen: KR_RENKLER\[l\.pos\]\.desen \? KR_RENKLER\[l\.pos\]\.desen\.join\(' '\) : null/.test(krKaynak));
  }

  /* ── (h) KU2 adres, sablon (WIG), CSS ──────────────────────────── */
  {
    const yaz = [];
    const eskiH = global.history;
    global.history = { replaceState: (a, b, h) => yaz.push(h), pushState: () => yaz.push('PUSH') };
    let kuruldu = 0;
    const u = { rota: { secim: [{ oturum: 4, kimlik: 2 }], kip: 'baslangic', kanal: 'V', fazla: 0, gecersiz: 0 }, kur() { kuruldu++; } };
    KR.KarsilastirEkrani.methods.rotaGuncelle.call(u, { kip: 'saat' });
    KR.KarsilastirEkrani.methods.rotaGuncelle.call(u, { kanal: 'W' });
    global.history = eskiH;
    ok('[!] KU2: kip / kanal degisince adres replaceState ile (gecmise girdi YOK: geri tusu ekrandan cikar); grafik yeniden kurulur',
       yaz.join(' ') === '#/karsilastir/4@2?x=saat #/karsilastir/4@2?x=saat&k=W' && kuruldu === 2 && u.rota.kanal === 'W', yaz.join(' '));
    const T = KR.KarsilastirEkrani.template;
    ok('[!] KR8/WIG: tuval role=img + aria-label; okuma TABLO (caption, th scope); ozet aria-live; secimler <label> icinde; bos durum Kayitlar`a baglanti',
       /<canvas ref="tuval" class="kr-grafik" role="img" :aria-label="grafikEtiket">/.test(T) && /<caption class="gorunmez">/.test(T)
       && /<th scope="row">/.test(T) && /<th scope="col">/.test(T) && /class="gorunmez" aria-live="polite">\{\{ duyuru \}\}/.test(T)
       && /<label>\{\{ m\.kanal \}\}\s*<select v-model="kanalSecim"/.test(T) && /<label>\{\{ m\.xEksen \}\}\s*<select v-model="kipSecim"/.test(T)
       && /v-if="!rota\.secim\.length"[\s\S]*?href="#\/kayitlar" data-kr="kayitlara-git"/.test(T) && /ref="baslik" tabindex="-1"/.test(T));
    const blok = css.slice(css.indexOf('3G — KARŞILAŞTIRMA'));
    ok('[!] 3G stilleri YALNIZ belirtecle (sabit renk yok); telefonda tuval kisalir',
       blok.length > 500 && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(blok.replace(/\/\*[\s\S]*?\*\//g, ''))
       && /@media \(max-width: 620px\) \{[^}]*canvas\.kr-grafik \{ height: 260px; \}/.test(blok));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   30. AYARLAR (3H-1 — alt proje 3, AY1-AY7; uygulama kararlari 3H-1)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H kararlari". Burada:
   (a) KABLOLAMA (AY2): yedi bolum karardaki sirayla, `#/ayar/<bolum>` rotasi
       (adres ezilmiyor), ic gezinme, her kart TEK bolume bagli; uc yeni bolum
       (kalibrasyon gecmisi, depolama, gelismis) TEMBEL modulde — acilis
       kumesine girmiyor, IndexedDB zinciri yalniz gereken bolumde DINAMIK.
   (b) DIL (AY3): secim `olcum.dil` (esitleme.js dilOku ile ayni anahtar),
       ANINDA (<html lang>, sekme basligi, alt ekranlar); sayi bicimi dile
       bagli degil; EN'de cevrilmemis metinler SAYILIP LISTELENIYOR (kilitli).
   (c) DEPOLAMA (AY4): akis basina boyut / oturum / son esitleme / eski kart
       kopyasi; storage.estimate + persist (yoksa sebep); iki asamali silme.
   (d) KALIBRASYON GECMISI (AY5): `/kal/liste` (yoksa bu tarayicidaki kopya),
       SALT OKUMA — kk/kn/kt ya da herhangi bir komut YOK; alanlar firmware'in
       JSON'undan turetiliyor.
   (e) GELISMIS (AY6): firmware (afis), panel surumu (`kunye.json` = _fs.json
       ozeti; Python ile capraz), yalniz `olcum.*` anahtarlarini silen iki
       asamali sifirlama.
   (f) WIG (AY7): etiketler, odak, tablo basliklari, tabular-nums, telefon.
   Gercek tarayici (IndexedDB, storage, dil gecisi, geri tusu, uc gorunum,
   390 px): tarayici_ayarlar.py (T3H).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 30. Ayarlar (3H-1) ---');
{
  const html = yorumsuz(htmlKaynak);
  const css = cssOku();
  const al = (ad) => { try { return vm.runInContext(ad, sandbox); } catch (e) { return undefined; } };
  const SZx = sozlukTum();
  const ESx = require(path.join(ARAYUZ, 'ekran', 'esitleme.js'));
  const KLx = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
  const KRx = require(path.join(ARAYUZ, 'ekran', 'karsilastir.js'));
  const ayYolu = path.join(ARAYUZ, 'ekran', 'ayarlar.js');
  let AY = {};
  try { AY = require(ayYolu); } catch (h) { console.log('     ekran/ayarlar.js yuklenemedi: ' + h.message); }
  const ayKaynak = fs.existsSync(ayYolu) ? fs.readFileSync(ayYolu, 'utf8') : '';
  const ayKod = yorumsuz(ayKaynak);
  const T = (AY.AyarlarEkrani && AY.AyarlarEkrani.template) || '';
  const ana = (ad) => { const m = html.match(new RegExp(`<main class="gorunum" v-show="gorunum === '${ad}'">([\\s\\S]*?)</main>`)); return m ? m[1] : ''; };
  const ayar = ana('ayar');
  const BOLUMLER = al('AYAR_BOLUMLERI') || [];
  const ids = BOLUMLER.map((b) => b.id);
  const bilesen = (B, props = {}) => {
    const o = Object.assign({}, props);
    Object.assign(o, B && B.data ? B.data.call(o) : {});
    Object.assign(o, (B && B.methods) || {});
    o.$nextTick = (f) => { if (f) f(); return Promise.resolve(); };
    o.$refs = {};
    for (const [ad, fn] of Object.entries((B && B.computed) || {})) {
      Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
    }
    return o;
  };
  const sahteDepo = (ilk = {}, atar = false) => {
    const m = new Map(Object.entries(ilk));
    return {
      m,
      get length() { if (atar) throw new Error('engelli'); return m.size; },
      key(i) { if (atar) throw new Error('engelli'); return [...m.keys()][i] ?? null; },
      getItem(a) { if (atar) throw new Error('engelli'); return m.has(a) ? m.get(a) : null; },
      setItem(a, d) { if (atar) throw new Error('engelli'); m.set(a, String(d)); },
      removeItem(a) { if (atar) throw new Error('engelli'); m.delete(a); },
    };
  };

  /* AY3: EN'de hala Turkce kalan (sozluge girmemis) metinler — GIZLENMEZ, sayilir ve listelenir.
     Kapsam: (1) index.html sablonu (#uyg): duz metin (satir ici b/code/... birlestirilerek),
     sabit placeholder / title / aria-label / alt ve baglamalardaki ('...') Turkce harfli dizgeler;
     (2) app.js + ekran/*.js: Turkce harf (çğıöşü) iceren dizge sabitleri (yorumlar haric;
     `<` iceren sablon dizgeleri (1)'in kuraliyla). Bilinen kor nokta: Turkce harfi olmayan
     (ASCII) Turkce dizge sabiti JS'te sayilmaz — sayilsaydi protokol sozcukleri ve firmware'in
     ASCII satirlari listeyi bogardi. sahte-kart.js (firmware'in taklidi) ve kartin kendi
     satirlari (Konsol) kapsam disi: onlar kartin dili. */
  const TR_HARF = /[çğıöşüÇĞİÖŞÜ]/;
  const HARF = /[A-Za-zçğıöşüÇĞİÖŞÜ]{2,}/;
  /* Dilden bagimsiz birim / kisaltma (yalniz bunlardan olusan metin ceviri istemez: "100 Hz", "Vrms / Irms"). */
  const NOTR = new Set(['Hz', 'kHz', 'MHz', 'mA', 'mV', 'kSa', 'Vrms', 'Irms', 'Vpp', 'USB', 'CSV', 'GPIO', 'ADC',
    'DC', 'AC', 'PF', 'VA', 'DEMO']);
  const cevrilecek = (x) => HARF.test(x) && !(x.match(/[A-Za-zçğıöşüÇĞİÖŞÜµΩ]{2,}/g) || []).every((w) => NOTR.has(w));
  const sablonMetinleri = (s, yer, liste) => {
    const t = s.replace(/<(script|style)\b[\s\S]*?<\/\1>/g, ' ')
      .replace(/<\/?(?:b|strong|em|i|code|kbd|sub|sup|br|abbr|small)\b[^>]*>/g, '');
    for (const m of t.matchAll(/>([^<>]+)</g)) {
      const x = m[1].replace(/\{\{[\s\S]*?\}\}/g, ' ').replace(/\s+/g, ' ').trim();
      if (cevrilecek(x)) liste.push({ yer, tur: 'metin', metin: x });
    }
    for (const m of t.matchAll(/\s(placeholder|title|aria-label|alt)="([^"]*)"/g)) {
      if (cevrilecek(m[2])) liste.push({ yer, tur: m[1], metin: m[2] });
    }
    const baglamalar = [...t.matchAll(/\{\{([\s\S]*?)\}\}/g)].map((m) => m[1])
      .concat([...t.matchAll(/\s[:@][\w.-]+="([^"]*)"/g)].map((m) => m[1]));
    for (const b of baglamalar) {
      for (const l of b.matchAll(/'([^']*)'/g)) if (TR_HARF.test(l[1])) liste.push({ yer, tur: 'baglama', metin: l[1] });
    }
  };
  const enEksikleri = (yalniz = null) => {
    const liste = [];
    if (yalniz !== null) { sablonMetinleri(yalniz, 'parca', liste); return liste; }
    const h = yorumsuz(htmlKaynak);
    sablonMetinleri(h.slice(h.indexOf('<div id="uyg"')), 'index.html', liste);
    for (const k of kodKaynaklari) {
      const kod = yorumsuz(k.kaynak);
      for (const m of kod.matchAll(/'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g)) {
        const d = m[1] ?? m[2] ?? m[3];
        if (/<[a-z]/.test(d)) { sablonMetinleri(d, k.ad, liste); continue; }
        if (TR_HARF.test(d)) liste.push({ yer: k.ad, tur: 'dizge', metin: d.replace(/\s+/g, ' ').trim() });
      }
    }
    return liste;
  };
  /* KILIT: 3H-1'de olculen. Azalirsa (eski metin sozluge tasindi) kilidi dusur; artarsa
     yeni metni sozluge koy — gomulu Turkce metin bu kilidi kirmiziya dondurur. */
  const EN_EKSIK_KILIT = 272;     /* 4D: skop eski arsiv basligi + aciklamasi sozluge (os.eski_arsiv*) */

  /* ── (a) KABLOLAMA (AY2) ────────────────────────────────────────── */
  {
    /* 3H-2 (ES1): Eslestirme Ag'dan sonra sekizinci bolum olarak eklendi (bolum 31) */
    ok('[!] AY2: sekiz bolum KARARDAKI sirayla (Baglanti · Ag · Eslestirme (3H-2) · Kalibrasyon · Kalibrasyon gecmisi · Depolama · Dil ve gorunum · Gelismis); adlari sozlukte (tr + en)',
       ids.join(' ') === 'baglanti ag eslestirme kalibrasyon kal-gecmis depolama dil-gorunum gelismis'
       && BOLUMLER.every((b) => b.ad in SZx.SOZLUK && SZx.SOZLUK[b.ad].tr && SZx.SOZLUK[b.ad].en)
       && BOLUMLER.map((b) => SZx.SOZLUK[b.ad] ? SZx.SOZLUK[b.ad].tr : '').join(' · ')
         === 'Bağlantı · Ağ · Eşleştirme · Kalibrasyon · Kalibrasyon geçmişi · Depolama · Dil ve görünüm · Gelişmiş', ids.join(' '));
    ok('[!] AY2: tembel modulun bolumleri (mod) tam olarak kalibrasyon gecmisi, depolama, gelismis — ekran/ayarlar.js MOD_BOLUMLER ile ayni',
       BOLUMLER.filter((b) => b.mod).map((b) => b.id).join() === 'kal-gecmis,depolama,gelismis'
       && Array.isArray(AY.MOD_BOLUMLER) && AY.MOD_BOLUMLER.join() === 'kal-gecmis,depolama,gelismis');
    const coz = al('ayarBolumCoz');
    ok('[!] AY2: ayarBolumCoz — #/ayar/<bolum> o bolum; #/ayar, bilinmeyen, eski bicim -> Baglanti (varsayilan)',
       typeof coz === 'function' && ids.every((i) => coz('#/ayar/' + i) === i) && coz('#/ayar/depolama/') === 'depolama'
       && coz('#/ayar') === 'baglanti' && coz('#/ayar/') === 'baglanti' && coz('#/ayar/yok') === 'baglanti'
       && coz('#/ayar/__proto__') === 'baglanti' && coz('') === 'baglanti' && coz('#/kayitlar') === 'baglanti'
       && al('AYAR_VARSAYILAN') === 'baglanti');
    const hashten = al('hashtenGorunum');
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('[!] AY2: hashtenGorunum — #/ayar, #/ayar/depolama, #/ayar/yok -> ayar; #/ayarx -> canli',
       dene('#/ayar') === 'ayar' && dene('#/ayar/depolama') === 'ayar' && dene('#/ayar/yok') === 'ayar'
       && dene('#/ayarx') === 'canli');
    const w = secenekler.watch.gorunum;
    const yazilan = [];
    sandbox.history = { replaceState: (a, b2, h) => yazilan.push(h) };
    sandbox.location = { hash: '#/ayar/depolama' };
    w.call({ $nextTick() {}, grafikCiz() {}, osiloCiz() {} }, 'ayar');
    ok('[!] AY2: watch.gorunum bolumlu adresi (#/ayar/depolama) EZMIYOR (geri tusu / paylasilan adres)',
       yazilan.length === 0, yazilan.join());
    /* data(): ilk acilista bolum + modul karari */
    sandbox.location = { hash: '#/ayar/depolama' };
    const d1 = secenekler.data();
    sandbox.location = { hash: '#/ayar/ag' };
    const d2 = secenekler.data();
    sandbox.location = { hash: '' };
    const d3 = secenekler.data();
    ok('[!] AY2: ilk acilis — #/ayar/depolama bolumu ve MODULU acar; #/ayar/ag modulu INDIRMEZ; varsayilan acilista ikisi de yok',
       d1.ayarBolum === 'depolama' && d1.ayarModAcik === true && d2.ayarBolum === 'ag' && d2.ayarModAcik === false
       && d3.ayarModAcik === false, `${d1.ayarBolum}/${d1.ayarModAcik} ${d2.ayarBolum}/${d2.ayarModAcik} ${d3.ayarModAcik}`);
    delete sandbox.location;
    delete sandbox.history;
    const gerekli = secenekler.computed && secenekler.computed.ayarModGerekli;
    const ws = secenekler.watch && secenekler.watch.ayarModGerekli;
    const s1 = { gorunum: 'ayar', ayarBolum: 'gelismis', ayarModAcik: false };
    const s2 = { gorunum: 'canli', ayarBolum: 'gelismis' };
    const s3 = { gorunum: 'ayar', ayarBolum: 'ag' };
    if (ws) ws.call(s1, true);
    ok('[!] AY2: modul YALNIZ Ayarlar gorunurken ve modul bolumu seciliyken iner (ayarModGerekli -> ayarModAcik, bir kez)',
       !!gerekli && gerekli.call(s1) === true && gerekli.call(s2) === false && gerekli.call(s3) === false
       && s1.ayarModAcik === true);
    ok('AY2: adres degisince (hashchange) bolum de guncelleniyor (geri tusu bolumler arasinda calisir)',
       govdeIcinde(appKaynak, 'mounted', "window.addEventListener('hashchange', () => { this.ayarBolum = ayarBolumCoz(location.hash); });"));

    const nav = ayar.match(/<nav class="ay-nav" :aria-label="ay\.bolumler">([\s\S]*?)<\/nav>/);
    ok('[!] AY2/AY7: Ayarlar`in ic gezinmesi <nav> (adli), bolum basina BAGLANTI #/ayar/<id>, secili olan aria-current',
       !!nav && /<a v-for="b in ayarBolumListesi" :key="b\.id"/.test(nav[1]) && /:href="'#\/ayar\/' \+ b\.id"/.test(nav[1])
       && /:aria-current="ayarBolum === b\.id \? 'true' : null"/.test(nav[1]) && /class="ay-sekme" :class="\{ etkin: ayarBolum === b\.id \}"/.test(nav[1])
       && /:data-ay-git="b\.id"/.test(nav[1]));
    const kartlar = [...ayar.matchAll(/<section class="kart"([^>]*)>\s*<h2>([^<]*)<\/h2>/g)].map((m) => ({
      bolum: (/v-show="ayarBolum === '([a-z-]+)'"/.exec(m[1]) || [])[1] || null, baslik: m[2].trim() }));
    const harita = Object.fromEntries(kartlar.map((k) => [k.baslik, k.bolum]));
    ok('[!] AY2: index.html`deki HER Ayarlar karti TEK bolumde (v-show); mevcut kartlar yerinde (AY1/AY7: hicbiri kalkmadi)',
       kartlar.length >= 5 && kartlar.every((k) => k.bolum && ids.includes(k.bolum))
       && harita['Bağlantı'] === 'baglanti' && harita['Kalibrasyon ve ayar'] === 'kalibrasyon'
       && harita['Ağ — kartı kablosuz yapma'] === 'ag' && harita['Görünüm'] === 'dil-gorunum'
       && harita['{{ ay.dil }}'] === 'dil-gorunum', JSON.stringify(harita));
    const modKart = [...T.matchAll(/<section class="kart" v-show="bolum === '([a-z-]+)'"/g)].map((m) => m[1]);
    /* 3H-2: Eslestirme bolumunun kartlari kendi modulunde (ekran/eslesme_ekran.js EslestirmeEkrani; EU30) */
    let esT = '';
    try { esT = require(path.join(ARAYUZ, 'ekran', 'eslesme_ekran.js')).EslestirmeEkrani.template || ''; } catch (h) { esT = ''; }
    const esKart = [...esT.matchAll(/<section class="kart"[^>]*data-ay-bolum="([a-z-]+)"/g)].map((m) => m[1]);
    ok('[!] AY2: her bolumun en az bir karti var — app bolumleri index.html`de, mod bolumleri ekran/ayarlar.js sablonunda, eslestirme ekran/eslesme_ekran.js`te (bos bolum yok)',
       BOLUMLER.every((b) => (b.mod ? modKart : b.es ? esKart : kartlar.map((k) => k.bolum)).includes(b.id))
       && esKart.length >= 3 && esKart.every((x) => x === 'eslestirme')
       && modKart.every((m) => AY.MOD_BOLUMLER.includes(m)), modKart.join(' '));
    const b = secenekler.components && secenekler.components['ayarlar-ekran'];
    const sec = b && b.yukleyici && typeof b.yukleyici === 'object' ? b.yukleyici : {};
    ok('[!] ayarlar-ekran ASENKRON: ./ekran/ayarlar.js (AyarlarEkrani); inmezse sebep + care, metin secili dilde',
       !!b && b.__asenkron === true && /import\('\.\/ekran\/ayarlar\.js'\)\.then\(\(m\) => m\.AyarlarEkrani\)/.test(String(sec.loader))
       && typeof (AY.AyarlarEkrani || {}).template === 'string' && !!sec.errorComponent
       && /class="hata"/.test(sec.errorComponent.template || '') && typeof sec.errorComponent.data === 'function'
       && /yüklenemedi[\s\S]*yenileyin/.test(SZx.ceviri('ay.mod_yuklenemedi', 'tr')), String(sec.loader));
    const ekr = ayar.match(/<ayarlar-ekran ([^>]*)>/);
    ok('[!] ayarlar-ekran Ayarlar`in icinde, YALNIZ gerekince (v-if ayarModAcik); bolum, kart adresi, tasiyici, baglanti, afis surumu, dil ve etkinlik veriliyor',
       !!ekr && /^v-if="ayarModAcik"/.test(ekr[1]) && [':bolum="ayarBolum"', ':kart-adres="kartAdres"', ':kart-taban="kartTaban"',
         ':tasiyici="tasiyiciAdi"', ':bagli="bagli"', ':afis-surum="afisSurum"', ':dil-secim="dil"', ":etkin=\"gorunum === 'ayar'\""]
         .every((x) => ekr[1].includes(x)), ekr ? ekr[1] : 'yok');

    /* butce: ayarlar.js ACILISTA inmez; statik agaci acilis kumesi + KENDI sozlugu (EU32: sozluk_ay.js — ekranin
       metinleri acilistan cikti, Gelismis artik IKI dosya indirir: ayarlar.js + sozluk_ay.js); IndexedDB zinciri DINAMIK */
    const statik = iceAktarmaGrafigi().map((x) => x.goruntu);
    const ayAgac = iceAktarmaGrafigi(ayYolu).map((x) => x.goruntu);
    const ayEk = ayAgac.filter((x) => !statik.includes(x));
    ok('[!] AY2 / EU32: ekran/ayarlar.js ACILISTA inmiyor; kendi statik agaci acilis kumesi + YALNIZ ortak/sozluk_ay.js (Gelismis iki dosya ekler: modul + metinleri)',
       !statik.includes('ekran/ayarlar.js') && ayAgac.length > 0 && ayEk.join(' ') === 'ortak/sozluk_ay.js', ayAgac.join(' '));
    /* 4H: ./pc_kopru.js da dinamik ama IndexedDB zinciri DEGIL (yalniz kopruda, Gelismis'te) — bolum 34 */
    const dinamik = [...ayKod.matchAll(/import\('(\.\/[a-z_]+\.js)'\)/g)].map((m) => m[1]).filter((d) => d !== './pc_kopru.js').sort();
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const kunye = fs.existsSync(kunyeYolu) ? JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')) : {};
    const by = kunye.bayt || {};
    const dinAgac = new Set();
    for (const d of dinamik) {
      const dosya = path.join(ARAYUZ, 'ekran', d.slice(2));
      for (const x of [path.relative(ARAYUZ, dosya).split(path.sep).join('/'), ...iceAktarmaGrafigi(dosya).map((y) => y.goruntu)]) {
        if (!statik.includes(x)) dinAgac.add(x);
      }
    }
    const dinBayt = [...dinAgac].reduce((n, a) => n + (Number.isFinite(by[a]) ? by[a] : NaN), 0);
    const ayBayt = by['ekran/ayarlar.js'];
    const aySozBayt = by['ortak/sozluk_ay.js'];
    ok('[!] EU32: ortak/sozluk_ay.js (Ayarlar modulunun metinleri) <= 5.5 KB gzip ve kunyede; ayarlar.js + sozluk_ay.js <= 17 KB gzip',
       aySozBayt > 0 && aySozBayt <= 5632 && ayBayt + aySozBayt <= 17 * 1024, `sozluk_ay.js ${aySozBayt} B · toplam ${ayBayt + aySozBayt} B`);
    ok('[!] AY4/AY5: IndexedDB zinciri ayarlar.js`e DINAMIK (yalniz esitleme.js + depo_idb.js), <= 6 dosya ve <= 48 KB gzip; ayarlar.js <= 12 KB gzip',
       dinamik.join(' ') === './depo_idb.js ./esitleme.js' && dinAgac.size > 0 && dinAgac.size <= 6 && dinBayt > 0 && dinBayt <= 48 * 1024
       && ayBayt > 0 && ayBayt <= 12 * 1024, `${[...dinAgac].join(' ')} · ${dinBayt} B · ayarlar.js ${ayBayt} B`);
    const statikBayt = statik.concat(['index.html', 'style.css', 'vendor/vue.global.prod.js', 'manifest.json', 'ikon-180.png', 'app.js'])
      .filter((x, i, a) => a.indexOf(x) === i).reduce((n, a) => n + (by[a] || 0), 0);
    /* Bilgi (iddia DEGIL — Kayitlar'in dogrudan acilisinda da kural yok, 3G KU1): dogrudan
       #/ayar/depolama acilisi = acilis kumesi (<= 250 KB, yukaridaki iddialar) + bu iki sinir. */
    console.log(`     #/ayar/depolama ile dogrudan acilis: ${statikBayt} + ${ayBayt} + ${aySozBayt} + ${dinBayt} = ${statikBayt + ayBayt + aySozBayt + dinBayt} B gzip`);
  }

  /* ── (b) DIL (AY3) ──────────────────────────────────────────────── */
  {
    ok('[!] AY3: dil secenekleri TR + EN; adlari sozlukte KENDI dillerinde (Türkçe / English)',
       JSON.stringify((al('DILLER') || []).map((d) => d.id)) === '["tr","en"]'
       && SZx.ceviri('ay.dil_tr', 'en') === 'Türkçe' && SZx.ceviri('ay.dil_en', 'tr') === 'English');
    const depo = sahteDepo({ 'olcum.tema': '"acik"' });
    const eskiW = sandbox.window;
    sandbox.window = Object.assign({}, eskiW, { localStorage: depo });
    const u = ornek();
    u.dilSecildi('en');
    const yazildi = depo.getItem('olcum.dil');
    const okunan = [al('dilSec')(depo), ESx.dilOku(depo)];
    u.dilSecildi('de');
    const deSonra = [u.dil, depo.getItem('olcum.dil')];
    u.dilSecildi('tr');
    sandbox.window = eskiW;
    ok('[!] AY3: dilSecildi `olcum.dil`e JSON yazar (3C dilOku ile ayni anahtar ve bicim); app ve esitleme.js ayni dili okur; bilinmeyen dil YAZILMAZ',
       yazildi === '"en"' && okunan.join() === 'en,en' && deSonra.join() === 'en,"en"' && u.dil === 'tr'
       && depo.getItem('olcum.dil') === '"tr"' && al('DIL_ANAHTAR') === ESx.DIL_ANAHTAR,
       `${yazildi} ${okunan} ${deSonra}`);
    const eskiD = sandbox.document;
    sandbox.document = { documentElement: {}, createElement: () => ({ click() {} }) };
    secenekler.watch.dil.call({ gorunum: 'ayar' }, 'en');
    const en = [sandbox.document.documentElement.lang, sandbox.document.title];
    secenekler.watch.dil.call({ gorunum: 'canli' }, 'tr');
    const tr = [sandbox.document.documentElement.lang, sandbox.document.title];
    sandbox.document = eskiD;
    ok('[!] AY3: dil degisince ANINDA <html lang> ve sekme basligi (yeniden yukleme yok)',
       en.join('|') === 'en|Settings — Measurement Board' && tr.join('|') === 'tr|Canlı — Ölçüm Kartı', `${en} / ${tr}`);
    ok('AY3: acilista kayitli dil <html lang>e de uygulanir (mounted dilUygula)',
       govdeIcinde(appKaynak, 'mounted', 'dilUygula(this.dil, this.gorunum)'));
    const etiket = (ad) => (html.match(new RegExp(`<${ad} ([^>]*)>`)) || [])[1] || '';
    let kl = null, kr = null;
    const fk = { dil: 'tr', listeKur() { kl = this.dil; }, kur() { kr = this.dil; } };
    if (KLx.KayitlarEkrani.watch && KLx.KayitlarEkrani.watch.dilSecim) KLx.KayitlarEkrani.watch.dilSecim.call(fk, 'en');
    const klDil = fk.dil;
    fk.dil = 'tr';
    if (KRx.KarsilastirEkrani.watch && KRx.KarsilastirEkrani.watch.dilSecim) KRx.KarsilastirEkrani.watch.dilSecim.call(fk, 'en');
    ok('[!] AY3: alt ekranlar (Kayitlar, Karsilastirma, Ayarlar modulu) secili dili ANINDA alir (prop dilSecim; liste/lejant yeniden kurulur)',
       ['kayitlar-ekran', 'karsilastir-ekran', 'ayarlar-ekran'].every((a) => etiket(a).includes(':dil-secim="dil"'))
       && KLx.KayitlarEkrani.props.dilSecim && KRx.KarsilastirEkrani.props.dilSecim && (AY.AyarlarEkrani || { props: {} }).props.dilSecim
       && klDil === 'en' && kl === 'en' && fk.dil === 'en' && kr === 'en', `${klDil} ${kl} ${kr}`);
    const kod = kodKaynaklari.map((k) => yorumsuz(k.kaynak)).join('\n');
    ok('[!] AY3: sayi / tarih bicimi dile bagli DEGIL — toLocaleString, toLocaleDateString, toLocaleTimeString, Intl.NumberFormat / DateTimeFormat YOK',
       !/\.toLocale(?:String|DateString|TimeString)\(|Intl\.(?:NumberFormat|DateTimeFormat)/.test(kod));

    /* EN'de cevrilmemis metinler — GIZLENMEZ, sayilir ve listelenir (AY3). */
    const liste = enEksikleri();
    const gruplar = {};
    for (const e of liste) gruplar[e.yer] = (gruplar[e.yer] || 0) + 1;
    console.log(`     EN'de cevrilmemis ${liste.length} metin (${Object.entries(gruplar).map(([a, n]) => a + ' ' + n).join(' · ')}):`);
    for (const e of liste) console.log(`       [EN?] ${e.yer} ${e.tur}: ${e.metin.slice(0, 90)}`);
    ok('[!] AY3: EN`de cevrilmemis metin sayisi KILITLI (azalirsa kilidi dusur, artarsa yeni metin sozluge girmeli)',
       liste.length === EN_EKSIK_KILIT, `${liste.length} (kilit ${EN_EKSIK_KILIT})`);
    const ayParca = ayar.match(/<nav class="ay-nav"[\s\S]*?<\/nav>/);
    const dilKart = ayar.match(/<section class="kart" v-show="ayarBolum === 'dil-gorunum'" data-ay-bolum="dil">[\s\S]*?<\/section>/);
    ok('[!] AY3: 3H`nin yeni parcalari (ic gezinme, Dil karti, ekran/ayarlar.js) listede YOK — hepsi sozlukten',
       liste.every((e) => e.yer !== 'ekran/ayarlar.js') && !!ayParca && !!dilKart
       && enEksikleri(ayParca[0] + dilKart[0]).length === 0, `${liste.filter((e) => e.yer === 'ekran/ayarlar.js').length}`);
    const ayAnahtar = Object.keys(SZx.SOZLUK).filter((a) => a.startsWith('ay.'));
    const trHarfli = ayAnahtar.filter((a) => a !== 'ay.dil_tr' && /[çğıöşüÇĞİÖŞÜ]/.test(SZx.SOZLUK[a].en));
    ok('AY3: `ay.` metinlerinin EN karsiliginda Turkce harf yok (Türkçe adinin kendisi haric)',
       ayAnahtar.length >= 40 && trHarfli.length === 0, trHarfli.join(' ') || `${ayAnahtar.length} anahtar`);
  }

  /* ── (c) DEPOLAMA (AY4) ─────────────────────────────────────────── */
  {
    const D = AY.depolamaDestegi || (() => ({}));
    const est = { estimate() {}, persist() {}, persisted() {} };
    ok('[!] AY4: storage yoksa SEBEP — guvenli baglam degil (http://kart) / tarayici desteklemiyor; estimate varsa destekli',
       D({ storage: undefined, guvenli: false }).neden === 'guvensiz' && D({ storage: undefined, guvenli: true }).neden === 'yok'
       && D({ storage: {}, guvenli: true }).neden === 'yok' && D({ storage: est, guvenli: true }).destek === true
       && D({ storage: est, guvenli: true }).neden === null && D({ storage: undefined, guvenli: false }).destek === false);
    const yaz = AY.boyutYaz || (() => '');
    ok('AY4: boyut yazimi Kayitlar`la AYNI (kayitlar.baytYaz)',
       [0, 1, 1023, 1024, 1536, 1048575, 1048576, 5.5 * 1048576, -1, NaN].every((n) => yaz(n) === KLx.baytYaz(n)));
    const ky = AY.kotaYazi || (() => '');
    ok('[!] AY4: kota yazisi kullanim / kota / yuzde (sayi bicimi dile gore DEGISMEZ: nokta)',
       ky({ usage: 1536, quota: 1073741824 }, 'tr') === '1.5 KB / 1024.00 MB kullanılıyor (%0.0)'
       && ky({ usage: 300 * 1048576, quota: 1200 * 1048576 }, 'en') === '300.00 MB of 1200.00 MB used (25.0%)'
       && ky({ usage: 5, quota: 0 }, 'tr') === '' && ky(null, 'tr') === '', ky({ usage: 1536, quota: 1073741824 }, 'tr'));
    const S = AY.depoSatirlari || (() => []);
    const akislar = [
      { kimlik: 3, bayt: 100, olusma: 1000, guncelleme: 1790000000000, durum: { son_sira: 40 } },
      { kimlik: 7, bayt: 2048, olusma: 5000, guncelleme: 1790000500000, durum: { son_sira: 12 } },
    ];
    const say = new Map([[3, 4], [7, 2]]);
    const r1 = S({ akislar, oturumSayisi: say, kartKimlik: 3, arsiv: (k) => k === 7 });
    const r2 = S({ akislar, oturumSayisi: say, kartKimlik: null, arsiv: () => false });
    const r3 = S({ akislar, oturumSayisi: new Map(), kartKimlik: 9, arsiv: () => false });
    ok('[!] AY4: akis basina boyut, oturum, son sira, son esitleme, arsiv secimi; yeniden eskiye; kart biliniyorsa ESKI = kartin kimligi degil',
       r1.map((r) => r.kimlik).join() === '7,3' && r1[0].eski === true && r1[1].eski === false && r1[1].guncel === true
       && r1[0].oturum === 2 && r1[0].sonSira === 12 && r1[0].bayt === 2048 && r1[0].boyut === '2.0 KB' && r1[0].arsiv === true
       && r1[1].arsiv === false && r1[0].zaman === 1790000500000 && r1[0].kartBilinen === true, JSON.stringify(r1));
    ok('[!] AY4: kart bilinmiyorsa en YENI acilan akis guncel sayilir (kimlik degisince yeni akis acilir, C2); oturum sayisi yoksa null; kart yeni bicimlendiyse ikisi de eski',
       r2[0].kimlik === 7 && r2[0].guncel === true && r2[1].eski === true && r2[0].kartBilinen === false
       && r3.every((r) => r.eski) && r3[0].oturum === null, JSON.stringify(r2.map((r) => [r.kimlik, r.guncel])));

    /* bilesen: sahte esitleme modulu + sahte storage */
    const AE = AY.AyarlarEkrani || {};
    const cagri = { liste: 0, sil: [], veri: [] };
    const sahteMod = (akisListe) => ({
      esitlemeUygunlugu: ESx.esitlemeUygunlugu,
      arsivOku: (k) => k === 7,
      EsitlemeDenetcisi: class {
        constructor(o) { this.kartAdres = o.kartAdres; }
        async akislar() { return akisListe; }
        async akisVerisi(k) { cagri.veri.push(k); return { kimlik: k, oturumlar: new Map(Array.from({ length: say.get(k) || 0 }, (_, j) => [j + 1, {}])) }; }
        async akisSil(k) { cagri.sil.push(k); akisListe = akisListe.filter((a) => a.kimlik !== k); }
        async kartListesi() { cagri.liste++; return { durum: 'tamam', liste: { kimlik: 3, oturumlar: [] } }; }
      },
    });
    const yap = (props) => {
      const o = bilesen(AE, { bolum: 'depolama', kartAdres: (y) => y, kartTaban: '', tasiyici: 'seri', bagli: false,
        afisSurum: '', dilSecim: 'tr', etkin: true, ...props });
      const m = sahteMod([...akislar]);
      o._esAl = async () => m;
      o._depolama = () => ({ storage: undefined, guvenli: false });
      return o;
    };
    SONRA.push(async () => {
      const o = yap({ tasiyici: 'seri' });
      await o.depoYukle();
      await o.kotaOku();
      const usb = [cagri.liste, o.depoSatir.map((r) => [r.kimlik, r.oturum, r.eski])];
      const o2 = yap({ tasiyici: 'akis', kartTaban: '' });
      await o2.depoYukle();
      ok('[!] AY4: kartin dizini YALNIZ C1 on kosulu tamamken sorulur (USB/demo/baska koken: sorulmaz, en yeni akis guncel)',
         usb[0] === 0 && JSON.stringify(usb[1]) === '[[7,2,false],[3,4,true]]' && cagri.liste === 1
         && JSON.stringify(o2.depoSatir.map((r) => [r.kimlik, r.eski])) === '[[7,true],[3,false]]',
         JSON.stringify(usb) + ' / ' + cagri.liste);
      ok('[!] AY4: storage YOKKEN (http:// kart = guvenli baglam degil) cokmez, sebebi soyler; kota istenmez',
         o.kotaDestek && o.kotaDestek.destek === false && o.kotaDestek.neden === 'guvensiz' && o.kota === null
         && /güvenli bağlam/.test(o.kotaSebep || ''), o.kotaSebep);
      /* iki asamali silme (Kayitlar'la ayni) */
      o.silBasla(7);
      const silahli = o.silOnay;
      await o.kopyaSil(3);              // silahli OLMAYAN kopya: silinmez
      const yanlis = cagri.sil.length;
      await o.kopyaSil(7);
      ok('[!] AY4: kopya silme IKI ASAMALI — silBasla silahlar, YALNIZ silahli kopya silinir, liste yeniden okunur',
         silahli === 7 && yanlis === 0 && cagri.sil.join() === '7' && o.silOnay === null
         && o.depoSatir.map((r) => r.kimlik).join() === '3', `${silahli} ${cagri.sil} ${o.depoSatir.map((r) => r.kimlik)}`);
      o.silBasla(3);
      o.silVazgec(3);
      ok('AY4: Vazgec silahi indirir', o.silOnay === null);
      /* kota + kalici depolama */
      let istendi = 0;
      const st = (izin) => ({ estimate: async () => ({ usage: 2048, quota: 4096 }), persisted: async () => false,
        persist: async () => { istendi++; return izin; } });
      const k1 = yap({});
      k1._depolama = () => ({ storage: st(true), guvenli: true });
      await k1.kotaOku();
      const once = [k1.kota && k1.kota.usage, k1.kalici];
      await k1.kaliciIste();
      const k2 = yap({});
      k2._depolama = () => ({ storage: st(false), guvenli: true });
      await k2.kotaOku();
      await k2.kaliciIste();
      ok('[!] AY4: estimate kullanim/kota, persisted ilk durum; persist() SONUCU yaziliyor (verildi / reddedildi)',
         once.join() === '2048,false' && istendi === 2 && k1.kalici === true && k1.kaliciSonuc === 'ay.kalici_verildi'
         && k2.kalici === false && k2.kaliciSonuc === 'ay.kalici_reddedildi' && /4\.0 KB/.test(k1.kotaMetni), k1.kotaMetni);
    });
    ok('[!] AY4/WIG: sablon — kopya tablosu (caption, th scope), silme iki asamali (Sil -> Eminim + Vazgec + uyari), kalici depolama sonucu canli bolgede',
       /<caption class="gorunmez">\{\{ m\.depoTablo \}\}<\/caption>/.test(T) && /<th scope="row">/.test(T)
       && /<template v-if="silOnay === r\.kimlik">[\s\S]*?:data-ay-sil-eminim="r\.kimlik" @click="kopyaSil\(r\.kimlik\)"[\s\S]*?@click="silVazgec\(r\.kimlik\)"[\s\S]*?<\/template>\s*<button v-else type="button" :data-ay-sil="r\.kimlik" @click="silBasla\(r\.kimlik\)"/.test(T)
       && /<p v-if="silOnay !== null" class="uyari"[^>]*>\{\{ m\.silUyari \}\}/.test(T)
       && /aria-live="polite"[^>]*>[\s\S]{0,200}kaliciSonucMetni/.test(T)
       && /<progress [^>]*:value="kota\.usage" :max="kota\.quota" :aria-label="m\.kota"/.test(T));
    ok('AY4: arsiv secimi (C3) depolamada da gorunur — degistirmek Kayitlar`dan (iki asamali onay orada)',
       /r\.arsiv \? m\.arsivAcik : m\.arsivKapali/.test(T) && /href="#\/kayitlar"/.test(T));
  }

  /* ── (d) KALIBRASYON GECMISI (AY5) ─────────────────────────────── */
  {
    const kn = (k) => ({ n: 21, pga: 4.096, kazanc: k, sifir_ham: 12, tau: 0.5 });
    const fw = { surum: 1, adet: 3, taslak: 0, etkin: 2, azami: 40, kayitlar: [
      { no: 1, unix: 0, acilis: 4, tur: 1, kaynak: 2, not: '', kal: { normal: kn(1), yuksek: kn(1.1), i_ofset: -3, i_pga: 0.256,
        sont_ohm: 0.005, i_duzeltme: 1, sebeke_hz: 0, faz0: 0, faz1: null } },
      { no: 3, bozuk: true },
      { no: 2, unix: 1790000000, acilis: 9, tur: 2, kaynak: 0, not: 'şönt değişti', kal: { normal: kn(1.02), yuksek: kn(1.12),
        i_ofset: 5, i_pga: 0.256, sont_ohm: 0.0049, i_duzeltme: 1.01, sebeke_hz: 50, faz0: 12.5, faz1: -3 } },
    ] };
    const C = AY.kalListesiCoz || (() => null);
    const c = C(fw);
    ok('[!] AY5: kalListesiCoz — firmware bicimi (surum, adet, taslak, etkin, azami, kayitlar); bozuk kayit SESSIZCE atlanmaz; numara sirasi',
       !!c && c.adet === 3 && c.taslak === false && c.etkin === 2 && c.azami === 40 && c.kayitlar.map((k) => k.no).join() === '1,2,3'
       && c.kayitlar[2].bozuk === true && c.kayitlar[1].not === 'şönt değişti' && c.kayitlar[0].kal.yuksek.kazanc === 1.1);
    ok('AY5: bicimsiz girdi -> null (atmaz); taslak bayragi 1 -> true',
       [null, 'x', 5, {}, { kayitlar: 'x' }, []].every((v) => C(v) === null) && C({ ...fw, taslak: 1, etkin: 0 }).taslak === true);
    const R = AY.kalSatirlari || (() => []);
    const rt = R(c, 'tr');
    const re = R(c, 'en');
    ok('[!] AY5: satirlar YENIDEN ESKIYE; etkin olan isaretli; tur / kaynak sozluk ailesinden (kal.tur., kal.kaynak.); saatsiz kayit acilis numarasiyla',
       rt.map((r) => r.no).join() === '3,2,1' && rt[1].etkin === true && rt.filter((r) => r.etkin).length === 1
       && rt[1].tur === SZx.ceviriKod('kal.tur.', 2, 'tr') && rt[1].kaynak === SZx.ceviriKod('kal.kaynak.', 0, 'tr')
       && re[1].tur === 'fine tuning' && /4/.test(rt[2].tarih) && rt[2].tarih === SZx.ceviri('ay.kal_saatsiz', 'tr', { acilis: 4 })
       && rt[0].bozuk === true && rt[0].tur === SZx.ceviri('kal.durum.bozuk', 'tr') && /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(rt[1].tarih),
       JSON.stringify(rt.map((r) => [r.no, r.tarih, r.etkin])));
    /* firmware'in /kal/liste JSON alanlari (kal_liste_sayfa) — elle liste DEGIL */
    const govde = (ino.match(/void kal_liste_sayfa\(\) \{([\s\S]*?)\n\}\n/) || [])[1] || '';
    const alanlar = [...govde.matchAll(/kal_json_f\(t, sizeof\(t\), "(\w+)"|\\"(\w+)\\":%d/g)].map((m) => m[1] || m[2]);
    const kanallar = /i \? "(\w+)" : "(\w+)"/.exec(govde);
    const fwAlan = kanallar ? [...[kanallar[2], kanallar[1]].flatMap((k) => alanlar.slice(0, 5).map((a) => `${k}.${a}`)), ...alanlar.slice(5)] : [];
    const KA = AY.KAL_ALANLARI || [];
    ok('[!] AY5: degerler tablosunun alanlari FIRMWARE`in /kal/liste JSON`undan (kal_liste_sayfa) — 17 alan, ayni sira; adlari sozlukte',
       fwAlan.length === 17 && KA.map((a) => a.alan).join() === fwAlan.join()
       && KA.every((a) => a.ad in SZx.SOZLUK), fwAlan.join(' '));
    const kalgec = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kalgec.h'), 'utf8');
    const uyari = Number((/#define KALGEC_UYARI\s+(\d+)u/.exec(kalgec) || [])[1]);
    const ozet = (ad, liste) => { const o = bilesen(AY.AyarlarEkrani || {}, { bolum: 'kal-gecmis', kartAdres: (y) => y, dilSecim: 'tr' }); o.kalListe = liste; return o[ad]; };
    ok('AY5: "dolmak uzere" esigi firmware`in KALGEC_UYARI`si (kalgec.h); esikte uyari var, altinda yok',
       uyari > 0 && AY.KAL_UYARI === uyari && /35 \/ 40/.test(ozet('kalDoluYazi', { ...c, adet: uyari, azami: 40 }))
       && ozet('kalDoluYazi', { ...c, adet: uyari - 1 }) === '', `${uyari}`);
    const dg = (AY.kalDegerleri || (() => []))(c.kayitlar[0].kal, 'tr');
    ok('AY5: kalDegerleri — degerler oldugu gibi (JSON sayisi), null -> "—", alan adi ham (mono) + sozluk etiketi',
       dg.length === 17 && dg.find((d) => d.alan === 'yuksek.kazanc').deger === '1.1' && dg.find((d) => d.alan === 'faz1').deger === '—'
       && dg.find((d) => d.alan === 'i_ofset').deger === '-3' && dg[0].ad === SZx.ceviri(KA[0].ad, 'tr')
       && (AY.kalDegerleri || (() => []))(null, 'tr').length === 0);
    /* kaynak secimi: kart -> yerel kopya; komut YOK */
    const AE = AY.AyarlarEkrani || {};
    const yerelKal = new TextEncoder().encode(JSON.stringify({ ...fw, etkin: 1 }));
    const fetchler = [];
    const sahteFetch = (kod, govde_) => async (u, o) => { fetchler.push([u, o]); return { status: kod, ok: kod === 200, json: async () => govde_, text: async () => '' }; };
    const yap = (props, fetchFn, yerelVar = true) => {
      const o = bilesen(AE, { bolum: 'kal-gecmis', kartAdres: (y) => 'K' + y, kartTaban: '', tasiyici: 'akis', bagli: true,
        afisSurum: '', dilSecim: 'tr', etkin: true, ...props });
      o._esAl = async () => ({
        esitlemeUygunlugu: ESx.esitlemeUygunlugu, kalJsonCoz: ESx.kalJsonCoz,
        EsitlemeDenetcisi: class { async akislar() { return yerelVar ? [{ kimlik: 5, olusma: 2, guncelleme: 1790000600000, kalVar: true }, { kimlik: 4, olusma: 1, kalVar: true }] : []; } },
      });
      o._idbAl = async () => ({ vtAc: async () => ({}), idbDepo: (vt, k) => ({ kalOku: async () => (k === 5 ? yerelKal : null) }) });
      o.__fetch = fetchFn;
      return o;
    };
    /* ekran modulu node'un GERCEK fetch'ini kullanir (B7 kurali: her fetch kartAdres'ten) — gecici degistirilir */
    const yukle = async (o) => {
      const eski = globalThis.fetch;
      globalThis.fetch = o.__fetch;
      try { await o.kalYukle(); } finally { globalThis.fetch = eski; }
    };
    SONRA.push(async () => {
      const a = yap({}, sahteFetch(200, fw));
      await yukle(a);
      const b2 = yap({}, sahteFetch(401, null));
      await yukle(b2);
      const c2 = yap({ tasiyici: 'seri' }, sahteFetch(200, fw));
      const once = fetchler.length;
      await yukle(c2);
      const d = yap({ kartTaban: '192.0.2.1' }, sahteFetch(200, fw), false);
      await yukle(d);
      ok('[!] AY5: kaynak — ayni kokenli kartta /kal/liste (kartAdres, no-store); 401/404/ag -> bu tarayicidaki EN YENI kopya (sebep yazilir); USB/baska koken -> karta sorulmaz',
         a.kalKaynak === 'kart' && a.kalListe && a.kalListe.etkin === 2 && fetchler[0][0] === 'K/kal/liste'
         && fetchler[0][1] && fetchler[0][1].cache === 'no-store'
         && b2.kalKaynak === 'yerel' && b2.kalNeden === 'imza' && b2.kalListe.etkin === 1 && b2.kalYerel.kimlik === 5
         && c2.kalKaynak === 'yerel' && c2.kalNeden === 'usb' && fetchler.length === once
         && d.kalKaynak === null && d.kalListe === null && d.kalNeden === 'taban', `${a.kalKaynak} ${b2.kalKaynak}/${b2.kalNeden} ${c2.kalNeden} ${d.kalNeden}`);
      ok('AY5: yerel kopyanin kaynagi ve tarihi yazilir; karttan gelince "kartin geçmişi"',
         /5/.test(b2.kalKaynakYazi) && /kart/i.test(a.kalKaynakYazi) && a.kalKaynakYazi !== b2.kalKaynakYazi, b2.kalKaynakYazi);
    });
    ok('[!] AY5: SALT OKUMA — ekran/ayarlar.js komut GONDERMEZ (gonder / komut / /komut / POST / kk kn kt yok), yalniz /kal/liste ve /kunye.json okur',
       !!ayKod && !/\bgonder\b|\bkomut\(|\/komut|method:|'k[knt]|"k[knt]|`k[knt]/.test(ayKod) && !('gonder' in ((AE || {}).props || {}))
       && [...ayKod.matchAll(/(?:kartAdres|_istek)\('([^']+)'/g)].map((m) => m[1]).sort().join() === '/kal/liste,/kunye.json');
    ok('[!] AY5/WIG: sablon — gecmis tablosu (caption, th scope), etkin satir METINLE (renk degil), degerler ayri tablo, taslak uyarisi',
       /<caption class="gorunmez">\{\{ m\.kalTablo \}\}<\/caption>/.test(T) && /<th scope="col">\{\{ m\.kalNo \}\}<\/th>/.test(T)
       && /r\.etkin \? m\.kalEtkin/.test(T) && /<caption class="ay-tablo-baslik">\{\{ kalDegerBaslik \}\}<\/caption>/.test(T)
       && /v-if="kalListe && kalListe\.taslak"/.test(T) && /:aria-pressed="kalSecili === r\.no \? 'true' : 'false'"/.test(T));
  }

  /* ── (e) GELISMIS (AY6) ─────────────────────────────────────────── */
  {
    const depo = sahteDepo({ 'olcum.dil': '"en"', 'olcum.tema': '"acik"', 'olcum.arsiv.7': 'true', baska: '1', olcumx: '2', 'olcum.': '3' });
    const A = (AY.olcumAnahtarlari || (() => null))(depo);
    const sil = (AY.ayarlariSifirla || (() => null))(depo);
    ok('[!] AY6: sifirlama YALNIZ `olcum.` onekli localStorage anahtarlarini siler (baska anahtar / IndexedDB kopyalari kalir)',
       JSON.stringify(A) === '["olcum.","olcum.arsiv.7","olcum.dil","olcum.tema"]' && JSON.stringify(sil) === JSON.stringify(A)
       && [...depo.m.keys()].sort().join() === 'baska,olcumx' && !/indexedDB|akisSil/.test(String(AY.ayarlariSifirla)));
    ok('AY6: depo engelliyse (ozel kip) atmaz, bos liste',
       JSON.stringify((AY.olcumAnahtarlari || (() => null))(sahteDepo({}, true))) === '[]'
       && JSON.stringify((AY.ayarlariSifirla || (() => null))(sahteDepo({}, true))) === '[]'
       && JSON.stringify((AY.olcumAnahtarlari || (() => null))(null)) === '[]');
    const AE = AY.AyarlarEkrani || {};
    const o = bilesen(AE, { bolum: 'gelismis', kartAdres: (y) => y, kartTaban: '', tasiyici: 'akis', bagli: true,
      afisSurum: 'A3-1D', dilSecim: 'tr', etkin: true });
    const d2 = sahteDepo({ 'olcum.dil': '"tr"', x: '1' });
    let yuklendi = 0;
    o._yerelDepo = () => d2;
    o._yenidenYukle = () => { yuklendi++; };
    if (o.sifirla) o.sifirla();
    const onaysiz = [d2.m.size, yuklendi];
    if (o.sifirlaBasla) o.sifirlaBasla();
    if (o.sifirla) o.sifirla();
    ok('[!] AY6: sifirlama IKI ASAMALI — onaysiz cagri hicbir sey silmez; onaydan sonra siler ve sayfayi yeniden yukler (varsayilanlar uygulansin)',
       onaysiz.join() === '2,0' && d2.m.size === 1 && d2.m.has('x') && yuklendi === 1);
    ok('[!] AY6/WIG: sablon — sifirla dugmesi -> "Eminim" + Vazgec; silinecek anahtarlar LISTELENIR; konsol baglantisi; firmware afisten',
       /<template v-if="sifirlaOnay">[\s\S]*?data-ay-sifirla-eminim[\s\S]*?@click="sifirla"[\s\S]*?@click="sifirlaVazgec"[\s\S]*?<\/template>\s*<button v-else type="button" data-ay-sifirla @click="sifirlaBasla"/.test(T)
       && /v-for="a in anahtarlar"/.test(T) && /href="#\/konsol"/.test(T) && /afisSurum \|\| m\.fwYok/.test(T));
    const K = AY.kunyeCoz || (() => undefined);
    ok('AY6: kunyeCoz — surum 12 onaltilik, dosya / bayt sayisi; bicimsiz -> null',
       JSON.stringify(K({ surum: '0123456789ab', dosya: 31, icerik_bayt: 600000, bicim: 1 })) === '{"surum":"0123456789ab","dosya":31,"bayt":600000}'
       && K({ surum: 'xyz', dosya: 1, icerik_bayt: 1 }) === null && K(null) === null && K({ surum: '0123456789AB', dosya: 1, icerik_bayt: 1 }) === null);
    /* panel surumu: _fs.json ozeti Python (arayuz-uret.py) ile node ayni sonucu veriyor mu */
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const k = fs.existsSync(kunyeYolu) ? JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')) : {};
    const satirlar = Object.keys(k.kaynak || {}).sort().map((a) => `${a}:${k.kaynak[a]}\n`).join('');
    const nodeSurum = require('crypto').createHash('sha256').update(satirlar, 'utf8').digest('hex').slice(0, 12);
    const uret = fs.readFileSync(path.join(KOK, 'uretim', 'arayuz-uret.py'), 'utf8');
    const sun = fs.readFileSync(path.join(ARAYUZ, 'sunucu.py'), 'utf8');
    ok('[!] AY6: panel surumu = _fs.json kaynak ozetinin sha256`si (ilk 12): Python (arayuz-uret.py) ile node AYNI; goruntuye kunye.json yaziliyor, sunucu.py de ayni islevle sunuyor',
       /^[0-9a-f]{12}$/.test(k.panel_surum || '') && k.panel_surum === nodeSurum && Number.isFinite((k.bayt || {})['kunye.json'])
       && /def panel_kunyesi\(/.test(uret) && /"kunye\.json\.gz"|kunye\.json/.test(uret)
       && /"\/kunye\.json"/.test(sun) && /u\.kunye_hesapla\(\)/.test(sun) && /return panel_kunyesi\(kaynak_ozeti\(\)/.test(uret),
       `${k.panel_surum} / ${nodeSurum}`);
  }

  /* ── (f) WIG (AY7) + telefon ────────────────────────────────────── */
  {
    const blok = css.slice(css.indexOf('3H — AYARLAR'));
    const kod = blok.replace(/\/\*[\s\S]*?\*\//g, '');
    ok('[!] AY7: 3H stilleri YALNIZ belirtecle; ic gezinmede odak gorunur, etkin bolum renkten ote (kalin + cizgi); sayilar tabular-nums',
       css.includes('3H — AYARLAR') && !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(kod)
       && /\.ay-sekme:focus-visible \{[^}]*outline: 2px solid var\(--vurgu\)/.test(kod)
       && /\.ay-sekme\.etkin \{[^}]*font-weight: 600[^}]*box-shadow: inset 3px 0 0 var\(--vurgu\)/.test(kod)
       && /\.ay-tablo td \{[^}]*font-variant-numeric: tabular-nums/.test(kod));
    ok('[!] AY2: telefonda (<= 900 px) ic gezinme icerigin USTUNDE (tek sutun), genis ekranda solda',
       /\.ay-duzen \{[^}]*grid-template-columns: 200px minmax\(0, 1fr\)/.test(kod)
       && /@media \(max-width: 900px\) \{[^}]*\.ay-duzen \{ grid-template-columns: minmax\(0, 1fr\); \}/.test(kod));
    const dugmeler = [...T.matchAll(/<button\b([^>]*)>/g)].map((m) => m[1]);
    ok('AY7/WIG: ayarlar modulunun BUTUN dugmeleri type="button"; tablolar kendi kutusunda kayar (390 px tasma yok)',
       dugmeler.length >= 6 && dugmeler.every((a) => /type="button"/.test(a)) && /\.ay-tablo-sarmal \{[^}]*overflow-x: auto/.test(kod),
       `${dugmeler.length} dugme`);
    const dil = ayar.match(/<section class="kart" v-show="ayarBolum === 'dil-gorunum'" data-ay-bolum="dil">([\s\S]*?)<\/section>/);
    ok('[!] AY3/WIG: Dil secici dugme grubu (adli), secili aria-pressed, her dugmenin lang`i kendi dili',
       !!dil && /<div class="dugme-grup" role="group" :aria-label="ay\.dil">/.test(dil[1])
       && /<button v-for="d in dilSecenekleri" :key="d\.id" type="button" :lang="d\.id"/.test(dil[1])
       && /:aria-pressed="dil === d\.id \? 'true' : 'false'"/.test(dil[1]) && /@click="dilSecildi\(d\.id\)"/.test(dil[1]));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   31. ESLESTIRME (3H-2 — tarayicidan eslestirme, ES1-ES10; uygulama kararlari 3H-2)

   Kararlar tasarim/2026-10-02-alt-proje-3-panel.md "3H-2 kararlari". Burada:
   (a) KABLOLAMA: Ayarlar'da sekizinci bolum `#/ayar/eslestirme`; ekran modulu
       (ekran/eslesme.js + ortak/imza.js + kripto.js) ACILISTA INMEZ — yalniz
       bu tarayicida bir cihaz kaydi varsa ya da bolum acilinca (dinamik import).
       EU30: Eslestirme EKRANI ve metinleri (eslesme_ekran.js + ortak/sozluk_es.js)
       istemciden ayri — yalniz bolum acilinca; eslesmis acilisa girmez.
   (b) ISTEK KATMANI (ES4): kartin uclari (/komut, /kayit/*, /kal/liste, /pil,
       /skop.bin, /kunye.json, /akis) TEK katmandan (app.js kartIstek); ekranlar
       fetch'i kendileri imzalamaz. Kayit yoksa bugunku yol AYNEN.
   (c) EMNIYET-P0: `p0` imza katmanina HIC girmez (kart onu K11 geregi imzasiz
       kabul ediyor): katman askida / bozuk olsa da tek tikla gider.
   (d) SAF MANTIK (node, GERCEK ortak/imza.js ile): yol ayirma, SSE cozucu,
       artan bekleme, ret sebepleri, kayit birlestirme (sayac TEKDUZE).
   (e) ISTEMCI (sahte fetch + bellek deposu): imzali istek basliklari, sayac
       istekten ONCE yazilir, ES5 tek yeniden deneme, "kart tanimiyor" -> imzasiz
       yol + bildirim, yeni acilis, unut, eslestirme (parola hicbir yere yazilmaz).
   (f) AKIS (ES6): imzali URL, koptugunda YENI imzali URL + artan bekleme.
   (g) SABLON (WIG, ES3/ES7/ES8/ES9).
   Imzanin BAGIMSIZ dogrulamasi (kopru/imza.py) ve gercek tarayici (IndexedDB,
   iki sekme, SSE, Basic-Auth onbellegi): tarayici_eslestirme.py (T3H2).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 31. Eslestirme (3H-2) ---');
{
  const html = yorumsuz(htmlKaynak);
  const al = (ad) => { try { return vm.runInContext(ad, sandbox); } catch (e) { return undefined; } };
  const IMx = require(path.join(KOK, 'ortak', 'src', 'imza.js'));
  const KRx = require(path.join(KOK, 'ortak', 'src', 'kripto.js'));
  const SZx = require(path.join(KOK, 'ortak', 'src', 'sozluk.js'));
  const esYolu = path.join(ARAYUZ, 'ekran', 'eslesme.js');
  /* EU30: Ayarlar > Eslestirme ekrani + metinleri (ortak/sozluk_es.js) ayri modulde — eslesmis tarayicinin
     acilisi yalniz istemciyi (eslesme.js) indirir. Testler iki modulun disa aktarimini birlikte gorur. */
  const esEkYolu = path.join(ARAYUZ, 'ekran', 'eslesme_ekran.js');
  let ES = {};
  try { ES = require(esYolu); } catch (h) { console.log('     ekran/eslesme.js yuklenemedi: ' + h.message); }
  let ESE = {};
  try { ESE = require(esEkYolu); } catch (h) { console.log('     ekran/eslesme_ekran.js yuklenemedi: ' + h.message); }
  ES = Object.assign({}, ES, ESE);
  let SEx = { SOZLUK_ES: {}, ceviriEs: (a) => String(a) };
  try { SEx = require(path.join(KOK, 'ortak', 'src', 'sozluk_es.js')); } catch (h) { console.log('     ortak/sozluk_es.js yuklenemedi: ' + h.message); }
  const esKaynak = [esYolu, esEkYolu].filter((y) => fs.existsSync(y)).map((y) => fs.readFileSync(y, 'utf8')).join('\n');
  const esKod = yorumsuz(esKaynak);
  const ayKod = yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'ayarlar.js'), 'utf8'));
  const esitKod = yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'esitleme.js'), 'utf8'));
  const appKod = yorumsuz(appKaynak);
  const T = (ES.EslestirmeEkrani && ES.EslestirmeEkrani.template) || '';
  const BOLUMLER = al('AYAR_BOLUMLERI') || [];
  const ayar = (html.match(/<main class="gorunum" v-show="gorunum === 'ayar'">([\s\S]*?)<\/main>/) || [])[1] || '';
  const uyu = () => new Promise((r) => setImmediate(r));
  const bayt = (s) => new TextEncoder().encode(s);
  /* sahte yanit (fetch'in Response'u): durum, govde, basliklar */
  const yanit = (durum, govde = '', bas = {}) => new Response(durum === 204 ? null : govde, { status: durum, headers: bas });
  /* bellek deposu: cihazDeposu ile AYNI arayuz, ayni birlestirme kurali (kayitBirlestir) */
  const bellekDepo = () => {
    const m = new Map();
    const log = [];
    return {
      m, log,
      async oku(k) { const c = m.get(k); return c ? { ...c } : null; },
      async yaz(c, o = {}) {
        const y = (ES.kayitBirlestir || ((a, b) => b))(m.get(c.kimlik) || null, c, o);
        if (y) m.set(c.kimlik, { ...y });
        log.push(['yaz', c.sayac]);
        return y;
      },
      async ayir(c, simdi) {
        const r = (ES.sayacAyir || (() => null))(m.get(c.kimlik) || null, c, simdi);
        if (r) m.set(c.kimlik, { ...r.kayit });
        log.push(['ayir', r && r.s]);
        return r ? { s: r.s, tanimiyor: r.tanimiyor } : null;
      },
      async sil(k) { m.delete(k); log.push(['sil', k]); },
      async hepsi() { return [...m.values()]; },
    };
  };
  const KIMLIK = '0123456789abcdef';
  const ACILIS = 'a'.repeat(32);
  const ACILIS2 = 'b'.repeat(32);
  const K = new Uint8Array(32).map((_, i) => i + 1);
  const bilgiJson = (ek = {}) => JSON.stringify({ surum: 'OK1', kimlik: KIMLIK, acilis: ACILIS, tuz: '00'.repeat(16), tur: 10000,
    zorunlu: 0, misafir: 0, saat: 0, cihaz_azami: 8, ...ek });
  /* kanonik imza kontrolu: URL + basliklar -> imza.js imzala ile AYNI mi */
  const imzaDogru = (url, sec, acilis = ACILIS, k = K) => {
    const u = new URL(url, 'http://x');
    const args = [...u.searchParams.entries()].filter(([a]) => !['_c', '_s', '_i'].includes(a));
    const h = sec.headers || {};
    const govde = sec.body === undefined ? new Uint8Array(0) : (typeof sec.body === 'string' ? bayt(sec.body) : sec.body);
    return h['X-Imza'] === IMx.imzala(k, sec.method || 'GET', u.pathname, args, acilis, Number(h['X-Sayac']), govde);
  };

  /* ── (a) KABLOLAMA ──────────────────────────────────────────────── */
  {
    const es = BOLUMLER.find((b) => b.id === 'eslestirme');
    ok('[!] ES1: Ayarlar`da sekizinci bolum `eslestirme` (Ag`dan sonra), adi sozlukte; tembel ayarlar.js`in bolumu DEGIL (kendi modulu)',
       BOLUMLER.map((b) => b.id).join(' ') === 'baglanti ag eslestirme kalibrasyon kal-gecmis depolama dil-gorunum gelismis'
       && !!es && es.mod === false && es.es === true && es.ad === 'ay.b_eslestirme'
       && SZx.SOZLUK['ay.b_eslestirme'].tr === 'Eşleştirme' && al('ayarBolumCoz')('#/ayar/eslestirme') === 'eslestirme',
       BOLUMLER.map((b) => b.id).join(' '));
    const e = ayar.match(/<eslestirme-ekran ([^>]*)>/);
    ok('[!] ES1: eslestirme-ekran Ayarlar`in icinde, YALNIZ gerekince (v-if eslesmeModAcik), bolumu secilince gorunur; istemci app`in TEK istemcisi',
       !!e && /^v-if="eslesmeModAcik" v-show="ayarBolum === 'eslestirme'"/.test(e[1])
       && [':istemci-al="eslesmeIstemcisi"', ':kart-taban="kartTaban"', ':tasiyici="tasiyiciAdi"', ':bagli="bagli"',
         ':dil-secim="dil"', ":etkin=\"gorunum === 'ayar' && ayarBolum === 'eslestirme'\""].every((x) => e[1].includes(x)),
       e ? e[1] : 'yok');
    const b = secenekler.components && secenekler.components['eslestirme-ekran'];
    const sec = b && b.yukleyici && typeof b.yukleyici === 'object' ? b.yukleyici : {};
    ok('[!] ES1/EU30: eslestirme-ekran ASENKRON: ./ekran/eslesme_ekran.js (EslestirmeEkrani; istemciden AYRI modul); inmezse sebep, secili dilde',
       !!b && b.__asenkron === true && /import\('\.\/ekran\/eslesme_ekran\.js'\)\.then\(\(m\) => m\.EslestirmeEkrani\)/.test(String(sec.loader))
       && !!sec.errorComponent && /class="hata"/.test(sec.errorComponent.template || '') && typeof T === 'string' && T.length > 0);
    const gerekli = secenekler.computed && secenekler.computed.eslesmeModGerekli;
    const w = secenekler.watch && secenekler.watch.eslesmeModGerekli;
    const s1 = { gorunum: 'ayar', ayarBolum: 'eslestirme', eslesmeModAcik: false };
    if (w) w.call(s1, true);
    sandbox.location = { hash: '#/ayar/eslestirme' };
    const d1 = secenekler.data();
    sandbox.location = { hash: '#/ayar/ag' };
    const d2 = secenekler.data();
    delete sandbox.location;
    ok('[!] ES1: modul YALNIZ Ayarlar`da Eslestirme bolumu seciliyken iner (bir kez); #/ayar/eslestirme ile acilis da indirir, baska bolum indirmez',
       !!gerekli && gerekli.call(s1) === true && gerekli.call({ gorunum: 'canli', ayarBolum: 'eslestirme' }) === false
       && gerekli.call({ gorunum: 'ayar', ayarBolum: 'ag' }) === false && s1.eslesmeModAcik === true
       && d1.eslesmeModAcik === true && d2.eslesmeModAcik === false && d1.ayarModAcik === false);
    const statik = iceAktarmaGrafigi().map((x) => x.goruntu);
    const esAgac = fs.existsSync(esYolu) ? iceAktarmaGrafigi(esYolu).map((x) => x.goruntu).sort() : [];
    const dinamik = [...appKod.matchAll(/import\('\.\/ekran\/eslesme\.js'\)/g)].length;
    const dinamikEk = [...appKod.matchAll(/import\('\.\/ekran\/eslesme_ekran\.js'\)/g)].length;
    ok('[!] ES2/butce: eslesme.js (ve imza.js / kripto.js) ACILISTA inmiyor; app.js istemciyi YALNIZ dinamik ister (eslesmeIstemcisi), ekrani YALNIZ bilesen yukleyicisi (EU30)',
       !statik.includes('ekran/eslesme.js') && !statik.includes('ortak/imza.js') && !statik.includes('ortak/kripto.js')
       && esAgac.join(' ') === 'ortak/imza.js ortak/kripto.js' && dinamik === 1 && dinamikEk === 1
       && govdeIcinde(appKaynak, 'eslesmeIstemcisi', "import('./ekran/eslesme.js')"), esAgac.join(' '));
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const by = fs.existsSync(kunyeYolu) ? (JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {}) : {};
    const esBayt = ['ekran/eslesme.js', ...esAgac].filter((x) => !statik.includes(x)).reduce((n, a) => n + (by[a] || 0), 0);
    ok('[!] ES2/butce: eslesme zinciri (acilista olmayan kismi; yalniz eslesmis tarayicida acilista) <= 24 KB gzip; eslesme.js (istemci) <= 10 KB gzip',
       esBayt > 0 && esBayt <= 24 * 1024 && by['ekran/eslesme.js'] > 0 && by['ekran/eslesme.js'] <= 10 * 1024,
       `${esBayt} B (eslesme.js ${by['ekran/eslesme.js']} B)`);
    /* Bilgi (iddia DEGIL): ESLESMIS bir tarayicida acilis bu zinciri de indirir (AU12 deseni). */
    console.log(`     eslesmis tarayicida acilisa eklenen: ${esBayt} B gzip (eslesme.js + imza.js + kripto.js)`);
    /* EU30: Eslestirme EKRANI + metinleri yalniz bolum acilinca; eslesmis tarayicinin acilisina GIRMEZ */
    const ekAgac = fs.existsSync(esEkYolu) ? iceAktarmaGrafigi(esEkYolu).map((x) => x.goruntu) : [];
    const ekZincir = ['ekran/eslesme_ekran.js', ...ekAgac].filter((x, i, a) => a.indexOf(x) === i && !statik.includes(x) && x !== 'ekran/eslesme.js' && !esAgac.includes(x));
    const ekBayt = ekZincir.reduce((n, a) => n + (Number.isFinite(by[a]) ? by[a] : NaN), 0);
    ok('[!] EU30: Eslestirme ekraninin metinleri (ortak/sozluk_es.js) ACILISTA DEGIL ve istemci zincirinde DEGIL — yalniz ekran modulunun (eslesme_ekran.js) agacinda; ekran zinciri <= 14 KB gzip',
       !statik.includes('ortak/sozluk_es.js') && !esAgac.includes('ortak/sozluk_es.js') && ekAgac.includes('ortak/sozluk_es.js')
       && !statik.includes('ekran/eslesme_ekran.js') && !esAgac.includes('ekran/eslesme_ekran.js')
       && ekZincir.join(' ') === 'ekran/eslesme_ekran.js ortak/sozluk_es.js' && ekBayt > 0 && ekBayt <= 14 * 1024,
       `${ekZincir.join(' ')} · ${ekBayt} B · istemci agaci: ${esAgac.join(' ')}`);
    const acilisEs = Object.keys(SZx.SOZLUK).filter((a) => /^es\./.test(a)).sort();
    const kabukEs = [...new Set([...appKod.matchAll(/'(es\.[a-z0-9_]+)'/g)].map((m) => m[1]))].sort();
    ok('[!] EU30: acilis sozlugunde (ortak/sozluk.js) YALNIZ kabugun es. metinleri (serit uyarisi, akis hatasi, modul yuklenemedi); ekranin metinleri sozluk_es.js`te, iki sozluk ayrik',
       acilisEs.length >= 4 && acilisEs.join() === kabukEs.join() && acilisEs.includes('es.uyari_modul')
       && Object.keys(SEx.SOZLUK_ES).length >= 70 && Object.keys(SEx.SOZLUK_ES).every((a) => /^es\./.test(a) && !(a in SZx.SOZLUK)),
       `acilista ${acilisEs.join(' ')} · sozluk_es ${Object.keys(SEx.SOZLUK_ES).length} anahtar`);
  }

  /* ── cihazKaydiVar: eslesme YOKSA IndexedDB'de veritabani YARATMAZ ── */
  {
    const var_ = al('cihazKaydiVar');
    const sahteIdb = ({ liste = null, var: vt = null, at = false } = {}) => {
      const iz = { acilan: 0, iptal: 0, yaratilan: 0 };
      const idb = {
        iz,
        open(ad) {
          if (at) throw new Error('engelli');
          iz.acilan++;
          const r = {};
          setImmediate(() => {
            if (!vt || ad !== vt.ad) {
              /* yeni veritabani: onupgradeneeded (oldVersion 0); iptal edilirse onerror */
              r.transaction = { abort() { iz.iptal++; } };
              r.result = { close() {}, objectStoreNames: { contains: () => false } };
              if (r.onupgradeneeded) r.onupgradeneeded({ oldVersion: 0 });
              if (iz.iptal) { r.error = new Error('AbortError'); if (r.onerror) r.onerror(); return; }
              iz.yaratilan++;
              if (r.onsuccess) r.onsuccess();
              return;
            }
            r.result = {
              close() {},
              objectStoreNames: { contains: (d) => d === vt.depo },
              transaction: () => ({ objectStore: () => ({ count() { const q = {}; setImmediate(() => { q.result = vt.adet; q.onsuccess(); }); return q; } }) }),
            };
            if (r.onsuccess) r.onsuccess();
          });
          return r;
        },
      };
      if (liste) idb.databases = async () => liste;
      return idb;
    };
    SONRA.push(async () => {
      const VT = al('CIHAZ_VT_AD');
      const yok1 = sahteIdb();
      const r1 = typeof var_ === 'function' ? await var_(yok1) : 'yok';
      const yok2 = sahteIdb({ liste: [{ name: 'olcum-kayit' }] });
      const r2 = typeof var_ === 'function' ? await var_(yok2) : 'yok';
      const dolu = sahteIdb({ liste: [{ name: VT }], var: { ad: VT, depo: 'cihaz', adet: 1 } });
      const r3 = typeof var_ === 'function' ? await var_(dolu) : 'yok';
      const bos = sahteIdb({ var: { ad: VT, depo: 'cihaz', adet: 0 } });
      const r4 = typeof var_ === 'function' ? await var_(bos) : 'yok';
      const r5 = typeof var_ === 'function' ? await var_(sahteIdb({ at: true })) : 'yok';
      const r6 = typeof var_ === 'function' ? await var_(null) : 'yok';
      ok('[!] ES4: cihazKaydiVar — kayit yoksa false ve veritabani YARATILMAZ (yukseltme iptal); databases() listesinde yoksa hic ACILMAZ; kayit varsa true; IndexedDB yok / atar -> false',
         r1 === false && yok1.iz.iptal === 1 && yok1.iz.yaratilan === 0 && r2 === false && yok2.iz.acilan === 0
         && r3 === true && r4 === false && r5 === false && r6 === false
         && VT === ES.CIHAZ_VT && al('CIHAZ_DEPO_AD') === ES.CIHAZ_DEPO && ES.CIHAZ_DEPO === 'cihaz',
         JSON.stringify({ r1, i1: yok1.iz, r2, a2: yok2.iz.acilan, r3, r4, r5, r6, VT }));
    });
  }

  /* ── (b) ISTEK KATMANI (ES4) ────────────────────────────────────── */
  {
    const UCLAR = /'\/(komut|kayit\/|kal\/liste|pil|skop\.bin|kunye\.json|akis|cihaz\/|saat|eslestir\/)/;
    const kaynaklar = kodKaynaklari.filter((k) => k.ad !== 'ekran/eslesme.js');
    const ciplak = [];
    for (const k of kaynaklar) {
      for (const m of yorumsuz(k.kaynak).matchAll(/fetch\(([^\n]*)/g)) if (UCLAR.test(m[1])) ciplak.push(k.ad + ': ' + m[1].slice(0, 60));
    }
    /* p0'in KASITLI ciplak yolu (EMNIYET) tek istisna */
    const p0Yolu = ciplak.filter((c) => c.startsWith("app.js: uyg.kartAdres('/komut')"));
    const kalan = ciplak.filter((c) => !p0Yolu.includes(c));
    const istekler = [...appKod.matchAll(/kartIstek\('([^'?]+)/g)].map((m) => m[1]);
    ok('[!] ES4: kartin uclarina giden HER fetch tek katmandan (kartIstek); dogrudan fetch YALNIZ p0`in emniyet yolu',
       kalan.length === 0 && p0Yolu.length === 1 && ['/komut', '/pil', '/skop.bin'].every((u) => istekler.includes(u))
       && /this\._istek\('\/kal\/liste'/.test(ayKod) && /this\._istek\('\/kunye\.json'/.test(ayKod)
       && /this\._getir\(yol/.test(esitKod) && /this\._getir\('\/kayit\/liste'/.test(esitKod),
       kalan.join(' | ') || `${istekler.join(' ')} + p0`);
    ok('[!] ES4: ekranlar istek katmanini ALIR: Kayitlar ve Ayarlar `:kart-istek`, Pil esitlemesi kartIstek, denetci `istek` ile kurulur',
       /<kayitlar-ekran [^>]*:kart-istek="kartIstek"/.test(html) && /<ayarlar-ekran [^>]*:kart-istek="kartIstek"/.test(html)
       && /new EsitlemeDenetcisi\(\{ kartAdres: this\.kartAdres, istek: this\.kartIstek \}\)/.test(
         yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'kayitlar.js'), 'utf8')))
       && /new es\.EsitlemeDenetcisi\(\{ kartAdres: this\.kartAdres, istek: this\.kartIstek \}\)/.test(ayKod)
       && govdeIcinde(appKaynak, 'pilKayitYukle', 'kartIstek')
       && /new es\.EsitlemeDenetcisi\(\{ kartAdres, istek: kartIstek \}\)/.test(yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'pil.js'), 'utf8'))));
    /* davranis: kayit YOK -> bugunku yol (fetch(kartAdres), ayni secenekler); istemci VAR -> istemci.istek */
    SONRA.push(async () => {
      const u = ornek();
      u.kartTaban = '';
      const giden = [];
      const eski = sandbox.fetch;
      sandbox.fetch = async (url, o) => { giden.push([url, o]); return { ok: true, status: 200 }; };
      const s1 = { cache: 'no-store' };
      let r1 = null;
      try { r1 = await u.kartIstek('/pil?sira=3', s1); } catch (h) { r1 = h; }
      const v = ornek();
      const cagri = [];
      v._esKarar = Promise.resolve({ istek: async (yol, sec, duz) => { cagri.push([yol, sec]); return duz(); } });
      let r2 = null;
      try { r2 = await v.kartIstek('/kal/liste', { cache: 'no-store' }); } catch (h) { r2 = h; }
      sandbox.fetch = eski;
      ok('[!] ES4: kartIstek — eslesme kaydi yoksa BUGUNKU yol (fetch(kartAdres(yol)), secenekler aynen); kayit varsa istemci.istek (yedek yolu duz fetch)',
         r1 && r1.status === 200 && giden.length === 2 && giden[0][0] === '/pil?sira=3' && giden[0][1] === s1
         && cagri.length === 1 && cagri[0][0] === '/kal/liste' && giden[1][0] === '/kal/liste' && r2 && r2.status === 200,
         JSON.stringify({ giden: giden.map((g) => g[0]), cagri: cagri.map((c) => c[0]) }));
    });
    /* EsitlemeDenetcisi istek enjeksiyonu */
    SONRA.push(async () => {
      const ESx = require(path.join(ARAYUZ, 'ekran', 'esitleme.js'));
      const yollar = [];
      const d = new ESx.EsitlemeDenetcisi({ kartAdres: (y) => 'X' + y,
        istek: async (yol, o) => { yollar.push([yol, o && o.cache]); return { status: 404, text: async () => 'yok' }; }, bekle: async () => {} });
      const l = await d.kartListesi();
      const y2 = await d._istek('/kayit/veri', [['sira', '4'], ['bayt', '8192']]);
      ok('[!] ES4: EsitlemeDenetcisi `istek` alir: /kayit/liste ve /kayit/veri ondan (kartAdres onekiyle DEGIL — onu katman ekler), no-store',
         l.durum === 'yok' && y2.status === 404 && yollar.map((y) => y.join(':')).join(' ') === '/kayit/liste:no-store /kayit/veri?sira=4&bayt=8192:no-store',
         JSON.stringify(yollar));
    });
  }

  /* ── (c) EMNIYET-P0 ─────────────────────────────────────────────── */
  {
    const TA = (al('TASIYICILAR') || {}).akis;
    SONRA.push(async () => {
      const giden = [];
      const eski = sandbox.fetch;
      sandbox.fetch = async (url, o) => { giden.push([url, o]); return { ok: true, status: 204, text: async () => '' }; };
      let katman = 0;
      const uyg = { kartAdres: (y) => 'K' + y, jeton: 'j1', hata: '', satirIsle() {},
        kartIstek: () => { katman++; return new Promise(() => {}); } };     // katman ASKIDA: hic cozulmez
      if (TA) TA.gonder(uyg, 'p0');
      await uyu();
      await uyu();
      const p0 = giden.slice();
      if (TA) TA.gonder(uyg, 'G?');
      await uyu();
      const uyg2 = { ...uyg, kartIstek: () => { throw new Error('imza bozuk'); } };
      if (TA) TA.gonder(uyg2, 'p0');
      await uyu();
      sandbox.fetch = eski;
      ok('[!] EMNIYET-P0 (ES4/K11): `p0` imza katmanina HIC girmez — katman askida ya da atiyor olsa da tek POST /komut (jeton ile) hemen gider; diger komutlar katmandan',
         !!TA && p0.length === 1 && p0[0][0] === 'K/komut' && p0[0][1].body === 'p0' && p0[0][1].method === 'POST'
         && p0[0][1].headers['X-Jeton'] === 'j1' && p0[0][1].headers['X-Olcum'] === '1' && katman === 1
         && giden.length === 2 && giden[1][1].body === 'p0',
         JSON.stringify({ p0: p0.map((g) => g[0]), katman, n: giden.length }));
    });
    ok('[!] EMNIYET-P0: p0 yolu eslesme modulunu BEKLEMEZ (TasiyiciAkis.gonder, p0 dali kartIstek`ten ONCE) ve pilDurdurKomut hala tek gonder(\'p0\')',
       /metin === 'p0'\s*\?\s*fetch\(uyg\.kartAdres\('\/komut'\), sec\)\s*:\s*uyg\.kartIstek\('\/komut', sec\)/.test(appKod)
       && /pilDurdurKomut\(\) \{ this\.gonder\('p0'\); \}/.test(appKaynak));
  }

  /* ── (d) SAF MANTIK ─────────────────────────────────────────────── */
  {
    const ya = ES.yolAyir || (() => ({}));
    const a1 = ya('/kayit/veri?sira=5&bayt=8192');
    const a2 = ya('/komut');
    const a3 = ya('/pil?sira=0&ad=%C5%9F%20x');
    ok('ES4: yolAyir — yol + argumanlar (gelis sirasi, URL-cozulmus); sorgusuz yol bos liste',
       a1.yol === '/kayit/veri' && JSON.stringify(a1.argumanlar) === '[["sira","5"],["bayt","8192"]]'
       && a2.yol === '/komut' && JSON.stringify(a2.argumanlar) === '[]' && JSON.stringify(a3.argumanlar) === '[["sira","0"],["ad","ş x"]]');
    const C = ES.SseCozucu ? new ES.SseCozucu() : null;
    const olaylar = C ? [
      ...C.ekle('retry: 3000\r\n\r\nevent: kim'), ...C.ekle('lik\ndata: {"jeton":"j"}\n\n: nabiz\n\nid: 7\ndata: D 1\ndata: 2\n'),
      ...C.ekle('\n'), ...C.ekle('event: kopru\ndata: http://pc\n\nevent: bos\n\n'),
    ] : [];
    ok('[!] ES6: SseCozucu — parcali gelis, CRLF, yorum, cok satirli data, olay adi, id, retry; verisiz blok olay degil',
       !!C && JSON.stringify(olaylar.map((o) => [o.olay, o.veri, o.id])) === JSON.stringify([
         ['kimlik', '{"jeton":"j"}', ''], ['message', 'D 1\n2', '7'], ['kopru', 'http://pc', '7']]) && C.retry === 3000,
       JSON.stringify(olaylar));
    const b = ES.akisBekleme || (() => NaN);
    ok('[!] ES6: yeniden baglanma beklemesi ARTAR (1, 2, 4, 8, 16 s) ve 30 s`de durur',
       [1, 2, 3, 4, 5, 6, 9].map(b).join() === '1000,2000,4000,8000,16000,30000,30000' && ES.AKIS_BEKLE_AZAMI_MS === 30000);
    const kb = ES.kayitBirlestir || (() => undefined);
    const e0 = { kimlik: KIMLIK, n: 2, K, ad: 'a', sayac: 50, acilis: ACILIS, eklenme: 10, tanimiyor: false };
    const g1 = kb(e0, { ...e0, sayac: 40, acilis: ACILIS2 });
    const g2 = kb({ ...e0, tanimiyor: true }, { ...e0, sayac: 60 });
    const g3 = kb(e0, { ...e0, n: 3, eklenme: 20, sayac: 0 });
    const g4 = kb({ ...e0, n: 3, eklenme: 20 }, { ...e0, sayac: 99 });
    ok('[!] ES5: kayitBirlestir — sayac GERI GITMEZ (iki sekme), acilis yeni yazandan, "tanimiyor" yapiskan; yeni eslestirme eskisini ezer, ESKI eslestirme yeniyi ezemez',
       g1 && g1.sayac === 50 && g1.acilis === ACILIS2 && g2 && g2.tanimiyor === true && g2.sayac === 60
       && g3 && g3.n === 3 && g3.sayac === 0 && g4 === null && kb(null, e0, { olustur: true }).sayac === 50,
       JSON.stringify([g1 && g1.sayac, g2 && g2.tanimiyor, g3 && g3.n, g4]));
    const sa = ES.sayacAyir || (() => null);
    const dk = { ...e0, sayac: 100 };
    const t1 = sa(dk, { ...e0, sayac: 0 }, 50);           // sekme A: bellekte geride, saat geride
    const t2 = t1 && sa(t1.kayit, { ...e0, sayac: 0 }, 50);  // sekme B: AYNI bellek + AYNI ms
    const t3 = t2 && sa(t2.kayit, { ...e0, sayac: 0 }, 900);
    ok('[!] ES5: sayacAyir — iki sekme ayni bellek sayaci ve AYNI ms ile ayirsa da FARKLI sayac (depo + 1); saat ilerideyse saat; baska eslestirmeye ayirmaz',
       !!t1 && t1.s === 101 && t2.s === 102 && t3.s === 900 && t3.kayit.sayac === 900 && sa(dk, { ...e0, n: 9 }, 1) === null && sa(null, e0, 1) === null,
       JSON.stringify([t1 && t1.s, t2 && t2.s, t3 && t3.s]));
    const rs = ES.retSebebi || (() => ({}));
    const ch = (m) => { const h = new IMx.CalismaHatasi(m); return h; };
    const r = [
      rs(ch('/eslestir/kanit: 403 kanit yanlis (parola?)')), rs(ch('/eslestir/baslat: 403 web parolasi yok')),
      rs(ch('/eslestir/baslat: 429 cok fazla yanlis deneme'), { retry: '8' }), rs(ch('/eslestir/baslat: 409 cihaz listesi dolu (8)')),
      rs(ch('/eslestir/kanit: 410 bekleyen eslestirme yok')), rs(ch('kart kaniti YANLIS — bu kart parolayi bilmiyor')),
      rs(new KRx.DegerHatasi('PBKDF2 turu 5 kabul edilmez')), rs(new TypeError('Failed to fetch')), rs(ch('/eslestir/baslat: 503 x')),
    ];
    ok('[!] ES3: retSebebi — kartin reddi SEBEBIYLE: yanlis parola / kartin parolasi yok / 429 (Retry-After saniyesi) / dolu / 60 s / sahte kart / bilgi / ag / HTTP; kartin metni tasinir',
       r.map((x) => x.anahtar).join() === 'es.ret_parola,es.ret_kart_parola,es.ret_bekle,es.ret_dolu,es.ret_sure,es.ret_sahte,es.ret_bilgi,es.ret_ag,es.ret_http'
       && r[0].d.kart === 'kanit yanlis (parola?)' && r[2].d.sn === '8' && r[8].d.kod === '503'
       && r.every((x) => x.anahtar in SEx.SOZLUK_ES), JSON.stringify(r));
    const va = ES.varsayilanAd || (() => '');
    const adlar = [va('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0'),
      va('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36'),
      va('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'),
      va('Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0'), va('')];
    ok('ES7: varsayilan cihaz adi tarayici + isletim sisteminden (listede ayirt edilsin), her zaman gecerli ad (1-24 bayt)',
       adlar.join(' | ') === 'Edge/Windows | Chrome/Android | Safari/iOS | Firefox/Linux | Tarayici' && adlar.every((a) => IMx.adGecerli(a)), adlar.join(' | '));
    const uy = ES.eslesmeUygunlugu || (() => ({}));
    ok('ES1: eslestirme yalniz panel kartin KENDI adresinden (akis kipi, bos taban): USB / demo / baska taban -> sebep',
       uy({ kartTaban: '', tasiyici: 'akis' }).uygun === true && uy({ kartTaban: '', tasiyici: 'seri' }).neden === 'usb'
       && uy({ kartTaban: '', tasiyici: 'demo' }).neden === 'demo' && uy({ kartTaban: '10.0.0.5', tasiyici: 'akis' }).neden === 'taban');
  }

  /* ── (e) ISTEMCI ────────────────────────────────────────────────── */
  if (ES.EslesmeIstemcisi) {
    const kur = (cevap, { cihaz = true } = {}) => {
      const depo = bellekDepo();
      if (cihaz) depo.m.set(KIMLIK, { kimlik: KIMLIK, n: 2, K, ad: 'Edge/Windows', sayac: 0, acilis: ACILIS2, eklenme: 5, tanimiyor: false });
      const bildirim = [];
      const ist = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo, bildir: (o) => bildirim.push(o) });
      const giden = [];
      const getir = async (url, o) => {
        giden.push({ url, o, sira: depo.log.length, kayitliSayac: (depo.m.get(KIMLIK) || {}).sayac });
        if (url === 'http://kart/eslestir/bilgi') return yanit(200, bilgiJson(), { 'Content-Type': 'application/json' });
        return cevap(url, o, giden.length);
      };
      return { ist, depo, bildirim, giden, getir };
    };
    const kos = async (getir, f) => {
      const eski = globalThis.fetch;
      globalThis.fetch = getir;
      try { return await f(); } finally { globalThis.fetch = eski; }
    };
    SONRA.push(async () => {
      /* imzali istek: basliklar, sayac ONCE yazilir, credentials omit, Authorization / X-Jeton YOK */
      const a = kur(() => yanit(204));
      const r = await kos(a.getir, async () => {
        const d = await a.ist.coz();
        const y = await a.ist.istek('/komut', { method: 'POST', headers: { 'Content-Type': 'text/plain', 'X-Olcum': '1', 'X-Jeton': 'j' }, body: 'G?' },
          () => { throw new Error('duz yola dusmemeli'); });
        const y2 = await a.ist.istek('/kayit/veri?sira=5&bayt=8192', { cache: 'no-store' }, () => null);
        return { d, y, y2 };
      });
      const k = a.giden.filter((g) => g.url.startsWith('http://kart/komut') || g.url.startsWith('http://kart/kayit'));
      const h = k.length ? k[0].o.headers : {};
      ok('[!] ES4/ES5: imzali istek — X-Cihaz/X-Sayac/X-Imza (kanonik metin imza.js ile ayni), sayac istekten ONCE depoya yazildi, credentials:omit, Authorization ve X-Jeton YOK; acilis /eslestir/bilgi`den tazelendi',
         r.d === 'hazir' && r.y.status === 204 && r.y2.status === 204 && k.length === 2
         && h['X-Cihaz'] === '2' && /^\d+$/.test(h['X-Sayac']) && imzaDogru(k[0].url, k[0].o) && imzaDogru(k[1].url, k[1].o)
         && k.every((g) => g.o.credentials === 'omit' && !('Authorization' in (g.o.headers || {})) && !('X-Jeton' in (g.o.headers || {})))
         && k.every((g) => g.kayitliSayac === Number(g.o.headers['X-Sayac'])) && Number(k[1].o.headers['X-Sayac']) > Number(h['X-Sayac'])
         && k[1].url === 'http://kart/kayit/veri?sira=5&bayt=8192' && a.depo.m.get(KIMLIK).acilis === ACILIS && k[0].o.body !== undefined,
         JSON.stringify(k.map((g) => [g.url, g.o.headers['X-Sayac'], g.kayitliSayac])));
      /* ES5: ayni acilisla 401 BIR kez -> yeni sayacla yeniden dene; tanimiyor DEGIL */
      const b = kur((url, o, n) => (n === 2 ? yanit(401, 'imza: sayac tekrar ya da cok eski', { 'X-Acilis': ACILIS }) : yanit(204)));
      const rb = await kos(b.getir, () => b.ist.istek('/komut', { method: 'POST', body: 'G?' }, () => 'DUZ'));
      const kb2 = b.giden.filter((g) => g.url === 'http://kart/komut');
      ok('[!] ES5: ayni acilisla tek 401 (iki sekmenin sayac carpismasi) -> YENI sayacla tek yeniden deneme, basarili; cihaz isaretlenmez',
         rb && rb.status === 204 && kb2.length === 2 && Number(kb2[1].o.headers['X-Sayac']) > Number(kb2[0].o.headers['X-Sayac'])
         && b.bildirim.length === 0 && !b.depo.m.get(KIMLIK).tanimiyor, JSON.stringify(kb2.map((g) => g.o.headers['X-Sayac'])));
      /* iki kez 401 ayni acilis -> kart tanimiyor: isaret + bildirim + imzasiz yol; sonrakiler dogrudan imzasiz */
      const c = kur((url) => (url === 'http://kart/komut' ? yanit(401, 'imza: cihaz kayitli degil', { 'X-Acilis': ACILIS }) : yanit(200)));
      let duz = 0;
      const rc = await kos(c.getir, () => c.ist.istek('/komut', { method: 'POST', body: 'G?' }, () => { duz++; return 'DUZ'; }));
      const once = c.giden.length;
      const rc2 = await kos(c.getir, () => c.ist.istek('/pil?sira=0', {}, () => { duz++; return 'DUZ2'; }));
      ok('[!] ES4: ayni acilisla IKI 401 -> "kart tanimiyor": cihaz depoda isaretli, kullaniciya bildirildi (kartin metniyle), istek IMZASIZ yoldan; sonraki istekler dogrudan imzasiz (imzali deneme yok)',
         rc === 'DUZ' && rc2 === 'DUZ2' && duz === 2 && c.giden.filter((g) => g.url === 'http://kart/komut').length === 2
         && c.giden.length === once && c.depo.m.get(KIMLIK).tanimiyor === true && c.ist.durum === 'tanimiyor'
         && c.bildirim.length >= 1 && c.bildirim[0].durum === 'tanimiyor' && c.bildirim[0].n === 2
         && /cihaz kayitli degil/.test(c.bildirim[0].mesaj), JSON.stringify(c.bildirim));
      /* 401 YENI acilis (kart yeniden basladi) -> acilis guncellenir, basarili */
      const d = kur((url, o, n) => (n === 2 ? yanit(401, 'imza gecersiz', { 'X-Acilis': ACILIS2 }) : yanit(204)));
      const rd = await kos(d.getir, () => d.ist.istek('/komut', { method: 'POST', body: 'x' }, () => 'DUZ'));
      const kd = d.giden.filter((g) => g.url === 'http://kart/komut');
      ok('[!] ES4: 401 + YENI X-Acilis (kart yeniden basladi) -> acilis guncellenir (depoda da), yeni acilisla imzali yeniden deneme basarili',
         rd && rd.status === 204 && kd.length === 2 && imzaDogru(kd[1].url, kd[1].o, ACILIS2) && d.depo.m.get(KIMLIK).acilis === ACILIS2
         && d.bildirim.length === 0);
      /* 401 disi hata yanit olarak doner (cagiran isler), imzasiz yola DUSULMEZ */
      const e = kur(() => yanit(503, 'mesgul'));
      const re = await kos(e.getir, () => e.ist.istek('/kal/liste', {}, () => 'DUZ'));
      ok('ES4: 401 disi hata (503) cagirana YANIT olarak doner; imzasiz yola dusulmez, cihaz isaretlenmez',
         re && re.status === 503 && !e.depo.m.get(KIMLIK).tanimiyor);
      /* kayit yok -> durum 'yok', istek dogrudan imzasiz */
      const f = kur(() => yanit(204), { cihaz: false });
      const rf = await kos(f.getir, () => f.ist.istek('/komut', { method: 'POST', body: 'x' }, () => 'DUZ'));
      ok('[!] ES4: bu kartin kimligiyle kayit YOKSA istek bugunku yoldan (imzali deneme yok)',
         rf === 'DUZ' && f.ist.durum === 'yok' && f.giden.every((g) => g.url === 'http://kart/eslestir/bilgi'));
      /* kart ulasilamazsa coz atar ve durum ezberlenmez */
      const g = kur(() => yanit(204));
      let ag = null;
      await kos(async () => { throw new TypeError('Failed to fetch'); }, async () => { try { await g.ist.coz(); } catch (h) { ag = h; } });
      const sonra = await kos(g.getir, () => g.ist.coz());
      ok('ES4: /eslestir/bilgi`e ulasilamazsa coz ATAR (istek ag hatasi gibi) ve sonuc ezberlenmez — kart donunce imzali yol',
         ag instanceof TypeError && sonra === 'hazir');
      /* unut: once kartta kendini sil (imzali POST /cihaz/sil?n=), sonra yerel; ulasilamazsa yine yerel + sebep */
      const u1 = kur(() => yanit(204));
      const ru1 = await kos(u1.getir, async () => { await u1.ist.coz(); return u1.ist.unut(); });
      const sil1 = u1.giden.find((x) => x.url.startsWith('http://kart/cihaz/sil'));
      const u2 = kur(() => yanit(204));
      await kos(u2.getir, () => u2.ist.coz());
      const ru2 = await kos(async (url) => { if (url.includes('/cihaz/sil')) throw new TypeError('Failed to fetch'); return u2.getir(url); }, () => u2.ist.unut());
      ok('[!] ES7: unut — ONCE kartta kendini siler (imzali POST /cihaz/sil?n=<kendi>), SONRA bu tarayicidaki kayit; kart ulasilamazsa yerel kayit yine silinir ve sonuc bunu soyler',
         ru1.kart === 'silindi' && !!sil1 && sil1.url === 'http://kart/cihaz/sil?n=2' && sil1.o.method === 'POST' && imzaDogru(sil1.url, sil1.o)
         && u1.depo.log.findIndex((l) => l[0] === 'sil') > sil1.sira - 1 && !u1.depo.m.has(KIMLIK) && u1.ist.durum === 'yok'
         && u1.bildirim.some((b2) => b2.durum === 'unutuldu')
         && ru2.kart === 'ulasilamadi' && ru2.n === 2 && !u2.depo.m.has(KIMLIK), JSON.stringify([ru1, ru2]));
      /* saat: imzali POST /saat?unix=<simdi> */
      const s = kur(() => yanit(204));
      await kos(s.getir, async () => { await s.ist.coz(); return s.ist.saatAyarla(); });
      const st = s.giden.find((x) => x.url.startsWith('http://kart/saat'));
      const unix = st ? Number(new URL(st.url).searchParams.get('unix')) : 0;
      ok('[!] ES8: saat — imzali POST /saat?unix=<bu cihazin saati> (otomatik degil: yalniz cagrilinca)',
         !!st && st.o.method === 'POST' && imzaDogru(st.url, st.o) && Math.abs(unix - Date.now() / 1000) < 5);
    });
    SONRA.push(async () => {
      /* eslestirme: JS'te kart taklidi (imza.js ile) — parola HICBIR istekte ve depoda yok */
      const PAROLA = 'sinama-parolasi-123';
      const tuz = new Uint8Array(16).fill(7);
      const P = IMx.pbkdf2(PAROLA, tuz, 10000);
      const nk = new Uint8Array(16).fill(9);
      let bekleyen = null;
      let yanlis = 0;
      const depo = bellekDepo();
      const bildirim = [];
      const ist = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo, bildir: (o) => bildirim.push(o) });
      const giden = [];
      const kart = async (url, o) => {
        giden.push({ url, o });
        const u = new URL(url);
        if (u.pathname === '/eslestir/bilgi') {
          return yanit(200, JSON.stringify({ surum: 'OK1', kimlik: KIMLIK, acilis: ACILIS, tuz: KRx.hex(tuz), tur: 10000, zorunlu: 0, misafir: 0, saat: 0, cihaz_azami: 8 }));
        }
        if (u.pathname === '/eslestir/baslat') {
          if (yanlis >= 2) return yanit(429, 'cok fazla yanlis deneme', { 'Retry-After': '4' });
          bekleyen = { ad: u.searchParams.get('ad'), nc: KRx.hexten(u.searchParams.get('nc')) };
          return yanit(200, JSON.stringify({ eno: 1, nk: KRx.hex(nk) }));
        }
        if (u.pathname === '/eslestir/kanit') {
          const beklenen = IMx.kanitIstemci(P, KIMLIK, nk, bekleyen.nc, bekleyen.ad);
          if (KRx.hex(beklenen) !== u.searchParams.get('kanit')) { yanlis++; return yanit(403, 'kanit yanlis (parola?)'); }
          return yanit(200, JSON.stringify({ n: 3, kart_kanit: KRx.hex(IMx.kanitKart(P, KIMLIK, nk, bekleyen.nc, 3)) }));
        }
        return yanit(404, 'yok');
      };
      const kos2 = async (f) => { const e = globalThis.fetch; globalThis.fetch = kart; try { return await f(); } catch (h) { return h; } finally { globalThis.fetch = e; } };
      const kisa = await kos2(() => ist.esles('Edge/Windows', 'kisa-parola'));
      const kisaGiden = giden.length;
      const yanlis1 = await kos2(() => ist.esles('Edge/Windows', 'yanlis-parola-1234'));
      const yanlis2 = await kos2(() => ist.esles('Edge/Windows', 'yanlis-parola-1234'));
      const bekle = await kos2(() => ist.esles('Edge/Windows', PAROLA));
      const bekleRetry = ist.sonRetry;
      yanlis = 0;
      const c = await kos2(() => ist.esles('Edge/Windows', PAROLA));
      const kayit = depo.m.get(KIMLIK);
      const tumMetin = JSON.stringify(giden.map((g) => [g.url, g.o && g.o.headers, g.o && g.o.body ? KRx.utf8Coz(new Uint8Array(g.o.body)) : '']))
        + JSON.stringify([...depo.m.values()].map((v) => ({ ...v, K: KRx.hex(v.K) })));
      ok('[!] ES3: eslestirme — kisa parola AG`A HIC CIKMADAN reddedilir; yanlis parola / deneme siniri kartin SEBEBIYLE (Retry-After); dogru parolada cihaz kaydi (K, n, acilis, eklenme) depoda',
         ES.retSebebi(kisa).anahtar === 'es.ret_kisa' && kisaGiden === 0
         && ES.retSebebi(yanlis1, { retry: ist.sonRetry }).anahtar === 'es.ret_parola'
         && ES.retSebebi(bekle, { retry: bekleRetry }).anahtar === 'es.ret_bekle' && ES.retSebebi(bekle, { retry: bekleRetry }).d.sn === '4'
         && c && c.n === 3 && kayit && kayit.n === 3 && kayit.K instanceof Uint8Array && kayit.K.length === 32 && kayit.acilis === ACILIS
         && kayit.eklenme > 0 && kayit.sayac === 0 && ist.durum === 'hazir' && bildirim.some((b) => b.durum === 'eslesti'),
         JSON.stringify({ kisa: ES.retSebebi(kisa), y1: ES.retSebebi(yanlis1), b: ES.retSebebi(bekle, { retry: bekleRetry }), n: c && c.n }));
      ok('[!] ES3: parola HICBIR istekte (URL, baslik, govde) ve depoda YOK; eslestirme istekleri credentials:omit',
         !tumMetin.includes(PAROLA) && !tumMetin.includes('yanlis-parola-1234') && giden.length > 0
         && giden.every((g) => g.o && g.o.credentials === 'omit'), String(giden.length));
      ok('ES3: K, eslestirmenin AYNI turetimiyle (imza.js cihazAnahtari) — kart ile tarayici ayni anahtari tutar',
         !!kayit && KRx.hex(kayit.K) === KRx.hex(IMx.cihazAnahtari(P, KIMLIK, nk, (bekleyen || {}).nc || new Uint8Array(16), 3)));
    });
  }

  /* ── (f) AKIS (ES6) ─────────────────────────────────────────────── */
  if (ES.ImzaliAkis && ES.EslesmeIstemcisi) {
    SONRA.push(async () => {
      const depo = bellekDepo();
      depo.m.set(KIMLIK, { kimlik: KIMLIK, n: 2, K, ad: 'x', sayac: 0, acilis: ACILIS, eklenme: 5, tanimiyor: false });
      const bildirim = [];
      const ist = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo, bildir: (o) => bildirim.push(o) });
      const urller = [];
      let baglanti = 0;
      const akisGovde = (parcalar) => new ReadableStream({ start(c) { for (const p of parcalar) c.enqueue(bayt(p)); c.close(); } });
      const getir = async (url, o) => {
        if (url === 'http://kart/eslestir/bilgi') return yanit(200, bilgiJson({ acilis: baglanti >= 4 ? ACILIS2 : ACILIS }));
        if (url.startsWith('http://kart/akis')) {
          baglanti++;
          urller.push({ url, o });
          if (baglanti === 4) return yanit(401, 'imza gecersiz', { 'X-Acilis': ACILIS2 });     // kart yeniden basladi
          if (baglanti === 2 || baglanti === 3) throw new TypeError('Failed to fetch');
          return new Response(akisGovde(['retry: 3000\n\nevent: kimlik\ndata: {"jeton":"j","surucu":true}\n\n', 'id: 1\ndata: D 1\n\n']), { status: 200 });
        }
        return yanit(404);
      };
      const eski = globalThis.fetch;
      globalThis.fetch = getir;
      const beklemeler = [];
      const olay = [];
      let akis = null;
      try {
        await ist.coz();
        akis = new ES.ImzaliAkis(ist, { bekle: async (ms) => { beklemeler.push(ms); if (beklemeler.length >= 4) akis.close(); } });
        akis.onmessage = (e) => olay.push('m:' + e.data);
        akis.onerror = () => olay.push('hata');
        akis.addEventListener('kimlik', (e) => olay.push('k:' + JSON.parse(e.data).jeton));
        for (let i = 0; i < 200 && akis.readyState !== 2; i++) await uyu();
      } finally { globalThis.fetch = eski; }
      const imzali = urller.filter((x) => /_i=/.test(x.url));
      const s = imzali.map((x) => new URL(x.url).searchParams.get('_s'));
      const dogru = (x, acilis) => { const q = new URL(x.url).searchParams;
        return q.get('_i') === IMx.imzala(K, 'GET', '/akis', [], acilis, Number(q.get('_s')), new Uint8Array(0)) && q.get('_c') === '2'; };
      ok('[!] ES6: akis IMZALI URL ile (/akis?_c&_s&_i, imza.js ile ayni), credentials:omit; olaylar (kimlik, data) EventSource gibi dagitilir',
         urller.length >= 5 && imzali.length === urller.length && dogru(urller[0], ACILIS) && urller.every((x) => x.o.credentials === 'omit')
         && olay.includes('k:j') && olay.includes('m:D 1'), JSON.stringify(olay));
      ok('[!] ES6: her yeniden baglanma YENI imzali URL (sayac ve imza hep farkli — EventSource`un eski URL`yi tekrar yollamasi yok); bekleme ARTAR (1, 2, 4 s)',
         new Set(urller.map((x) => x.url)).size === urller.length && s.every((v, i) => i === 0 || Number(v) > Number(s[i - 1]))
         && beklemeler.slice(0, 3).join() === '1000,2000,4000' && olay.filter((o) => o === 'hata').length >= 3, `${beklemeler} · ${urller.length}`);
      ok('[!] ES6: akista 401 + YENI acilis (kart yeniden basladi) -> acilis guncellenir, HEMEN yeni acilisla imzali yeniden baglanir',
         urller.length >= 5 && dogru(urller[4], ACILIS2) && depo.m.get(KIMLIK).acilis === ACILIS2 && bildirim.length === 0,
         JSON.stringify(urller.map((x) => new URL(x.url).searchParams.get('_s'))));
      /* tanimiyor: iki 401 ayni acilis -> bildirim + IMZASIZ /akis (EventSource ile ayni kimlik bilgisi kipi) */
      const depo2 = bellekDepo();
      depo2.m.set(KIMLIK, { kimlik: KIMLIK, n: 2, K, ad: 'x', sayac: 0, acilis: ACILIS, eklenme: 5, tanimiyor: false });
      const b2 = [];
      const ist2 = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo: depo2, bildir: (o) => b2.push(o) });
      const u2 = [];
      globalThis.fetch = async (url, o) => {
        if (url === 'http://kart/eslestir/bilgi') return yanit(200, bilgiJson());
        u2.push({ url, o });
        if (/_i=/.test(url)) return yanit(401, 'imza: cihaz kayitli degil', { 'X-Acilis': ACILIS });
        return new Response(akisGovde(['data: D 2\n\n']), { status: 200 });
      };
      let a2 = null;
      try {
        await ist2.coz();
        a2 = new ES.ImzaliAkis(ist2, { bekle: async () => { a2.close(); } });
        for (let i = 0; i < 200 && a2.readyState !== 2; i++) await uyu();
      } finally { globalThis.fetch = eski; }
      ok('[!] ES4/ES6: akista iki 401 ayni acilis -> "kart tanimiyor" bildirilir, akis IMZASIZ /akis ile surer (credentials same-origin: bugunku EventSource yolu)',
         u2.length === 3 && /_i=/.test(u2[0].url) && /_i=/.test(u2[1].url) && u2[2].url === 'http://kart/akis'
         && u2[2].o.credentials === 'same-origin' && b2.some((b) => b.durum === 'tanimiyor') && depo2.m.get(KIMLIK).tanimiyor === true,
         JSON.stringify(u2.map((x) => x.url.slice(0, 40))));
    });
    ok('[!] ES6: TasiyiciAkis eslesmisken istemcinin akisini (ImzaliAkis) acar, yoksa bugunku EventSource(kartAdres(\'/akis\'))',
       /const ist = await uyg\.eslesmeHazirla\(\);/.test(appKod) && /uyg\.akis = imzali \|\| new EventSource\(uyg\.kartAdres\('\/akis'\)\);/.test(appKod)
       && /imzali = ist \? await ist\.akisAc\(\) : null/.test(appKod));
  }

  /* ── (g) SABLON (WIG, ES3 ES7 ES8 ES9) + app tepkisi ─────────────── */
  {
    const form = T.match(/<form ([^>]*)>([\s\S]*?)<\/form>/);
    const parola = T.match(/<input ([^>]*type="password"[^>]*)>/);
    ok('[!] ES3/WIG: eslestirme formu — etiketli ad + parola; parola type=password, autocomplete="current-password", name; v-model YOK (Vue durumunda da tutulmaz), gonder type=submit + aria-busy',
       !!form && /@submit\.prevent="eslestir"/.test(form[1]) && !!parola && /autocomplete="current-password"/.test(parola[1])
       && /\bname="parola"/.test(parola[1]) && /\bid="es-parola"/.test(parola[1]) && !/v-model/.test(parola[1]) && /ref="parola"/.test(parola[1])
       && /<label for="es-parola">/.test(form[2]) && /<label for="es-ad">/.test(form[2]) && /<input [^>]*id="es-ad"[^>]*maxlength="24"/.test(form[2])
       && /<button type="submit"[^>]*:aria-busy=/.test(form[2]), parola ? parola[1] : 'yok');
    const E = ES.EslestirmeEkrani || {};
    SONRA.push(async () => {
      if (!E.methods || !E.methods.eslestir) { ok('[!] ES3: gonderilince parola alani HEMEN bosaltilir', false, 'eslestir yok'); return; }
      const alan = { value: 'sinama-parolasi-123' };
      let gelen = null;
      let coz;
      const ist = { esles: (ad, p) => { gelen = [ad, p, alan.value]; return new Promise((r) => { coz = r; }); }, durum: 'yok', cihaz: null };
      const o = Object.assign({ $refs: { parola: alan }, $nextTick: (f) => { if (f) f(); return Promise.resolve(); }, ad: 'Edge/Windows',
        istemciAl: async () => ist, dilSecim: 'tr' }, E.data ? E.data.call({}) : {}, E.methods);
      for (const [ad, fn] of Object.entries(E.computed || {})) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      o.ad = 'Edge/Windows';
      const p = o.eslestir();
      for (let i = 0; i < 5; i++) await uyu();
      const ara = { alan: alan.value, gelen, durum: JSON.stringify(o.$data || {}) };
      if (coz) coz({ n: 3 });
      await p;
      ok('[!] ES3: gonderilince parola alani esles cagrilmadan ONCE bosaltilir; parola bilesenin durumunda (data) YOK',
         alan.value === '' && gelen && gelen[1] === 'sinama-parolasi-123' && gelen[2] === ''
         && !Object.values(o).some((v) => typeof v === 'string' && v.includes('sinama-parolasi-123')), JSON.stringify(ara.gelen));
    });
    ok('[!] ES9: zorunluluk / misafir SALT OKUMA — onlara bagli girdi / dugme yok; USB komutlari (Ez1, Em1) sozluk metninde, bolumde gosteriliyor',
       !/v-model="[^"]*(zorunlu|misafir)|@click="[^"]*(zorunlu|misafir)/.test(T) && /m\.guvAciklama/.test(T) && /bilgi\.zorunlu/.test(T) && /bilgi\.misafir/.test(T));
    ok('[!] ES1: bildirim (MQTT) ayari panelde YOK — yalniz USB oldugu yaziyor; Q komutu gonderen kod yok',
       /m\.bildirimAciklama/.test(T) && !/['"`]Q[a-z?0-9]/.test(esKod));
    ok('[!] ES8: "saati bu cihazdan ayarla" yalniz eslesmisken ve kartin NTP saati YOKKEN (saat !== 1); otomatik cagri yok',
       /v-if="hazir && bilgi && bilgi\.saat !== 1"/.test(T) && /@click="saatAyarla"/.test(T)
       && (esKod.match(/\.saatAyarla\(/g) || []).length === 1);
    ok('[!] ES7/WIG: cihaz listesi tablo (caption, th scope), bu tarayici METINLE isaretli; baska cihazi kaldirma IKI ASAMALI (Eminim + Vazgec); kendi satiri "unut" yoluna gider',
       /<caption class="gorunmez">\{\{ m\.listeTablo \}\}<\/caption>/.test(T) && /<th scope="col">\{\{ m\.lN \}\}<\/th>/.test(T)
       && /c\.n === kendiN \? m\.buTarayici/.test(T) && /<template v-(?:else-)?if="kaldirOnay === c\.n">[\s\S]*?data-es-kaldir-eminim[\s\S]*?@click="kaldir\(c\.n\)"[\s\S]*?@click="kaldirVazgec\(c\.n\)"/.test(T)
       && /<template v-if="unutOnay">[\s\S]*?data-es-unut-eminim[\s\S]*?@click="unut"/.test(T));
    const dugmeler = [...T.matchAll(/<button\b([^>]*)>/g)].map((m) => m[1]);
    ok('ES/WIG: eslestirme bolumunun dugmeleri type="button" (formun gonderi disinda); durum metni aria-live; ret role=alert',
       dugmeler.length >= 6 && dugmeler.filter((a) => !/type="button"/.test(a)).length === 1 && /data-es-durum[^>]*aria-live="polite"|aria-live="polite"[^>]*data-es-durum/.test(T)
       && /class="hata" role="alert" data-es-ret/.test(T), `${dugmeler.length}`);
    SONRA.push(async () => {
      const E2 = ES.EslestirmeEkrani || {};
      if (!E2.methods) { ok('[!] ES7: kaldirma iki asamali', false); return; }
      const sil = [];
      const ist = { cihazSil: async (n) => { sil.push(n); return { tamam: true }; }, cihazListe: async () => [], cihaz: { n: 2 }, durum: 'hazir' };
      const o = Object.assign({ $nextTick: (f) => { if (f) f(); return Promise.resolve(); }, istemciAl: async () => ist, dilSecim: 'tr' },
        E2.data ? E2.data.call({}) : {}, E2.methods);
      for (const [ad, fn] of Object.entries(E2.computed || {})) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      o._odakla = () => {};
      await o.kaldir(5);
      const onaysiz = sil.length;
      o.kaldirBasla(5);
      await o.kaldir(6);
      const baska = sil.length;
      await o.kaldir(5);
      ok('[!] ES7: baska cihazi kaldirma IKI ASAMALI — onaysiz ya da baska satirin onayiyla cagri karta GITMEZ, ikinci asamada yalniz o cihaz',
         onaysiz === 0 && baska === 0 && sil.join() === '5', sil.join());
    });
    /* app tepkisi: tanimiyor -> serit uyarisi; eslesti -> uyari temizlenir + akis yenilenir */
    const u = ornek();
    let yenile = 0;
    u.akisYenile = () => { yenile++; };
    if (u.eslesmeBildir) u.eslesmeBildir({ durum: 'tanimiyor', n: 4, ad: 'x', mesaj: 'imza: cihaz kayitli degil' });
    const metin1 = u.eslesmeUyariMetni;
    if (u.eslesmeBildir) u.eslesmeBildir({ durum: 'eslesti' });
    const metin2 = u.eslesmeUyariMetni;
    ok('[!] ES4: "kart tanimiyor" kullaniciya SOYLENIR (her gorunumde serit uyarisi, cihaz no ile); eslesince uyari kalkar ve akis imzali yeniden acilir',
       typeof metin1 === 'string' && metin1.includes('4') && /tanımıyor/.test(metin1) && !metin2 && yenile === 1
       && /<div v-if="eslesmeUyariMetni" class="uyari" role="alert" data-es-uyari>\{\{ eslesmeUyariMetni \}\}\s*<a href="#\/ayar\/eslestirme">\{\{ eslesmeGit \}\}<\/a><\/div>/.test(html),
       String(metin1));
    ok('[!] ES3/ES2: eslesme.js parolayi ve anahtari hicbir yere YAZMAZ (localStorage / sessionStorage / console yok); N? gondermez',
       !!esKod && !/localStorage|sessionStorage|console\.(log|info|warn|error)|'N\?'|"N\?"/.test(esKod));
  }

  /* ── (h) INCELEME DUZELTMELERI (3H-2 guvenlik incelemesi; EU17-EU28) ──────── */
  if (ES.EslesmeIstemcisi && ES.ImzaliAkis) {
    const akisGovde = (parcalar, { hata = false } = {}) => new ReadableStream({
      start(c) { for (const p of parcalar) c.enqueue(bayt(p)); if (hata) c.error(new TypeError('network error')); else c.close(); },
    });
    const kayitliDepo = (ek = {}) => {
      const d = bellekDepo();
      d.m.set(KIMLIK, { kimlik: KIMLIK, n: 2, K, ad: 'x', sayac: 0, acilis: ACILIS, eklenme: 5, tanimiyor: false, ...ek });
      return d;
    };
    /* bir akis senaryosu: getir(url, o, baglantiNo), bekle(ms, akis) -> {urller, beklemeler, olay, bildirim, depo} */
    const akisKos = async (getir, { bekle = null, onmessage = null, bilgi = () => bilgiJson() } = {}) => {
      const depo = kayitliDepo();
      const bildirim = [];
      const ist = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo, bildir: (o) => bildirim.push(o) });
      const urller = [];
      const beklemeler = [];
      const olay = [];
      const eski = globalThis.fetch;
      let akis = null;
      globalThis.fetch = async (url, o) => {
        if (url === 'http://kart/eslestir/bilgi') return yanit(200, bilgi());
        urller.push({ url, o });
        return getir(url, o, urller.length);
      };
      try {
        await ist.coz();
        akis = new ES.ImzaliAkis(ist, { bekle: async (ms) => { beklemeler.push(ms); if (bekle) await bekle(ms, akis, urller); else akis.close(); } });
        akis.onmessage = onmessage || ((e) => olay.push('m:' + e.data));
        akis.addEventListener('kimlik', () => olay.push('kimlik'));
        for (let i = 0; i < 400 && akis.readyState !== 2; i++) await uyu();
      } finally { globalThis.fetch = eski; if (akis) akis.close(); }
      return { urller, beklemeler, olay, bildirim, depo, ist };
    };

    const r4b = [];
    SONRA.push(async () => {
      /* EU17 (inceleme [onemli]): kart yeniden basladi -> yeni acilisli 401 SAYILMAZ; ardindan TEK ayni-acilisli 401
         (sayac carpismasi) ES5'in yeni sayacli yeniden denemesini alir — kalici "tanimiyor" DEGIL */
      const r = await akisKos((url, o, n) => {
        if (n === 1) return yanit(401, 'imza gecersiz', { 'X-Acilis': ACILIS2 });
        if (n === 2) return yanit(401, 'imza: sayac tekrar ya da cok eski', { 'X-Acilis': ACILIS2 });
        return new Response(akisGovde(['data: D 1\n\n']), { status: 200 });
      });
      const s = r.urller.map((x) => new URL(x.url).searchParams.get('_s'));
      ok('[!] EU17: akista yeni acilisli 401 ayni-acilis sayacina GIRMEZ — yeniden baslamadan sonra tek bir ayni-acilisli 401 kalici "kart tanimiyor" yapmaz; ucuncu baglanti yeni acilisla imzali, veri geliyor',
         r.urller.length >= 3 && r.bildirim.length === 0 && r.depo.m.get(KIMLIK).tanimiyor === false && r.depo.m.get(KIMLIK).acilis === ACILIS2
         && r.olay.includes('m:D 1') && s.every((v, i) => i === 0 || Number(v) > Number(s[i - 1])),
         JSON.stringify({ n: r.urller.length, b: r.bildirim.map((b) => b.durum), olay: r.olay }));
      /* gercekten silinmis cihaz: ayni acilisla IKI 401 -> yine "tanimiyor" (EU7 korunuyor), yeni acilis olsa da */
      const r2 = await akisKos((url, o, n) => {
        if (n === 1) return yanit(401, 'imza gecersiz', { 'X-Acilis': ACILIS2 });
        if (/_i=/.test(url)) return yanit(401, 'imza: cihaz kayitli degil', { 'X-Acilis': ACILIS2 });
        return new Response(akisGovde(['data: D 2\n\n']), { status: 200 });
      });
      ok('[!] EU17: yeniden baslama + ayni acilisla IKI 401 -> yine "kart tanimiyor" ve imzasiz /akis (EU7 korunur)',
         r2.bildirim.some((b) => b.durum === 'tanimiyor') && r2.depo.m.get(KIMLIK).tanimiyor === true
         && r2.urller.filter((x) => /_i=/.test(x.url)).length === 3 && r2.urller.some((x) => x.url === 'http://kart/akis'),
         JSON.stringify(r2.urller.map((x) => x.url.slice(11, 40))));

      /* EU19 (inceleme [kucuk]): onmessage'tan atilan istisna akisi KOPARMAZ (EventSource gibi raporlanir) */
      const raporlanan = [];
      const eskiRapor = globalThis.reportError;
      globalThis.reportError = (h) => raporlanan.push(String(h && h.message));
      let r3;
      const mesaj3 = [];
      try {
        r3 = await akisKos(() => new Response(akisGovde(['data: D 1\n\n', 'data: D 2\n\n']), { status: 200 }), {
          onmessage: (e) => { mesaj3.push(e.data); if (e.data === 'D 1') throw new Error('satir isleyici patladi'); },
        });
      } finally { if (eskiRapor === undefined) delete globalThis.reportError; else globalThis.reportError = eskiRapor; }
      ok('[!] EU19: onmessage istisnasi akisi koparmaz — ayni baglantida sonraki olay da gelir, istisna reportError ile raporlanir (yeniden baglanma YOK)',
         mesaj3.join() === 'D 1,D 2' && r3.urller.length === 1 && raporlanan.join() === 'satir isleyici patladi',
         JSON.stringify({ mesaj3, n: r3.urller.length, raporlanan }));
      /* kopan baglanti (okuma hatasi) bekleme BASLAMADAN iptal edilir: eski fetch kartin akis yuvasini tutmaz */
      const iptalAni = [];
      await akisKos(() => new Response(akisGovde(['data: D 1\n\n'], { hata: true }), { status: 200 }), {
        bekle: async (ms, akis, urller) => { iptalAni.push(!!(urller[0] && urller[0].o.signal && urller[0].o.signal.aborted)); akis.close(); },
      });
      ok('[!] EU19: akis koptugunda eski baglantinin fetch`i bekleme BASLAMADAN iptal edilir (AbortController) — kartin AKIS_AZAMI yuvasini tutmaz',
         iptalAni.length === 1 && iptalAni[0] === true, JSON.stringify(iptalAni));

      /* EU20 (inceleme [kucuk]): 'dolu' / 'kopru' cevabi (200 + olay + kapanis) bekleme sayacini SIFIRLAMAZ */
      const r4 = await akisKos(() => new Response(akisGovde(['event: dolu\ndata: 4\n\n']), { status: 200 }), {
        bekle: async (ms, akis) => { if (r4b.push(ms) >= 4) akis.close(); },
      });
      ok('[!] EU20: kart "dolu" (ya da "kopru") yazip kapatinca bekleme ARTAR (1, 2, 4, 8 s) — ilk bayt degil GERCEK olay (kimlik / veri) sayaci sifirlar',
         r4b.join() === '1000,2000,4000,8000' && r4.urller.length === 4, r4b.join());
    });

    {
      /* EU18 (inceleme [kucuk]): kartin GERCEK SSE metni (firmware literal'leri) her bayt sinirinda bolunse de ayni olaylar;
         CRLF'li sunucuda '\r' | '\n' bolunmesi sahte bos satir uretmez */
      const ino = fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum-karti-a3.ino'), 'utf8');
      const lit = (re) => { const m = ino.match(re); return m ? JSON.parse('"' + m[1] + '"') : null; };
      const retry = lit(/akis\[yuva\]\.print\(F\("(retry: \d+\\n\\n)"\)\)/);
      const kimBas = lit(/akis\[yuva\]\.print\(F\("(event: kimlik\\ndata: )\{\\"jeton\\":\\""\)\)/);
      const olayBic = lit(/snprintf\(olay, sizeof\(olay\), "(id: %lu\\ndata: %s\\n\\n)"/);
      const doluBas = lit(/c\.print\(F\("(event: dolu\\ndata: )"\)\)/);
      const kartMetni = retry && kimBas && olayBic && doluBas
        ? retry + kimBas + '{"jeton":"a1b2","surucu":true}' + '\n\n'
          + olayBic.replace('%lu', '41').replace('%s', 'K 12.0012 0.5003 6.0 1') + olayBic.replace('%lu', '42').replace('%s', 'G 0 0')
          + doluBas + '4\n\n' : '';
      const coz = (parcalar) => { const C = new ES.SseCozucu(); return JSON.stringify(parcalar.flatMap((p) => C.ekle(p)).map((o) => [o.olay, o.veri, o.id])); };
      const kontrol = (metin) => {
        const tek = coz([metin]);
        const bozuk = [];
        for (let i = 0; i <= metin.length; i++) if (coz([metin.slice(0, i), metin.slice(i)]) !== tek) bozuk.push(i);
        for (let i = 1; i < metin.length - 1; i += 3) if (coz([metin.slice(0, i), metin.slice(i, i + 2), metin.slice(i + 2)]) !== tek) bozuk.push('3@' + i);
        return { tek, bozuk };
      };
      const lf = ES.SseCozucu ? kontrol(kartMetni) : { bozuk: ['yok'] };
      const crlf = ES.SseCozucu ? kontrol(kartMetni.replace(/\n/g, '\r\n') + 'data: a\r\ndata: b\r\n\r\n') : { bozuk: ['yok'] };
      ok('[!] EU18: SseCozucu — kartin gercek SSE metni (firmware literal\'leri: retry, kimlik, id+data, dolu) HER bayt sinirinda bolunse de tek parcayla AYNI olaylar; CRLF\'de \\r|\\n bolunmesi sahte bos satir uretmez (cok satirli olay ikiye bolunmez)',
         !!kartMetni && lf.bozuk.length === 0 && crlf.bozuk.length === 0
         && lf.tek === JSON.stringify([['kimlik', '{"jeton":"a1b2","surucu":true}', ''], ['message', 'K 12.0012 0.5003 6.0 1', '41'],
           ['message', 'G 0 0', '42'], ['dolu', '4', '42']])
         && crlf.tek === JSON.stringify([['kimlik', '{"jeton":"a1b2","surucu":true}', ''], ['message', 'K 12.0012 0.5003 6.0 1', '41'],
           ['message', 'G 0 0', '42'], ['dolu', '4', '42'], ['message', 'a\nb', '42']]),
         JSON.stringify({ lf: lf.bozuk.slice(0, 5), crlf: crlf.bozuk.slice(0, 5), metin: kartMetni.length }));
    }

    SONRA.push(async () => {
      /* EU22 (inceleme [kucuk]): "unut" ile es zamanli imzali istek silinen kaydi (K ile) GERI YAZAMAZ — yazmalar yalniz
         VAR OLAN kaydi gunceller; kaydi yalniz eslestirme yaratir */
      const depo = kayitliDepo();
      const bildirim = [];
      const ist = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo, bildir: (o) => bildirim.push(o) });
      let n = 0;
      const eski = globalThis.fetch;
      globalThis.fetch = async (url) => {
        if (url === 'http://kart/eslestir/bilgi') return yanit(200, bilgiJson());
        n++;
        if (n === 2) depo.m.delete(KIMLIK);               // baska sekme tam bu arada "unut" dedi (yerel kayit silindi)
        return yanit(401, 'imza: cihaz kayitli degil', { 'X-Acilis': ACILIS });
      };
      let r = null;
      try { await ist.coz(); r = await ist.istek('/komut', { method: 'POST', body: 'G?' }, () => 'DUZ'); } finally { globalThis.fetch = eski; }
      ok('[!] EU22: unut ile es zamanli imzali istegin ikinci 401`i silinen kaydi (K ile) YENIDEN YARATMAZ; "tanimiyor" bildirilmez, istemci kaydi birakir, istek imzasiz yoldan',
         r === 'DUZ' && !depo.m.has(KIMLIK) && bildirim.length === 0 && ist.cihaz === null && n === 2,
         JSON.stringify({ r, var: depo.m.has(KIMLIK), b: bildirim.map((b) => b.durum), n }));
      const kb = ES.kayitBirlestir || (() => undefined);
      const e0 = { kimlik: KIMLIK, n: 2, K, ad: 'a', sayac: 50, acilis: ACILIS, eklenme: 10 };
      ok('[!] EU22: kayitBirlestir — kayit YOKKEN yalniz {olustur:true} (eslestirme) yazar; diger yazmalar (sayac, acilis, tanimiyor) null',
         kb(null, e0) === null && kb(null, e0, { olustur: true }) && kb(null, e0, { olustur: true }).sayac === 50
         && kb(e0, { ...e0, sayac: 60 }).sayac === 60);

      /* EU21 (inceleme [kucuk]): bayat ekran — kayit baska sekmede silinip YENIDEN eslestirildi; bu sekmenin "unut"u yeni kaydi
         SILMEZ, karta /cihaz/sil gondermez ve "kart da sildi" demez */
      const d2 = kayitliDepo();
      const ist2 = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo: d2 });
      const giden2 = [];
      globalThis.fetch = async (url) => { giden2.push(url); return url === 'http://kart/eslestir/bilgi' ? yanit(200, bilgiJson()) : yanit(204); };
      let u = null;
      try {
        await ist2.coz();
        d2.m.set(KIMLIK, { kimlik: KIMLIK, n: 5, K, ad: 'yeni', sayac: 0, acilis: ACILIS, eklenme: 99, tanimiyor: false });
        u = await ist2.unut();
      } finally { globalThis.fetch = eski; }
      ok('[!] EU21: bayat ekranda "unut" — kayit artik bu eslestirme degil: kart "yok" doner, karta /cihaz/sil GITMEZ, yeni kayit SILINMEZ',
         u && u.kart === 'yok' && !giden2.some((x) => x.includes('/cihaz/sil')) && d2.m.get(KIMLIK) && d2.m.get(KIMLIK).n === 5,
         JSON.stringify({ u, giden2 }));
      const E = ES.EslestirmeEkrani || {};
      let yenilendi = 0;
      const o = Object.assign({ $nextTick: (f) => { if (f) f(); return Promise.resolve(); }, dilSecim: 'tr',
        istemciAl: async () => ({ unut: async () => ({ kart: 'yok', n: null, kod: null }), durum: 'bilinmiyor', cihaz: null, bilgi: null }) },
      E.data ? E.data.call({}) : {}, E.methods || {});
      for (const [ad, fn] of Object.entries(E.computed || {})) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      o._odakla = () => {};
      o.yenile = async () => { yenilendi++; };
      o.unutOnay = true;
      if (o.unut) await o.unut();
      ok('[!] EU21: ekran — "unut" {kart:"yok"} donerse "kart da sildi" DEMEZ, kaydin artik olmadigini soyler ve durumu yeniler',
         o.sonuc === SEx.ceviriEs('es.unutuldu_yok', 'tr') && !/kart da sildi/.test(o.sonuc) && yenilendi === 1, String(o.sonuc));

      /* EU24 (inceleme [kucuk]): /eslestir/bilgi zaman asimli — kart TCP'yi kabul edip susarsa coz ASILI KALMAZ */
      const d3 = kayitliDepo();
      const ist3 = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo: d3, bilgiSureMs: 40 });
      let sinyal = null;
      globalThis.fetch = (url, o2) => new Promise((coz, red) => {
        sinyal = o2 && o2.signal;
        if (sinyal) sinyal.addEventListener('abort', () => red(sinyal.reason || new Error('abort')));
      });
      let sonuc3 = 'ASILI';
      let akis3 = null;
      try {
        sonuc3 = await Promise.race([ist3.coz().then((d) => 'coz:' + d, (h) => 'atti:' + (h && h.name)),
          new Promise((r2) => setTimeout(() => r2('ASILI'), 1500))]);
        akis3 = await Promise.race([ist3.akisAc(), new Promise((r2) => setTimeout(() => r2('ASILI'), 1500))]);
      } finally { globalThis.fetch = eski; if (akis3 && akis3.close) akis3.close(); }
      ok('[!] EU24: /eslestir/bilgi zaman asimli (AbortSignal.timeout) — kart susarsa coz ATAR (asili kalmaz, ezberlenmez); akisAc ImzaliAkis doner (ag gibi)',
         /^atti:(TimeoutError|AbortError)$/.test(sonuc3) && !!sinyal && ist3.durum === 'bilinmiyor' && akis3 instanceof ES.ImzaliAkis
         && ES.BILGI_SURE_MS > 0 && ES.BILGI_SURE_MS <= 10000, JSON.stringify({ sonuc3, akis: akis3 && akis3.constructor && akis3.constructor.name }));

      /* EU26 (inceleme [kucuk]): BASKA kart kimligine ait kayitlar listelenir ve yerelden silinebilir; bu kartinki bu yoldan silinemez */
      const YABANCI = 'fedcba9876543210';
      const d4 = kayitliDepo();
      d4.m.set(YABANCI, { kimlik: YABANCI, n: 1, K, ad: 'eski kart', sayac: 9, acilis: ACILIS, eklenme: 3, tanimiyor: false });
      const ist4 = new ES.EslesmeIstemcisi({ kartAdres: (y) => 'http://kart' + y, depo: d4 });
      let l4 = null, sil4a = null, sil4b = null;
      globalThis.fetch = async (url) => (url === 'http://kart/eslestir/bilgi' ? yanit(200, bilgiJson()) : yanit(204));
      try {
        await ist4.coz();
        l4 = ist4.yabancilar ? await ist4.yabancilar() : null;
        sil4a = ist4.yerelSil ? await ist4.yerelSil(KIMLIK) : null;
        sil4b = ist4.yerelSil ? await ist4.yerelSil(YABANCI) : null;
      } finally { globalThis.fetch = eski; }
      ok('[!] EU26: baska kart kimligine ait kayitlar listelenir (kimlik, n, ad — K YOK) ve yerelden silinir; bu kartin kaydi bu yoldan SILINEMEZ ("unut" yolu)',
         Array.isArray(l4) && l4.length === 1 && l4[0].kimlik === YABANCI && l4[0].n === 1 && !('K' in l4[0])
         && sil4a === false && sil4b === true && d4.m.has(KIMLIK) && !d4.m.has(YABANCI), JSON.stringify({ l4, sil4a, sil4b }));
      const silinen = [];
      const o5 = Object.assign({ $nextTick: (f) => { if (f) f(); return Promise.resolve(); }, dilSecim: 'tr',
        istemciAl: async () => ({ yerelSil: async (k) => { silinen.push(k); return true; }, yabancilar: async () => [] }) },
      E.data ? E.data.call({}) : {}, E.methods || {});
      for (const [ad, fn] of Object.entries(E.computed || {})) Object.defineProperty(o5, ad, { get: fn.bind(o5), configurable: true });
      const odak5 = [];
      o5._odakla = (s) => odak5.push(s);
      if (o5.yabanciSil) {
        await o5.yabanciSil(YABANCI);
        o5.yabanciBasla(YABANCI);
        await o5.yabanciSil('0000000000000000');
        await o5.yabanciSil(YABANCI);
      }
      ok('[!] EU26/WIG: baska kartin kaydini silmek IKI ASAMALI (onaysiz / baska satirin onayiyla silmez), sonra liste yenilenir; liste bosalinca odak durum satirina',
         silinen.join() === YABANCI && odak5[odak5.length - 1] === '[data-es-durum]', JSON.stringify({ silinen, odak5 }));
      const ty = T.match(/<section class="kart" v-if="yabanci\.length"[^>]*>([\s\S]*?)<\/section>/);
      ok('[!] EU26: sablonda "baska kartlarin kayitlari" bolumu (kimlik + ad + n), her satirda iki asamali "bu tarayicidan sil"; anahtar aciklamasi onu gosteriyor',
         !!ty && /<h2 id="es-yabanci-baslik" tabindex="-1">/.test(ty[1]) && /y\.kimlik/.test(ty[1])
         && /<template v-if="yabanciOnay === y\.kimlik">[\s\S]*?@click="yabanciSil\(y\.kimlik\)"[\s\S]*?@click="yabanciVazgec\(y\.kimlik\)"/.test(ty[1])
         && /@click="yabanciBasla\(y\.kimlik\)"/.test(ty[1]) && /başka kart/i.test(SEx.ceviriEs('es.anahtar_aciklama', 'tr')),
         ty ? 'var' : 'yok');

      /* EU27 (WIG, inceleme [kucuk]): odak kaybolmaz; hata alanla iliskili */
      const odak = [];
      const kurE = (ist5) => {
        const x = Object.assign({ $refs: { parola: { value: 'sinama-parolasi-123' } }, $nextTick: (f) => { if (f) f(); return Promise.resolve(); },
          dilSecim: 'tr', istemciAl: async () => ist5 }, E.data ? E.data.call({}) : {}, E.methods || {});
        for (const [ad, fn] of Object.entries(E.computed || {})) Object.defineProperty(x, ad, { get: fn.bind(x), configurable: true });
        x._odakla = (s) => odak.push(s);
        x.listeYukle = async () => {};
        return x;
      };
      const ok1 = kurE({ esles: async () => ({ n: 3 }), durum: 'hazir', cihaz: { n: 3, ad: 'a' }, bilgi: { kimlik: KIMLIK, saat: 0 } });
      if (ok1.eslestir) await ok1.eslestir();
      const sonEs = odak.slice();
      odak.length = 0;
      const ok2 = kurE({});
      ok2.ad = '';
      if (ok2.eslestir) await ok2.eslestir();
      const adHata = { odak: odak.slice(), alan: ok2.retAlan };
      odak.length = 0;
      const ok3 = kurE({ unut: async () => ({ kart: 'silindi', n: 3, kod: null }), durum: 'yok', cihaz: null, bilgi: { kimlik: KIMLIK, saat: 0 } });
      ok3.unutOnay = true;
      if (ok3.unut) await ok3.unut();
      const unutOdak = odak.slice();
      odak.length = 0;
      const ok4 = kurE({ cihazSil: async () => ({ tamam: true }), cihazListe: async () => [] });
      ok4.kaldirOnay = 4;
      if (ok4.kaldir) await ok4.kaldir(4);
      const kaldirOdak = odak.slice();
      ok('[!] EU27/WIG: odak kaybolmaz — eslesince durum satirina, gecersiz adda ad alanina (retAlan "ad"), unuttan sonra ad alanina, kaldirdiktan sonra liste basligina',
         sonEs.join() === '[data-es-durum]' && adHata.odak.join() === '#es-ad' && adHata.alan === 'ad'
         && unutOdak.join() === '#es-ad' && kaldirOdak.join() === '#es-liste-baslik', JSON.stringify({ sonEs, adHata, unutOdak, kaldirOdak }));
    });
    {
      const T2 = T;
      ok('[!] EU27/WIG: hata alanla iliskili — ad ve parola alaninda :aria-invalid ve hata id`si (es-ret) :aria-describedby`de; durum satiri ve liste basligi odaklanabilir (tabindex -1)',
         /<input id="es-ad"[^>]*:aria-invalid="retAlan === 'ad' \? 'true' : null"[^>]*:aria-describedby="retAlan === 'ad' \? 'es-ad-ipucu es-ret' : 'es-ad-ipucu'"/.test(T2)
         && /<input id="es-parola"[^>]*:aria-invalid="retAlan === 'parola' \? 'true' : null"[^>]*:aria-describedby="retAlan === 'parola' \? 'es-parola-ipucu es-ret' : 'es-parola-ipucu'"/.test(T2)
         && /<p v-if="ret" id="es-ret" class="hata" role="alert" data-es-ret>/.test(T2)
         && /<p class="ay-ozet" data-es-durum tabindex="-1" aria-live="polite">/.test(T2) && /<h2 id="es-liste-baslik" tabindex="-1">/.test(T2));
      /* EU25 (inceleme [kucuk]): parola alani tarayicinin parola yoneticisine acik (autocomplete current-password — kart
         kokeninin kayitli web parolasi); metin "kaydedilmez" demez, panelin saklamadigini ve tarayicinin teklif edebilecegini soyler */
      const ip = SEx.ceviriEs('es.parola_ipucu', 'tr');
      const ipEn = SEx.ceviriEs('es.parola_ipucu', 'en');
      const ac = SEx.ceviriEs('es.aciklama', 'tr');
      ok('[!] EU25: parola metni dogru — panel saklamaz, tarayici kendi parola yoneticisine kaydetmeyi onerebilir (TR + EN); "hiçbir yere kaydedilmez" iddiasi YOK',
         /parola yöneticisi/.test(ip) && /panel/i.test(ip) && /password manager/.test(ipEn) && !/kaydedilmez/.test(ip) && !/hiçbir yere kaydedilmez/.test(ac)
         && /autocomplete="current-password"/.test(T2), ip);
    }
    /* EU23 (inceleme [kucuk], ES4 "sessiz degil"): kayit VARKEN IndexedDB acilamazsa serit uyarisi */
    SONRA.push(async () => {
      const var_ = al('cihazKaydiVar');
      const VT = al('CIHAZ_VT_AD');
      const bozukIdb = (tur) => ({
        databases: async () => [{ name: VT }],
        open() {
          if (tur === 'atar') throw new Error('UnknownError: Internal error opening backing store');
          const r = {};
          setImmediate(() => {
            if (tur === 'acilmaz') { r.error = new Error('UnknownError'); if (r.onerror) r.onerror(); return; }
            r.result = { close() {}, objectStoreNames: { contains: () => true },
              transaction: () => ({ objectStore: () => ({ count() { const q = {}; setImmediate(() => { q.error = new Error('x'); q.onerror(); }); return q; } }) }) };
            if (r.onsuccess) r.onsuccess();
          });
          return r;
        },
      });
      const sonuc = [];
      for (const tur of ['acilmaz', 'sayilmaz', 'atar']) sonuc.push(typeof var_ === 'function' ? await var_(bozukIdb(tur)) : 'yok');
      const u = ornek();
      const eskiIdb = sandbox.indexedDB;
      sandbox.indexedDB = bozukIdb('acilmaz');
      let ist = 'yok';
      try { ist = await u.eslesmeHazirla(); } finally { if (eskiIdb === undefined) delete sandbox.indexedDB; else sandbox.indexedDB = eskiIdb; }
      ok('[!] EU23: cihaz veritabani VARKEN (databases() listesinde) acilamaz / sayilamaz / atarsa "hata" -> imzasiz yol AMA serit uyarisi (sessiz degil); karar ezberlenmez',
         sonuc.join() === 'hata,hata,hata' && ist === null && /okunamadı/.test(u.eslesmeUyariMetni || '') && !u._esKarar,
         JSON.stringify({ sonuc, ist: ist === null ? null : typeof ist, uyari: u.eslesmeUyariMetni }));
    });
    /* EU29 -> EU30: eslesmis tarayicinin ACILIS boyu. EU29'da 266 199 B / 15 dosya. EU30: Eslestirme
       ekrani + metinleri istemciden ayrildi; IDDIA: ekran modulu ve sozluk_es.js bu kumeye GIRMEZ.
       Toplam 3D'nin 256 000 B sinirinin hala ~1 KB ustunde -> BILGI (iddia degil): kalan fark ancak
       kripto.js'in acilista yalniz HMAC'i (EU29 secenek b) ya da baska sozluk ailelerini ayirmakla kapanir
       — ikisi de bu dilimin kapsami disi (EU30). Dosya sayisi da bilgi (12'ye inmek imza/kripto birlesmesi ister). */
    {
      const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
      const by = fs.existsSync(kunyeYolu) ? (JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).bayt || {}) : {};
      const acK = new Set(['index.html']);
      for (const m of html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)) if (!/^(https?:|data:|#|mailto:)/.test(m[1])) acK.add(m[1]);
      for (const g of iceAktarmaGrafigi()) acK.add(g.goruntu);
      const canliZ = ['ekran/canli.js', ...iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'canli.js')).map((g) => g.goruntu)].filter((x) => !acK.has(x));
      const esZ = fs.existsSync(esYolu) ? ['ekran/eslesme.js', ...iceAktarmaGrafigi(esYolu).map((g) => g.goruntu)].filter((x) => !acK.has(x)) : [];
      const top = (l) => l.reduce((n, a) => n + (by[a] || 0), 0);
      const a0 = top([...acK]);
      const c0 = top([...new Set(canliZ)]);
      const e0 = top([...new Set(esZ)]);
      const hepsi = new Set([...acK, ...canliZ, ...esZ]);
      const toplam = top([...hepsi]);
      ok('[!] EU30: ESLESMIS tarayicinin Canli ile acilisi (acilis kumesi + Canli zinciri + istemci zinciri) Eslestirme EKRANINI ve metinlerini (eslesme_ekran.js, sozluk_es.js) ICERMEZ',
         esZ.length > 0 && esZ.includes('ekran/eslesme.js') && !hepsi.has('ekran/eslesme_ekran.js') && !hepsi.has('ortak/sozluk_es.js'),
         [...hepsi].filter((x) => /eslesme|sozluk|imza|kripto/.test(x)).join(' '));
      /* EU31 (karar, kullanicinin devriyle 2026-10-03): eslesmis acilisin 3D sinirini ~1 KB / 3 dosya asmasi
         ESLESMIS TARAYICIYA OZGU istisna olarak kabul — kalan farki kapatmak kripto.js'i bolmeyi ister,
         %0.4'luk asim icin orantisiz. Ama sessizce buyumesin: AYRI tavan 262 144 B (256 KiB) / 15 dosya. */
      const ES_ACILIS_TAVAN = 262144;
      const ES_ACILIS_DOSYA = 15;
      ok('[!] EU31: ESLESMIS tarayicinin Canli ile acilisi <= 262 144 B gzip ve <= 15 dosya (3D sinirinin eslesmis istisnasi; buyume kilitli)',
         toplam > 0 && toplam <= ES_ACILIS_TAVAN && hepsi.size <= ES_ACILIS_DOSYA,
         `${a0} + ${c0} + ${e0} = ${toplam} B (%${(100 * toplam / 256000).toFixed(1)} / 3D 256000), ${hepsi.size} dosya`);
      /* EU32 (W3, 2026-10-03): tembel ekran zincirlerinin YALNIZ kendi kullandigi metinleri acilis sozlugunden
         ayrildi (sozluk_kayit.js: Kayitlar / kayit gorunumu / Karsilastirma; sozluk_ay.js: Ayarlar modulu).
         Kazanc ancak bu dosyalar acilisa, #/skop'a, #/pil'e ve eslesmis acilisa GIRMEZSE gercek: iddia. */
      const zin = (ad) => [ad, ...iceAktarmaGrafigi(path.join(ARAYUZ, ad)).map((g) => g.goruntu)];
      const skopK = new Set([...acK, ...zin('ekran/osiloskop.js')]);
      const pilK = new Set([...acK, ...zin('ekran/pil.js')]);
      const tembel = ['ortak/sozluk_kayit.js', 'ortak/sozluk_ay.js'];
      const kayitZ = zin('ekran/kayitlar.js');
      const krZ = zin('ekran/karsilastir.js');
      const ayZ = zin('ekran/ayarlar.js');
      ok('[!] EU32: tembel ekran sozlukleri (sozluk_kayit.js, sozluk_ay.js) acilis kumesinde, #/skop ve #/pil acilisinda, eslesmis acilista YOK; sozluk_kayit yalniz Kayitlar / Karsilastirma, sozluk_ay yalniz Ayarlar zincirinde',
         tembel.every((x) => !acK.has(x) && !skopK.has(x) && !pilK.has(x) && !hepsi.has(x) && by[x] > 0)
         && kayitZ.includes('ortak/sozluk_kayit.js') && krZ.includes('ortak/sozluk_kayit.js') && !ayZ.includes('ortak/sozluk_kayit.js')
         && ayZ.includes('ortak/sozluk_ay.js') && !kayitZ.includes('ortak/sozluk_ay.js') && !krZ.includes('ortak/sozluk_ay.js'),
         tembel.map((x) => `${x} ${by[x]} B`).join(' · '));
      /* Buyume kilidi: W3 oncesi acilis sozlugu 27 727 B gzip, sonrasi 18 187 B. Tavan kabugun yeni metinlerine
         ~1.3 KB pay birakir; asilirsa once yeni metin tembel bir ekranin sozlugune gidebilir mi diye bakilir. */
      const SOZ_ACILIS_TAVAN = 19500;
      ok('[!] EU32: acilis sozlugu (ortak/sozluk.js) <= 19 500 B gzip (W3 oncesi 27 727 B; ekran metinleri acilisa geri donerse kirmizi)',
         by['ortak/sozluk.js'] > 0 && by['ortak/sozluk.js'] <= SOZ_ACILIS_TAVAN, `${by['ortak/sozluk.js']} B`);
    }
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   32. p0 SAGLAMLIGI (3H-2 guvenlik incelemesi, 2026-10-02 gece)
   - p0 tek atimlikti: kartin komut kuyrugu doluyken 503 ("kuyruk dolu") ya da tek bir ag
     hatasi DURDURMA'yi kaybettiriyordu. p0 es etkili (iki kez durdurmak zararsiz) ->
     ag hatasi ve 503'te kisa artan beklemeyle yeniden denenir; 4xx hemen doner.
   - p0 tarayicinin onbellekteki Basic-Auth basligini tasiyordu (credentials varsayilani
     'same-origin'): kart p0'i parolasiz kabul ediyor (komut_serbest), kopru Basic hic
     kullanmiyor — her durdurmada parola acik HTTP'den gidiyordu. Artik credentials 'omit'.
   - /durum (kopru yoklamasi) da ayni sebeple 'omit'.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 32. p0 sagligi (yeniden deneme + parolasiz) ---');
{
  let p0Gonder = null, P0_DENEME = null, P0_BEKLE_MS = null;
  try {
    p0Gonder = vm.runInContext('p0Gonder', sandbox);
    P0_DENEME = vm.runInContext('P0_DENEME', sandbox);
    P0_BEKLE_MS = vm.runInContext('P0_BEKLE_MS', sandbox);
  } catch (e) { /* yok -> iddialar kirmizi */ }
  SONRA.push(async () => {
    const bekleyen = [];
    const bekle = (ms) => { bekleyen.push(ms); return Promise.resolve(); };
    const sirayla = (dizi) => { let n = 0; const f = async () => { const v = dizi[Math.min(n++, dizi.length - 1)]; if (v === 'at') throw new TypeError('Failed to fetch'); return v; }; f.say = () => n; return f; };
    let a = null, b = null, c = null, aB = [], bB = [], cB = [], aN = 0, bN = 0, cN = 0;
    if (typeof p0Gonder === 'function') {
      const fa = sirayla([null, { ok: false, status: 503 }, 'at', { ok: true, status: 200 }]);
      a = await p0Gonder(fa, bekle); aN = fa.say(); aB = bekleyen.splice(0);
      const fb = sirayla([{ ok: false, status: 403 }, { ok: true, status: 200 }]);
      b = await p0Gonder(fb, bekle); bN = fb.say(); bB = bekleyen.splice(0);
      const fc = sirayla([{ ok: false, status: 503 }]);
      c = await p0Gonder(fc, bekle); cN = fc.say(); cB = bekleyen.splice(0);
    }
    const toplam = cB.reduce((s, x) => s + x, 0);
    ok('[!] EMNIYET-P0: ag hatasi / istisna / 503\'te kisa artan beklemeyle yeniden denenir, 4xx hemen doner, en fazla P0_DENEME',
       a && a.status === 200 && aN === 4 && aB.join() === `${P0_BEKLE_MS},${2 * P0_BEKLE_MS},${3 * P0_BEKLE_MS}`
       && b && b.status === 403 && bN === 1 && bB.length === 0
       && c && c.status === 503 && cN === P0_DENEME && cB.length === P0_DENEME - 1 && P0_DENEME >= 3,
       JSON.stringify({ a, aN, aB, b, bN, bB, c, cN, cB }));
    ok('[!] EMNIYET-P0: en kotu durumda toplam bekleme <= 1.5 s (durdurma gecikmesin)', toplam > 0 && toplam <= 1500, `${toplam} ms`);

    /* Tasiyici: p0 parolasiz (omit), baska komut eskisi gibi (Basic-Auth gerekebilir) */
    const giden = [];
    const eskiFetch = sandbox.fetch;
    let p0Ilk = true;
    sandbox.fetch = async (url, sec) => {
      giden.push({ url, sec });
      if (sec && sec.body === 'p0' && p0Ilk) { p0Ilk = false; return { ok: false, status: 503, text: async () => 'kuyruk dolu' }; }
      return { ok: true, status: 200, text: async () => '' };
    };
    const eskiZaman = sandbox.setTimeout;
    sandbox.setTimeout = (f) => { f(); return 0; };     // p0Gonder'in varsayilan beklemesi aninda
    try {
      const TA = vm.runInContext('TasiyiciAkis', sandbox);
      const uyg = { kartAdres: (y) => y, jeton: 'j', satirIsle() {}, hata: '',
        kartIstek: (y, s) => sandbox.fetch(y, s) };   // eslesmemis yol: katman fetch'i aynen cagirir
      await TA.gonder(uyg, 'p0');
      await TA.gonder(uyg, 'G?');
    } catch (e) { giden.push({ hata: String(e) }); } finally { sandbox.fetch = eskiFetch; sandbox.setTimeout = eskiZaman; }
    ok('[!] EMNIYET-P0: tasiyici p0\'i p0Gonder\'den yollar (503\'ten sonra 2. deneme) ve onbellekteki Basic-Auth\'u TASIMAZ (credentials omit); diger komutlar degismedi',
       giden.length === 3 && giden.slice(0, 2).every((g) => g.sec && g.sec.credentials === 'omit' && g.sec.body === 'p0'
         && g.sec.headers['X-Olcum'] === '1')
       && giden[2].sec && giden[2].sec.credentials !== 'omit' && giden[2].sec.body === 'G?',
       JSON.stringify(giden.map((g) => g.sec ? { c: g.sec.credentials, b: g.sec.body } : g)));
  });
  ok('/durum yoklamalari (kopruYokla, kopruyuAlgila) onbellekteki Basic-Auth\'u tasimaz (credentials omit)',
     govdeIcinde(appKaynak, 'kopruYokla', "credentials: 'omit'") && govdeIcinde(appKaynak, 'kopruyuAlgila', "credentials: 'omit'"));
}

/* ═══════════════════════════════════════════════════════════════════════
   33. 4F (PC17) — PWA KABUGU: service worker, cevrimdisi sayfa, manifest

   Ayni panel karttan (`http://olcum.local`, guvenli baglam DEGIL), gelistirme
   sunucusundan (`localhost`) ve PC koprusunden (`http://olcum.localhost:8770`)
   aciliyor. Service worker YALNIZ kopru kokeninde ve guvenli baglamda kaydolur,
   acilisi bekletmez. sw.js'te onbellege yalniz IZIN LISTESINDEKI duragan kabuk
   dosyalari girer; API (/akis /komut /arsiv /kayit /skop* /pil /kal /eslestir
   /cihaz /saat /bildirim /kunye.json /durum) ASLA. Ag once, onbellek yedek;
   gezinme ag yoksa "kopru calismiyor". Gercek tarayicida olcum: T4F tarayici_pwa.py.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 33. 4F PWA kabugu (service worker + manifest) ---');
{
  /* (a) kayit karari — saf islev */
  let uygunF = null, SW_YOL = null;
  try { uygunF = vm.runInContext('swKaydiUygun', sandbox); SW_YOL = vm.runInContext('SW_YOL', sandbox); } catch (e) { /* yok */ }
  const K = (h, p = 'http:') => ({ protocol: p, hostname: h });
  const tablo = [
    ['PC koprusu olcum.localhost, guvenli', { guvenli: true, swVar: true, konum: K('olcum.localhost') }, true],
    ['kart olcum.local (guvenli degil)', { guvenli: false, swVar: false, konum: K('olcum.local') }, false],
    ['kart IP (guvenli degil)', { guvenli: false, swVar: false, konum: K('192.168.1.50') }, false],
    ['kopru adi ama guvenli baglam DEGIL', { guvenli: false, swVar: true, konum: K('olcum.localhost') }, false],
    ['gelistirme sunucusu localhost', { guvenli: true, swVar: true, konum: K('localhost') }, false],
    ['127.0.0.1 (guvenli ama kopru kokeni degil)', { guvenli: true, swVar: true, konum: K('127.0.0.1') }, false],
    ['serviceWorker API yok', { guvenli: true, swVar: false, konum: K('olcum.localhost') }, false],
    ['file://', { guvenli: true, swVar: true, konum: K('', 'file:') }, false],
    ['olcum.localhost.kotu.example', { guvenli: true, swVar: true, konum: K('olcum.localhost.kotu.example', 'https:') }, false],
    ['konum yok', { guvenli: true, swVar: true, konum: null }, false],
  ];
  const yanlis = typeof uygunF === 'function' ? tablo.filter(([, g, b]) => uygunF(g) !== b).map(([ad]) => ad) : ['swKaydiUygun yok'];
  ok('[!] 4F: service worker YALNIZ guvenli baglamdaki *.localhost (PC koprusu) kokeninde; kart, IP, localhost, file:// ATLANIR',
     yanlis.length === 0, yanlis.join(' | ') || `${tablo.length} durum`);

  /* (b) swKur: erteleme + atlama + eski kaydi silme (sahte pencere/gezgin) */
  const v = ornek();
  const ortam = ({ guvenli, sw = true, konum, hazir = 'interactive' }) => {
    const e = { kayit: [], silinen: 0, dinleyici: {}, zaman: [] };
    e.gezgin = sw ? { serviceWorker: {
      register(y, s) { e.kayit.push({ y, s }); return Promise.resolve({}); },
      getRegistrations() { return Promise.resolve([{ unregister() { e.silinen++; return Promise.resolve(true); } }]); },
    } } : {};
    e.pencere = { isSecureContext: guvenli, addEventListener(t, f, o) { e.dinleyici[t] = { f, o }; } };
    e.belge = { readyState: hazir };
    e.konum = konum;
    return e;
  };
  const eskiZaman = sandbox.setTimeout;
  let aktif = null;
  sandbox.setTimeout = (f) => { if (aktif) aktif.zaman.push(f); return 1; };
  const kopru = aktif = ortam({ guvenli: true, konum: K('olcum.localhost') });
  v.swKur(kopru.pencere, kopru.gezgin, kopru.konum, kopru.belge);
  const esz = kopru.kayit.length;                                  /* mounted aninda */
  const yukDinle = kopru.dinleyici.load;
  if (yukDinle) yukDinle.f();
  const loadSonrasi = kopru.kayit.length;                          /* load: yine sonraki tura */
  kopru.zaman.forEach((f) => f());
  const k0 = kopru.kayit[0] || { s: {} };
  ok('[!] 4F: kopru kokeninde kayit acilisi BEKLETMEZ: mounted\'ta ve load aninda degil, load\'dan sonraki gorev turunda',
     esz === 0 && !!yukDinle && yukDinle.o && yukDinle.o.once === true && loadSonrasi === 0 && kopru.kayit.length === 1,
     `mounted=${esz} load=${loadSonrasi} sonra=${kopru.kayit.length}`);
  ok('4F: kayit /sw.js, kapsam /, updateViaCache none (sw.js guncellemesi HTTP onbellegini atlar)',
     SW_YOL === '/sw.js' && k0.y === '/sw.js' && k0.s.scope === '/' && k0.s.updateViaCache === 'none',
     JSON.stringify(k0));
  const hazirOrtam = aktif = ortam({ guvenli: true, konum: K('olcum.localhost'), hazir: 'complete' });
  v.swKur(hazirOrtam.pencere, hazirOrtam.gezgin, hazirOrtam.konum, hazirOrtam.belge);
  hazirOrtam.zaman.forEach((f) => f());
  ok('4F: sayfa zaten yuklendiyse (readyState complete) load beklenmeden ertelenmis kayit',
     !hazirOrtam.dinleyici.load && hazirOrtam.kayit.length === 1);
  const kart = aktif = ortam({ guvenli: false, sw: false, konum: K('olcum.local') });
  v.swKur(kart.pencere, kart.gezgin, kart.konum, kart.belge);
  kart.zaman.forEach((f) => f());
  const kartSw = v._sw;
  const gel = aktif = ortam({ guvenli: true, konum: K('localhost') });
  v.swKur(gel.pencere, gel.gezgin, gel.konum, gel.belge);
  gel.zaman.forEach((f) => f());
  const sahteKopru = aktif = ortam({ guvenli: false, konum: K('olcum.localhost') });
  v.swKur(sahteKopru.pencere, sahteKopru.gezgin, sahteKopru.konum, sahteKopru.belge);
  sahteKopru.zaman.forEach((f) => f());
  sandbox.setTimeout = eskiZaman;
  aktif = null;
  ok('[!] 4F: kartta (guvenli degil) ve gelistirme sunucusunda kayit YOK, load dinleyicisi YOK',
     kart.kayit.length === 0 && !kart.dinleyici.load && kartSw && kartSw.uygun === false && kartSw.durum === 'atlandi'
     && gel.kayit.length === 0 && !gel.dinleyici.load && sahteKopru.kayit.length === 0,
     `kart=${kart.kayit.length} gelistirme=${gel.kayit.length} guvensiz-kopru=${sahteKopru.kayit.length}`);
  SONRA.push(async () => {
    await new Promise((c) => setImmediate(c));
    ok('4F: uygun olmayan guvenli kokende onceden kalmis kayit SILINIR (sessiz yarim durum yok)',
       gel.silinen === 1 && kopru.silinen === 0, `gelistirme=${gel.silinen} kopru=${kopru.silinen}`);
  });
  ok('4F: mounted() swKur\'u cagiriyor', govdeIcinde(appKaynak, 'mounted', 'this.swKur()'));

  /* (c) sw.js — node vm'de, sahte self/caches/fetch ile */
  const SWD = path.join(ARAYUZ, 'sw.js');
  const swKaynak = fs.existsSync(SWD) ? fs.readFileSync(SWD, 'utf8') : '';
  const KOKEN = 'http://olcum.localhost:8770';
  class Istek {
    constructor(u, o = {}) {
      this.url = typeof u === 'string' ? new URL(u, KOKEN).href : u.url;
      this.method = o.method || (typeof u === 'object' ? u.method : 'GET');
      this.mode = o.mode || (typeof u === 'object' ? u.mode : 'cors');
      this.cache = o.cache || 'default';
    }
  }
  class Yanit {
    constructor(govde, o = {}) {
      this.govde = govde; this.status = o.status === undefined ? 200 : o.status;
      this.ok = this.status >= 200 && this.status < 300; this.type = 'basic'; this.headers = o.headers || {};
    }
    clone() { return new Yanit(this.govde, { status: this.status, headers: this.headers }); }
  }
  const anahtar = (i) => (typeof i === 'string' ? new URL(i, KOKEN).href : i.url);
  const ag = { kapali: false, cagri: [], surum: 'yeni' };
  const depolar = new Map();
  const yazilan = [];
  const isleyici = {};
  const swB = {
    URL, Promise, console,
    Request: Istek, Response: Yanit,
    fetch: async (i, o = {}) => {
      const r = i instanceof Istek ? i : new Istek(i);
      ag.cagri.push({ url: r.url, cache: o.cache || r.cache, mode: r.mode });
      if (ag.kapali) throw new TypeError('Failed to fetch');
      return new Yanit(`${ag.surum}:${new URL(r.url).pathname}`);
    },
    caches: {
      async open(ad) {
        if (!depolar.has(ad)) depolar.set(ad, new Map());
        const m = depolar.get(ad);
        return {
          async put(i, y) { yazilan.push({ ad, url: anahtar(i) }); m.set(anahtar(i), y); },
          async match(i) { return m.get(anahtar(i)); },
          async add(i) { const y = await swB.fetch(i); yazilan.push({ ad, url: anahtar(i), cache: i.cache }); m.set(anahtar(i), y); },
        };
      },
      async keys() { return [...depolar.keys()]; },
      async delete(ad) { return depolar.delete(ad); },
    },
    self: null,
  };
  let atla = 0, sahip = 0;
  swB.self = {
    location: { origin: KOKEN },
    addEventListener(t, f) { isleyici[t] = f; },
    skipWaiting() { atla++; return Promise.resolve(); },
    clients: { claim() { sahip++; return Promise.resolve(); } },
  };
  vm.createContext(swB);
  let swYuklendi = true;
  try { vm.runInContext(swKaynak, swB, { filename: 'sw.js' }); } catch (e) { swYuklendi = false; console.log('     sw.js yuklenemedi: ' + e); }
  const swDeger = (ad) => { try { return vm.runInContext(ad, swB); } catch (e) { return undefined; } };
  const izinli = swDeger('onbellekIzinli');
  const ONB = swDeger('ONBELLEK');
  const SURUM = swDeger('SURUM');
  ok('4F: sw.js yuklendi; onbellek adi olcum-kabuk-<SURUM> (SURUM 12 onaltilik, arayuz-uret.py yazar)',
     swYuklendi && typeof izinli === 'function' && /^[0-9a-f]{12}$/.test(SURUM || '') && ONB === 'olcum-kabuk-' + SURUM
     && ['install', 'activate', 'fetch'].every((t) => typeof isleyici[t] === 'function'),
     `${ONB}`);

  /* izin listesi: PC17'nin yasak yollari + her API ucu + sorgulu adres + gezinme kabugu disari */
  const YASAK = ['/akis', '/komut', '/arsiv/liste', '/arsiv/veri', '/kayit/liste', '/kayit/veri', '/skop.bin',
    '/skop/liste', '/skop/al', '/pil', '/kal/liste', '/eslestir', '/cihaz', '/saat', '/bildirim/bilgi',
    '/kunye.json', '/durum', '/devral', '/sw.js', '/sahte-kart.js', '/', '/index.html',
    '/ortak/x.json', '/ekran/alt/x.js', '/ortak/../akis.js', '/vendor/baska.js'];
  const sizan = typeof izinli === 'function' ? YASAK.filter((y) => izinli(y)) : ['onbellekIzinli yok'];
  ok('[!] 4F: izin listesi API yollarini (PC17: /akis /komut /arsiv /kayit /skop* /pil /kal /eslestir /cihaz /saat /bildirim /kunye.json) ve /durum, /sw.js, gezinme kabugunu KABUL ETMEZ',
     sizan.length === 0, sizan.join(' ') || `${YASAK.length} yol`);
  const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
  const goruntu = fs.existsSync(kunyeYolu) ? Object.keys(JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')).kaynak || {}) : [];
  const kabukDosya = goruntu.filter((a) => a !== 'index.html').concat(['cevrimdisi.html']);
  const disarda = typeof izinli === 'function' ? kabukDosya.filter((a) => !izinli('/' + a)) : ['onbellekIzinli yok'];
  ok('4F: kart goruntusundeki her duragan dosya (index.html haric) + cevrimdisi.html izin listesinde (yeni varlik unutulmasin)',
     goruntu.length > 10 && disarda.length === 0, disarda.join(' ') || `${kabukDosya.length} dosya`);

  SONRA.push(async () => {
    const gonder = async (istek) => {
      let yp = null; const bekleyen = [];
      const olay = { request: istek, respondWith(p) { yp = Promise.resolve(p); }, waitUntil(p) { bekleyen.push(p); } };
      isleyici.fetch(olay);
      let yanit = null, hata = null;
      if (yp) { try { yanit = await yp; } catch (e) { hata = e; } }
      await Promise.all(bekleyen);
      return { cevap: !!yp, yanit, hata };
    };
    const kur = async () => {
      const b = []; isleyici.install({ waitUntil(p) { b.push(p); } }); await Promise.all(b);
    };
    if (!swYuklendi || typeof isleyici.fetch !== 'function') {
      ok('[!] 4F: sw.js fetch isleyicisi sinanabildi', false, 'sw.js yuklenmedi');
      return;
    }
    await kur();
    const cevrim = (depolar.get(ONB) || new Map()).get(KOKEN + '/cevrimdisi.html');
    ok('4F: install cevrimdisi.html\'i onbellege alir (HTTP onbellegini atlayarak) ve skipWaiting',
       !!cevrim && yazilan.some((y) => y.url === KOKEN + '/cevrimdisi.html' && y.cache === 'reload') && atla === 1);

    /* API ve yasak yollar: respondWith YOK, onbellege yazim YOK (GET, POST, gezinme disi) */
    const yazOnce = yazilan.length;
    const dokunan = [];
    for (const y of YASAK.filter((x) => x !== '/' && x !== '/index.html')) {
      const s = await gonder(new Istek(y));
      if (s.cevap) dokunan.push(y);
    }
    for (const y of ['/komut', '/eslestir', '/kayit/onay', '/app.js']) {
      const s = await gonder(new Istek(y, { method: 'POST' }));
      if (s.cevap) dokunan.push('POST ' + y);
    }
    for (const y of ['/app.js?v=2', '/ortak/sozluk.js?x', '/akis?jeton=abc']) {
      const s = await gonder(new Istek(y));
      if (s.cevap) dokunan.push(y);
    }
    const yabanci = await gonder(new Istek('http://olcum.local/app.js'));
    if (yabanci.cevap) dokunan.push('baska koken');
    ok('[!] 4F: API / yasak / sorgulu / baska kokenli istekte service worker KARISMAZ ve onbellege HICBIR SEY yazilmaz',
       dokunan.length === 0 && yazilan.length === yazOnce, dokunan.join(' ') || `yazilan ${yazilan.length - yazOnce}`);

    /* ag once: onbellekte ESKI kopya varken ag acik -> agdan gelen (yeni) doner ve onbellek guncellenir */
    const onb = depolar.get(ONB);
    onb.set(KOKEN + '/style.css', new Yanit('eski:/style.css'));
    ag.cagri.length = 0;
    const s1 = await gonder(new Istek('/style.css'));
    ok('[!] 4F: AG ONCE: onbellekte eski kopya varken agdan gelen doner, HTTP onbellegi atlanir (no-cache), onbellek tazelenir',
       s1.cevap && s1.yanit && s1.yanit.govde === 'yeni:/style.css' && ag.cagri.length === 1 && ag.cagri[0].cache === 'no-cache'
       && onb.get(KOKEN + '/style.css').govde === 'yeni:/style.css',
       JSON.stringify({ g: s1.yanit && s1.yanit.govde, c: ag.cagri }));
    ag.kapali = true;
    const s2 = await gonder(new Istek('/style.css'));
    const s3 = await gonder(new Istek('/ekran/hic-inmedi.js'));
    ok('4F: ag yokken (kopru kapali) onbellekteki kabuk dosyasi doner; hic inmemis modul HATA verir (yanlis dosya degil)',
       s2.yanit && s2.yanit.govde === 'yeni:/style.css' && s3.cevap && s3.yanit === null && s3.hata instanceof TypeError);
    const s4 = await gonder(new Istek('/#/canli', { mode: 'navigate' }));
    ok('[!] 4F: gezinme ag yokken "kopru calismiyor" sayfasini verir (cevrimdisi.html)',
       s4.cevap && s4.yanit === cevrim, s4.yanit ? String(s4.yanit.govde).slice(0, 40) : String(s4.hata));
    onb.delete(KOKEN + '/cevrimdisi.html');
    const s5 = await gonder(new Istek('/', { mode: 'navigate' }));
    ok('4F: cevrimdisi.html de onbellekte yoksa dis kaynaksiz yedek sayfa (503)',
       s5.yanit && s5.yanit.status === 503 && /Köprü çalışmıyor/.test(s5.yanit.govde) && !/https?:/.test(s5.yanit.govde));
    ag.kapali = false;
    const yazOnce2 = yazilan.length;
    const s6 = await gonder(new Istek('/', { mode: 'navigate' }));
    ok('4F: gezinme ag acikken agdan gelir ve onbellege YAZILMAZ (eski index.html yeni modullerle karismaz)',
       s6.yanit && s6.yanit.govde === 'yeni:/' && yazilan.length === yazOnce2);

    /* activate: yalniz kendi eski surumlerini siler, kontrolu hemen alir */
    depolar.set('olcum-kabuk-000000000001', new Map());
    depolar.set('baska-uygulama', new Map());
    const b = []; isleyici.activate({ waitUntil(p) { b.push(p); } }); await Promise.all(b);
    ok('4F: activate eski olcum-kabuk-* onbelleklerini siler, guncel ve yabanci onbellege dokunmaz, clients.claim',
       !depolar.has('olcum-kabuk-000000000001') && depolar.has('baska-uygulama') && depolar.has(ONB) && sahip === 1,
       [...depolar.keys()].join(' '));
  });

  /* (d) manifest + ikonlar */
  const zlib = require('zlib');
  const png = (dosya) => {
    /* Kucuk PNG cozucu: 8 bit, renk tipi 2 (RGB) ya da 3 (paletli), 5 filtrenin hepsi */
    const b = fs.readFileSync(dosya);
    if (b.slice(0, 8).toString('hex') !== '89504e470d0a1a0a') return null;
    let i = 8, en = 0, boy = 0, tip = 0, derinlik = 0, plte = null; const idat = [];
    while (i < b.length) {
      const n = b.readUInt32BE(i), t = b.slice(i + 4, i + 8).toString('latin1'), d = b.slice(i + 8, i + 8 + n);
      if (t === 'IHDR') { en = d.readUInt32BE(0); boy = d.readUInt32BE(4); derinlik = d[8]; tip = d[9]; }
      else if (t === 'PLTE') plte = d;
      else if (t === 'IDAT') idat.push(d);
      i += 12 + n;
    }
    if (derinlik !== 8 || (tip !== 2 && tip !== 3)) return { en, boy, piksel: null };
    const bpp = tip === 2 ? 3 : 1, satir = en * bpp, ham = zlib.inflateSync(Buffer.concat(idat));
    const out = Buffer.alloc(satir * boy);
    for (let y = 0; y < boy; y++) {
      const f = ham[y * (satir + 1)];
      for (let x = 0; x < satir; x++) {
        const r = ham[y * (satir + 1) + 1 + x];
        const a = x >= bpp ? out[y * satir + x - bpp] : 0, u = y ? out[(y - 1) * satir + x] : 0;
        const c = x >= bpp && y ? out[(y - 1) * satir + x - bpp] : 0;
        const p = a + u - c, pa = Math.abs(p - a), pb = Math.abs(p - u), pc = Math.abs(p - c);
        const tah = [0, a, u, (a + u) >> 1, pa <= pb && pa <= pc ? a : (pb <= pc ? u : c)][f];
        out[y * satir + x] = (r + tah) & 255;
      }
    }
    const renk = (x, y) => {
      if (tip === 2) return out.slice((y * en + x) * 3, (y * en + x) * 3 + 3).toString('hex');
      const k = out[y * en + x]; return plte.slice(k * 3, k * 3 + 3).toString('hex');
    };
    return { en, boy, renk };
  };
  let man = null;
  try { man = JSON.parse(fs.readFileSync(path.join(ARAYUZ, 'manifest.json'), 'utf8')); } catch (e) { man = null; }
  ok('[!] 4F: manifest id, scope, start_url = "/" (kart ve kopru paneli kokten), standalone, Turkce ad',
     !!man && man.id === '/' && man.scope === '/' && man.start_url === '/' && man.display === 'standalone'
     && man.name === 'Ölçüm Kartı' && man.short_name === 'Ölçüm' && man.lang === 'tr',
     man ? JSON.stringify({ id: man.id, scope: man.scope, start_url: man.start_url }) : 'manifest okunamadi');
  const ikonlar = (man && man.icons) || [];
  const var2 = (n, amac) => ikonlar.some((x) => x.sizes === `${n}x${n}` && x.purpose === amac && x.type === 'image/png');
  ok('[!] 4F: 192 ve 512 px ikon, hem any hem maskable (Edge/Chrome kurulum olcutu)',
     var2(192, 'any') && var2(512, 'any') && var2(192, 'maskable') && var2(512, 'maskable'),
     ikonlar.map((x) => `${x.src}:${x.sizes}:${x.purpose}`).join(' '));
  const zeminHex = ((man && man.background_color) || '').replace('#', '').toLowerCase();
  const olcuYanlis = [];
  const maskeTasan = [];
  for (const x of ikonlar) {
    const p = fs.existsSync(path.join(ARAYUZ, x.src)) ? png(path.join(ARAYUZ, x.src)) : null;
    if (!p || `${p.en}x${p.boy}` !== x.sizes || !p.renk) { olcuYanlis.push(`${x.src}=${p ? p.en + 'x' + p.boy : 'yok'}`); continue; }
    let dolu = 0, uzak = 0;
    const r2 = (0.4 * p.en) ** 2;
    for (let y = 0; y < p.boy; y++) {
      for (let xx = 0; xx < p.en; xx++) {
        if (p.renk(xx, y) === zeminHex) continue;
        dolu++;
        if (((xx + 0.5 - p.en / 2) ** 2 + (y + 0.5 - p.boy / 2) ** 2) > r2) uzak++;
      }
    }
    if (p.renk(0, 0) !== zeminHex || dolu < p.en * 2) olcuYanlis.push(`${x.src}: kose zemini ${p.renk(0, 0)} / dolu ${dolu}`);
    if (x.purpose === 'maskable' && uzak > 0) maskeTasan.push(`${x.src}: ${uzak} piksel`);
  }
  ok('4F: her manifest ikonu diskte, PNG olcusu `sizes` ile AYNI, zemini background_color, bos degil',
     ikonlar.length >= 5 && olcuYanlis.length === 0, olcuYanlis.join(' | ') || `${ikonlar.length} ikon`);
  ok('[!] 4F: maskable ikonlarin cizimi guvenli dairede (merkez, yaricap %40) — maske kirpinca egriler kesilmez',
     ikonlar.some((x) => x.purpose === 'maskable') && maskeTasan.length === 0, maskeTasan.join(' | ') || 'tasma yok');
  const meta = (htmlKaynak.match(/<meta name="theme-color" content="(#[0-9a-fA-F]{6})">/) || [])[1];
  ok('4F: manifest theme_color index.html theme-color ile AYNI (ilk boyama ile kurulu pencere ayrismaz)',
     !!man && !!meta && man.theme_color.toLowerCase() === meta.toLowerCase(), `${man && man.theme_color} / ${meta}`);
  /* (e) butce: PC kabugu kartin ACILIS kumesine girmez */
  const istenen = [...yorumsuz(htmlKaynak).matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)].map((m) => m[1]);
  const kabukIstek = istenen.filter((u) => /^(sw\.js|cevrimdisi\.html)$/.test(u) || (/^ikon-/.test(u) && u !== 'ikon-180.png'));
  ok('[!] 4F: sw.js, cevrimdisi.html ve yeni ikonlar index.html\'den istenmiyor (kartta acilis istegi ve butce degismez)',
     kabukIstek.length === 0 && istenen.includes('ikon-180.png'), kabukIstek.join(' ') || 'yalniz ikon-180 (apple-touch-icon)');
}

/* ═══════════════════════════════════════════════════════════════════════
   33. 4D — PANEL PC'DE (alt proje 4; PC10, PC11, PC12)
   Kararlar tasarim/2026-10-03-alt-proje-4-pc.md "4D uygulama kararlari".
   (a) KAYNAK: denetci kopru kokeninde `/durum` `pc_arsiv` ile PC arsivini secer; kart
       kokeninde bu karar ICIN istek YOK (kartin sundugu panel aynen).
   (b) depo_pc.js SALT OKUMA: yazan her yontem reddeder, aga istek gitmez; okuma kopru
       baytlarini AYNEN birlestirir (X-Arsiv-Boy).
   (c) Kayitlar PC kipinde: nerede 'pc', esitleme / arsiv onayi / silme yok, kopru
       esitlemesinin durum satiri (TR + EN), canli bolgede.
   (d) PC11: /pil kopru vekilinden ('http'), vekil karta ulasamazsa (502) `p` -> B;
       Ayarlar kalibrasyon gecmisi vekilden, 502'de PC arsivinin kopyasi.
   (e) EU8'/EU9': kopru uclari (/durum, /arsiv/*, /esitleme/durum) imza katmanina girmez;
       kartin uclari (/pil, /kal/liste, /kunye.json) kartIstek'ten (kopruda vekil imzalar).
   (f) PC12: skop "eski arsiv" basligi sozlukten, bayat `kopru/arsiv` yolu yok.
   Gercek tarayici + gercek kopru + gercek arsiv baytlari: tarayici_pc_kayit.py (T4D).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 33. 4D: panel PC koprusunde (PC arsivi salt okuma, vekil, eski skop arsivi) ---');
{
  const ek = (ad) => require(path.join(ARAYUZ, 'ekran', ad));
  const src = (ad) => require(path.join(KOK, 'ortak', 'src', ad));
  const ES = ek('esitleme.js');
  const DPC = ek('depo_pc.js');
  const KL = ek('kayitlar.js');
  const AY = ek('ayarlar.js');
  const K = src('kayit.js');
  const ESI = src('esitle.js');
  const IM = src('imza.js');
  const SZP = src('sozluk_pc.js');
  const SZ = sozlukTum();
  const kaynak = (ad) => fs.readFileSync(path.join(ARAYUZ, 'ekran', ad), 'utf8');
  const html = yorumsuz(htmlKaynak);

  /* gercek kayit bicimi: oturum 5 (3 NOKTA) + oturum 9 (2 NOKTA) */
  const nokta = (sira, ot) => K.kayitPaketle(K.T_NOKTA, sira, ot, new Uint8Array(4 + 36));
  const parcalar = [nokta(101, 5), nokta(102, 5), nokta(103, 5), nokta(104, 9), nokta(105, 9)];
  const VERI = new Uint8Array(parcalar.reduce((n, p) => n + p.length, 0));
  { let a = 0; for (const p of parcalar) { VERI.set(p, a); a += p.length; } }
  const KUYRUK = new Uint8Array([0xA5, 2, 40, 0, 1, 2, 3]);       // kalici onekin otesi — kopru VERMEZ
  const KAL = new TextEncoder().encode(JSON.stringify({ adet: 1, etkin: 1, azami: 40, kayitlar: [{ no: 1, unix: 1790000000 }] }));
  const LISTE = { arsivler: [
    { kart: '0a1b2c3d4e5f6a7b', akis: 3995957410, bayt: VERI.length, dosya_bayt: VERI.length + KUYRUK.length, degisim: 1790000100.5,
      durum: { son_sira: 105, bayt: VERI.length, onaylanan: 0, kimlik: 3995957410 }, kal: true, oturum: 2, oturumlar: [] },
    { kart: '0a1b2c3d4e5f6a7b', akis: 77, bayt: 0, degisim: 1790000000, durum: null, kal: false, oturum: 0 },
    { kart: 'KOTU', akis: 1, bayt: 0 },
  ] };
  const yanit = (status, govde, basliklar = {}) => {
    const b = typeof govde === 'string' ? new TextEncoder().encode(govde) : govde || new Uint8Array(0);
    const h = new Map(Object.entries(basliklar).map(([a, v]) => [a.toLowerCase(), String(v)]));
    return { status, ok: status >= 200 && status < 300, headers: { get: (a) => (h.has(a.toLowerCase()) ? h.get(a.toLowerCase()) : null) },
      text: async () => new TextDecoder().decode(b), json: async () => JSON.parse(new TextDecoder().decode(b)),
      arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) };
  };
  /* Kopru taklidi: /durum, /arsiv/liste, /arsiv/veri (aralik + X-Arsiv-Boy), /arsiv/kal, /esitleme/durum */
  const kopru = ({ pcArsiv = true, durumKod = 200 } = {}) => {
    const cagri = [];
    const f = async (url, sec = {}) => {
      cagri.push({ url: String(url), yontem: (sec && sec.method) || 'GET', sec });
      const u = new URL(String(url), 'http://olcum.localhost:8770');
      if (u.pathname === '/durum') return durumKod === 200 ? yanit(200, JSON.stringify({ kart: 'wifi:olcum.local', skop_arsiv: true, pc_arsiv: pcArsiv, vekil: true })) : yanit(durumKod, 'yok');
      if (u.pathname === '/arsiv/liste') return yanit(200, JSON.stringify(LISTE));
      if (u.pathname === '/arsiv/veri') {
        const of = Number(u.searchParams.get('ofset')), n = Number(u.searchParams.get('bayt'));
        if (u.searchParams.get('akis') !== '3995957410' || of > VERI.length) return yanit(400, 'x');
        return yanit(200, VERI.slice(of, Math.min(VERI.length, of + Math.min(n, 13))), { 'X-Arsiv-Boy': VERI.length });   // 13 B'lik parcalar
      }
      if (u.pathname === '/arsiv/kal') return u.searchParams.get('akis') === '3995957410' ? yanit(200, KAL) : yanit(404, '');
      if (u.pathname === '/esitleme/durum') return yanit(200, JSON.stringify({ etkin: true, onay: true, sonuc: 'tamam', son_basari: 1790000200, yeni_kayit: 3, toplam_yeni: 9, kart_son_sira: 105 }));
      return yanit(404, '');
    };
    f.cagri = cagri;
    return f;
  };
  const fetchIle = async (f, islev) => {
    const eski = globalThis.fetch;
    globalThis.fetch = f;
    try { return await islev(); } finally { globalThis.fetch = eski; }
  };
  const KOPRU_KONUM = { protocol: 'http:', hostname: 'olcum.localhost', host: 'olcum.localhost:8770' };
  const KART_KONUM = { protocol: 'http:', hostname: 'olcum.local', host: 'olcum.local' };
  const pcYukle = async () => DPC;
  const den = (konum, ek_ = {}) => new ES.EsitlemeDenetcisi({ kartAdres: (y) => y, konum, pcYukle, ...ek_ });

  /* ── (a) kaynak karari ─────────────────────────────────────────────── */
  const KS = ES.kokenSinama || (() => null);
  const kok = (h, p = 'http:') => KS({ protocol: p, hostname: h });
  ok('[!] 4D (a): koken sinamasi — olcum.localhost / localhost / 127.x / [::1] kopru olabilir; kart (olcum.local, IP), file: ve bos konum ASLA',
     kok('olcum.localhost') === true && kok('localhost') === true && kok('127.0.0.1') === true && kok('[::1]') === true
     && kok('olcum.local') === false && kok('192.168.1.50') === false && kok('olcum.localhost.example') === false
     && kok('localhost', 'file:') === false && KS(null) === false && KS(undefined) === false);
  SONRA.push(async () => {
    const fk = kopru();
    const kartK = await fetchIle(fk, () => den(KART_KONUM).kaynak());
    const kartIstek = fk.cagri.length;
    const kopruK = await fetchIle(fk, () => den(KOPRU_KONUM).kaynak());
    const lan = await fetchIle(kopru({ pcArsiv: false }), () => den(KOPRU_KONUM).kaynak());
    const gel = await fetchIle(kopru({ durumKod: 404 }), () => den({ protocol: 'http:', hostname: 'localhost' }).kaynak());
    let atan = 0;
    const d = den(KOPRU_KONUM);
    const ilk = await fetchIle(async () => { atan++; throw new TypeError('Failed to fetch'); }, () => d.kaynak());
    const ikinci = await fetchIle(fk, () => d.kaynak());
    ok('[!] 4D (a): KART kokeninde kaynak "tarayici" ve bu karar icin HICBIR istek yok (kartin sundugu panel aynen); kopruda /durum pc_arsiv:true -> "pc"; yerel ag (pc_arsiv false) / gelistirme sunucusu (404) -> "tarayici"; ag hatasi ezberlenmez',
       kartK === 'tarayici' && kartIstek === 0 && kopruK === 'pc' && fk.cagri.some((c) => c.url === '/durum' && c.sec.credentials === 'omit')
       && lan === 'tarayici' && gel === 'tarayici' && ilk === 'tarayici' && atan === 1 && ikinci === 'pc',
       `kart=${kartK}/${kartIstek} kopru=${kopruK} lan=${lan} gel=${gel} ag=${ilk}->${ikinci}`);
    ok('4D (a): kaynakCoz — yalniz 200 + JSON + `kart` + pc_arsiv === true "pc" (kartin 404\'u, bicimsiz govde, pc_arsiv "1" degil)',
       ES.kaynakCoz(200, '{"kart":"x","pc_arsiv":true}') === 'pc' && ES.kaynakCoz(404, '') === 'tarayici'
       && ES.kaynakCoz(200, '<html>') === 'tarayici' && ES.kaynakCoz(200, '{"kart":"x","pc_arsiv":"1"}') === 'tarayici'
       && ES.kaynakCoz(200, '{"pc_arsiv":true}') === 'tarayici');
  });

  /* ── (b) depo_pc.js salt okuma ─────────────────────────────────────── */
  SONRA.push(async () => {
    const fk = kopru();
    const liste = DPC.pcListeCoz(LISTE);
    const a = liste ? liste[0] : null;
    const depo = a ? DPC.pcDepo(fk, a) : null;
    const ret = [];
    for (const ad of ['kilitAl', 'durumYaz', 'veriEkle', 'veriKirp', 'kalYaz', 'kalArsivle']) {
      try { await depo[ad](new Uint8Array(3)); ret.push(ad + ':kabul'); } catch (h) { ret.push(h instanceof IM.CalismaHatasi ? 'ret' : ad + ':' + h.name); }
    }
    const yazmaIstek = fk.cagri.length;
    /* Esitleyici bu depoyla calisirsa ilk adimda (kilitAl) durur, /kayit/veri istenmez */
    let esit = 'gecti';
    const esitIstek = [];
    try {
      await new ESI.Esitleyici({ tabanUrl: '', depo, istek: async (t, y) => { esitIstek.push(y); return yanit(200, ''); } }).esitle();
    } catch (h) { esit = h instanceof IM.CalismaHatasi ? 'ret' : h.name; }
    const veri = await depo.veriOku(0);
    const kal = await depo.kalOku();
    const kalYok = await DPC.pcDepo(fk, liste[1]).kalOku();
    ok('[!] 4D (b): PC deposu SALT OKUMA — yazan her yontem (kilitAl, durumYaz, veriEkle, veriKirp, kalYaz, kalArsivle) CalismaHatasi ile reddeder ve aga istek atmaz; Esitleyici ilk adimda durur, /kayit/veri ISTENMEZ',
       ret.every((x) => x === 'ret') && ret.length === 6 && yazmaIstek === 0 && esit === 'ret' && esitIstek.length === 0,
       `${ret.join(' ')} istek=${yazmaIstek} esit=${esit}/${esitIstek.length}`);
    const vIstek = fk.cagri.filter((c) => c.url.startsWith('/arsiv/veri'));
    ok('[!] 4D (b): veriOku koprunun baytlarini AYNEN birlestirir (parca parca, X-Arsiv-Boy\'da durur — kuyruk istenmez); yalniz GET /arsiv/veri?kart&akis&ofset&bayt; kalOku /arsiv/kal, kopyasi yoksa istek atmadan null',
       veri.length === VERI.length && veri.every((x, i) => x === VERI[i]) && vIstek.length === Math.ceil(VERI.length / 13)
       && vIstek.every((c) => c.yontem === 'GET' && /^\/arsiv\/veri\?kart=0a1b2c3d4e5f6a7b&akis=3995957410&ofset=\d+&bayt=\d+$/.test(c.url))
       && new TextDecoder().decode(kal) === new TextDecoder().decode(KAL) && kalYok === null
       && fk.cagri.filter((c) => c.url.includes('akis=77')).length === 0,
       `${veri.length}/${VERI.length} istek=${vIstek.length}`);
    ok('4D (b): pcListeCoz — bicimsiz arsiv (kart 16 kucuk onaltilik degil) atilir; durum yalniz tamsayi alanlar; liste degilse null',
       liste.length === 2 && liste[0].durum.son_sira === 105 && liste[1].durum === null && DPC.pcListeCoz({}) === null
       && DPC.pcListeCoz(null) === null && DPC.pcListeCoz({ arsivler: [{ kart: '0A1B2C3D4E5F6A7B', akis: 1, bayt: 0 }] }).length === 0);
  });

  /* ── denetci PC kipinde ─────────────────────────────────────────────── */
  SONRA.push(async () => {
    const fk = kopru();
    const imzali = [];
    const d = den(KOPRU_KONUM, { istek: async (y) => { imzali.push(y); return yanit(500, ''); } });
    const r = await fetchIle(fk, async () => {
      const ak = await d.akislar();
      const v = await d.akisVerisi(3995957410);
      const b = await d.akisBaytlari(3995957410);
      const kb = await d.kalBaytlari(3995957410);
      const e = await d.esitle({ kimlik: 3995957410 });
      let sil = 'silindi';
      try { await d.akisSil(3995957410); } catch (h) { sil = h instanceof IM.CalismaHatasi ? 'ret' : h.name; }
      const ed = await d.esitlemeDurumu();
      return { ak, v, b, kb, e, sil, ed };
    });
    const bekl = K.oturumlariKur(K.akisOnek(VERI)[0]);
    ok('[!] 4D (PC10): kopruda denetci PC arsivini okur — akislar /arsiv/liste\'den (pc, kimlik = akis kimligi, kart), akisVerisi AYNI cozumle (oturumlar 5 ve 9), kalBaytlari kopyayi verir; esitle {durum:"pc"} (/kayit/* ISTENMEZ, onay yok), akisSil reddeder; hicbir istek imza katmanindan (istek) gecmez',
       r.ak.length === 2 && r.ak[0].pc === true && r.ak[0].kimlik === 3995957410 && r.ak[0].kart === '0a1b2c3d4e5f6a7b' && r.ak[0].kalVar === true
       && [...r.v.oturumlar.keys()].join() === [...bekl.keys()].join() && [...bekl.keys()].join() === '5,9'
       && r.b.length === VERI.length && r.v.kart === '0a1b2c3d4e5f6a7b' && r.kb && r.kb.length === KAL.length
       && r.e.durum === 'pc' && r.sil === 'ret' && r.ed && r.ed.sonuc === 'tamam' && imzali.length === 0
       && !fk.cagri.some((c) => /\/kayit\/|\/komut/.test(c.url)) && fk.cagri.every((c) => c.yontem === 'GET'),
       `${r.ak.length} ${[...r.v.oturumlar.keys()]} e=${r.e.durum} sil=${r.sil} imzali=${imzali.length} ${fk.cagri.map((c) => c.url.split('?')[0]).join(' ')}`);
  });

  /* ── (c) Kayitlar PC kipinde ───────────────────────────────────────── */
  {
    const U = ES.esitlemeUygunlugu;
    ok('[!] 4D (C1): PC kipinde esitleme YOK (sebep "pc"); kopru disinda C1 kurallari aynen',
       U({ kartTaban: '', tasiyici: 'akis', pc: true }).neden === 'pc' && U({ kartTaban: '', tasiyici: 'akis', pc: true }).uygun === false
       && U({ kartTaban: '', tasiyici: 'akis' }).uygun === true && U({ kartTaban: 'x', tasiyici: 'akis', pc: false }).neden === 'taban');
    const yerel = { kimlik: 3995957410, kart: '0a1b2c3d4e5f6a7b', bayt: 10, oturumlar: K.oturumlariKur(K.akisOnek(VERI)[0]), sonSira: new Map() };
    const sat = KL.listeBirlestir({ kart: null, yereller: [yerel], yerelNerede: 'pc' });
    const satT = KL.listeBirlestir({ kart: null, yereller: [yerel] });
    ok('[!] 4D: PC arsivinin satirlari nerede "pc" (metni sozluk_pc: "bu PC\'de"); varsayilan yine "tarayici"; karsilastirmaya secilebilir (yerelde)',
       sat.length === 2 && sat.every((s) => s.nerede === 'pc' && s.yerelde) && satT.every((s) => s.nerede === 'tarayici')
       && SZP.ceviriPc(require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js')).NEREDE_METIN.pc, 'tr').includes("PC'de")
       && SZP.ceviriPc('pc.nerede', 'en').includes('PC'), sat.map((s) => s.nerede).join());
    const PD = KL.pcDurumYazi || (() => '');
    const tamam = { etkin: true, onay: true, sonuc: 'tamam', son_basari: 1790000200, yeni_kayit: 3, toplam_yeni: 9, kart_son_sira: 105 };
    const t1 = PD(tamam, 'tr');
    const t2 = PD({ ...tamam, onay: false, sonuc: 'hata', mesaj: 'kart erisilemiyor', sonraki_deneme_s: 30 }, 'tr');
    const t3 = PD({ ...tamam, sonuc: 'atlandi', mesaj: 'yalniz USB' }, 'en');
    const t4 = PD({ etkin: false, neden: '--esitleme-yok' }, 'tr');
    const t5 = PD({ hata: 'HTTP 403' }, 'en');
    const t6 = PD({ etkin: true, onay: false, sonuc: 'bekliyor', son_basari: null }, 'tr');
    ok('[!] 4D: kopru esitlemesinin durum satiri — son basarili zaman, yeni kayit, kartin son sirasi, karta onay ACIK/KAPALI (acik: kart silebilir); hata sebebi + bekleme; atlandi; kapali; durum alinamadi; ilk tur bekleniyor (TR + EN)',
       /Köprü eşitlemesi: son başarılı \d{4}-\d\d-\d\d/.test(t1) && /3 yeni kayıt/.test(t1) && /105/.test(t1) && /silebilir/.test(t1)
       && /başarısız \(kart erisilemiyor\) — 30 s/.test(t2) && /kapalı/.test(t2) && /skipped \(yalniz USB\)/.test(t3)
       && /kapalı \(--esitleme-yok\)/.test(t4) && /did not report[\s\S]*HTTP 403/.test(t5) && /henüz bir tur/.test(t6)
       && PD(null) === '' && !/\{/.test(t1 + t2 + t3 + t4 + t5 + t6), [t1, t2, t3].join(' | '));
    const T = KL.KayitlarEkrani.template;
    ok('[!] 4D/WIG: Kayitlar sablonu — PC durum satiri CANLI bolgede (aria-live), salt okuma aciklamasi, nerede suzgecinde "pc" (PC kipinde tarayici/kart/ikisi yok), kopya silme dugmeleri PC kipinde YOK, ozet satiri PC arsivini anlatir',
       /data-kl-pc-durum/.test(((T.match(/<div class="kl-duyuru" aria-live="polite">((?:(?!<\/div>)[\s\S])*)<\/div>/) || [])[1]) || '')
       && /<p v-if="pc" class="ipucu" data-kl-pc-salt>\{\{ pm\.salt \}\}<\/p>/.test(T)
       && /<option v-if="pc" value="pc">[\s\S]*?<template v-else>[\s\S]*?value="tarayici"/.test(T)
       && /<template v-if="!pc && silOnay === k\.kimlik">/.test(T) && /<button v-else-if="!pc" type="button" :data-kl-sil=/.test(T)
       && /v-else-if="pc" class="kl-kart-ozet" data-kl-pc-ozet>\{\{ pcOzetMetin \}\}/.test(T));
    /* bilesen mantigi: etkinlesti once kaynak; PC kipinde kartin dizini sorulmaz, esitleme cagrilmaz */
    const o = Object.assign({}, KL.KayitlarEkrani.data.call({ dilSecim: 'tr' }), KL.KayitlarEkrani.methods,
      { kartAdres: (y) => y, kartTaban: '', tasiyici: 'akis', bagli: true, dilSecim: 'tr', $nextTick: (f) => f && f() });
    for (const [ad, fn] of Object.entries(KL.KayitlarEkrani.computed)) Object.defineProperty(o, ad, { get: fn.bind(o) });
    const olay = [];
    o._den = { kaynak: async () => 'pc', akislar: async () => [{ kimlik: 3995957410, kart: '0a1b2c3d4e5f6a7b', olusma: 1, pc: true }],
      akisVerisi: async () => ({ ...yerel, durum: { son_sira: 105 } }), kartListesi: async () => { olay.push('kartListesi'); return { durum: 'yok' }; },
      esitle: async () => { olay.push('esitle'); return { durum: 'pc' }; }, esitlemeDurumu: async () => { olay.push('durum'); return tamam; } };
    o._yereller = [];
    o.kayitAc = async () => {};
    SONRA.push(async () => {
      const eskiVue = globalThis.Vue;
      globalThis.Vue = { markRaw: (x) => x };
      try {
        await o.etkinlesti();
        await new Promise((r) => setImmediate(r));
      } finally { globalThis.Vue = eskiVue; }
      ok('[!] 4D: Kayitlar PC kipinde — kaynak once sorulur, kartin dizini (/kayit/liste) SORULMAZ, esitleme CAGRILMAZ, uyari kutusu bos (sebep "pc" kullaniciya hata degil), kopya satiri kart + akis yazar, durum satiri yuklenir',
         o.pc === true && !olay.includes('kartListesi') && !olay.includes('esitle') && olay.includes('durum') && o.nedenMetni === ''
         && o.satirlar.length === 2 && o.satirlar.every((s) => s.nerede === 'pc') && /0a1b2c3d4e5f6a7b[\s\S]*3995957410/.test(o.kopyalar[0].metin)
         && /Bu PC'deki arşiv \(köprü\): 1 akış · 2 oturum/.test(o.pcOzetMetin) && /Köprü eşitlemesi/.test(o.pcDurumMetni),
         `pc=${o.pc} olay=${olay} neden=${o.nedenMetni} ozet=${o.pcOzetMetin}`);
    });
  }

  /* ── (d) PC11: /pil vekilden, 502'de `p` ──────────────────────────── */
  {
    const u = ornek();
    u.bagli = true; u.tasiyiciAdi = 'akis'; u.bagliTasiyici = 'akis';
    u.kopruda = true; u.kopruVekil = true;
    const vekilli = u.pilKaynak;
    u.kopruVekil = false;
    const vekilsiz = u.pilKaynak;
    u.kopruda = false;
    const kart = u.pilKaynak;
    ok('[!] 4D (PC11): pil durum kaynagi — kopru /pil\'i vekil ediyorsa (/durum vekil) kopruda da "http" (egri noktalari gelir); vekil yoksa "satir" (PU13); kartin kendi WiFi\'sinde "http" aynen',
       vekilli === 'http' && vekilsiz === 'satir' && kart === 'http', `${vekilli} ${vekilsiz} ${kart}`);
    const w = ornek();
    const giden = [];
    w.gonder = async (k) => { giden.push(k); };
    w.bagli = true; w.tasiyiciAdi = 'akis'; w.bagliTasiyici = 'akis'; w.kopruda = true; w.kopruVekil = true; w.surucuyum = true;
    w.kartIstek = async () => yanit(502, '{"vekil":"erisim","mesaj":"x"}', { 'X-Kopru-Vekil': 'hata' });
    const y = ornek();
    y.bagli = true; y.tasiyiciAdi = 'akis'; y.bagliTasiyici = 'akis';
    SONRA.push(async () => {
      await w.pilYokla();
      const sonra = w.pilKaynak;
      const eskiF = sandbox.fetch;
      sandbox.fetch = async () => yanit(200, JSON.stringify({ kart: 'wifi:x', skop_arsiv: false, pc_arsiv: true, vekil: true }));
      try { await y.kopruYokla(); } finally { sandbox.fetch = eskiF; }
      const vk = y.kopruVekil;
      sandbox.fetch = async () => yanit(200, JSON.stringify({ kart: 'kayit:0', skop_arsiv: false, pc_arsiv: true, vekil: false }));
      try { await y.kopruYokla(); } finally { sandbox.fetch = eskiF; }
      ok('[!] 4D (PC11): vekil karta ulasamazsa (502 + X-Kopru-Vekil) pil bu baglantida `p` -> B satirina doner (surucuyse `p` gider, hata metni yok); kopruYokla /durum `vekil`ini okur',
         sonra === 'satir' && w.kopruVekil === false && giden.join() === 'p' && !w.pilHataMetni && vk === true && y.kopruVekil === false,
         `${sonra} ${giden} ${w.pilHataMetni} vk=${vk}/${y.kopruVekil}`);
    });
  }
  {
    const AE = AY.AyarlarEkrani;
    const yap = (yanitF, pc) => {
      const o = Object.assign({}, AE.data.call({}), AE.methods, { bolum: 'kal-gecmis', kartAdres: (y) => y, kartIstek: null, kartTaban: '',
        tasiyici: 'akis', bagli: true, afisSurum: '', dilSecim: 'tr', etkin: true, $nextTick: (f) => f && f() });
      for (const [ad, fn] of Object.entries(AE.computed)) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      const idb = [];
      o._esAl = async () => ({ esitlemeUygunlugu: ES.esitlemeUygunlugu, kalJsonCoz: ES.kalJsonCoz,
        EsitlemeDenetcisi: class { async kaynak() { return pc ? 'pc' : 'tarayici'; }
          async akislar() { return [{ kimlik: 3995957410, kart: '0a1b2c3d4e5f6a7b', olusma: 2, guncelleme: 1790000600000, kalVar: true }]; }
          async kalBaytlari() { return KAL; } } });
      o._idbAl = async () => { idb.push('idb'); return { vtAc: async () => ({}), idbDepo: () => ({ kalOku: async () => null }) }; };
      o._pcSozlukAl = async () => ({ SOZLUK_PC: SZP.SOZLUK_PC });
      o.__f = yanitF;
      o.__idb = idb;
      return o;
    };
    SONRA.push(async () => {
      const a = yap(async () => yanit(502, '{"vekil":"dogrulanamadi","mesaj":"kart WiFi\'den dogrulanamadi"}', { 'X-Kopru-Vekil': 'hata' }), true);
      await fetchIle(a.__f, () => a.kalYukle());
      const b = yap(async () => yanit(200, '{"adet":2,"etkin":2,"azami":40,"kayitlar":[{"no":1},{"no":2}]}'), true);
      await fetchIle(b.__f, () => b.kalYukle());
      ok('[!] 4D (PC11): Ayarlar kalibrasyon gecmisi kopruda VEKILDEN (kaynak "kart"); vekil karta ulasamazsa (502) sebep JSON\'dan ("köprü karta WiFi\'den ulaşamadı") ve PC arsivinin kopyasi (kaynak "pc", kart + akis yazilir) — IndexedDB acilmaz',
         b.kalKaynak === 'kart' && b.kalListe && b.kalListe.etkin === 2
         && a.kalKaynak === 'pc' && a.kalNeden === 'kopru' && a.kalListe && a.kalListe.etkin === 1 && a.__idb.length === 0
         && /köprü karta WiFi'den ulaşamadı \(kart WiFi'den dogrulanamadi\)/.test(a.kalKaynakYazi)
         && /bu PC'deki arşivin kopyası[\s\S]*0a1b2c3d4e5f6a7b[\s\S]*3995957410/.test(a.kalKaynakYazi),
         `${a.kalKaynak}/${a.kalNeden} ${a.kalKaynakYazi}`);
      const d = Object.assign(yap(null, true), {});
      await d._pcKur(new (await d._esAl()).EsitlemeDenetcisi());
      d.depoSatir = AY.depoSatirlari({ akislar: [{ kimlik: 3995957410, bayt: 10, pc: true, olusma: 1 }] });
      ok('4D: Ayarlar depolama PC kipinde satiri "pc" isaretler (silme yok — sablonda salt okuma), PC metni sozluk_pc\'den',
         d.pc === true && d.depoSatir[0].pc === true && d.t('pc.ay_depo_salt') === 'salt okuma'
         && /<span v-if="r\.pc" class="ay-aciklama" data-ay-salt>/.test(AE.template) && /<p v-if="pc" class="ipucu" data-ay-depo-pc>/.test(AE.template));
    });
  }

  /* ── (e) EU8' / EU9' ───────────────────────────────────────────────── */
  {
    const es = yorumsuz(kaynak('esitleme.js'));
    const kopruUc = [...es.matchAll(/_kopruGetir\('([^']+)'\)/g)].map((m) => m[1]).sort();
    ok("[!] 4D EU8': kopru uclari (/durum, /esitleme/durum) duz fetch(kartAdres) ile, imza katmanina (istek) GIRMEZ; /arsiv/* depo_pc.js'e verilen getir de ayni yol; depo_pc.js'te fetch YOK",
       kopruUc.join() === '/durum,/esitleme/durum'
       && /_kopruGetir\(yol\) \{\s*return fetch\(this\.kartAdres\(yol\), \{ cache: 'no-store', credentials: 'omit'/.test(es)
       && /pcAkislar\(\(y\) => this\._kopruGetir\(y\)\)/.test(es) && /pcDepo\(\(y\) => this\._kopruGetir\(y\), a\)/.test(es)
       && !/fetch\(/.test(yorumsuz(kaynak('depo_pc.js'))), kopruUc.join());
    const ayKod = yorumsuz(kaynak('ayarlar.js'));
    ok("[!] 4D EU9': kartin uclari (/kal/liste, /kunye.json, /pil) kartIstek / _istek'ten (kopruda kopru imzalar — panel imzalamaz, kopru /eslestir/*'i vekil ETMEZ: imzasiz yol); kopru vekil hatasi X-Kopru-Vekil ile ayirt edilir",
       [...ayKod.matchAll(/_istek\('([^']+)'/g)].map((m) => m[1]).sort().join() === '/kal/liste,/kunye.json'
       && /this\.kartIstek\('\/pil\?sira=' \+ this\.pilYerelSira/.test(appKaynak) && (ayKod.match(/X-Kopru-Vekil/g) || []).length === 2);
    const statik = iceAktarmaGrafigi().map((g) => g.goruntu);
    const esAgac = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'esitleme.js')).map((g) => g.goruntu);
    ok('[!] 4D: depo_pc.js YALNIZ dinamik (esitleme.js, kopru kokeninde) — acilista ve esitleme zincirinin statik agacinda YOK; sozluk_pc.js acilista YOK',
       !statik.includes('ekran/depo_pc.js') && !esAgac.includes('ekran/depo_pc.js') && !statik.includes('ortak/sozluk_pc.js')
       && /pcYukle = \(\) => import\('\.\/depo_pc\.js'\)/.test(yorumsuz(kaynak('esitleme.js'))), esAgac.join(' '));
  }

  /* ── (f) PC12: eski skop arsivi ────────────────────────────────────── */
  {
    const bolum = (html.match(/<section class="kart" v-if="skopArsivVar">([\s\S]*?)<\/section>/) || [])[1] || '';
    const tr = SZ.ceviri('os.eski_arsiv_ipucu', 'tr');
    ok('[!] 4D (PC12): skop arsivi kopruda "ESKI ARSIV" basligi altinda (sozlukten, TR + EN), salt okuma ve donusturulmez yazar, yeri bayat `kopru/arsiv` DEGIL (4C: olcum-karti/satir); kartin kendi skop gunlukleri Kayitlar\'da',
       /<h2 data-skop-eski-arsiv>\{\{ os\.eskiArsiv \}\}<\/h2>/.test(bolum) && /\{\{ os\.eskiArsivIpucu \}\}/.test(bolum)
       && !/kopru\/arsiv/.test(bolum) && /^Eski arşiv/.test(SZ.ceviri('os.eski_arsiv', 'tr')) && /^Legacy archive/.test(SZ.ceviri('os.eski_arsiv', 'en'))
       && /Salt okuma, dönüştürülmez/.test(tr) && /olcum-karti\/satir/.test(tr) && /Kayıtlar/.test(tr) && !/kopru\/arsiv/.test(tr),
       SZ.ceviri('os.eski_arsiv', 'tr'));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   34. 4H — PANEL PC KOPRUSUNDE: bildirim bolumu, yerel ag uyarisi, kabuk surumu
   Kararlar tasarim/2026-10-03-alt-proje-4-pc.md "4H uygulama kararlari".
   (a) Gelismis kopru bolumu YALNIZ kopruda: kart kokeninde HICBIR istek / indirme yok
       (AY2: Gelismis yalniz modul + metinleri, EU32); kopruda 4D'nin karari (/durum pc_arsiv) — yerel ag istemcisi YOK.
   (b) ekran/pc_kopru.js YALNIZ dinamik: acilista, ayarlar.js'in statik agacinda yok; app.js onu
       yalniz koprunun isaretli 403'unde ister.
   (c) bildirim bolumu: GET /bildirim/durum, POST /bildirim/ayar (X-Olcum, JSON, yalniz degisen alan),
       sonuc / hata canli bolgede; metinler sozluk_pc.js'te (TR + EN).
   (d) yerel ag istemcisi: 403 + X-Kopru-Ret: lan -> ham ret metni yerine cevrilmis "salt okuma" uyarisi.
   Gercek tarayici + gercek kopru: tarayici_pc_kayit.py (T4D, 4H bolumu).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 34. 4H: panel PC koprusunde (bildirim bolumu, yerel ag uyarisi, kabuk surumu) ---');
{
  const ek = (ad) => require(path.join(ARAYUZ, 'ekran', ad));
  const PK_YOL = path.join(ARAYUZ, 'ekran', 'pc_kopru.js');
  const PK = fs.existsSync(PK_YOL) ? ek('pc_kopru.js') : {};
  const AY = ek('ayarlar.js');
  const ES = ek('esitleme.js');
  const SZP = require(path.join(KOK, 'ortak', 'src', 'sozluk_pc.js'));
  const ayKod = yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'ayarlar.js'), 'utf8'));
  const pkKod = fs.existsSync(PK_YOL) ? yorumsuz(fs.readFileSync(PK_YOL, 'utf8')) : '';
  const appKod = yorumsuz(appKaynak);
  const yanit = (status, govde, basliklar = {}) => {
    const b = new TextEncoder().encode(typeof govde === 'string' ? govde : '');
    const h = new Map(Object.entries(basliklar).map(([a, v]) => [a.toLowerCase(), String(v)]));
    return { status, ok: status >= 200 && status < 300, headers: { get: (a) => (h.has(a.toLowerCase()) ? h.get(a.toLowerCase()) : null) },
      text: async () => new TextDecoder().decode(b), json: async () => JSON.parse(new TextDecoder().decode(b)) };
  };
  const fetchIle = async (f, islev) => {
    const eski = globalThis.fetch;
    globalThis.fetch = f;
    try { return await islev(); } finally { globalThis.fetch = eski; }
  };
  const KOPRU_KONUM = { protocol: 'http:', hostname: 'olcum.localhost', host: 'olcum.localhost:8770' };
  const KART_KONUM = { protocol: 'http:', hostname: 'olcum.local', host: 'olcum.local' };
  const LAN_RET = 'yerel agdan salt okuma: bu baglanti yalniz izleyebilir';
  const DURUM = { etkin: true, bilgi: 'onbellek', abone: true, kart_cevrimici: true, son_olay: 1790000000, son_olay_tur: 'kayit_bitti',
    ayar: { kopuk: true, bitti: true, dolu: true, esik: true, yeniden_basladi: true, kacirilan: true, deneme: true }, dil: 'tr', ayar_uyari: null, mesaj: '' };
  const yeni = (B, props = {}) => {
    const o = Object.assign({}, props);
    Object.assign(o, B && B.data ? B.data.call(o) : {});
    Object.assign(o, (B && B.methods) || {});
    o.$nextTick = (f) => { if (f) f(); return Promise.resolve(); };
    for (const [ad, fn] of Object.entries((B && B.computed) || {})) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
    return o;
  };

  /* ── (a) koken kurali: kokenSinama ile AYNI ─────────────────────────── */
  const KK = AY.kopruKokeni || (() => null);
  const vektor = [['http:', 'olcum.localhost'], ['http:', 'localhost'], ['https:', 'a.localhost'], ['http:', '127.0.0.1'], ['http:', '127.9.8.7'],
    ['http:', '[::1]'], ['http:', 'olcum.local'], ['http:', '192.168.1.50'], ['http:', 'olcum.localhost.example'], ['file:', 'localhost'],
    ['http:', 'LOCALHOST'], ['http:', '127.0.0.1.example'], ['http:', '']].map(([p, h]) => ({ protocol: p, hostname: h }));
  ok('[!] 4H (a): ayarlar.js kopruKokeni esitleme.js kokenSinama ile AYNI karari veriyor (Gelismis kartta esitleme.js\'i indirmeden karar verir)',
     typeof AY.kopruKokeni === 'function' && vektor.every((k) => KK(k) === ES.kokenSinama(k)) && KK(null) === false && KK(undefined) === false
     && KK(KOPRU_KONUM) === true && KK(KART_KONUM) === false,
     vektor.filter((k) => KK(k) !== ES.kokenSinama(k)).map((k) => k.protocol + k.hostname).join(' ') || 'ayni');

  const AE = AY.AyarlarEkrani;
  const ayarYap = ({ konum, kaynak = 'pc', durum = { kart: 'wifi:olcum.local', pc_arsiv: true, kabuk: '0123456789ab' } } = {}) => {
    const o = Object.assign({}, AE.data.call({}), AE.methods, { bolum: 'gelismis', kartAdres: (y) => y, kartIstek: null, kartTaban: '',
      tasiyici: 'akis', bagli: true, afisSurum: '', dilSecim: 'tr', etkin: true, $nextTick: (f) => f && f() });
    for (const [ad, fn] of Object.entries(AE.computed)) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
    const iz = { es: 0, pk: 0, fetch: [] };
    o._konum = () => konum;
    o._esAl = async () => { iz.es++; return { EsitlemeDenetcisi: class { async kaynak() { return kaynak; } } }; };
    o._pcSozlukAl = async () => ({ SOZLUK_PC: SZP.SOZLUK_PC });
    o._pcKopruAl = async () => { iz.pk++; return PK; };
    o._istek = async () => yanit(404, '');
    o.__f = async (url, sec) => { iz.fetch.push({ url: String(url), sec }); return String(url) === '/durum' ? yanit(200, JSON.stringify(durum)) : yanit(404, ''); };
    o.__iz = iz;
    return o;
  };
  SONRA.push(async () => {
    const kart = ayarYap({ konum: KART_KONUM });
    await fetchIle(kart.__f, async () => { kart.bolumAcildi(); await (kart.pcKopruKur ? kart.pcKopruKur() : null); });
    ok('[!] 4H (a): KART kokeninde Gelismis kopru bolumu icin HICBIR istek yok, esitleme.js ve pc_kopru.js INMEZ (AY2: yalniz modul + sozluk_ay.js); bolum ve kabuk satiri yok',
       typeof kart.pcKopruKur === 'function' && kart.__iz.es === 0 && kart.__iz.pk === 0 && kart.__iz.fetch.length === 0
       && !kart.pcBilesen && !kart.kabuk, JSON.stringify(kart.__iz));
    const kopru = ayarYap({ konum: KOPRU_KONUM });
    await fetchIle(kopru.__f, () => (kopru.pcKopruKur ? kopru.pcKopruKur() : null));
    const lan = ayarYap({ konum: KOPRU_KONUM, kaynak: 'tarayici' });
    await fetchIle(lan.__f, () => (lan.pcKopruKur ? lan.pcKopruKur() : null));
    ok('[!] 4H (a): KOPRUDE (4D karari: /durum pc_arsiv) bildirim bolumu kurulur ve kabuk surumu /durum `kabuk`tan; yerel ag istemcisi / gelistirme sunucusu (kaynak "tarayici") pc_kopru.js\'i INDIRMEZ',
       kopru.__iz.pk === 1 && kopru.pcBilesen === PK.PcBildirimBolumu && kopru.kabuk === '0123456789ab'
       && kopru.__iz.fetch.some((c) => c.url === '/durum' && c.sec && c.sec.credentials === 'omit')
       && lan.__iz.pk === 0 && !lan.pcBilesen && !lan.kabuk, `${kopru.__iz.pk} ${kopru.kabuk} lan=${lan.__iz.pk}`);
    ok('4H (a): kabuk satiri Gelismis\'te kartin arayuz surumunun HEMEN ardinda (v-if, sozluk_pc metni TR + EN); bildirim bolumu v-if ile (kartta hic kurulmaz)',
       /<dd data-ay-panel[^>]*>\{\{ panelYazi \}\}<\/dd>\s*<template v-if="kabuk"><dt>\{\{ pm\.kabuk \}\}<\/dt><dd data-ay-kabuk>\{\{ kabuk \}\}<\/dd><\/template>/.test(AE.template)
       && /<component v-if="pcBilesen" :is="pcBilesen"[^>]*v-show="bolum === 'gelismis'"[^>]*:kart-adres="kartAdres"[^>]*:dil-secim="dil"/.test(AE.template)
       && /Bu PC/.test(SZP.ceviriPc('pc.ay_kabuk', 'tr')) && /this PC/i.test(SZP.ceviriPc('pc.ay_kabuk', 'en')));
  });

  /* ── (b) tembel yukleme ve butce ────────────────────────────────────── */
  {
    const statik = iceAktarmaGrafigi().map((g) => g.goruntu);
    const ayAgac = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'ayarlar.js')).map((g) => g.goruntu);
    const pkAgac = fs.existsSync(PK_YOL) ? iceAktarmaGrafigi(PK_YOL).map((g) => g.goruntu) : ['yok'];
    const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
    const by = (fs.existsSync(kunyeYolu) ? JSON.parse(fs.readFileSync(kunyeYolu, 'utf8')) : {}).bayt || {};
    const pkBayt = by['ekran/pc_kopru.js'];
    ok('[!] 4H (b): ekran/pc_kopru.js YALNIZ dinamik — acilis kumesinde ve ayarlar.js\'in statik agacinda YOK; kendi statik agaci yalniz sozluk_pc.js + sozluk.js; <= 6 KB gzip',
       !statik.includes('ekran/pc_kopru.js') && !ayAgac.includes('ekran/pc_kopru.js') && !statik.includes('ortak/sozluk_pc.js')
       && pkAgac.length > 0 && pkAgac.every((x) => ['ortak/sozluk_pc.js', 'ortak/sozluk.js'].includes(x))
       && Number.isFinite(pkBayt) && pkBayt > 0 && pkBayt <= 6 * 1024, `${pkAgac.join(' ')} · ${pkBayt} B`);
    const appDin = [...appKod.matchAll(/import\('\.\/ekran\/pc_kopru\.js'\)/g)].length;
    const ayDin = [...ayKod.matchAll(/import\('\.\/pc_kopru\.js'\)/g)].length;
    ok('[!] 4H (b): app.js pc_kopru.js\'i TEK yerden (_pcKopruAl) ister ve onu yalniz lanUyarisi cagirir — o da yalniz 403 + X-Kopru-Ret: lan iken; ayarlar.js tek yerden (_pcKopruAl), yalniz kopru kokeninde ve kaynak "pc" iken',
       appDin === 1 && /_pcKopruAl\(\) \{ return import\('\.\/ekran\/pc_kopru\.js'\); \}/.test(appKod)
       && (appKod.match(/_pcKopruAl\(\)/g) || []).length === 2
       && /async lanUyarisi\(y\) \{\s*if \(!y \|\| y\.status !== 403 \|\| !y\.headers \|\| y\.headers\.get\('X-Kopru-Ret'\) !== 'lan'\) return '';/.test(appKod)
       && ayDin === 1 && /if \(!kopruKokeni\(this\._konum\(\)\)\) return;[\s\S]{0,200}await this\._pcKur\(den\);\s*if \(!this\.pc\) return;\s*const m = await this\._pcKopruAl\(\);/.test(ayKod),
       `app ${appDin} ayarlar ${ayDin}`);
  }

  /* ── (c) bildirim bolumu ────────────────────────────────────────────── */
  {
    const py = fs.readFileSync(path.join(KOK, 'kopru', 'pc_bildirim.py'), 'utf8');
    const pySinif = ((py.match(/^SINIFLAR = \(([^)]*)\)/m) || [])[1] || '').match(/"([a-z_]+)"/g) || [];
    const sinif = PK.BILDIRIM_SINIFLARI || [];
    const B = PK.PcBildirimBolumu || {};
    const ad = (d) => (yeni(B, { kartAdres: (y) => y, dilSecim: d }).siniflar || []).map((s) => s.ad);
    ok('[!] 4H (c): panelin bildirim siniflari koprununkiyle (kopru/pc_bildirim.py SINIFLAR) AYNI ve AYNI sirada; her birinin TR ve EN adi var, adlar ayri',
       sinif.join() === pySinif.map((x) => x.slice(1, -1)).join() && sinif.length === 7
       && ad('tr').length === 7 && new Set(ad('tr')).size === 7 && ad('en').length === 7 && new Set(ad('en')).size === 7
       && ad('tr').every((x, i) => x !== ad('en')[i] && !/^pc\./.test(x)), `${sinif.join()} / ${pySinif.join()}`);
    const T = B.template || '';
    ok('[!] 4H (c)/WIG: bolum sablonu — baslik, canli bolgede (aria-live) durum ve kaydetme sonucu, siniflar fieldset + legend icinde onay kutulari, dil secimi etiketli; yenile aria-busy; gomulu Turkce metin YOK',
       /<section class="kart" data-pc-bildirim>\s*<h2>\{\{ m\.baslik \}\}<\/h2>/.test(T)
       && /aria-live="polite"[^>]*data-pc-bl-durum/.test(T) && /<div class="ay-duyuru" aria-live="polite">[\s\S]*?data-pc-bl-sonuc/.test(T)
       && /<fieldset[^>]*data-pc-bl-siniflar>\s*<legend>/.test(T) && /<input type="checkbox"[^>]*:data-pc-bl-sinif="s\.id"/.test(T)
       && /<label class="skop-alan">\{\{ m\.dil \}\}\s*<select[^>]*data-pc-bl-dil/.test(T) && /:aria-busy="yukleniyor \? 'true' : 'false'"/.test(T)
       && !/[çğıöşüÇĞİÖŞÜ]/.test(T));
    SONRA.push(async () => {
      const c = yeni(B, { kartAdres: (y) => y, dilSecim: 'tr' });
      const istek = [];
      let cevap = (u, s) => (u === '/bildirim/durum' ? yanit(200, JSON.stringify(DURUM)) : yanit(200, JSON.stringify({ ayar: { ...DURUM.ayar, kopuk: false }, dil: 'tr', ayar_uyari: null })));
      const f = async (u, s = {}) => { istek.push({ u: String(u), s }); return cevap(String(u), s); };
      await fetchIle(f, async () => { if (c.yukle) await c.yukle(); });
      const ilk = istek[0] || { s: {} };
      const dYazi = c.durumYazi;
      await fetchIle(f, async () => { if (c.sinifDegistir) await c.sinifDegistir('kopuk', false); });
      const p = istek[1] || { s: { headers: {} } };
      ok('[!] 4H (c): bolum durumu GET /bildirim/durum (no-store, kimlik bilgisi tasimaz) ile okur; bir sinif degisince POST /bildirim/ayar YALNIZ o sinifi yollar ({"bildirim":{"kopuk":false}}, X-Olcum: 1, application/json); yanitin ayari gosterilir, sonuc "kaydedildi"',
         ilk.u === '/bildirim/durum' && ilk.s.cache === 'no-store' && ilk.s.credentials === 'omit' && /dinliyor/.test(dYazi || '')
         && p.u === '/bildirim/ayar' && p.s.method === 'POST' && p.s.body === '{"bildirim":{"kopuk":false}}'
         && p.s.headers && p.s.headers['X-Olcum'] === '1' && p.s.headers['Content-Type'] === 'application/json' && p.s.credentials === 'omit'
         && c.ayar && c.ayar.kopuk === false && c.ayar.bitti === true && c.sonuc === SZP.ceviriPc('pc.bl_kaydedildi', 'tr') && !c.sonucHata,
         `${ilk.u} ${p.u} ${p.s.body} ${c.sonuc}`);
      await fetchIle(f, async () => { if (c.dilDegistir) await c.dilDegistir('en'); });
      const pd = istek[2] || { s: {} };
      const once = istek.length;
      await fetchIle(f, async () => {
        if (c.sinifDegistir) { await c.sinifDegistir('parola', false); await c.sinifDegistir('kopuk', 'false'); }
        if (c.dilDegistir) await c.dilDegistir('de');
      });
      ok('[!] 4H (c): dil degisimi YALNIZ {"dil":"en"} yollar; bilinmeyen sinif, true/false olmayan deger, bilinmeyen dil kopruye HIC gitmez (istemci de dogrular)',
         pd.u === '/bildirim/ayar' && pd.s.body === '{"dil":"en"}' && istek.length === once
         && typeof PK.ayarGovdesi === 'function' && PK.ayarGovdesi({ bildirim: { kopuk: true } }) === '{"bildirim":{"kopuk":true}}'
         && PK.ayarGovdesi({ bildirim: { x: true } }) === null && PK.ayarGovdesi({ bildirim: { kopuk: 1 } }) === null
         && PK.ayarGovdesi({ dil: 'de' }) === null && PK.ayarGovdesi({}) === null && PK.ayarGovdesi({ parola: 'x', dil: 'en' }) === null,
         `${pd.s.body} ${istek.length - once}`);
      cevap = (u) => (u === '/bildirim/ayar' ? yanit(409, 'ayar.json okunamadi (JSONDecodeError) — uzerine YAZILMADI') : yanit(200, JSON.stringify(DURUM)));
      await fetchIle(f, async () => { if (c.sinifDegistir) await c.sinifDegistir('esik', false); });
      const hata409 = c.sonuc;
      const h409 = c.sonucHata;
      cevap = (u) => (u === '/bildirim/ayar' ? yanit(403, LAN_RET, { 'X-Kopru-Ret': 'lan' }) : yanit(200, JSON.stringify(DURUM)));
      await fetchIle(f, async () => { if (c.sinifDegistir) await c.sinifDegistir('esik', false); });
      ok('[!] 4H (c): kopru reddederse (409 bozuk ayar.json) sebep cevrilmis cerceveyle yazilir ve bolum durumu yeniden okunur; yerel ag reddi (403 lan) "salt okuma" uyarisi',
         h409 === true && hata409 === SZP.ceviriPc('pc.bl_kayit_hata', 'tr', { mesaj: 'ayar.json okunamadi (JSONDecodeError) — uzerine YAZILMADI' })
         && c.sonuc === (PK.lanMetni ? PK.lanMetni('tr') : 'x') && c.sonucHata === true && istek[istek.length - 1].u === '/bildirim/durum',
         `${hata409} | ${c.sonuc}`);
      const y = (d, dil) => (PK.bildirimDurumYazi ? PK.bildirimDurumYazi(d, dil) : '');
      ok('[!] 4H (c): durum metinleri (TR + EN) — kapali (sebep), aboneyken "dinliyor" + kart cevrimici, abone degilken koprunun mesaji, alinamadi; son olay zamani ve turu, yoksa "henuz yok"',
         /kapalı \(--bildirim-yok\)/.test(y({ etkin: false, neden: '--bildirim-yok' }, 'tr')) && /off \(--bildirim-yok\)/.test(y({ etkin: false, neden: '--bildirim-yok' }, 'en'))
         && /dinliyor[\s\S]*çevrimiçi/.test(y(DURUM, 'tr')) && /listening[\s\S]*online/.test(y(DURUM, 'en'))
         && /bağlı değil \(! bildirim: aracıya bağlanılamadı\)[\s\S]*bilinmiyor/.test(y({ etkin: true, abone: false, kart_cevrimici: null, mesaj: '! bildirim: aracıya bağlanılamadı' }, 'tr'))
         && /HTTP 403/.test(y({ hata: 'HTTP 403' }, 'tr')) && /HTTP 403/.test(y({ hata: 'HTTP 403' }, 'en'))
         && PK.sonOlayYazi && /kayit_bitti/.test(PK.sonOlayYazi(DURUM, 'tr')) && /\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(PK.sonOlayYazi(DURUM, 'tr'))
         && PK.sonOlayYazi({ etkin: true }, 'en') === SZP.ceviriPc('pc.bl_son_yok', 'en'),
         y(DURUM, 'tr'));
    });
  }

  /* ── (d) yerel ag istemcisi: cevrilmis salt okuma uyarisi ───────────── */
  SONRA.push(async () => {
    const u = ornek();
    u.bagli = true; u.tasiyiciAdi = 'akis'; u.bagliTasiyici = 'akis'; u.kopruda = true; u.surucuyum = false;
    let yuklenen = 0;
    u._pcKopruAl = async () => { yuklenen++; return PK; };
    u.kartIstek = async () => yanit(403, LAN_RET, { 'X-Kopru-Ret': 'lan' });
    await u.gonder('?');
    const tr = u.hata;
    u.dil = 'en';
    u.hata = '';
    await u.gonder('?');
    const en = u.hata;
    u.dil = 'tr';
    const eskiFetch = sandbox.fetch;
    sandbox.fetch = async () => yanit(403, LAN_RET, { 'X-Kopru-Ret': 'lan' });
    u.hata = '';
    try { await u.devral(); } catch (e) { /* asagida */ }
    const dv = u.hata;
    const n = yuklenen;
    u.kartIstek = async () => yanit(403, 'bu oturum SURUCU degil — komut reddedildi.');
    await u.gonder('?');
    const isaretsiz = u.hata;
    sandbox.fetch = eskiFetch;
    ok('[!] 4H (d): koprunun yerel ag reddi (403 + X-Kopru-Ret: lan) komutta ve devralmada HAM METIN yerine cevrilmis "salt okuma — bu PC ya da kart" uyarisi (TR + EN); baska 403 (isaretsiz) eskisi gibi sebebiyle, modul de INMEZ',
       !!PK.lanMetni && tr === PK.lanMetni('tr') && en === PK.lanMetni('en') && dv === PK.lanMetni('tr') && n === 3
       && /salt okuma/i.test(tr) && /bu bilgisayar/i.test(tr) && /olcum\.local/.test(tr) && /read-only/i.test(en) && /p0/.test(tr)
       && isaretsiz === 'Komut gönderilemedi (403): bu oturum SURUCU degil — komut reddedildi.' && yuklenen === 3,
       `${tr} | ${en} | ${dv} | ${isaretsiz}`);
  });
}

/* ═══════════════════════════════════════════════════════════════════════
   35. 5P — PANEL TELEFONDA (globalThis.__olcumOrtam; tasarim/2026-10-07-5p-panel-telefonda.md K5-K14)
   Android uygulamasi paneli gomer ve ONCE ortami kurar (sozlesme: tasarim/2026-10-07-plan-5p.md).
   (a) ortam YOKKEN panel bugunku yoldan: tasiyicilar seri/akis/demo, ayar bolumleri aynen, serit kurali aynen.
   (b) panelin kullandigi ortam adlari sozlesmenin ALT KUMESI; kanca yalniz okunur.
   (c) kullaniciya dosya TEK yoldan (dosyaVer): a.download / createObjectURL yalniz onun govdesinde; app.js ile
       ekran/kayit_gorunum.js'teki ikiz govde bayt bayt ayni; tarayici yolu ad / bayt / MIME'yi AYNEN verir.
   (d) TELEFON KIPI (app.js ayri bir vm baglaminda, sahte ortamla): tasiyici `telefon` (saklanmaz), kopru /
       servis iscisi / tarayici eslestirmesi YOK, kart istekleri ortam.istek'ten, p0 ortam.p0'dan (onaysiz, tek
       cagri), Gb -> komutGitti (atsa da panel etkilenmez), serit ortam.serit(true|false|null), dosya
       ortam.dosyaVer'den, Ayarlar ilk bolum "Bu telefon" (Baglanti / Eslestirme / Depolama yok) —
       ve BUTUN bunlar boyunca fetch SAYISI 0.
   (e) esitleme.js kaynak 'telefon': akislar / depo / esitle ortamdan, onay panelden GITMEZ, kopya silme ret,
       kopru sorusu yok (kokenSinama false), fetch 0.
   (f) ayarlar.js: kopruKokeni ortamda false; "Bu telefon" bileseni ortam.ayarBolumu'ndan (hata metniyle);
       Kayitlar: telefon kopyasi (nerede 'telefon'), arsiv onayi ve kopya silme telefonda YOK.
   Gercek WebView acilisi mobil/ tarafinda (P1 basliksiz tarayici testi + cihaz kabulu).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 35. 5P: panel telefonda (globalThis.__olcumOrtam) ---');
{
  const SOZLESME = ['ad', 'surum', 'tasiyici', 'istek', 'p0', 'serit', 'akislar', 'depo', 'esitle', 'dosyaVer', 'yazdir',
    'ayarBolumu', 'komutGitti'];
  const SZa = require(path.join(KOK, 'ortak', 'src', 'sozluk.js'));
  const tumKod = kodKaynaklari.map((k) => ({ ad: k.ad, kod: yorumsuz(k.kaynak) }));
  const html5 = yorumsuz(htmlKaynak);

  /* ── (a) ortam YOKKEN ─────────────────────────────────────────────── */
  {
    const u0 = ornek();
    ok('[!] 5P (a): ortam YOKKEN TASIYICILAR tam olarak seri/akis/demo, varsayilan seri, ayar bolumleri AYNEN (varsayilan Baglanti), telefon seridi kapali',
       vm.runInContext('Object.keys(TASIYICILAR).join()', sandbox) === 'seri,akis,demo'
       && vm.runInContext('ORTAM', sandbox) === null && u0.tasiyiciAdi === 'seri'
       && vm.runInContext('AYAR_ETKIN === AYAR_BOLUMLERI && AYAR_VARSAYILAN', sandbox) === 'baglanti'
       && u0.ayarBolumListesi.map((b) => b.id).join() === 'baglanti,ag,eslestirme,kalibrasyon,kal-gecmis,depolama,dil-gorunum,gelismis'
       && u0.acilTelefon === false,
       vm.runInContext('Object.keys(TASIYICILAR).join()', sandbox));
  }

  /* ── (b) sozlesme ─────────────────────────────────────────────────── */
  {
    const kullanilan = new Map();
    for (const k of tumKod) {
      for (const m of k.kod.matchAll(/\b(?:ORTAM|ortam|_ortam)\??\.([A-Za-z_$][\w$]*)/g)) {
        if (!kullanilan.has(m[1])) kullanilan.set(m[1], new Set());
        kullanilan.get(m[1]).add(k.ad);
      }
    }
    const disari = [...kullanilan.keys()].filter((a) => !SOZLESME.includes(a));
    const gerekli = ['tasiyici', 'istek', 'p0', 'serit', 'komutGitti', 'dosyaVer', 'yazdir', 'ayarBolumu', 'akislar', 'depo', 'esitle'];
    const yazma = tumKod.filter((k) => /__olcumOrtam\s*=(?!=)/.test(k.kod)).map((k) => k.ad);
    const okuma = tumKod.filter((k) => /globalThis\.__olcumOrtam\b/.test(k.kod)).map((k) => k.ad);
    ok('[!] 5P (b): panelin kullandigi ortam adlari sozlesmenin ALT KUMESI (ve gerekli her ad gercekten kullaniliyor); kanca yalniz OKUNUR (globalThis.__olcumOrtam), panel onu yazmaz',
       disari.length === 0 && gerekli.every((a) => kullanilan.has(a)) && yazma.length === 0
       && ['app.js', 'ekran/esitleme.js', 'ekran/ayarlar.js', 'ekran/kayit_gorunum.js'].every((a) => okuma.includes(a))
       && !/__olcumOrtam/.test(html5),
       disari.length ? 'sozlesme disi: ' + disari.join(' ') : [...kullanilan.entries()].map(([a, f]) => a + '@' + [...f].join('+')).join(' '));
  }

  /* ── (c) dosyaVer ─────────────────────────────────────────────────── */
  const govdeAraligi = (kod, imza) => {
    const i = kod.indexOf(imza);
    if (i < 0) return null;
    const j = kod.indexOf('{', kod.indexOf(')', i));
    let d = 0;
    for (let k = j; k < kod.length; k++) {
      if (kod[k] === '{') d++;
      else if (kod[k] === '}') { d--; if (d === 0) return [j, k + 1]; }
    }
    return null;
  };
  {
    const tanimlar = tumKod.filter((k) => /\bfunction dosyaVer\(/.test(k.kod));
    const govdeler = tanimlar.map((k) => { const r = govdeAraligi(k.kod, 'function dosyaVer('); return r ? k.kod.slice(r[0], r[1]) : ''; });
    const kacak = [];
    for (const k of tumKod) {
      const r = govdeAraligi(k.kod, 'function dosyaVer(');
      for (const m of k.kod.matchAll(/\.download\b|createObjectURL\(/g)) {
        if (!r || m.index < r[0] || m.index > r[1]) kacak.push(k.ad + ':' + m[0]);
      }
    }
    const ekranKod = (ad) => (tumKod.find((k) => k.ad === ad) || { kod: '' }).kod;
    const ekranGovde = (ad, yontem) => { const kod = ekranKod(ad); const r = govdeAraligi(kod, '\n    ' + yontem + '('); return r ? kod.slice(r[0], r[1]) : ''; };
    ok('[!] 5P (c) K11: dosya TEK yoldan — a.download / createObjectURL YALNIZ dosyaVer govdesinde; iki tanim (app.js acilista, ekran/kayit_gorunum.js tembel) govdesi BAYT BAYT ayni; bes uretici onu cagiriyor',
       kacak.length === 0 && tanimlar.map((k) => k.ad).join() === 'app.js,ekran/kayit_gorunum.js'
       && govdeler.length === 2 && govdeler[0] === govdeler[1] && /ORTAM\.dosyaVer\(/.test(govdeler[0]) && /a\.download = ad/.test(govdeler[0])
       && ['pilCsvIndir', 'pilKayitCsv', 'csvIndir'].every((y) => govdeIcinde(appKaynak, y, 'dosyaVer('))
       && /dosyaVer\(d\.ad, d\.mime, d\.bayt\)/.test(ekranGovde('ekran/kayit_gorunum.js', 'indir'))
       && /dosyaVer\(karsilastirDosyaAdi\(kip, kanal, dil\)/.test(ekranGovde('ekran/karsilastir.js', 'indir')),
       kacak.join(' ') || tanimlar.map((k) => k.ad).join(' '));
    /* tarayici yolu (ortamsiz): ad, MIME ve bayt (BOM dahil) bugunkuyle ayni */
    const eski = { URL: sandbox.URL, Blob: sandbox.Blob, document: sandbox.document };
    const bloblar = [];
    const ogeler = [];
    sandbox.URL = { createObjectURL: (b) => { bloblar.push(b); return 'blob:' + bloblar.length; }, revokeObjectURL() {} };
    sandbox.Blob = class { constructor(p, o) { this.parcalar = p; this.type = o && o.type; } };
    sandbox.document = { ...eski.document, body: { appendChild() {} },
      createElement: () => { const a = { click() { a.tik = (a.tik || 0) + 1; }, remove() {} }; ogeler.push(a); return a; } };
    const u = ornek();
    u.gecmis = [{ t: 1.5, v: 2, i: NaN, w: 3 }];
    u.pilNokta = [{ sira: 1, ms: 10, v: 3.7, i: 0.5 }, { sira: 2, bosluk: true }];
    u.csvIndir();
    u.pilCsvIndir();
    Object.assign(sandbox, eski);
    const b0 = bloblar[0] || { parcalar: [''] };
    const b1 = bloblar[1] || { parcalar: [''] };
    ok('[!] 5P (c): ortamsiz dosyaVer tarayici yolu — Canli CSV olcum-<tarih>.csv, text/csv;charset=utf-8, BOM + ";" + ondalik virgul, NaN bos; pil CSV pil-testi.csv text/csv; tiklanan baglanti',
       ogeler.length === 2 && /^olcum-\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d\.csv$/.test(ogeler[0].download) && ogeler[0].tik === 1
       && b0.type === 'text/csv;charset=utf-8' && b0.parcalar[0] === '﻿saniye;volt;amper;watt\r\n1,500;2;;3'
       && ogeler[1].download === 'pil-testi.csv' && b1.type === 'text/csv'
       && b1.parcalar[0] === 'sira,ms,volt,amper,bosluk\n1,10,3.7,0.5,0\n2,,,,1',
       JSON.stringify({ ad: ogeler.map((a) => a.download), tur: bloblar.map((b) => b.type) }));
  }

  /* ── (d) TELEFON KIPI: app.js ayri baglamda, sahte ortamla ───────────── */
  {
    const iz = { istek: [], p0: 0, serit: [], komut: [], dosya: [], ayar: 0, yazdir: 0, giden: [], ac: 0, kapat: 0 };
    const ORT = {
      ad: 'telefon', surum: 1,
      tasiyici: { ad: 'telefon', yetenek: { ad: 'telefon', komut: 'hepsi', skop: 'ikili', skop_azami: 4000, gecmis_s: 86400,
        cok_istemci: false, surucu: false },
      destekli() { return true; }, async ac() { iz.ac++; }, async kapat() { iz.kapat++; }, async gonder(u, m) { iz.giden.push(m); } },
      async istek(yol, sec) { iz.istek.push([yol, sec]); return { ok: true, status: 200, text: async () => '' }; },
      async p0() { iz.p0++; if (ORT.p0Atar) throw new Error('kanal'); return ORT.p0Sonuc; },
      serit(p) { iz.serit.push(p); return p !== false; },
      async akislar() { return []; }, async depo() { return {}; }, async esitle() { return { durum: 'tamam' }; },
      async dosyaVer(d) { iz.dosya.push(d); return true; }, async yazdir() { iz.yazdir++; },
      async ayarBolumu() { iz.ayar++; return { name: 'BuTelefon' }; },
      komutGitti(m) { iz.komut.push(m); throw new Error('izleme sorusu patladi'); },
      p0Sonuc: true, p0Atar: false,
    };
    let secT = null;
    let fetchSayisi = 0;
    let idbSayisi = 0;
    const sw = { kayit: 0, sil: 0 };
    const yazilan = [];
    let kayitliTasiyici = true;                       // tercihte 'akis' (eski secim) — telefonu EZMEMELI
    const sandboxT = {
      Vue: { createApp(o) { secT = o; return { mount() { return {}; } }; },
             defineAsyncComponent(y) { return { __asenkron: true, yukleyici: y }; } },
      navigator: { serial: {}, serviceWorker: { register() { sw.kayit++; return Promise.resolve(); },
        getRegistrations() { sw.sil++; return Promise.resolve([]); } } },
      window: { addEventListener() {}, devicePixelRatio: 1, isSecureContext: true },
      document: { documentElement: {}, readyState: 'complete',
        createElement: () => { throw new Error('telefonda DOM indirmesi YOK'); } },
      getComputedStyle: () => ({ getPropertyValue: () => '#000' }),
      setTimeout: () => 0, console, TextEncoder,
      fetch: () => { fetchSayisi++; return Promise.reject(new Error('telefonda fetch YOK')); },
      location: { protocol: 'https:', hostname: 'localhost', host: 'localhost', search: '', hash: '' },
      localStorage: { getItem: (a) => (a === 'olcum.tasiyici' && kayitliTasiyici ? '"akis"' : null), setItem: (a) => { yazilan.push(a); }, removeItem() {} },
      get indexedDB() { idbSayisi++; return undefined; },
      __olcumOrtam: ORT,
    };
    vm.createContext(sandboxT);
    for (const g of ICE_AKTARILAN) for (const ad of g.adlar) sandboxT[ad] = sandbox[ad];
    let kurulum = '';
    try { vm.runInContext('"use strict"; ' + appBetik, sandboxT, { filename: 'app.js (telefon)' }); } catch (h) { kurulum = h.message; }
    const T = (ifade) => { try { return vm.runInContext(ifade, sandboxT); } catch (h) { return undefined; } };
    const ornekT = () => {
      const o = Object.assign({}, secT.data());
      Object.assign(o, secT.methods);
      o.$nextTick = () => {};
      o.$refs = {};
      o.grafikCiz = () => {};
      o.osiloCiz = () => {};
      for (const [ad, fn] of Object.entries(secT.computed || {})) Object.defineProperty(o, ad, { get: fn.bind(o) });
      return o;
    };
    ok('[!] 5P (d) K6: telefon kipinde TASIYICILAR + telefon (ortamin tasiyicisi AYNEN), acilis tasiyicisi telefon; ayar bolumleri: Bu telefon ILK, Baglanti / Eslestirme / Depolama YOK (K14); #/ayar ve gizli bolumun adresi -> Bu telefon',
       !kurulum && !!secT && T('Object.keys(TASIYICILAR).join()') === 'seri,akis,demo,telefon' && T('TASIYICILAR.telefon') === ORT.tasiyici
       && secT.data().tasiyiciAdi === 'telefon'
       && T('AYAR_ETKIN.map((b) => b.id).join()') === 'telefon,ag,kalibrasyon,kal-gecmis,dil-gorunum,gelismis'
       && T('ayarBolumCoz("#/ayar")') === 'telefon' && T('ayarBolumCoz("#/ayar/baglanti")') === 'telefon'
       && T('ayarBolumCoz("#/ayar/eslestirme")') === 'telefon' && T('ayarBolumCoz("#/ayar/depolama")') === 'telefon'
       && T('ayarBolumCoz("#/ayar/ag")') === 'ag' && T('ayarBolumModul("telefon")') === true,
       kurulum || String(T('Object.keys(TASIYICILAR).join()')));
    if (secT) {
      SONRA.push(async () => {
        const u = ornekT();
        u.tercihleriYukle();                          // localStorage 'akis' diyor — telefon EZILMEZ
        await secT.watch.tasiyiciAdi.call(u, 'telefon', 'seri');
        const listeAd = u.ayarBolumListesi[0];
        kayitliTasiyici = false;                      // tercih yokken kopruyuAlgila /durum'u sorardi
        await u.kopruyuAlgila();
        const otoBagliDegil = u.otomatikBaglanmali();
        u.swKur(sandboxT.window, sandboxT.navigator, sandboxT.location, sandboxT.document);
        u._kopruBilindi = false;
        await u.kopruYokla();
        await u.kartIstek('/pil?sira=3', { cache: 'no-store' });
        await u.kartIstek('/kunye.json');
        const ist = await u.eslesmeHazirla();
        ok('[!] 5P (d) K5/K7: telefonda tasiyici saklanmaz ve tercih onu ezmez; kopru algilama / /durum / servis iscisi (kayit da eski kaydi silme de) / tarayici eslestirmesi YOK; kendiliginden baglanir; kart istekleri ortam.istek (yol + sorgu, secenekler aynen)',
           u.tasiyiciAdi === 'telefon' && u.tasiyici === ORT.tasiyici && !yazilan.includes('olcum.tasiyici')
           && listeAd.id === 'telefon' && listeAd.ad === SZa.ceviri('ay.b_telefon', 'tr') && SZa.ceviri('ay.b_telefon', 'en') === 'This phone'
           && otoBagliDegil === true && sw.kayit === 0 && sw.sil === 0 && u._sw.durum === 'atlandi'
           && u._kopruBilindi === true && u.kopruda === false && ist === null && idbSayisi === 0
           && iz.istek.length === 2 && iz.istek[0][0] === '/pil?sira=3' && iz.istek[0][1].cache === 'no-store'
           && iz.istek[1][0] === '/kunye.json' && typeof iz.istek[1][1] === 'object' && fetchSayisi === 0,
           JSON.stringify({ t: u.tasiyiciAdi, yazilan, sw, kb: u._kopruBilindi, istek: iz.istek.map((x) => x[0]), fetchSayisi, idbSayisi }));
        u.bagli = true;
        const otoBagli = u.otomatikBaglanmali();
        u.hata = '';
        await u.gonder('p0');
        const p0Tek = iz.p0 === 1 && iz.giden.length === 0 && u.hata === '';
        ORT.p0Sonuc = false;
        await u.gonder('p0');
        const p0Yok = u.hata === SZa.ceviri('kb.komut_kart_yok', 'tr');
        ORT.p0Atar = true;
        u.hata = '';
        let atti = null;
        try { await u.gonder('p0'); } catch (h) { atti = h; }
        const p0Atti = atti === null && u.hata === SZa.ceviri('kb.komut_kart_yok', 'tr') && iz.p0 === 3;
        ORT.p0Atar = false; ORT.p0Sonuc = true;
        u.pilDurdurKomut();                            // acil serit / Pil sekmesi: tek tik, beklemeden p0
        const p0Serit = iz.p0 === 4;
        await u.gonder('Gb200');
        await u.gonder('?');
        await u.gonder('Gd');
        ok('[!] 5P (d) K8: telefonda p0 ortam.p0`dan — TEK cagri, tasiyiciya / fetch`e GITMEZ, onaysiz (pilDurdurKomut tek tik); kart 204 demezse ya da kanal atarsa panel ATMAZ ve "komut gitmedi" der; Gb -> tasiyici + komutGitti (atsa da panel etkilenmez), baska komut komutGitti DEGIL; baglaninca kendiliginden baglanmaz',
           p0Tek && p0Yok && p0Atti && p0Serit && otoBagli === false && iz.giden.join() === 'Gb200,?,Gd' && iz.komut.join() === 'Gb200'
           && fetchSayisi === 0,
           JSON.stringify({ p0: iz.p0, giden: iz.giden, komut: iz.komut, hata: u.hata }));
        /* K9 serit: true | false | null */
        const s = [];
        u.bagli = false; u.pilDurum = 'BEKLEMEDE'; u.pilDurumBilinen = false;
        s.push([u.pilSuruyorBilgi, u.acilTelefon]);
        u.bagli = true;
        s.push([u.pilSuruyorBilgi, u.acilTelefon]);
        u.pilDurumAyarla('BEKLEMEDE');
        s.push([u.pilSuruyorBilgi, u.acilTelefon]);
        u.pilDurumAyarla('CALISIYOR');
        s.push([u.pilSuruyorBilgi, u.acilTelefon]);
        await u.kes();
        u.pilDurum = 'BEKLEMEDE';
        s.push([u.pilSuruyorBilgi, u.acilTelefon]);
        const eskiSerit = ORT.serit;
        ORT.serit = () => { throw new Error('x'); };
        const atarsa = u.acilTelefon;
        ORT.serit = eskiSerit;
        /* Telefonda bulundu (2026-10-07, Xiaomi): ortamin karari (Android'in /pil + akis tazeligi) Vue'nun
           GORMEDIGI durumdan geliyor; computed ilk "gorunur"u onbellekleyip kart BEKLEMEDE dedikten sonra da
           seridi gosteriyordu. Bu adimin Vue taklidi computed'i onbelleklemez — kural metinden olculur:
           acilTelefon saniyelik saati (saatTik) OKUMALI ki her saniye yeniden sorulsun. */
        const acilGovde = (appKaynak.match(/\n    acilTelefon\(\) \{([\s\S]*?)\n    \},/) || [])[1] || '';
        ok('[!] 5P (d) K9: acilTelefon her saniye yeniden hesaplanir (saatTik okunur) — ortamin karari reaktif degil',
           /this\.saatTik/.test(acilGovde), acilGovde.trim().slice(0, 200));
        /* Telefonda bulundu (2026-10-07): pil egrisi "bu baglantida egri yok" diyordu — telefon /pil'i
           imzali istekle (ORTAM.istek) okuyabilir; kaynak 'http' olmali (kartin kendi WiFi'si gibi). */
        ok('[!] 5P (d) K7: telefonda pil durumu/egrisi /pil`den (pilKaynak http)', u.pilKaynak === 'http', String(u.pilKaynak));
        /* Honor'da goruldu (2026-10-07): kart-yok uyarisi telefonda "USB kablosu COM soketinde mi?" diyordu —
           telefona USB ile kart baglanmaz (K1 kapsam disi). Acilis sozlugu dolu (19 500 B): yeni anahtar yerine
           ayni metnin ilk iki parcasi; sozlukte TR ve EN UC parca (" · ") olmali, sonuncusu USB. */
        const ipT = String(u.kartYokIpucuMetni || '');
        const parca = (d) => String((sozlukTum().SOZLUK['kb.kart_yok_ipucu'] || {})[d] || '').split(' · ');
        ok('[!] 5P (d): telefonda kart-yok ipucu USB / COM DEMEZ; sozlukte TR/EN uc parca, sonuncusu USB',
           ipT.length > 0 && !/USB|COM/.test(ipT) && ['tr', 'en'].every((d) => parca(d).length === 3 && /USB/.test(parca(d)[2])),
           ipT);
        ok('[!] 5P (d) K9: acil serit karari ortam.serit(pilSuruyor) — baglanti yok / kart soylemedi: null (gorunur), kart BEKLEMEDE dedi: false (gizli), CALISIYOR: true; kesilince yeniden bilinmiyor; serit atarsa GORUNUR',
           JSON.stringify(s) === JSON.stringify([[null, true], [null, true], [false, false], [true, true], [null, true]])
           && atarsa === true && iz.kapat === 1,
           JSON.stringify(s));
        /* K11: dosya ortamdan (Paylas) — bayt Uint8Array, DOM indirmesi yok */
        u.gecmis = [{ t: 1.5, v: 2, i: NaN, w: 3 }];
        u.csvIndir();
        await T('dosyaVer')('a.csv', 'text/csv', 'x;ç');
        const d0 = iz.dosya[0] || {};
        const d1 = iz.dosya[1] || {};
        const bayt = (x) => (x && typeof x.length === 'number' ? Buffer.from(x).toString('hex') : 'yok');
        ok('[!] 5P (d) K11: telefonda dosya ortam.dosyaVer`den ({ad, mime, bayt: Uint8Array}); Canli CSV ayni ad / MIME / bayt (BOM EF BB BF dahil); DOM indirmesi YOK; fetch 0',
           iz.dosya.length === 2 && /^olcum-\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d\.csv$/.test(d0.ad) && d0.mime === 'text/csv;charset=utf-8'
           && bayt(d0.bayt) === Buffer.from('﻿saniye;volt;amper;watt\r\n1,500;2;;3', 'utf8').toString('hex')
           && d1.ad === 'a.csv' && d1.mime === 'text/csv' && bayt(d1.bayt) === Buffer.from('x;ç', 'utf8').toString('hex')
           && fetchSayisi === 0,
           JSON.stringify({ ad: iz.dosya.map((d) => d.ad), hata: u.hata }));
        /* ilk acilis: #/ayar -> Bu telefon bolumu ve modulu */
        sandboxT.location.hash = '#/ayar';
        const d = secT.data();
        sandboxT.location.hash = '';
        ok('[!] 5P (d) K13: telefonda #/ayar ilk acilista Bu telefon bolumunu ve Ayarlar modulunu acar; index.html`de telefon seridi acil seridin v-else-if`i (onaysiz DURDUR, sozluk metni)',
           d.ayarBolum === 'telefon' && d.ayarModAcik === true
           && /<div v-if="pilDurum === 'CALISIYOR'" class="acil">[\s\S]*?<\/button>\s*<\/div>\s*<div v-else-if="acilTelefon" class="acil" data-acil-telefon>[\s\S]*?@click="pilDurdurKomut"[\s\S]*?\{\{ metin\('pl\.durdur'\) \}\}<\/button>/.test(html5),
           `${d.ayarBolum}/${d.ayarModAcik}`);
      });
    }
  }

  /* ── (e) esitleme.js kaynak 'telefon' ─────────────────────────────── */
  SONRA.push(async () => {
    const ES = require(path.join(ARAYUZ, 'ekran', 'esitleme.js'));
    const IM = require(path.join(KOK, 'ortak', 'src', 'imza.js'));
    const izE = { istek: [], esitle: [], depo: [], akislar: 0 };
    const depoT = { kart: 'k1', async veriBoyu() { return 0; }, async veriOku() { return new Uint8Array(0); },
      async kalOku() { return null; }, async durumOku() { return { son_sira: 0 }; } };
    const ortE = {
      async istek(y) { izE.istek.push(y); return { status: 200, text: async () => JSON.stringify({ kimlik: 7, oturumlar: [] }) }; },
      async akislar() { izE.akislar++; return [{ kimlik: 7, kart: 'k1', bayt: 0, durum: null, olusma: 1, guncelleme: 1, kalVar: false, telefon: true }]; },
      async depo(k) { izE.depo.push(k); return depoT; },
      async esitle(a) { izE.esitle.push(a); return { durum: 'tamam', sonuc: { yeni_kayit: 2, son_sira: 9 }, bayt: 10 }; },
    };
    const eskiF = globalThis.fetch;
    let fetchE = 0;
    globalThis.fetch = () => { fetchE++; return Promise.reject(new Error('fetch YOK')); };
    let r = {};
    try {
      const konum = { protocol: 'https:', hostname: 'localhost' };
      const den = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y, ortam: ortE, konum });
      const ilerleme = () => {};
      r.kaynak = await den.kaynak();
      r.akislar = (await den.akislar()).map((a) => a.kimlik).join();
      r.veri = (await den.akisVerisi(7)).kart;
      r.kal = await den.kalBaytlari(7);
      r.liste = (await den.kartListesi()).durum;
      r.es = await den.esitle({ kimlik: 7, onay: async () => {}, ilerleme });
      r.esArg = izE.esitle[0] ? Object.keys(izE.esitle[0]).sort().join() : '';
      r.ilerlemeAyni = !!izE.esitle[0] && izE.esitle[0].ilerleme === ilerleme;
      r.durum = await den.esitlemeDurumu();
      try { await den.akisSil(7); r.sil = 'silindi'; } catch (h) { r.sil = h instanceof IM.CalismaHatasi ? 'calisma' : String(h); }
      const katmanli = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y, ortam: ortE, istek: async (y) => { r.katman = y; return { status: 200, text: async () => '{}' }; } });
      await katmanli.kartListesi();
      r.koken = [ES.kokenSinama(konum, ortE), ES.kokenSinama(konum)];
      const ortamsiz = new ES.EsitlemeDenetcisi({ kartAdres: (y) => y, konum: { protocol: 'http:', hostname: 'olcum.local' } });
      r.ortamsiz = await ortamsiz.kaynak();
    } catch (h) { r.hata = String(h && h.stack || h); }
    globalThis.fetch = eskiF;
    ok('[!] 5P (e) K10: esitleme.js telefon kaynagi — akislar / depo / esitle ortamdan (onay panelden GITMEZ, ilerleme aynen), kartin dizini ortam.istek (katman verilirse katman), esitlemeDurumu null, kopya silme CalismaHatasi, kokenSinama ortamda false; ortamsiz kaynak AYNEN tarayici; fetch 0',
       r.kaynak === 'telefon' && r.akislar === '7' && r.veri === 'k1' && r.kal === null && r.liste === 'tamam'
       && r.es && r.es.durum === 'tamam' && r.es.sonuc.yeni_kayit === 2 && r.esArg === 'ilerleme,kimlik' && r.ilerlemeAyni
       && r.durum === null && r.sil === 'calisma' && r.katman === '/kayit/liste' && izE.istek.join() === '/kayit/liste'
       && izE.depo.length >= 2 && izE.depo.every((k) => k === 7)
       && JSON.stringify(r.koken) === '[false,true]' && r.ortamsiz === 'tarayici' && fetchE === 0 && !r.hata,
       r.hata || JSON.stringify({ ...r, es: r.es && r.es.durum, fetchE }));
  });

  /* ── (f) Ayarlar + Kayitlar ───────────────────────────────────────── */
  SONRA.push(async () => {
    const AY = require(path.join(ARAYUZ, 'ekran', 'ayarlar.js'));
    const KLx = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
    const KGx = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
    const KYs = require(path.join(KOK, 'ortak', 'src', 'sozluk_kayit.js'));
    const yap = (ek) => {
      const o = Object.assign({}, AY.AyarlarEkrani.data.call({}), AY.AyarlarEkrani.methods,
        { bolum: 'telefon', etkin: true, dilSecim: 'tr', tasiyici: 'telefon', kartAdres: (y) => y, $nextTick: (f) => f && f() }, ek);
      for (const [ad, fn] of Object.entries(AY.AyarlarEkrani.computed)) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      return o;
    };
    const BIL = { name: 'BuTelefon' };
    const o1 = yap({ _ortam: () => ({ ayarBolumu: async () => BIL }) });
    o1.bolumAcildi();
    await new Promise((c) => setImmediate(c));
    const o2 = yap({ _ortam: () => ({ ayarBolumu: async () => { throw new Error('modul yok'); } }) });
    await o2.telefonKur();
    const o3 = yap({});
    await o3.telefonKur();
    const o4 = yap({});
    await o4._pcKur({ kaynak: async () => 'telefon' });
    const T = AY.AyarlarEkrani.template;
    const loc = { protocol: 'http:', hostname: 'olcum.localhost' };
    ok('[!] 5P (f) K13: Ayarlar "Bu telefon" — bolum acilinca bilesen ortam.ayarBolumu`ndan (sablonda dil-secim ile), hata metniyle (TR + EN), ortamsiz hicbir sey; tasiyici yazisi "Telefon"; denetci kaynagi telefon -> telefon kopyasi (pc degil); kopruKokeni ortamda false',
       !!o1.telBilesen && o1.telBilesen.name === 'BuTelefon' && o1.telHata === '' && o2.telBilesen === null && /modul yok/.test(o2.telHataMetni)
       && /Bu telefon/.test(o2.telHataMetni) && o3.telBilesen === null && o3.telHata === ''
       && /<component v-if="telBilesen" :is="telBilesen" v-show="bolum === 'telefon'" :dil-secim="dil"><\/component>/.test(T)
       && o1.tasiyiciYazi === 'Telefon (imzalı Wi-Fi)' && o4.telefon === true && o4.pc === false
       && AY.kopruKokeni(loc, {}) === false && AY.kopruKokeni(loc) === true,
       JSON.stringify({ b: o1.telBilesen, h: o2.telHataMetni, t: o1.tasiyiciYazi }));
    const KT = KLx.KayitlarEkrani.template;
    const Kx = require(path.join(KOK, 'ortak', 'src', 'kayit.js'));
    const tek = Kx.kayitPaketle(Kx.T_NOKTA, 101, 5, new Uint8Array(4 + 36));
    const yerel = { kimlik: 9, kart: 'k', bayt: tek.length, oturumlar: Kx.oturumlariKur(Kx.akisOnek(tek)[0]), sonSira: new Map() };
    let sat = [];
    try { sat = KLx.listeBirlestir({ kart: null, yereller: [yerel], yerelNerede: 'telefon' }); } catch (h) { sat = []; }
    ok('[!] 5P (f) K10: Kayitlar telefonda — yerel kopya "yalniz bu telefonda", arsiv onayi ve kopya listesi / silme YOK, bilgi satiri Bu telefon > Esitleme`yi gosterir; PC sablonu (pc / tarayici dallari) AYNEN',
       /<label v-if="kartKimlik !== null && !telefon" class="kl-arsiv">/.test(KT) && /<section class="kart" v-if="kopyalar\.length && !telefon">/.test(KT)
       && /<option v-if="telefon" value="telefon">/.test(KT) && /<p v-if="telefon" class="ipucu" data-kl-telefon>/.test(KT)
       && KGx.NEREDE_METIN.telefon === 'kl.nerede_telefon' && KYs.ceviriKayit('kl.nerede_telefon', 'tr') === 'yalnız bu telefonda'
       && /Bu telefon/.test(KYs.ceviriKayit('kl.telefon_kopya', 'tr')) && /This phone/.test(KYs.ceviriKayit('kl.telefon_kopya', 'en'))
       && sat.length === 1 && sat[0].nerede === 'telefon',
       JSON.stringify(sat.map((s) => s.nerede)));
    const kgKod = yorumsuz(fs.readFileSync(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'), 'utf8'));
    ok('[!] 5P (f) K12: rapor Yazdir — ortamsiz window.print() AYNEN; telefonda once acik gorunum (yazdirmaOncesi), ORTAM.yazdir(), sonra geri (WebView beforeprint ikinci kez uygulamaz)',
       /async yazdir\(\) \{\s*if \(!ORTAM\) \{ window\.print\(\); return; \}\s*this\.yazdirmaOncesi\(\);\s*this\._elleYazdir = true;\s*try \{ await ORTAM\.yazdir\(\);[\s\S]*?finally \{\s*this\._elleYazdir = false;\s*this\.yazdirmaSonrasi\(\);/.test(kgKod)
       && /yazdirmaOncesi\(\) \{[^\n]*\n\s*if \(!this\.rapor \|\| this\._elleYazdir\) return;/.test(kgKod));
  });
}

/* ═══ 2026-10-07 — IMLEC ACIKLAMASI · AD / ETIKET (Ga / Ge) · COP KUTUSU ═══════════════════════
   Kullanici: (1) okuma izgarasindaki A, B, ΔT, V A/B, ΔV, A ORT, YÜK, ENERJİ ne demek — "ⓘ" aciklama,
   TEK bilesen uc yerde (Canli / kayit / Karsilastirma), metinleri tembel sozlukte (sozluk_imlec.js);
   (2) kayit gorunumunden ad + etiket (kartin Ga / Ge komutlari, sonucu kartin satiri);
   (3) tek kayit karttan silinemez -> "Sil" = ayrilmis `silindi` etiketi (cop kutusu), "Geri al" onu
   cikarir; liste onlari gizler, "Cop kutusu" suzgeci gosterir, Karsilastirma secemez. */
{
  SONRA.push(async () => {
    const IA = require(path.join(ARAYUZ, 'ekran', 'imlec_aciklama.js'));
    const SI = require(path.join(KOK, 'ortak', 'src', 'sozluk_imlec.js'));
    const SZa = require(path.join(KOK, 'ortak', 'src', 'sozluk.js'));
    const KYs = require(path.join(KOK, 'ortak', 'src', 'sozluk_kayit.js'));
    const IST = require(path.join(KOK, 'ortak', 'src', 'istatistik.js'));
    const KGx = require(path.join(ARAYUZ, 'ekran', 'kayit_gorunum.js'));
    const KLx = require(path.join(ARAYUZ, 'ekran', 'kayitlar.js'));
    const KRx = require(path.join(ARAYUZ, 'ekran', 'karsilastir.js'));
    const Kx = require(path.join(KOK, 'ortak', 'src', 'kayit.js'));
    const al = (ad) => vm.runInContext(ad, sandbox);
    const html = yorumsuz(htmlKaynak);
    const canliMain = (html.match(/<main class="gorunum" v-show="gorunum === 'canli'">([\s\S]*?)<\/main>/) || [])[1] || '';
    const bil = (B, props = {}) => {
      const o = Object.assign({}, props);
      Object.assign(o, B.data ? B.data.call(o) : {});
      Object.assign(o, B.methods || {});
      o.$nextTick = (f) => { if (f) f(); return Promise.resolve(); };
      o.$el = null;
      o.$emit = (ad, d) => { (o._yayin = o._yayin || []).push([ad, d]); };
      for (const [ad, fn] of Object.entries(B.computed || {})) Object.defineProperty(o, ad, { get: fn.bind(o), configurable: true });
      return o;
    };

    /* ── (1) aciklama ── */
    const kipler = Object.keys(IA.IMLEC_ACIKLAMA_SATIR);
    const tumAnahtar = kipler.flatMap((k) => IA.IMLEC_ACIKLAMA_SATIR[k].flat());
    const enSatir = IA.imlecAciklamaSatirlari('canli', 'en');
    ok('[!] IA1: imlec aciklamasi uc kipte (canli / kayit / kr); her satirin terimi VE aciklamasi sozluk_imlec.js`te TR + EN; satirlar secili dilde; bilinmeyen kip -> kayit',
       kipler.join() === 'canli,kayit,kr' && tumAnahtar.every((a) => a in SI.SOZLUK_IMLEC && SI.SOZLUK_IMLEC[a].tr && SI.SOZLUK_IMLEC[a].en)
       && enSatir.length === IA.IMLEC_ACIKLAMA_SATIR.canli.length && enSatir.every((s) => s.metin === SI.SOZLUK_IMLEC[s.a].en)
       && JSON.stringify(IA.imlecAciklamaSatirlari('yok', 'tr')) === JSON.stringify(IA.imlecAciklamaSatirlari('kayit', 'tr')),
       `${tumAnahtar.length} anahtar`);
    /* Terimler EKRANIN etiketleriyle ayni (etiket degisir, aciklama eskirse kirmizi) */
    const t = (a, d) => SI.SOZLUK_IMLEC[a][d];
    const ayni = (a, b, s) => ['tr', 'en'].every((d) => t(a, d) === s[b][d]);
    ok('[!] IA2: aciklamanin terimleri ekrandaki etiketlerle AYNI (Canli cn.okuma_dt / _dv / _ort_i; kayit kg.okuma_sure; Karsilastirma kr.fark) — her kipin satirlari ekranin gosterdigi alanlar',
       ayni('ia.t_dt', 'cn.okuma_dt', SZa.SOZLUK) && ayni('ia.t_dv', 'cn.okuma_dv', SZa.SOZLUK) && ayni('ia.t_ort_i', 'cn.okuma_ort_i', SZa.SOZLUK)
       && ayni('ia.t_sure', 'kg.okuma_sure', KYs.SOZLUK_KAYIT) && ayni('ia.t_fark', 'kr.fark', KYs.SOZLUK_KAYIT)
       && IA.IMLEC_ACIKLAMA_SATIR.canli.map((x) => x[1]).join() === 'ia.ab_canli,ia.dt,ia.deger,ia.dv,ia.ort_i,ia.yuk,ia.enerji,ia.bosluk'
       && IA.IMLEC_ACIKLAMA_SATIR.kayit.some((x) => x[1] === 'ia.minmaks') && IA.IMLEC_ACIKLAMA_SATIR.kayit.some((x) => x[1] === 'ia.sure')
       && !IA.IMLEC_ACIKLAMA_SATIR.kr.some((x) => x[1] === 'ia.sure'));
    /* Metin FORMULU soyluyor: integral isaretli (enerji() eksi akimda eksi mAh), ortalama zaman agirliksiz
       (istatistik() ornek ortalamasi), bosluk ustunden integral yok (boslukMs) */
    const tt = Float64Array.of(0, 1800000, 3600000);
    const e = IST.enerji(tt, Float64Array.of(2, 2, 2), Float64Array.of(-1, -1, -1), 0, 3600000);
    const eb = IST.enerji(Float64Array.of(0, 1000, 5000), Float64Array.of(1, 1, 1), Float64Array.of(1, 1, 1), 0, 5000, { boslukMs: 2000 });
    const is = IST.istatistik(Float64Array.of(0, 1, 1000), Float64Array.of(0, 0, 3));
    ok('[!] IA3: aciklama formulle tutarli — Yuk/Enerji ISARETLI integral (eksi akim -> eksi mAh/Wh), ortalama ornek ortalamasi (zaman agirliksiz), bosluk integrale girmez',
       Math.abs(e.mah + 1000) < 1e-9 && Math.abs(e.wh + 2) < 1e-9 && /İşaretli/.test(t('ia.yuk', 'tr')) && /Signed/.test(t('ia.yuk', 'en'))
       && is.ort === 1 && /Zaman ağırlıklı değil/.test(t('ia.ort', 'tr')) && /Zaman ağırlıklı değil/.test(t('ia.ort_i', 'tr'))
       && Math.abs(eb.sureS - 1) < 1e-9 && /integral alınmaz/.test(t('ia.bosluk', 'tr')) && /V × I/.test(t('ia.enerji', 'tr')),
       JSON.stringify({ e, eb, ort: is.ort }));
    const yuk = secenekler.components && secenekler.components['imlec-aciklama'];
    const kgT = KGx.KayitGorunumu.template;
    const krT = KRx.KarsilastirEkrani.template;
    ok('[!] IA4: TEK bilesen uc yerde — Canli`da yalniz dondurulunca (app.js async bilesen, ekran/imlec_aciklama.js), kayit gorunumu kip="kayit", Karsilastirma kip="kr" (statik, ayni nesne); KAPALI baslar, dugme aria-expanded',
       !!yuk && yuk.__asenkron === true && /import\('\.\/ekran\/imlec_aciklama\.js'\)\.then\(\(m\) => m\.ImlecAciklama\)/.test(String(yuk.yukleyici.loader))
       && /<imlec-aciklama v-if="donmus" kip="canli" :dil="dil"><\/imlec-aciklama>/.test(canliMain)
       && /<imlec-aciklama kip="kayit" :dil="dil"><\/imlec-aciklama>/.test(kgT) && /<imlec-aciklama kip="kr" :dil="dil"><\/imlec-aciklama>/.test(krT)
       && KGx.KayitGorunumu.components['imlec-aciklama'] === IA.ImlecAciklama && KRx.KarsilastirEkrani.components['imlec-aciklama'] === IA.ImlecAciklama
       && IA.ImlecAciklama.data().acik === false && /:aria-expanded="acik \? 'true' : 'false'"/.test(IA.ImlecAciklama.template));
    {
      const by = fs.existsSync(path.join(KOK, 'uretim', '_fs.json')) ? JSON.parse(fs.readFileSync(path.join(KOK, 'uretim', '_fs.json'), 'utf8')).bayt || {} : {};
      const acilis = iceAktarmaGrafigi().map((g) => g.goruntu);
      const canliZ = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'canli.js')).map((g) => g.goruntu);
      const iaZ = ['ekran/imlec_aciklama.js', ...iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'imlec_aciklama.js')).map((g) => g.goruntu)];
      const ek = iaZ.filter((x) => !acilis.includes(x));
      const ekBayt = ek.reduce((n, a) => n + (Number.isFinite(by[a]) ? by[a] : NaN), 0);
      const klZ = iceAktarmaGrafigi(path.join(ARAYUZ, 'ekran', 'kayitlar.js')).map((g) => g.goruntu);
      ok('[!] IA5: aciklama ACILISTA ve Canli zincirinde YOK (acilis sozlugu butcesi); dondurunca yalniz modul + sozluk_imlec.js iner, <= 4.5 KB gzip (kunyede); Kayitlar zincirinde var',
         !acilis.includes('ekran/imlec_aciklama.js') && !acilis.includes('ortak/sozluk_imlec.js') && !canliZ.includes('ortak/sozluk_imlec.js')
         && ek.slice().sort().join(' ') === 'ekran/imlec_aciklama.js ortak/sozluk_imlec.js' && ekBayt > 0 && ekBayt <= 4608
         && klZ.includes('ekran/imlec_aciklama.js') && klZ.includes('ortak/sozluk_imlec.js'),
         `${ek.join(' ')} · ${ekBayt} B`);
    }

    /* ── (2) ad / etiket komutlari (saf) ── */
    const A = KGx;
    const s60 = 'ş'.repeat(60);
    ok('[!] AE1: sinirlar app.js ve firmware ile AYNI (komut 175 bayt, metin 120 bayt = KAYIT_NOT_METIN); kayit_not_ayir a / e alt komutlarini taniyor',
       A.KOMUT_AZAMI_BAYT === al('KOMUT_AZAMI_BAYT') && A.NOT_METIN_AZAMI_BAYT === al('NOT_METIN_AZAMI_BAYT')
       && /#define KAYIT_NOT_METIN 120u/.test(fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_bicim.h'), 'utf8'))
       && /if \(a == 'a'\) k->alan = KNT_AD;\s*else if \(a == 'e'\) k->alan = KNT_ETIKET;/.test(fs.readFileSync(path.join(KOK, 'kod', 'olcum-karti-a3', 'kayit_bicim.h'), 'utf8'))
       && [0x22, 0x5c, 0x00, 0x1f, 0x7f, 0x41].map((c) => A.adKomutu(1, 'a' + String.fromCharCode(c)).hata || 'ok').join() === 'kg.hata_karakter,kg.hata_karakter,kg.hata_karakter,kg.hata_karakter,kg.hata_karakter,ok');
    const ad1 = A.adKomutu(12, '  Akü\tşarj  ');
    ok('[!] AE2: adKomutu — `Ga<no> <ad>` (sekme/satir bosluga, kenarlar kirpilir); bos ad = `Ga<no>` (sil); 120 bayt gecer, 121 bayt (UTF-8) REDDEDILIR; gecersiz oturum',
       ad1.komut === 'Ga12 Akü şarj' && A.adKomutu(12, '').komut === 'Ga12' && A.adKomutu(12, '   ').komut === 'Ga12'
       && A.adKomutu(3, s60).komut === 'Ga3 ' + s60 && A.adKomutu(3, s60 + 'x').hata === 'kg.hata_ad_uzun' && A.adKomutu(3, s60 + 'x').bayt === 121
       && A.adKomutu(0, 'x').hata === 'kg.hata_oturum' && A.adKomutu(1.5, 'x').hata === 'kg.hata_oturum' && A.adKomutu('3', 'x').hata === 'kg.hata_oturum',
       JSON.stringify(ad1));
    ok('[!] AE3: etiketKomutu — liste `, ` ile (Ge listeyi DEGISTIRIR), tekrar/bos atilir; bos = `Ge<no>`; virgullu etiket, kartin attigi karakter, KULLANICININ `silindi`si ve 120 bayti asan liste REDDEDILIR',
       A.etiketKomutu(12, ['akü', ' şarj ', '', 'akü']).komut === 'Ge12 akü, şarj' && A.etiketKomutu(12, []).komut === 'Ge12'
       && A.etiketKomutu(12, ['a,b']).hata === 'kg.hata_etiket_virgul' && A.etiketKomutu(12, ['a"']).hata === 'kg.hata_karakter'
       && A.etiketKomutu(12, ['Silindi']).hata === 'kg.hata_silindi_ayrilmis' && A.etiketKomutu(12, ['silindi'], { izinCop: true }).komut === 'Ge12 silindi'
       && A.etiketKomutu(12, ['x'.repeat(60), 'y'.repeat(59)]).hata === 'kg.hata_etiket_uzun' && A.etiketKomutu(12, ['x'.repeat(60), 'y'.repeat(58)]).komut.length === 4 + 1 + 120
       && JSON.stringify(A.etiketAyir(' akü, şarj ,,akü,\n12V ')) === '["akü","şarj","12V"]');
    const d0 = A.duzenKomutlari(5, { ad: 'Kayıt', etiket: 'akü, şarj' }, { ad: 'Kayıt', etiketler: ['akü', 'şarj'] });
    const d1 = A.duzenKomutlari(5, { ad: 'Yeni', etiket: 'akü' }, { ad: 'Eski', etiketler: ['akü'] });
    const d2 = A.duzenKomutlari(5, { ad: '', etiket: 'akü, 12V' }, { ad: 'Eski', etiketler: ['akü', 'silindi'] });
    const d3 = A.duzenKomutlari(5, { ad: 'x', etiket: 'akü, silindi' }, { ad: 'x', etiketler: ['akü'] });
    ok('[!] AE4: duzenKomutlari — yalniz DEGISENLER gider (once ad); degisiklik yoksa bos; copteki kaydin etiket duzenlemesi `silindi`yi KORUR; kullanici silindi yazarsa ret',
       d0.komutlar.length === 0 && d1.komutlar.join('|') === 'Ga5 Yeni' && d2.komutlar.join('|') === 'Ga5|Ge5 akü, 12V, silindi'
       && d3.hata === 'kg.hata_silindi_ayrilmis', JSON.stringify([d0, d1, d2, d3]));

    /* ── (3) cop kutusu (saf + oturumlariKur ile gidis-donus) ── */
    const sil = A.copKomutu(7, ['akü', '12V'], true);
    const geri = A.copKomutu(7, ['akü', ' Silindi', '12V', 'silindi'], false);
    const kur = (metinler) => {
      let sira = 100;
      const parca = [Kx.kayitPaketle(Kx.T_NOKTA, sira++, 7, new Uint8Array(4 + 36))];
      for (const m of metinler) parca.push(Kx.kayitPaketle(Kx.T_NOT, sira++, 0, Kx.notPaketle(7, Kx.KNT_ETIKET, 0, 0, new TextEncoder().encode(m))));
      const b = new Uint8Array(parca.reduce((n, x) => n + x.length, 0));
      let o = 0;
      for (const x of parca) { b.set(x, o); o += x.length; }
      return Kx.oturumlariKur(Kx.akisOnek(b)[0]).get(7);
    };
    const met = (k) => k.komut.replace(/^Ge7 ?/, '');
    const oSil = kur(['akü, 12V', met(sil)]);
    const oGeri = kur(['akü, 12V', met(sil), met(A.copKomutu(7, oSil.etiketler, false))]);
    ok('[!] CK1: Sil = mevcut etiketler + `silindi` (Ge7 akü, 12V, silindi); Geri al YALNIZ silindi`yi (her yazimi) cikarir, digerleri SIRASIYLA kalir; ikinci Sil tekrar eklemez; karttan gecen NOT kaydindan oturumlariKur ayni durumu kurar',
       sil.komut === 'Ge7 akü, 12V, silindi' && geri.komut === 'Ge7 akü, 12V' && A.copKomutu(7, ['silindi'], true).komut === 'Ge7 silindi'
       && A.copKomutu(7, [], false).komut === 'Ge7' && A.silindiMi(oSil.etiketler) && !A.silindiMi(oGeri.etiketler)
       && JSON.stringify(oGeri.etiketler) === '["akü","12V"]' && JSON.stringify(A.gorunenEtiketler(oSil.etiketler)) === '["akü","12V"]',
       JSON.stringify({ sil, geri, oSil: oSil && oSil.etiketler, oGeri: oGeri && oGeri.etiketler }));
    const yer = (id, et) => ({ kimlik: 9, oturum: id, tur: 'olcum', ad: null, etiketler: et, silindi: A.silindiMi(et), notlar: [], nokta: 5,
      yerelde: true, nerede: 'tarayici', aramaMetni: KLx.metinSadele(A.gorunenEtiketler(et).join(' ')) });
    const sat = [yer(1, ['akü']), yer(2, ['akü', 'silindi']), yer(3, [])];
    const no = (l) => l.map((s) => s.oturum).join();
    ok('[!] CK2: liste — `silindi`li oturum her tur suzgecinde GIZLI, "Cop kutusu" (tur silinen) YALNIZ onlari gosterir; aramada `silindi` gecmez; Karsilastirma secemez (kr.sec_silindi, TR + EN)',
       no(KLx.satirSuz(sat)) === '1,3' && no(KLx.satirSuz(sat, { tur: 'olcum' })) === '1,3' && no(KLx.satirSuz(sat, { tur: 'silinen' })) === '2'
       && no(KLx.satirSuz(sat, { tur: 'silinen', arama: 'akü' })) === '2' && no(KLx.satirSuz(sat, { tur: 'silinen', arama: 'silindi' })) === ''
       && KLx.secilebilir(sat[1]).sebep === 'kr.sec_silindi' && KLx.secilebilir(sat[0]).uygun
       && KYs.ceviriKayit('kr.sec_silindi', 'en') !== 'kr.sec_silindi' && KYs.SOZLUK_KAYIT['kl.tur_silinen'].en === 'Trash');
    {
      const Kk = Kx;
      const tek = Kk.kayitPaketle(Kk.T_NOKTA, 101, 4, new Uint8Array(4 + 36));
      const n1 = Kk.kayitPaketle(Kk.T_NOT, 102, 0, Kk.notPaketle(4, Kk.KNT_ETIKET, 0, 0, new TextEncoder().encode('ölçüm, silindi')));
      const b = new Uint8Array(tek.length + n1.length); b.set(tek); b.set(n1, tek.length);
      const yerel = { kimlik: 9, kart: 'k', bayt: b.length, oturumlar: Kk.oturumlariKur(Kk.akisOnek(b)[0]), sonSira: new Map() };
      const l = KLx.listeBirlestir({ kart: null, yereller: [yerel] });
      ok('[!] CK3: listeBirlestir satiri `silindi` alanini oturumun etiketlerinden kurar (kart dizini satiri silindi:false); arama metninde silindi YOK; rozet sablonu gorunen(s.etiketler), Geri al dugmesi baglantinin DISINDA ve yalniz copteki satirda; tur secicide "silinen"; cop sayaci',
         l.length === 1 && l[0].silindi === true && !/silindi/.test(l[0].aramaMetni) && KLx.kartSatiri(1, { id: 2, tur: 1 }).silindi === false
         && /<span v-for="e in gorunen\(s\.etiketler\)" :key="e" class="kl-rozet kl-etiket">/.test(KLx.KayitlarEkrani.template)
         && /<\/a>\s*<!--[^>]*-->\s*<button v-if="s\.silindi" type="button" class="kl-geri-al" :data-kl-geri-al="s\.anahtar"/.test(KLx.KayitlarEkrani.template)
         && /<option value="silinen">\{\{ m\.turSilinen \}\}<\/option>/.test(KLx.KayitlarEkrani.template)
         && /data-kl-cop-sayi/.test(KLx.KayitlarEkrani.template), JSON.stringify(l.map((x) => [x.silindi, x.aramaMetni])));
    }
    ok('[!] CK4: duzenNedeni — kart bagli DEGIL / duzen islevi yok -> bagli_degil; bagli kartin akisi BILINMIYOR -> kart_bilinmiyor; baska akis (eski kart / bicim oncesi) -> baska_kart; ayni akis -> \'\'; kopruda akis /esitleme/durum arsiv yolundan',
       KLx.duzenNedeni({ duzenVar: true, bagli: false, aktif: 9, kimlik: 9 }) === 'kg.duzen_bagli_degil'
       && KLx.duzenNedeni({ duzenVar: false, bagli: true, aktif: 9, kimlik: 9 }) === 'kg.duzen_bagli_degil'
       && KLx.duzenNedeni({ duzenVar: true, bagli: true, aktif: null, kimlik: 9 }) === 'kg.duzen_kart_bilinmiyor'
       && KLx.duzenNedeni({ duzenVar: true, bagli: true, aktif: 8, kimlik: 9 }) === 'kg.duzen_baska_kart'
       && KLx.duzenNedeni({ duzenVar: true, bagli: true, aktif: 9, kimlik: 9 }) === ''
       && KLx.pcAkisCoz({ arsiv: 'arsiv/ba9f/akis-3995957410' }) === 3995957410 && KLx.pcAkisCoz({ arsiv: null }) === null && KLx.pcAkisCoz(null) === null);

    /* ── kayit gorunumu bileseni (Vue'suz) ── */
    const oturum = (et, ad = 'Deneme') => ({ id: 7, ad, etiketler: et, notlar: new Map(), skoplar: new Map(), noktalar: [], ayrinti: [], basla: null, bitir: null });
    const giden = [];
    const kd = (yanit) => async (k) => { giden.push(k); return yanit; };
    const KGb = KGx.KayitGorunumu;
    const g1 = bil(KGb, { veri: { oturum: oturum(['akü']), kimlik: 9 }, dil: 'tr', rapor: false, duzenNeden: '', kayitDuzen: kd({ durum: 'tamam' }) });
    const ilk = await g1.copIslem(true);              // onaysiz: gitmez
    g1.copOnayIste();
    const ikinci = await g1.copIslem(true);
    const g2 = bil(KGb, { veri: { oturum: oturum(['akü', 'silindi']), kimlik: 9 }, dil: 'en', rapor: false, duzenNeden: '',
      kayitDuzen: kd({ durum: 'ret', satir: '! G: oturum numarasi gerekli (yalniz rakam, 0 degil)' }) });
    await g2.copIslem(false);
    const g3 = bil(KGb, { veri: { oturum: oturum(['akü']), kimlik: 9 }, dil: 'tr', rapor: false, duzenNeden: 'kg.duzen_baska_kart', kayitDuzen: kd({ durum: 'tamam' }) });
    const n3 = giden.length;
    g3.duzenAd = 'Yeni ad';
    await g3.duzenKaydet();
    ok('[!] CK5: kayit gorunumu — Sil IKI ASAMALI (onaysiz copIslem karta GITMEZ), onayla `Ge7 akü, silindi` + "degisti"; copteki kayit: rozette silindi YOK, banner + Geri al `Ge7 akü`; kartin reddi satiriyla (EN); duzenNeden varken HICBIR komut gitmez ve sebep yazilir',
       ilk === false && ikinci === true && giden[0] === 'Ge7 akü, silindi' && g1._yayin && g1._yayin[0][0] === 'degisti'
       && g1.duzenMesaj.tur === 'tamam' && g2.copte === true && JSON.stringify(g2.etiketler) === '["akü"]' && g2.duzenEtiket === 'akü'
       && giden[1] === 'Ge7 akü' && g2.duzenMesaj.tur === 'hata' && /^The board rejected it: ! G: oturum/.test(g2.duzenMesaj.metin)
       && giden.length === n3 && g3.duzenAcik === false && /başka bir kart/.test(g3.duzenNedenMetni),
       JSON.stringify({ giden, m1: g1.duzenMesaj, m2: g2.duzenMesaj }));
    const g4 = bil(KGb, { veri: { oturum: oturum(['akü'], 'Eski'), kimlik: 9 }, dil: 'tr', rapor: false, duzenNeden: '', kayitDuzen: kd({ durum: 'tamam' }) });
    g4.duzenAd = 'Yeni'; g4.duzenEtiket = 'akü, 12V';
    const n4 = giden.length;
    await g4.duzenKaydet();
    const g5 = bil(KGb, { veri: { oturum: oturum(['akü'], 'Eski'), kimlik: 9 }, dil: 'tr', rapor: false, duzenNeden: '', kayitDuzen: kd({ durum: 'tamam' }) });
    g5.duzenAd = 'x'.repeat(121);
    const n5 = giden.length;
    await g5.duzenKaydet();
    ok('[!] CK6: Kaydet — Ga sonra Ge SIRAYLA (ilk basarisizda durur); 121 baytlik ad karta GITMEZ, bayt ve sinir mesajda; sablon: duzen bolumu rapor DISINDA, girisler etiketli (label), Sil "Eminim" tehlike sinifli, cop banner data-kg-cop',
       giden.slice(n4).join('|') === 'Ga7 Yeni|Ge7 akü, 12V' && giden.length === n5 + 0 && g5.duzenMesaj.tur === 'hata' && /121/.test(g5.duzenMesaj.metin) && /120/.test(g5.duzenMesaj.metin)
       && /<section class="kart yazdirma-yok kg-duzen" v-if="!rapor" data-kg-duzen>/.test(kgT)
       && /<label>\{\{ m\.duzenAd \}\}\s*<input type="text" v-model="duzenAd"/.test(kgT) && /<label>\{\{ m\.duzenEtiket \}\}\s*<input type="text" v-model="duzenEtiket"/.test(kgT)
       && /class="tehlike" data-kg-sil-eminim @click="copIslem\(true\)"/.test(kgT) && /<p v-if="copte" class="uyari kg-cop" data-kg-cop>/.test(kgT),
       JSON.stringify({ giden: giden.slice(n4), m5: g5.duzenMesaj }));

    /* ── app.js: kayitDuzenGonder (kartin yaniti beklenir) ── */
    const u = ornek();
    const gid = [];
    u.bagli = true;
    u.gonder = async (k) => { gid.push(k); };
    const p1 = u.kayitDuzenGonder('Ge7 akü, silindi');
    await Promise.resolve();
    const mesgul = await u.kayitDuzenGonder('Ga7 x');
    u.satirIsle('* G not kuyrukta (verilmemis oturuma yazilmaz; sonuc esitlenen dosyada)');
    const r1 = await p1;
    const p2 = u.kayitDuzenGonder('Ga7 x');
    await Promise.resolve();
    u.satirIsle('! G: oturum numarasi gerekli (yalniz rakam, 0 degil)');
    const r2 = await p2;
    /* Gd / tavani asan komut GITMEMELI; giderse yanit beklenirdi — zamanlayici elle tetiklenir (askida kalmasin) */
    const eskiZ = sandbox.setTimeout;
    const zk = [];
    sandbox.setTimeout = (fn) => { zk.push(fn); return zk.length; };
    let r3;
    let r4;
    try {
      const p3 = u.kayitDuzenGonder('Gd');
      await Promise.resolve();
      zk.splice(0).forEach((f) => f());
      r3 = await p3;
      const p4 = u.kayitDuzenGonder('Ga7 ' + 'x'.repeat(200));
      await Promise.resolve();
      zk.splice(0).forEach((f) => f());
      r4 = await p4;
    } finally {
      sandbox.setTimeout = eskiZ;
    }
    u.bagli = false;
    const r5 = await u.kayitDuzenGonder('Ga7 x');
    u.satirIsle('* G not kuyrukta (verilmemis oturuma yazilmaz; sonuc esitlenen dosyada)');   // bekleyen yok: yok sayilir
    ok('[!] CK7: app.js kayitDuzenGonder — yalniz Ga / Ge gider (Gd ve tavani asan GITMEZ); kartin `* G not kuyrukta` satiri -> tamam, `! G…` -> ret (satir oldugu gibi); ayni anda tek istek (mesgul); bagli degilse gitmez; Kayitlar`a :kayit-duzen ile verilir',
       r1.durum === 'tamam' && mesgul.durum === 'mesgul' && r2.durum === 'ret' && /oturum numarasi/.test(r2.satir)
       && r3.durum === 'gitmedi' && r4.durum === 'gitmedi' && r5.durum === 'bagli_degil' && gid.join('|') === 'Ge7 akü, silindi|Ga7 x'
       && /<kayitlar-ekran[^>]*:kayit-duzen="kayitDuzenGonder"/.test(html),
       JSON.stringify({ r1, mesgul, r2, r3, r4, r5, gid }));

    /* ── Kayitlar: copGeriAl + esitleme ── */
    const KLb = KLx.KayitlarEkrani;
    const kl = bil(KLb, { dilSecim: 'tr', bagli: true, kayitDuzen: kd({ durum: 'tamam' }), kartAdres: (y) => y });
    kl.kartKimlik = 9; kl.pc = false;
    let esitlendi = 0;
    kl._bekle = async () => {};
    kl.esitle = async () => { esitlendi++; };
    Object.defineProperty(kl, 'esitlenebilir', { get: () => true, configurable: true });
    const n6 = giden.length;
    const s2 = { kimlik: 9, oturum: 2, tur: 'olcum', ad: null, etiketler: ['akü', 'silindi'], silindi: true };
    const ok1 = await kl.copGeriAl(s2);
    const bild = kl.bildirim;
    const yabanci = await kl.copGeriAl({ ...s2, kimlik: 8 });
    kl.pc = true; kl.pcDurum = { arsiv: 'arsiv/k/akis-9' };
    const ok2 = await kl.copGeriAl(s2);
    ok('[!] CK8: Kayitlar "Geri al" (cop kutusu satiri) — `Ge2 akü` gider, sonra kisa bekleyip eşitler, sonuc "eşitlendi"; baska akistaki satir GITMEZ; kopruda eşitleme yok (kopru 2 dk), sonuc kg.duzen_pc',
       ok1 === true && giden[n6] === 'Ge2 akü' && esitlendi === 1 && bild.anahtar === 'kg.duzen_esitlendi' && yabanci === false
       && ok2 === true && esitlendi === 1 && kl.bildirim.anahtar === 'kg.duzen_pc' && giden.length === n6 + 2,
       JSON.stringify({ giden: giden.slice(n6), esitlendi, bild, b2: kl.bildirim }));
  });
}

/* Asenkron iddialar OZETTEN ONCE — sayilsinlar diye. Kuyruk bu
   fonksiyonun govdesinde (bolum 13) dolduruluyor; bosaltma burada,
   ozetin hemen oncesinde. */
for (const f of SONRA) await f();

console.log(`\n${gecti}/${gecti + kaldi} dogrulama gecti`);
ozetBasildi = true;

/* ── TEZGAH KALEMLERI (B23.1) ──────────────────────────────────────────
   Bicim `uretim/tezgah.py` ile AYNI olmali — dogrula3.py ikisini de ayni
   ayristiriciyla topluyor. Node tarafinda ayri bir modul yazmak yerine
   uc satirlik ciktiyi burada uretmek yeterli; bicim degisirse tek yer
   (tezgah.py) degil IKI yer guncellenmeli — bu bilincli bir odun ve
   sim3_web.py'de bir iddia bunu civiliyor. */
function tezgah(adim, kalemler) {
  if (!kalemler.length) return;
  console.log('');
  console.log(`  === TEZGAH: ${adim} ===`);
  for (const [kalem, kabul] of kalemler) {
    console.log(`  [T] ${kalem}`);
    console.log(`      -> ${kabul}`);
  }
}

tezgah('B7 Arayuz', [
  ['[!] Arayuz tarayicida GERCEKTEN dogru gorunuyor mu',
   'Bu adim Vue`yu TAKLIT ediyor; sayfa hic render edilmiyor. B22.0`da '
   + 'arayuz zincir 15/15 yesilken tarayicida HIC acilmiyordu. '
   + '`python arayuz3/sunucu.py` -> konsolda 0 hata, ham {{ }} yok'],
  ['J7/J3 baypas uyarisi KIRMIZI seritli gorunuyor mu',
   'Emniyet uyarisi govde metninden ayirt edilebilmeli. B22.0 oncesi '
   + '`.uyari` sinifi hic tanimli degildi ve duz paragraf olarak cikiyordu'],
  ['Osiloskop iki yoldan da AYNI cizimi veriyor mu',
   'USB`de ASCII, WiFi`de ikili (/skop.bin) yol kullaniliyor. Ayni '
   + 'sinyalde iki kip AYNI dalgayi cizmeli; farkliysa cozuculerden biri '
   + 'yanlis (endian, olcek ya da ofset)'],
  ['Telefonda Ana Ekrana Ekle',
   'iPhone: adres cubugu OLMADAN, kendi ikonuyla acilmali. '
   + 'Android: kisayol Chrome sekmesinde acilir — bu beklenen davranis, '
   + 'gercek PWA kurulumu HTTPS istiyor'],
]);

process.exit(kaldi ? 1 : 0);
}

