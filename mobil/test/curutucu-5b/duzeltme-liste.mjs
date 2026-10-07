// Curutucu 5B duzeltmelerinin mutasyonlari ("5B-C:" oneki). mutasyon/liste.mjs bunu ice aktarir:
//   node mutasyon/kos.mjs --neden 5B-C
// Ilk bolum: curutucunun YASAYAN buldugu mutasyonlar (test/curutucu-5b/yasayan-liste.mjs).
// Sonraki bolumler: her duzeltmenin (bulgu 1–9) onu YALANLAYAN degisikligi.
import yasayan from "./yasayan-liste.mjs";

const KART = "src/cekirdek/kart.js";
const KASA = "src/cekirdek/kasa.js";
const SAHTE = "test/yardim/kasa_sahtesi.mjs";
const LOGCAT = "araclar/logcat_tara.mjs";
const DURUM = "src/ekran/esles_durum.js";
const T_YARIS = "test/curutucu-5b/yaris.test.js";
const T_KOTU = "test/curutucu-5b/kotu-kart.test.js";
const T_YARIM = "test/curutucu-5b/kasa-yarim.test.js";
const T_AYRISMA = "test/curutucu-5b/ayrisma.test.js";
const T_LOGCAT = "test/curutucu-5b/logcat.test.js";

const DEGERSIZ = String.raw`(?!(?:yok|null|none|bos|undefined)(?![A-Za-z0-9]))`;

// Satir sonu notu: .mjs / .vue / .xml / manifest calisma agacinda CRLF olabilir (text=auto); bu dosyalara
// giden `bul` dizgileri TEK satirdir. .js dosyalari eol=lf (cok satirli desen guvenli).
const liste = [
  ...yasayan,

  // ── bulgu 1, 3, 6: imzali istegin yeniden imzalanmasi ───────────────────
  {
    ad: "Y1: 401'den sonra dis dongu yeniden imzalamiyor (es zamanli isteklerde acilis coktan guncellenmis)",
    dosya: KART,
    bul: "        if (e instanceof HttpHatasi && e.durum === 401 && yenidenImzala && imzaSayisi < IMZA_AZAMI) continue;\n",
    koy: "",
    test: T_YARIS,
  },
  {
    ad: "Y1: kimlik yeniden dogrulamasi IMZALANAN acilisa degil cihaz.acilis'e bakiyor",
    dosya: KART,
    bul: "      if (yeni !== imzalanan) {",
    koy: "      if (yeni !== c.acilis) {",
    test: "test/kart-5bc.test.js",
  },
  {
    ad: "Y2: ayni acilista 401 yeni sayacla yeniden imzalanmiyor (pencere gerisi = 'cihaz-silinmis')",
    dosya: KART,
    bul: '      if (!ACILIS.test(yeni)) throw new KartHatasi("kart-gecersiz");',
    koy: '      if (yeni === imzalanan) return y;\n      if (!ACILIS.test(yeni)) throw new KartHatasi("kart-gecersiz");',
    test: T_YARIS,
  },
  {
    ad: "O1: 401'deki X-Acilis bicim denetimsiz imzaya giriyor",
    dosya: KART,
    bul: '      if (!ACILIS.test(yeni)) throw new KartHatasi("kart-gecersiz");\n',
    koy: "",
    test: T_KOTU,
  },
  {
    ad: "O2: istek basina imza ust siniri kalkti (kotu kart ucuncu imzayi aliyor)",
    dosya: KART,
    bul: "if (imzali && imzaSayisi >= IMZA_AZAMI) throw",
    koy: "if (false) throw",
    test: T_KOTU,
  },
  {
    ad: "O2: X-Acilis'siz 401 de yeniden imza / bicim hatasi sayiliyor",
    dosya: KART,
    bul: "      if (yeni === null) return y;\n",
    koy: "",
    test: "test/kart-5bc.test.js",
  },
  {
    ad: "O3: kanit gittikten sonra gelen bicimsiz 2xx 'kart-sahte' sayilmiyor",
    dosya: KART,
    bul: 'if (son && son.yol === "/eslestir/kanit" && son.durum >= 200 && son.durum < 300) return new KartHatasi("kart-sahte");',
    koy: 'if (e instanceof CalismaHatasi && son && son.durum >= 200 && son.durum < 300) return new KartHatasi("kart-sahte");',
    test: T_KOTU,
  },
  // ── bulgu 2: eslesmeyi kaldir ──────────────────────────────────────────
  {
    ad: "Y3: eslesmeyiKaldir 401'de 'kartta: true' diyor (eski davranis)",
    dosya: KART,
    bul: 'if (e instanceof KartHatasi && e.tur === "cihaz-silinmis") kartta = null;',
    koy: 'if (e instanceof KartHatasi && e.tur === "cihaz-silinmis") kartta = true;',
    test: "test/kart-5bc.test.js",
  },
  {
    ad: "Y3: ekranda 401 (null) icin ayri metin yok",
    dosya: DURUM,
    bul: 'return kartta === null ? "m.bg.kaldirildi_belirsiz" : "m.bg.kaldirildi_yerel";',
    koy: 'return kartta === null ? "m.bg.kaldirildi" : "m.bg.kaldirildi_yerel";',
    test: "test/esles.test.js",
  },
  // ── bulgu 4: yarim kayit ───────────────────────────────────────────────
  {
    ad: "S1: cihazSakla yarida kalinca disk kaydi silinmiyor",
    dosya: KASA,
    bul: '        try { await cagir("sil", { kimlik }); } catch { /* cihazYukle: isaret 0 -> yarim kayit */ }\n',
    koy: "",
    test: T_YARIM,
  },
  {
    ad: "S2: cihazSakla yarida kalinca bellekteki nesne kasada kaliyor (sifir K ile 'bagli')",
    dosya: KASA,
    bul: '        yuklu.delete(kimlik);\n        try { await cagir("sil"',
    koy: '        try { await cagir("sil"',
    test: "test/kasa.test.js",
  },
  {
    ad: "S2: yarim kalan saklamada ESKI nesnenin K'si sifirlanmiyor",
    dosya: KASA,
    bul: "        if (kalan && kalan.cihaz !== cihaz) kalan.cihaz.K.fill(0);",
    koy: "",
    test: "test/kasa.test.js",
  },
  {
    ad: "S2: kaydet SIFIR anahtarli cihazi kabul ediyor (sifir K ile imza)",
    dosya: KASA,
    bul: '|| sifirMi(cihaz.K)) throw new KasaHatasi("kayitsiz");',
    koy: ') throw new KasaHatasi("kayitsiz");',
    test: "test/kasa.test.js",
  },
  {
    ad: "S2: cihazSakla SIFIR anahtari kabul ediyor",
    dosya: KASA,
    bul: '|| !adGecerli(cihaz.ad) || sifirMi(cihaz.K)) throw new KasaHatasi("bicim");',
    koy: '|| !adGecerli(cihaz.ad)) throw new KasaHatasi("bicim");',
    test: "test/kasa.test.js",
  },
  {
    ad: "S3: 'anahtar var, isaret 0' yarim kaydi cihazYukle tanimiyor (sessizce eslesmis)",
    dosya: KASA,
    bul: "      if (isaret === 0) {",
    koy: "      if (false) {",
    test: "test/kasa.test.js",
  },
  {
    ad: "S3: yarim kayit taninca diskten silinmiyor",
    dosya: KASA,
    bul: '        K.fill(0);\n        await cagir("sil", { kimlik });\n        return null;',
    koy: "        K.fill(0);\n        return null;",
    test: "test/kasa.test.js",
  },
  // ── bulgu 5: iki yazar ─────────────────────────────────────────────────
  {
    ad: "S4: sahte eklenti esit isaret yazimini kabul ediyor (iki kasa ayni sayaci kullanir)",
    dosya: SAHTE,
    bul: "if (disk.isaretler.has(v.kimlik) && yeni <= disk.isaretler.get(v.kimlik)) throw",
    koy: "if (disk.isaretler.has(v.kimlik) && yeni < disk.isaretler.get(v.kimlik)) throw",
    test: T_YARIM,
  },
  {
    ad: "S4: kartAl her cagrida yeni kart / kasa kuruyor",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  if (!soz) {",
    koy: "  if (true) {",
    test: "test/uygulama.test.js",
  },
  {
    ad: "S4: basarisiz kurulum sozu saklaniyor (uygulama bir daha kart kuramaz)",
    dosya: "src/cekirdek/uygulama.js",
    bul: "    yeni.catch(() => { if (soz === yeni) soz = null; });",
    koy: "    yeni.catch(() => {});",
    test: "test/uygulama.test.js",
  },
  {
    ad: "S4: Bu telefon (kart_bolum.js; once Baglanti ekrani) kendi kasasini kuruyor",
    dosya: "src/telefon/kart_bolum.js",
    bul: 'import { ESLES_HATA, baglantiHatasi, kaldirGorunur, kaldirMesaji } from "../ekran/esles_durum.js";\n',
    koy: 'import { ESLES_HATA, baglantiHatasi, kaldirGorunur, kaldirMesaji } from "../ekran/esles_durum.js";\nconst yedekKart = () => kartKur({ ag: null, kesif: null, kasa: kasaKur(null) });\n',
    test: "test/uygulama.test.js",
  },
  // ── bulgu 7: sahte <-> Kotlin ──────────────────────────────────────────
  {
    ad: "A1: sahte eklenti 24 bayttan uzun adi kabul ediyor",
    dosya: SAHTE,
    bul: '    if (Buffer.byteLength(v.ad, "utf8") > AD_AZAMI_BAYT) throw hata("bicim");',
    koy: "",
    test: T_AYRISMA,
  },
  {
    ad: "A1: sahte eklenti fazla dolgulu base64'u kabul ediyor",
    dosya: SAHTE,
    bul: "  return m[2].length === 0 || m[2].length === (4 - (m[1].length % 4)) % 4;",
    koy: "  return true;",
    test: T_AYRISMA,
  },
  {
    ad: "A1: sahte eklenti Long sinirini asan isareti kabul ediyor",
    dosya: SAHTE,
    bul: " || BigInt(v.isaret) > LONG_AZAMI) throw",
    koy: ") throw",
    test: T_AYRISMA,
  },
  {
    ad: "A1: sahte eklenti listeyi kimlige gore siralamiyor",
    dosya: SAHTE,
    bul: ".sort(([a], [b]) => (a < b ? -1 : 1))",
    koy: "",
    test: T_AYRISMA,
  },
  {
    ad: "A2: kasa.cihazSakla adi kendisi denetlemiyor",
    dosya: KASA,
    bul: " || !adGecerli(cihaz.ad) ||",
    koy: " ||",
    test: T_AYRISMA,
  },
  // ── bulgu 8: gizlilik kurali ───────────────────────────────────────────
  {
    ad: "C1: kuresel nesne adlari (window / globalThis / self) yasak listesinden cikti",
    dosya: "test/gizlilik.test.js",
    bul: String.raw`|\bglobalThis\b|\bwindow\b|\bself\b(?!-)|`,
    koy: "|",
    test: "test/gizlilik.test.js",
  },
  // ── bulgu 8: logcat tarayicisi ─────────────────────────────────────────
  {
    ad: "L1: URL kodlu sir cozulmuyor",
    dosya: LOGCAT,
    bul: 'const metinler = [satir, yuzdeCoz(satir), yuzdeCoz(satir.replace(/\\+/g, " ")), kacisCoz(satir)];',
    koy: "const metinler = [satir, kacisCoz(satir)];",
    test: T_LOGCAT,
  },
  {
    ad: "L1: form kodlu ('+' = bosluk) sir cozulmuyor",
    dosya: LOGCAT,
    bul: ', yuzdeCoz(satir.replace(/\\+/g, " ")), kacisCoz(satir)];',
    koy: ", kacisCoz(satir)];",
    test: T_LOGCAT,
  },
  {
    ad: "L1: JSON kacisli sir cozulmuyor",
    dosya: LOGCAT,
    bul: ", kacisCoz(satir)];",
    koy: "];",
    test: T_LOGCAT,
  },
  {
    ad: "L1: ayracli (bosluk / iki nokta) onaltilik aranmiyor",
    dosya: LOGCAT,
    bul: 'const ayracsiz = [k, k.replace(/[^0-9a-f]/g, ""), k.replace(/0x/g, "").replace(/[^0-9a-f]/g, "")];',
    koy: 'const ayracsiz = [k, k.replace(/0x/g, "").replace(/, /g, "")];',
    test: T_LOGCAT,
  },
  {
    ad: "L1: 0x onekli onaltilik aranmiyor",
    dosya: LOGCAT,
    bul: ', k.replace(/0x/g, "").replace(/[^0-9a-f]/g, "")];',
    koy: "];",
    test: T_LOGCAT,
  },
  {
    ad: "L1: UTF-16LE onaltilik aranmiyor",
    dosya: LOGCAT,
    bul: '    kucuk.push(Buffer.from(sir, "utf16le").toString("hex"));',
    koy: "",
    test: T_LOGCAT,
  },
  {
    ad: "L1: ondalik bayt dokumu aranmiyor",
    dosya: LOGCAT,
    bul: "    if (ondalik.some((d) => dokum.includes(d))) return true;",
    koy: "",
    test: T_LOGCAT,
  },
  {
    ad: "L1: isaretli (Kotlin) ondalik bayt isaretsize indirilmiyor",
    dosya: LOGCAT,
    bul: "n >= -128 && n <= 255 ? n & 255 : \"x\"",
    koy: "n >= 0 && n <= 255 ? n : \"x\"",
    test: T_LOGCAT,
  },
  {
    ad: "L1: onaltilik sirrin ham baytlarinin ondalik dokumu aranmiyor",
    dosya: LOGCAT,
    bul: '    diziler.push(Buffer.from(sir, "hex"));',
    koy: "",
    test: T_LOGCAT,
  },
  {
    ad: "L1: iki satira bolunmus sir aranmiyor",
    dosya: LOGCAT,
    bul: "      if (arayicilar[j].var(birlesik)) bulgular.push",
    koy: "      if (false) bulgular.push",
    test: T_LOGCAT,
  },
  {
    ad: "L1: bolunmus sirda ikinci satirin logcat onu atilmiyor",
    dosya: LOGCAT,
    bul: 'satirlar[i + 1].replace(SATIR_ONU, "")',
    koy: "satirlar[i + 1]",
    test: T_LOGCAT,
  },
  {
    ad: "L1: bolunmus sir, ikinci satirda tek basina bulunsa da iki kez bildiriliyor",
    dosya: LOGCAT,
    bul: "      if (i + 1 >= satirlar.length || tek[j][i + 1]) continue;",
    koy: "      if (i + 1 >= satirlar.length) continue;",
    test: T_LOGCAT,
  },
  {
    ad: "L1b: anahtar= / sifre= / key= / secret= alani aranmiyor",
    dosya: LOGCAT,
    bul: String.raw`re: /(?:[Aa]nahtar|ANAHTAR|[SsŞş]ifre|[Ss]ecret|SECRET|(?<![A-Za-z])key|Key|KEY)["']?\s*[:=]\s*["']?` + DEGERSIZ + String.raw`[^\s"']/ }`,
    koy: "re: /(?!)/ }",
    test: "test/logcat_tara.test.js",
  },
  {
    ad: "L1b: satir basindaki _i= (imza sorgusu) aranmiyor",
    dosya: LOGCAT,
    bul: String.raw`re: /(?:^|[?&\s"'(,;])_[isc]=/`,
    koy: String.raw`re: /[?&]_[isc]=/`,
    test: "test/logcat_tara.test.js",
  },
  {
    ad: "L1b: kirpik (40–63 hane) onaltilik aranmiyor",
    dosya: LOGCAT,
    bul: String.raw`(?<![0-9A-Fa-f])[0-9A-Fa-f]{40,}(?![0-9A-Fa-f])/ }`,
    koy: String.raw`(?<![0-9A-Fa-f])[0-9A-Fa-f]{64,}(?![0-9A-Fa-f])/ }`,
    test: T_LOGCAT,
  },
  {
    ad: "L2: 'parola: yok' alarm veriyor (deger olmayan sozcukler ayiklanmiyor)",
    dosya: LOGCAT,
    bul: String.raw`re: /(?:parola|password|passwd)[A-Za-z_]*["']?\s*[:=]\s*["']?` + DEGERSIZ + String.raw`[^\s"']/i }`,
    koy: String.raw`re: /(?:parola|password|passwd)[A-Za-z_]*["']?\s*[:=]\s*["']?[^\s"']/i }`,
    test: T_LOGCAT,
  },
  {
    ad: "L2: 'monkey=' gizli alan sayiliyor (sozcuk siniri yok)",
    dosya: LOGCAT,
    bul: String.raw`(?<![A-Za-z])key|Key|KEY)`,
    koy: String.raw`key|Key|KEY)`,
    test: "test/logcat_tara.test.js",
  },
  // ── bulgu 9: ekran + manifest ──────────────────────────────────────────
  {
    ad: "9a: 'Eslesmeyi kaldir' kimlik uymazken gorunmuyor",
    dosya: DURUM,
    bul: ' && (baglanti.durum === "bagli" || baglanti.durum === "kimlik-uymuyor");',
    koy: ' && baglanti.durum === "bagli";',
    test: "test/esles.test.js",
  },
  {
    ad: "9a: 'Eslesmeyi kaldir' kasa bozukken gorunmuyor",
    dosya: DURUM,
    bul: "  if (kasaBozuk === true) return true;\n",
    koy: "",
    test: "test/esles.test.js",
  },
  {
    ad: "9a: 'kasa' hatasi icin ayri metin yok",
    dosya: DURUM,
    bul: '  if (tur === "kasa") return { anahtar: "m.bg.kasa_bozuk", degerler: null, kasaBozuk: true };\n',
    koy: "",
    test: "test/esles.test.js",
  },
  {
    ad: "9a: Bu telefon › Kart (kart_bolum.js; once Baglanti.vue) dugme kosulunda kararlari kullanmiyor",
    dosya: "src/telefon/kart_bolum.js",
    bul: "    kaldirAcik() { return kaldirGorunur(this.baglanti, this.kasaBozuk); },",
    koy: '    kaldirAcik() { return Boolean(this.baglanti) && this.baglanti.durum === "bagli"; },',
    test: "test/esles.test.js",
  },
  {
    ad: "9c: manifestte veri cikarma kurallari yok (Android 12+ cihazdan cihaza aktarim acik)",
    dosya: "android/app/src/main/AndroidManifest.xml",
    bul: 'android:dataExtractionRules="@xml/veri_cikarma"',       // satir sonu yok: manifest calisma agacinda CRLF olabilir
    koy: "",
    test: "test/gizlilik.test.js",
  },
  {
    ad: "9c: fullBackupContent kapali degil",
    dosya: "android/app/src/main/AndroidManifest.xml",
    bul: 'android:fullBackupContent="false"',       // satir sonu yok: manifest calisma agacinda CRLF olabilir
    koy: "",
    test: "test/gizlilik.test.js",
  },
  {
    ad: "9c: cihazdan cihaza aktarimda uygulama dosyalari (kasa) dislanmiyor",
    dosya: "android/app/src/main/res/xml/veri_cikarma.xml",
    bul: "<device-transfer>",
    koy: '<device-transfer><include domain="file" path="." />',
    test: "test/gizlilik.test.js",
  },
];

export default liste.map((m) => ({ ...m, ad: `5B-C: ${m.ad}` }));
