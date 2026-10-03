# Alt proje 5 — Android uygulaması: uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kartı bulan, eşleşen, izleyen, kaydı başlatıp durduran, kayıtları telefona eşitleyip inceleyen
ve kayıt sürerken kart düşerse haber veren, telefona özel Android uygulaması.

**Architecture:** Ionic Vue ekranları WebView'de; hesap kodu `ortak/src` (içe aktarılır, değiştirilmez);
ağ, anahtar kasası, dosya deposu, izleme servisi ve MQTT Kotlin eklentilerinde. Yalnız WebView imzalar.

**Tech Stack:** Capacitor 6.2.x · Ionic Vue 8 · Vue 3 · Vite · vitest · Kotlin (AGP/Gradle Capacitor 6'nın
şablonu) · JDK 17 · compile/target SDK 34 · minSdk 28 · Node 24.

**Spec:** `tasarim/2026-10-04-alt-proje-5-android.md` (A1–A48, Ş1–Ş6). Üst tasarım ve protokoller oradan bağlı.

Bu belge bütün dilimlerin sırasını, dosya düzenini ve arayüzlerini; **5A'nın** adım adım görevlerini
içerir. 5B–5G'nin adım adım görevleri, her dilim başlarken bu belgeye eklenir (5A'nın ölçümleri —
cleartext, araç zinciri — onların ayrıntısını belirliyor).

## Global Constraints

- Çalışma ağacı: `projeler/olcum-karti-android` (dal `5-android`). Bunun DIŞINA yazılmaz.
- DEĞİŞTİRİLMEZ: `ortak/`, `arayuz3/`, `kopru/`, `kod/`, `uretim/dogrula3.py`, `uretim/mutasyon.py`,
  `uretim/beklenen_sayim.json`, `DEVIR.md`, `tasarim/1-acik-isler.md`. Gereken değişiklik
  `mobil/DEVIR-ISTEK.md`'ye yazılır.
- ÇALIŞTIRILMAZ: `uretim/dogrula3.py`, `uretim/mutasyon.py`.
- Push yok, `main`'e birleştirme yok. Commit mesajı sonu: `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Her commit'ten önce `python uretim/gizlilik_dogrula.py` temiz. Depoya girmez: parola, IP, kişisel yol,
  cihaz adı/seri numarası, keystore, `local.properties`, derleme çıktısı.
- KART: kullanıcı "kart serbest" diyene kadar gerçek karta (`olcum.local`, kartın IP'si, COM6) HİÇ istek yok.
  Serbest olunca bile yasak: `N…`, `E…`, `Q…`, `k…`, `GF!`, `p1`, firmware, seri port.
- TELEFON: adb her zaman `-s <seri>`. Geliştirme telefonu (Xiaomi, API 33): yalnız kendi debug APK'mız
  (`tr.olcumkarti.mobil`) kurulur/kaldırılır; `pm clear`, root, başka uygulama/ayar yok; logcat yalnız kendi
  paketimiz. Yeni telefon (Honor, API 36): her kurulum/testten ÖNCE kullanıcıya sorulur.
- Bağımlılık az ve sabit (`package-lock.json`); CLI'lar proje içinde (`npx`), global kurulum yok.
  Sistem `JAVA_HOME`/`PATH` değiştirilmez (Ş4).
- Ekrana gömülü metin yok: her metin sözlükte (TR + EN). Dokunma alanı ≥ 48 dp.
- Günlükte sır yok (A45, Ş3). Hata metni istisna türünden kurulur.
- Aynı anda en fazla 3–4 ağır ajan; uzun koşular arka planda ve tek seferde (makine paylaşılıyor).
- Her iddianın bir testi ve onu yalanlayan bir mutasyonu (`mobil/mutasyon/liste.mjs`) olur.

## Review Focus

1. **Kart kendi AP'sindeyken telefonun hücresel verisi açık** → istek hücresele gider, kart "yok" görünür.
   Beklenen: istek Wi-Fi ağına bağlı (A4). Test: Görev 4 (bağlama kodu yolu) + cihazda Görev 6.
2. **Aynı ağda `/eslestir/bilgi`'ye yanıt veren başka bir cihaz / eski önbellek IP'si başka cihaza
   geçmiş** → beklenen: kimlik uymayana imzalı istek gitmez (A2). Test: Görev 5.
3. **Elle girilen adres herkese açık bir IP ya da alan adı** → beklenen: ret, açık hata (Ş5). Test: Görev 4.
4. **Sahte kart yavaş / yarım yanıt / bağlantıyı açık bırakıyor** → beklenen: zaman aşımı, keşif takılmaz,
   öteki adaylar yarışı kazanır. Test: Görev 5.
5. **Yanıt gövdesi JSON değil / kimlik 16 onaltılık değil / devasa gövde** → beklenen: ret, çökme yok,
   gövde üst sınırı (A2). Test: Görev 4 (gövde sınırı) + Görev 5.

## Dosya düzeni (bütün dilimler)

```
mobil/
  package.json · package-lock.json · vite.config.js · vitest.config.js · capacitor.config.json
  index.html · .gitignore · DURUM.md · DEVIR-ISTEK.md
  src/
    main.js · App.vue · yonlendirme.js
    cekirdek/            Vue'suz, Node'da sınanır
      ag.js              KartAg sarmalayıcı: fetch-uyumlu `kartFetch`, `p0`, akış
      hedef.js           adres ayrıştırma + "yalnız özel/yerel IP" kuralı (Kotlin ikiziyle aynı vektörler)
      kesif.js           aday yarışı + kimlik doğrulama + IP önbelleği
      kasa.js            (5B) K sarma, sayaç işareti
      kart.js            (5B/5C) bağlantı durum makinesi, imzalı istek, akış
      depo.js            (5D) esitle.js DEPO dosya uygulaması
      bildirim.js        (5E) zarf alma, servis denetimi
      sozluk_mobil.js    telefona özel metinler (TR + EN)
    ekran/               Durum.vue · Canli.vue · Kayitlar.vue · KayitGorunum.vue · Ayarlar.vue · KartBul.vue · Esles.vue
    bilesen/             DurdurDugmesi.vue · GrafikTuval.vue · …
  android/               Capacitor projesi
    app/src/main/java/tr/olcumkarti/mobil/
      MainActivity.kt
      ag/KartAgPlugin.kt · ag/Hedef.kt · ag/HttpIstek.kt · ag/Akis.kt
      kesif/KesifPlugin.kt
      kasa/KasaPlugin.kt            (5B)
      depo/KartDepoPlugin.kt        (5D)
      izleme/…                      (5E) servis, MQTT, zarf, bildirim, iş
      Gunluk.kt
    app/src/test/java/…            JVM birim testleri
  test/
    *.test.js                       vitest
    sahte-kart/sunucu.mjs · sahte-kart/imza_dogrula.mjs
    sahte-araci/…                   (5E)
    vektor/hedef.json               JS ↔ Kotlin ortak vektör
  mutasyon/kos.mjs · mutasyon/liste.mjs
```

## Dilimler

| Dilim | Görevler (özet) | Paralellik | Bitiş ölçütü |
|---|---|---|---|
| **5A** | 1 iskelet + araç zinciri · 2 test altyapısı + mutasyon koşucusu · 3 sahte kart · 4 `KartAg` + hedef kuralı + cleartext ölçümü · 5 keşif · 6 "Kartı bul" ekranı + cihaz duman testi · 7 çürütücü | 2 ∥ 3 (1'den sonra); 4 ve 5 sırayla | Xiaomi'de uygulama sahte kartı buluyor, kimliğini gösteriyor; herkese açık IP reddi yeşil; mutasyonlar ölü |
| Görsel tur | 3 aday (Durum + Canlı + kayıt görünümü; açık/koyu), telefonda | 5B ile paralel | Kullanıcı seçer |
| **5B** | `Kasa` (Keystore AES-GCM sarma) · sayaç işareti (A16, Ş1) · eşleştirme ekranı (A12–A13) · `kart.js` imzalı istek + kimlik (A2) · eşleşmeyi kaldır (A19) · `/saat` (A18) | Kasa ∥ ekran | Sahte kartla eşleşme + imzalı `/kayit/liste`; çökme/saat-geri testleri; Ş1 testi |
| **5C** | Kabuk + sekmeler · `DurdurDugmesi` + `p0` yolu (A8–A11) · akış (A6–A7) · Durum · Canlı | p0 ∥ akış | `p0` kilit tutulurken < 1 s (test); canlı grafik sahte karttan |
| **5D** | `KartDepo` · `depo.js` · eşitleme döngüsü (A20–A23) · Kayıtlar · kayıt görünümü · Worker (A24) · Ö6 aracı (A27) | Kotlin ∥ JS ekran | Sahte karttan eşitlenen dosya bayt bayt; yarım yazma testleri; Ö6 sayısı Xiaomi'de |
| **5E** | MQTT abonesi (Ş2) · zarf (A31–A32) · `Izleme` servisi (A28) · bildirimler (A33–A36, A38) · WorkManager (A29–A30) · izin + üretici yönergesi (A37, Ş6) · sır taraması (Ş3) | MQTT çekirdeği ∥ servis kabuğu | Sahte aracıda vasiyet → bildirim süresi; TLS ret testleri |
| **5F** | Paylaşım (CSV/ham/rapor) · EN · erişilebilirlik · tema | — | — |
| **5G** | Gerçek kart + iki telefon kabulü (spec §6) · release imzası | Kart serbest olunca | Ö3–Ö6, `p0`, Ö4 iki telefonda |

Her dilimin sonunda: bağımsız çürütücü ajan (bulgu = kanıtlı; doğrulanan bulgu önce kırmızı test),
mutasyon koşusu, `DURUM.md` güncellemesi, commit.

---

# 5A — iskelet, sahte kart, ağ, keşif

### Görev 1: İskelet ve araç zinciri ölçümü

**Files:** Create `mobil/package.json`, `mobil/vite.config.js`, `mobil/capacitor.config.json`, `mobil/index.html`,
`mobil/src/main.js`, `mobil/src/App.vue`, `mobil/.gitignore`, `mobil/android/**` (`npx cap add android` üretir).

**Interfaces — Produces:** `npm run build` → `mobil/dist`; `npm run apk` → debug APK
(`android/app/build/outputs/apk/debug/app-debug.apk`); Vite takma adı `@ortak` → `../ortak/src`;
uygulama kimliği `tr.olcumkarti.mobil`, ad "Ölçüm Kartı".

- [ ] 1. `mobil/.gitignore`: `node_modules/`, `dist/`, `android/app/build/`, `android/build/`, `android/.gradle/`,
  `android/local.properties`, `android/app/src/main/assets/public/`, `android/capacitor-cordova-android-plugins/`,
  `*.keystore`, `*.jks`, `*.apk`, `*.aab`, `.env*`.
- [ ] 2. `package.json` (private, `"type":"module"`): bağımlılıklar tam sürümle — `vue`, `vue-router`, `@ionic/vue`,
  `@ionic/vue-router`, `@capacitor/core`, `@capacitor/android` (ikisi 6.2.2); geliştirme: `@capacitor/cli` (6.2.2),
  `vite`, `@vitejs/plugin-vue`, `vitest`. Betikler: `build`, `test`, `test:ortak`
  (`node --test ../ortak/test/`), `mutasyon`, `esitle` (`vite build && cap sync android`), `apk`
  (`cd android && gradlew assembleDebug`). `npm install` → `package-lock.json`.
- [ ] 3. `vite.config.js`: Vue eklentisi, `resolve.alias['@ortak']`, `build.target` WebView 100+, `base: './'`;
  `server.fs.allow` üst klasör (ortak için).
- [ ] 4. En küçük `App.vue`: `IonApp` + tek sayfa; ekranda `@ortak/kripto.js`'den `hex(sha256(utf8Kodla("abc")))`
  (paketlenmiş `ortak/`'ın WebView'de çalıştığının kanıtı; beklenen `ba7816bf…f20015ad`).
- [ ] 5. `npx cap add android`; `capacitor.config.json`: `appId`, `appName`, `webDir: "dist"`,
  `android.allowMixedContent: false`. `variables.gradle`: `minSdkVersion = 28`, compile/target 34.
  Manifest: `allowBackup="false"` (A46).
- [ ] 6. `npm run esitle && npm run apk` — süre ve APK boyutu not edilir. Derleme JDK 17 ile geçmezse:
  yalnız `android/gradle.properties` `org.gradle.java.home` (depoya girmeyen yerel dosyada) — sistem ortamı
  değişmez (Ş4); durum kullanıcıya bildirilir.
- [ ] 7. Xiaomi'ye kur (`adb -s <seri> install -r`), başlat (`am start -n tr.olcumkarti.mobil/.MainActivity`),
  ekran görüntüsüyle SHA-256 satırını doğrula; logcat yalnız `--pid`.
- [ ] 8. `python uretim/gizlilik_dogrula.py`; commit "5A-1: iskelet".

### Görev 2: Test altyapısı ve mutasyon koşucusu

**Files:** Create `mobil/vitest.config.js`, `mobil/test/duman.test.js`, `mobil/mutasyon/kos.mjs`,
`mobil/mutasyon/liste.mjs`, `mobil/test/sozluk.test.js`, `mobil/src/cekirdek/sozluk_mobil.js`.

**Interfaces — Produces:**
- `liste.mjs`: `export default [{ ad, dosya, bul, koy, test }]` — `dosya` `mobil/`'e göreli; `bul` kaynakta
  TAM BİR KEZ geçmeli; `test` vitest dosya yolu ya da `{ komut: [...] }`.
- `kos.mjs [--neden ÖNEK]`: her mutasyon için `mobil/`'i (node_modules, android/build, dist hariç; node_modules
  bağlantı ile) geçici dizine kopyalar, `bul`→`koy` uygular, testi koşar. Çıktı: `ÖLDÜ` (test kırmızı) /
  `YAŞIYOR` (test yeşil → boş iddia, çıkış kodu 1) / `UYGULANAMADI` (desen yok ya da birden çok → çıkış 1).
  Asıl ağaca dokunmaz; geçici dizin `finally` ile silinir.
- `sozluk_mobil.js`: `export const METIN = { tr: {...}, en: {...} }`, `export function cevir(dil, anahtar, degerler)`.

- [ ] 1. Kırmızı: `duman.test.js` — `@ortak/imza.js` içe aktarılır; `uretim/vektor_guvenlik.json`'dan bir
  kanonik metin + imza vektörü `imzala` ile doğrulanır (takma ad ve vektör yolunun çalıştığı kanıtı).
- [ ] 2. `vitest.config.js` (alias, `environment: 'node'`); yeşil.
- [ ] 3. `sozluk.test.js`: TR ve EN anahtar kümeleri eşit; boş değer yok; `src/**/*.vue` şablonlarında
  harf içeren düz metin düğümü yok (yalnız `{{ }}` / `:özellik`), `aria-label="..."` düz metin yok.
- [ ] 4. `kos.mjs` + koşucunun KENDİ testi: (a) bilinen bir sabiti bozan mutasyon ÖLDÜ, (b) yorumu bozan
  mutasyon YAŞIYOR ve çıkış 1, (c) deseni olmayan mutasyon UYGULANAMADI.
- [ ] 5. İlk mutasyonlar: sözlükten EN anahtarı silme → `sozluk.test.js` kırmızı.
- [ ] 6. Commit "5A-2".

### Görev 3: Sahte kart (Node)

**Files:** Create `mobil/test/sahte-kart/sunucu.mjs`, `mobil/test/sahte-kart/imza_dogrula.mjs`,
`mobil/test/sahte-kart.test.js`.

**Interfaces — Produces:**
```js
// sunucu.mjs
export async function sahteKartAc({ port = 0, host = "127.0.0.1", kimlik = "0123456789abcdef",
  parola = "sinama-parolasi-1", tur = 10000, zorunlu = 0 } = {})
// -> { port, taban, kapat(), durum, ayarla(parca) }
// durum: { komutlar: [], imzali: n, ret401: n, cihazlar: Map<n,{K,ad}>, akisAcik: n, acilis }
// ayarla: { gecikmeMs, hata503: adet, yarimYanit: bool, kimlik, yenidenBasla: true, kayitlar: Uint8Array }
```
Uçlar (gerçek kartın davranışı; kaynak `kod/olcum-karti-a3/olcum-karti-a3.ino` salt okunur):
`GET /eslestir/bilgi` · `POST /eslestir/baslat` · `POST /eslestir/kanit` · `GET /akis` (SSE; 4 yuva, 5.'ye
`event: dolu`; 200 ms'de bir `D` satırı; `_c _s _i` imzası) · `POST /komut` (`p0` ve `?` imzasız serbest; ötekiler
imzalı) · `GET /kayit/liste` · `GET /kayit/veri` · `GET /cihaz/liste` · `POST /cihaz/sil` · `POST /saat` ·
`GET /bildirim/bilgi` · `GET /kal/liste`. Kurallar: `Host` yalnız `olcum.local`, `olcum`, bağlanılan IP — yoksa 403;
`X-Olcum` yoksa 403; hiçbir yanıtta `Access-Control-Allow-Origin` yok; 64'lük kayan pencere; 401'de `X-Acilis`;
yanlış kanıtta `2^k` s bekleme (test için ölçeklenebilir).
`imza_dogrula.mjs` imzayı `node:crypto` ile BAĞIMSIZ doğrular (`ortak/src/imza.js`'i içe aktarmaz) — iki
uygulama `uretim/vektor_guvenlik.json` üzerinde uzlaşmalı.

- [ ] 1. Kırmızı testler: `imza_dogrula` vektörleri; `ortak` `esles()` sahte kartla baştan sona (K iki tarafta aynı);
  `ac()` ile imzalı `/kayit/liste`; tekrar oynatma 401; değişik gövde 401; yeniden başlama → `ac()` bir kez yeniden
  dener ve geçer; yabancı `Host` 403; `p0` imzasız 200; 5. akış `dolu`; yanlış parola → ret + bekleme.
- [ ] 2. Uygulama; yeşil.
- [ ] 3. Mutasyonlar: pencere denetimini kaldır → tekrar testi kırmızı; `Host` denetimini kaldır; `p0` serbestliğini kaldır.
- [ ] 4. Commit "5A-3".

### Görev 4: `KartAg` + hedef kuralı + cleartext ölçümü

**Files:** Create `mobil/src/cekirdek/hedef.js`, `mobil/src/cekirdek/ag.js`, `mobil/test/hedef.test.js`,
`mobil/test/ag.test.js`, `mobil/test/vektor/hedef.json`,
`android/.../ag/Hedef.kt`, `ag/HttpIstek.kt`, `ag/KartAgPlugin.kt`, `Gunluk.kt`,
`android/app/src/test/java/tr/olcumkarti/mobil/ag/HedefTest.kt`, `HttpIstekTest.kt`;
Modify `MainActivity.kt` (eklenti kaydı), `AndroidManifest.xml`, `res/xml/network_security_config.xml`.

**Interfaces — Produces:**
```js
// hedef.js
export function hedefAyir(metin)   // "192.168.1.7" | "192.168.1.7:8080" | "olcum.local" | "http://..." ->
                                   // { ad, port } | HedefHatasi (kullanıcı adı, yol, sorgu, IPv6 dışı köşeli vs. ret)
export function ozelAdres(ip)      // true: 10/8, 172.16/12, 192.168/16, 169.254/16; false: gerisi (0.0.0.0, 127/8,
                                   // 100.64/10, çok noktalı/onaltılık/sekizlik yazımlar, IPv6 → false)
export class HedefHatasi extends Error { constructor(tur) }   // tur: "bicim" | "ozel-degil" | "ad-izinsiz"
// ag.js
export function agKur(eklenti)     // eklenti: Capacitor eklentisi ya da testte sahte
// -> { kartFetch(url, {method, headers, body}) -> Response benzeri {status, ok, headers.get(), arrayBuffer(), text()},
//      p0(adresler: string[]) -> {tamam: bool, sureMs, adres|null},
//      akisAc(url, satirGeldi, durumDegisti) -> kapat() }
```
```kotlin
// Hedef.kt — hedef.js ile AYNI vektörler (test/vektor/hedef.json)
object Hedef { fun ozelAdres(ip: String): Boolean; fun ayir(metin: String): HedefSonuc }
// HttpIstek.kt — saf JVM, Android sınıfı yok (birim testinde yerel sunucuya karşı koşar)
class HttpIstek(private val baglantiAc: (URL) -> HttpURLConnection) {
  fun yap(yontem: String, url: String, basliklar: Map<String,String>, govde: ByteArray?,
          zamanAsimiMs: Int, azamiGovde: Int = 64 * 1024): HttpYanit   // HttpYanit(kod, basliklar, govde)
}
// KartAgPlugin.kt — yöntemler: istek, p0, akisAc, akisKapat, wifiDurumu
```
Kurallar: çözülen HER adres `Hedef.ozelAdres` değilse istek atılmaz (`ozel-degil`); ad yalnız `olcum.local`
(çözülür, sonucu yine özel olmalı); yönlendirme izlenmez (`instanceFollowRedirects = false`); vekil yok
(`Proxy.NO_PROXY`); bağlantı etkin Wi-Fi `Network.openConnection` ile, Wi-Fi yoksa `wifi-yok`; gövde üst sınırı
aşılırsa kesilir (`govde-buyuk`); `Host` başlığı ayarlanmaz (URL IP olduğundan kendiliğinden IP). Gövdeler
köprüden base64. Hata, tür adıyla döner (`zaman-asimi`, `baglanti`, `wifi-yok`, `ozel-degil`, `govde-buyuk`,
`cleartext`); istisna mesajı köprüye ve günlüğe GİTMEZ.
Hata ayıklama derlemesine özel: `BuildConfig.DEBUG` iken `127.0.0.1` de kabul (adb reverse ile sahte kart) ve
Wi-Fi bağlaması o adres için atlanır; release'de bu dal YOK (test: `Hedef.ozelAdres("127.0.0.1")` false,
izin yalnız eklentideki `DEBUG` dalında).

- [ ] 1. `hedef.json` vektörleri (≥ 40): özel aralıkların uçları (`10.0.0.0`, `10.255.255.255`, `172.15.255.255` ✗,
  `172.16.0.0`, `172.31.255.255`, `172.32.0.0` ✗, `192.168.0.0`, `192.169.0.0` ✗, `169.254.1.1`), herkese açık
  (`8.8.8.8`, `1.1.1.1`, `100.64.0.1`), tuhaf yazımlar (`192.168.1`, `0300.0250.1.1`, `0xC0A80101`, `3232235777`,
  `192.168.1.1.`, ` 192.168.1.1`, `192.168.1.256`, `::1`, `[::ffff:192.168.1.1]`), adresler
  (`http://192.168.1.5/`, `192.168.1.5:8080`, kullanıcı adı taşıyan adres (`ad` + at işareti + IP; vektör dosyasında parçalardan kurulur — gizlilik denetimi e-posta sanmasın), `192.168.1.5/yol`, `evil.com`,
  `olcum.local`, `OLCUM.LOCAL`, `olcum.local.evil.com`).
- [ ] 2. Kırmızı `hedef.test.js` → `hedef.js` → yeşil. Kırmızı `HedefTest.kt` (aynı JSON'u okur) → `Hedef.kt` → yeşil
  (`gradlew testDebugUnitTest`).
- [ ] 3. `HttpIstekTest.kt`: JDK'nın `com.sun.net.httpserver`'ına karşı — GET/POST gövdesi, başlıklar, 503,
  zaman aşımı (yanıt vermeyen sunucu), gövde sınırı, yönlendirme izlenmiyor (302 → kod 302 döner).
- [ ] 4. `ag.test.js`: sahte eklentiyle — `kartFetch` yanıtı `ortak` `bilgi()`/`ac()`'nin beklediği biçimde
  (Görev 3'ün sahte kartına Node `fetch` üstünden bağlanan köprü-sahtesi ile `esles()` + `ac()` uçtan uca
  `kartFetch` içinden geçer); hata türleri `KartAgHatasi(tur)`.
- [ ] 5. `KartAgPlugin.kt` (`istek`, `wifiDurumu`; `p0` ve `akis*` 5C'de doldurulmak üzere YALNIZ yöntem
  imzası değil — 5A'da yok, 5C görevinde eklenir). Manifest: `INTERNET`, `ACCESS_NETWORK_STATE`,
  `ACCESS_WIFI_STATE`, `CHANGE_NETWORK_STATE`.
- [ ] 6. **Cleartext ölçümü (A5, Ş5)** — Xiaomi'de, sahte kart PC'nin yerel ağ adresinde (Görev 6'nın
  düzeneği): (a) `network_security_config` cleartext KAPALI + yalnız `olcum.local`/`192.168.4.1` izinli iken
  özel IP'ye istek → sonuç kaydedilir; (b) reddediliyorsa ikinci yol: `cleartextTrafficPermitted="true"` +
  yukarıdaki `Hedef` kapısı. Sonuç ve seçilen yol spec A5'e sayılarıyla yazılır.
- [ ] 7. Mutasyonlar: `172.16/12` sınırını `172.0/8` yap; `ozelAdres` denetimini `istek`'ten kaldır; gövde
  sınırını kaldır; yönlendirmeyi aç; hata mesajını köprüye sızdır (test: hata nesnesinde yalnız `tur`).
- [ ] 8. Commit "5A-4".

### Görev 5: Keşif

**Files:** Create `mobil/src/cekirdek/kesif.js`, `mobil/test/kesif.test.js`, `android/.../kesif/KesifPlugin.kt`.

**Interfaces — Consumes:** `agKur().kartFetch`, `hedefAyir`, `ortak` `bilgi`, `bilgiDenetle`.
**Produces:**
```js
export function kesifKur({ kartFetch, onbellek, eklenti, simdi = Date.now, zamanAsimiMs = 1500 })
// onbellek: { oku() -> {adres, kimlik, ms} | null, yaz(kayit) }   (5A'da Capacitor Preferences YOK: localStorage sarmalayıcı)
// eklenti: { nsdTara(sureMs) -> [{ad, ip, port, txt}], coz(ad) -> [ip] }   (yoksa o adaylar atlanır)
// -> { bul({ beklenenKimlik = null, elle = null }) -> { adres, kimlik, bilgi, kaynak } | KesifHatasi(tur, denenenler),
//      adaylar({elle}) -> [{adres, kaynak}] }
// kaynak: "onbellek" | "ad" | "nsd" | "ap" | "elle";  tur: "bulunamadi" | "kimlik-uymuyor" | "wifi-yok"
```
Kurallar (A1–A3): adaylar eşzamanlı yoklanır; `beklenenKimlik` verilmişse kimliği uyan İLK aday kazanır, uymayan
adaylar `kimlik-uymuyor` listesine; hiçbiri uymuyor ama yanıt veren varsa hata `kimlik-uymuyor` (adresleriyle);
`beklenenKimlik` yoksa (eşleşmemiş) öncelik sırası onbellek > ad > nsd > ap > elle değil — **elle verilen her
zaman önce**, sonra yanıt hızı; kimlik `/^[0-9a-f]{16}$/` değilse aday geçersiz; başarıda önbellek yazılır
(adres IP olarak); önbellekteki adres kimlik uymazsa önbellek SİLİNMEZ ama kullanılmaz.

- [ ] 1. Kırmızı testler (sahte kartlar gerçek portlarda, `kartFetch` = Node fetch köprüsü; adaylar test
  enjeksiyonuyla): önbellek kazanır · önbellek ölü → ad/ap · iki kart, yanlış kimlikli önce yanıt veriyor →
  doğru olan seçilir · yalnız yanlış kimlik → `kimlik-uymuyor` · hepsi sessiz → `bulunamadi` ≤ zaman aşımı + 300 ms ·
  biri bağlantıyı açık tutup yanıt vermiyor → ötekini bekletmez · JSON olmayan yanıt / kimlik bozuk / 5 MB gövde →
  aday geçersiz, çökme yok · elle `8.8.8.8` → `HedefHatasi("ozel-degil")`, istek ATILMAZ (sayaçla ölçülür) ·
  NSD eklentisi yok/boş → akış değişmez.
- [ ] 2. `kesif.js`; yeşil.
- [ ] 3. `KesifPlugin.kt`: `nsdTara` (`NsdManager`, `_http._tcp.`, ad `olcum*`; TXT `kimlik` varsa döner),
  `coz` (Wi-Fi `Network.getAllByName`), izin gerekmez (API 33'e kadar; API 34+ NSD için izin gerekmez).
- [ ] 4. Mutasyonlar: kimlik karşılaştırmasını kaldır; elle adresin hedef denetimini kaldır; zaman aşımını kaldır.
- [ ] 5. Commit "5A-5".

### Görev 6: "Kartı bul" ekranı ve cihaz duman testi

**Files:** Create `mobil/src/ekran/KartBul.vue`, `mobil/src/yonlendirme.js`; Modify `App.vue`, `sozluk_mobil.js`.

- [ ] 1. Ekran (geçici, sade; görsel tur sonra): "Ara" düğmesi, elle adres alanı, sonuç (kimlik, firmware,
  kaynak, süre), hata türüne göre sözlükten metin. Dokunma alanları ≥ 48 dp. Sözlük testi yeşil.
- [ ] 2. Düzenek A (adb reverse, ağsız): PC'de `node test/sahte-kart/sunucu.mjs --port 18080`;
  `adb -s <Xiaomi> reverse tcp:18080 tcp:18080`; uygulamada elle `127.0.0.1:18080` (yalnız debug) → bulundu.
- [ ] 3. Düzenek B (gerçek Wi-Fi yolu, cleartext ölçümü için): sahte kart PC'nin yerel ağ adresinde. Windows
  güvenlik duvarı gelen bağlantıyı engelliyorsa güvenlik duvarı DEĞİŞTİRİLMEZ — kullanıcıya sorulur.
- [ ] 4. Kayıt: bulma süresi, logcat'te (yalnız kendi PID) sır/adres taraması, ekran görüntüsü.
- [ ] 5. `DURUM.md`; commit "5A-6".

### Görev 7: Bağımsız çürütücü

- [ ] Yeni bir ajan (yüksek düzey), yalnız 5A'nın diff'i + spec ile: hedef kuralını atlatma (DNS'in herkese açık
  IP döndürmesi, yönlendirme, tuhaf IP yazımı, `olcum.local` taklidi), keşifte yanlış karta bağlanma, köprüden sır
  sızması, mutasyon koşucusunun yalancı "ÖLDÜ" vermesi. Bulgu = çalışan kanıt (kırmızı test). Doğrulanan her bulgu
  önce kırmızı test, sonra düzeltme, sonra mutasyon.
