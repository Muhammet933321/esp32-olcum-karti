# 5E / 5F bağımsız çürütücü — bulgular (2026-10-05)

Kapsam: bildirim tarafı (Kotlin `bildirim/*`, `paylas/*`, manifest, `file_paths.xml`; JS `bildirim.js`,
`paylas.js`, `rapor_metin.js`, `kayit_veri.js`, `kayitlar.js`, `bildirim_gorunum.js`, `BildirimAyar.vue`,
`KayitDugmesi.vue`, `kabuk_durum.js`, `uygulama.js`). Kod DÜZELTİLMEDİ; yalnız bu dizine dosya yazıldı.
Karta, telefona, gerçek aracıya bağlanılmadı.

**Sonuç:** 21 bulgu — **1 yüksek, 9 orta, 11 düşük** (kritik yok). 16'sı çalıştırılabilir kırmızı testle
(11 Kotlin + 5 JS), 5'i Android'e özgü olduğu için kaynak okumasıyla. 57 yeni mutasyon elle denendi:
**21'i yaşıyor**. Sır sızıntısı, TLS zorunluluğu, "yalnız abone", zarf / AAD ve CSV formül koruması
çürütülemedi.

## Kanıtlar nasıl koşulur

```
# JS (bulgu VARKEN kırmızı: 6 test kırmızı, 1 yeşil)
cd mobil && npx vitest run test/curutucu-5e

# Kotlin (11 test, 11'i kırmızı). Dosya GEÇİCİ kopyalanır, koşulur, silinir:
cd mobil
cp test/curutucu-5e/kotlin/Curutucu5eTest.kt android/app/src/test/java/tr/olcumkarti/mobil/bildirim/
(cd android && ./gradlew testDebugUnitTest --tests "tr.olcumkarti.mobil.bildirim.Curutucu5eTest")
rm android/app/src/test/java/tr/olcumkarti/mobil/bildirim/Curutucu5eTest.kt
```

⚠ `vitest.config.js` `test/**/*.test.js`'i kapsadığı için `npx vitest run` artık **6 kırmızı** verir
(`test/curutucu-5e/izleyici-kenar.test.js` 4, `rapor-kenar.test.js` 2). Bulgular kapanınca yeşile dönerler;
o zamana dek öbür testleri `--exclude 'test/curutucu-5e/**'` ile koş (559/559 yeşil — ölçüldü).

| Kanıt dosyası | İçerik |
|---|---|
| `kotlin/Curutucu5eTest.kt` | B1–B11 (`b1_…` … `b11_…`) |
| `izleyici-kenar.test.js` | B12–B15 |
| `rapor-kenar.test.js` | B16 + çürütülemeyen CSV formül koruması (yeşil) |
| `yasayan-liste.mjs` | Yaşayan 21 mutasyon (`mobil/mutasyon/*-liste.mjs` biçiminde) |

---

## Bulgular — çalıştırılabilir kanıtlı

### B1 · orta · 15 dakikalık yoklama eskimiş bildirim anahtarını HİÇ fark etmez
- **Yer:** `bildirim/Izleyici.kt:100` (`cozulen == 0 && atilan >= ATILAN_SINIR`), `:106` (tek seferlik kapanış);
  `bildirim/YoklamaIsi.kt:44–52`.
- **Neden yanlış:** "anahtar eskidi" kararı 3 atılan mesaj ister. Tek seferlik oturumda aracı yalnız BİR
  kalıcı mesaj (`durum`) yollar; sayaç 1'de kalır, oturum 20 s sonra `sure` (sınıf `tamam`) ile biter.
  `YoklamaIsi` `okunan == null` görür, hiçbir şey yapmaz. A31'in "çözme hatası → bildirim ayarı yenilenmeli"
  yolu yoklamada işlemez.
- **Senaryo:** kartta bildirim anahtarı yenilendi (`QR!`), kullanıcı uygulamayı kartın ağında açmadı. Anlık
  izleme kapalı (VARSAYILAN). → Yoklama her 15 dakikada 20 s bağlanır, mesajı atar, susar. Kayıt bitti /
  karttan haber yok bildirimi sonsuza dek gelmez; "ayar yenilenmeli" de gelmez.
- **Kanıt:** `b1_yoklama_eskimisAnahtarla_ayarYenilenmeliDemeli` → `expected:<[ayar]> but was:<[tamam]>` (tur=sure).
- **Yön:** tek seferlik kipte çözülemeyen kalıcı durumu ayrı say (ör. atılan sayısını yoklamalar arasında
  özet dosyasında biriktir; N yoklamadır çözülemiyorsa "ayar").

### B2 · orta · Aracıya yazabilen biri üç çöp mesajla izlemeyi KALICI olarak "ayar"a düşürür
- **Yer:** `bildirim/Izleyici.kt:97–101`; sonuç `IzlemeDongusu.kt:36` (`"ayar" -> return "ayar"`),
  `YoklamaIsi.kt:51` (`ayarYenile(); continue`).
- **Neden yanlış:** sayaç "henüz hiç mesaj çözülmedi" koşuluna bağlı. `ok/<önek>/x1…x3` konularına bırakılmış
  KALICI çöp mesajlar her abonelikte geçerli `durum`'dan önce gelebilir (kalıcı mesaj sırası aracıya bağlı;
  saldırgan alfabetik olarak hem öne hem arkaya koyabilir). Uçtan uca şifrelemenin amacı aracıya güvenmemekti;
  burada aracı hesabını bilen biri (kart, PC ve telefon AYNI hesabı kullanıyor) yalnız "mesaj düşürmekle"
  kalmaz: servis durur, "Bildirim ayarı yenilenmeli" çıkar ve zarf dosyası değişmeden bir daha denenmez;
  yoklama da her turda aynı yere düşer.
- **Senaryo:** 3 kalıcı çöp + geçerli kalıcı durum → oturum `anahtar`, `cozulen = 0`; geçerli durum işlenmez.
- **Kanıt:** `b2_ucSahteMesaj_gecerliDurumdanOnceGelirse_izlemeAyaraDusmemeli` → `Actual: anahtar`.
- **Yön:** kararı yalnız BİLİNEN konulara (`durum`, `olay`) gelen mesajlardan ver; bilinmeyen alt konuyu
  sayma. Kalıcı `durum` çözülmeden "anahtar" deme; "ayar" bitişini kalıcı durdurma yerine seyrek yeniden dene.

### B3 · orta · Kart her yeniden başladığında ilk izlenen kayıtta SAHTE "1 olay kaçırıldı"
- **Yer:** `bildirim/BildirimKarar.kt:194–211` (`bosluk`; `:203` `else n - 1`).
- **Neden yanlış:** mantık PC'den birebir taşındı, ama PC köprüsü sürekli bağlı; telefonda servis YALNIZ kayıt
  sürerken çalışıyor. Kart her açılışta `n=1` "basladi" (`devam=0`) yayınlar (`kod/olcum-karti-a3/bildirim.h:296`,
  sayaç `:211`'de 1'den başlar); bu olayın bildirimi yoktur ve servis onu hiç göremez. Servisin gördüğü ilk
  olay `n=2` olur → `eksik = n - 1 = 1` → "1 olay kaçırıldı (bu telefon bağlı değilken)".
- **Senaryo:** önceki izleme `(a=3, n=2)` kaydetti; kart kapatılıp açıldı (`a=4`); kullanıcı kayıt başlattı,
  kayıt bitti (`n=2`). → Doğru "kayıt bitti" bildirimiyle birlikte `kacirilan` sınıfında yanlış alarm. Kartın
  her güç çevriminden sonraki ilk kayıtta yinelenir. Aynı şey, arada servissiz (yoklamayla bildirilmiş) bir
  kayıt bittiğinde de olur: kullanıcı o bildirimi almıştı, yine "kaçırıldı" denir.
- **Kanıt:** `b3_yeniAcilistaIlkIzlenenKayit_kacirilanBildirimiCikmamali` → `but was:<[bld.kacirilan]>`.
- **Yön:** telefonda boşluk sayımı servisin BAĞLI olduğu aralıkla sınırlansın (oturum içi boşluk); ya da yeni
  açılışın `n=1`'i (bildirimsiz "basladi") sayılmasın. PC davranışı değişmek zorunda değil.

### B4 · orta · Yoklama, servisin YEREL yoldan bildirdiği "kayıt bitti"yi 15 dakika sonra yineler
- **Yer:** `bildirim/IzlemeServisi.kt:117` (özet yalnız `durumGoruldu`'da, yani MQTT durum mesajında yazılır);
  `bildirim/Yoklama.kt:45–63`.
- **Neden yanlış:** iddia "yoklama servisin bildirdiğini yinelemez". Bitiş yerel akıştan (`yerelG`) duyulduysa
  servis bildirir, `kayitSuruyor() == false` olur ve 10 s sonra kendini durdurur; kartın MQTT durum mesajı bu
  10 s içinde gelmediyse (ev interneti kesik — A36'nın tam senaryosu — ya da kart → aracı yolu yavaş) özet
  "kayıt sürüyor"da kalır.
- **Senaryo:** özet `{k:2,o:81}`; uygulama önde, kayıt bitti → servis `os-51` "kayıt bitti" gösterdi ve durdu.
  Sonraki yoklama `{k:1,o:0}` okur → aynı etiketle, SESLİ, ikinci "kayıt bitti (oturum 81)".
- **Kanıt:** `b4_servisinYerelYoldanBildirdigiBitis_yoklamadaYinelenmemeli` →
  `but was:<[os-51:bld.kayit_bitti_yerel]>`.
- **Yön:** servis yerel haberden bildirim ürettiğinde de özeti güncellesin (ya da "bildirilen son oturum"u
  özete yazsın, yoklama onu atlasın).

### B5 · YÜKSEK · Aracıya ulaşılamıyorken servis, kayıt bitse de kendini durdurmaz (A28)
- **Yer:** `bildirim/Izleyici.kt:115–117` (`surdur` yalnız MQTT döngüsünün tikinde sorulur);
  `bildirim/IzlemeDongusu.kt:30–42` (bağlı değilken kayıt durumuna bakan kod yok); `IzlemeServisi.kt:115`.
- **Neden yanlış:** A28 "kayıt bitince servis kendini durdurur" diyor. Durdurma kararı yalnız aracıya BAĞLI
  bir oturumun içinde veriliyor. Oturum `ag` / `koptu` / `tls` ile bitiyorsa döngü 2 s … 60 s (güvende 15 dk)
  aralıklarla sonsuza dek yeniden dener; karar katmanı "kayıt bitti"yi (yerel akıştan) bilse de sorulmaz.
- **Senaryo:** telefon kartın kendi AP'sinde ya da interneti yok; anlık izleme açık (ya da soruya "aç" dendi).
  Servis başlar ("Telefonun interneti yok — kart izlenemiyor"), kayıt biter, uygulama bunu yerel akıştan
  görür ve servise iletir → kalıcı bildirim ve yeniden bağlanma denemeleri internet gelene dek sürer (saatler /
  günler). Bu sürede `YoklamaIsi` de çalışmaz (`calisanKimlik != null` → dönüş).
- **Kanıt:** `b5_internetYokkenKayitBittiyse_donguBitmeli` (servisteki oturum lambdasının aynısı, gerçek
  `Izleyici` + `IzlemeDongusu`) → `expected:<[kayit-bitti]> but was:<[50 denemeden sonra hala donuyor]>`.
- **Yan etki (aynı kök):** `karar.tik()` de yalnız bağlıyken çağrılıyor; PC'de saniyede bir, koşulsuz.
- **Yön:** `IzlemeDongusu` her turda (ve beklemeden önce) `surdur`'u sorsun; `tik` bağlantıdan bağımsız dönsün.

### B6 · düşük · SUBACK'ten önce gelen PUBLISH'ler sınırsız biriktirilir
- **Yer:** `bildirim/MqttIstemci.kt:81–92` (`bekleyenYayin`).
- **Neden yanlış:** iddia "bozuk / dev paket … bellek şişirmez". Tek paket 16 KiB ile sınırlı, ama SUBACK
  beklenirken (10 s) gelen yayınların ADEDİ sınırsız; hepsi listede tutulur.
- **Senaryo:** aracı (ya da TLS'i sonlandıran taraf) SUBACK yollamadan yayın akıtır.
- **Kanıt:** `b6_subacktenOnceYayinSeli_bellektekiBirikimSinirliOlmali` → `SUBACK beklenirken 39507 KiB yayin
  biriktirildi` (sanal saatle; gerçek hatta üst sınır bant genişliği × 10 s).
- **Yön:** bekleyen yayın sayısına / toplam bayta sınır; aşılırsa `bicim`.

### B7 · düşük · Ayrıştırıcı, sınırın ALTINDAKİ paketlerden oluşan geçerli akışı "buyuk" diye reddeder
- **Yer:** `bildirim/MqttPaket.kt:133–140` (`besle`: `boy + n > azami + 5`).
- **Neden yanlış:** tampon sınırı "tek paket" için düşünülmüş, ama okuma 4096'lık parçalarla geliyor; büyük bir
  paketin sonu ile sonrakinin başı aynı okumada gelince `boy + n` sınırı aşar.
- **Senaryo:** arka arkaya iki tam 16384 baytlık yayın → 16384. baytta `MqttHatasi("buyuk")`, hiç paket
  çözülmeden. (Bizim yüklerimiz küçük; gerçek hayatta ancak yabancı / büyük mesajla görülür.)
- **Kanıt:** `b7_azamiBoydaIkiPaket_4096lukOkumalarla_buyukDenmemeli`.
- **Yön:** sınırı tampona değil pakete uygula (başlık çözülünce `u.first > azami`), tampon `azami + 5 + okuma boyu`.

### B8 · düşük · `adresYaz`'ın kabul ettiği adresi `adresOku` okuyamaz
- **Yer:** `bildirim/BildirimDeposu.kt:86–90` (boy denetimi yok, HAM metin yazılır) ↔ `:80` (`> ADRES_AZAMI` → null).
- **Neden yanlış:** `Hedef.ayir` `http://` önekini, sondaki `/`'yi ve baştaki / sondaki boşluğu kabul eder;
  yazım "yazıldı" döner ama dosya 21 baytı aşınca okuma null verir → A36 sessizce devre dışı.
- **Senaryo:** `adresYaz("http://192.168.100.100:8080")` → hata yok; `adresOku` → `null`.
  (Bugün JS çıplak `ip:port` ve ≤ 21 karakter yolluyor; kusur Kotlin kapısının kendi içinde tutarsız olması.)
- **Kanıt:** `b8_yazilanAdres_okunabilmeli` → `yazilan adres okunamiyor: boy 27`.
- **Yön:** yazarken `Hedef.ayir` sonucunu ("ip:port") yaz; ya da yazımda da aynı boy sınırı.

### B9 · düşük · "Katı" JSON okuyucu `\u` kaçışında ASCII olmayan rakamları kabul eder
- **Yer:** `bildirim/DuzJson.kt:116` (`Character.digit(ch, 16)` Unicode rakamlarını da çözer).
- **Senaryo:** `"\u` + Arap-Hint `٠٠٤١` + `"` → `"A"`. Python ve JS çözücüleri reddeder; "aynı mesaj üç yerde
  aynı okunur" varsayımı bozulur (yük kimlik doğrulamalı olduğu için istismar yolu yok).
- **Kanıt:** `b9_json_uKacisindaYalnizAsciiOnaltilik` → `expected:<null> but was:<A>`.
- **Yön:** `0-9a-fA-F` aralığını elle denetle.

### B10 · düşük · Yoklama, `k` / `o` alanı eksik bir durum mesajında "kayıt bitti"yi sessizce kaybeder
- **Yer:** `bildirim/Yoklama.kt:59–61` (`yerel` erken döner, özet yine de yeni mesajla EZİLİR), `:75–79`.
- **Senaryo:** özet `{k:2,o:81}`; okunan `{c:1,a:3,t:…}` (k, o yok) → bildirim yok, özet artık kayıt durumu
  taşımıyor; sonraki `{k:1,o:0}` yoklamasında da bildirim yok. Kartın bugünkü firmware'i alanları hep yollar;
  kusur "bozuk / eksik alanlı özet" sorusunun cevabı.
- **Kanıt:** `b10_eksikAlanliDurum_kayitDurumuOzettenSilinmemeli` → `expected:<[os-51]> but was:<[]>`.
- **Yön:** `k` / `o` tamsayı değilse özeti DEĞİŞTİRME (okunamadı say).

### B11 · düşük · Canlı akış sürerken 20 s sonra sahte "Karttan haber yok … yerel bağlantı da koptu"
- **Yer:** `bildirim/BildirimKarar.kt:97–113` (`tik`, `yerelYol`), `bildirim/IzlemeServisi.kt:55–62`,
  `src/cekirdek/bildirim.js:209–217`.
- **Neden yanlış:** PC'de HER kart satırı `yerelSon`'u tazeler (`pc_bildirim.py` `yerel_satir`); telefonda
  servise yalnız G satırı DEĞİŞİNCE haber gider. Aracı bağlıyken kalıcı durum henüz yok / gelmediyse
  (`kartCevrimici == null`) son yerel haberden 20 s sonra `tik` "yerel yol sessiz" der.
- **Senaryo:** aracıda kalıcı durum mesajı yok (aracı sıfırlandı, kart henüz yayınlamadı — kart durumu 60 s'de
  bir yeniler); uygulama önde, kayıt sürüyor. → 20. saniyede `bld.kopuk_yerel` (uyarı kanalı, sesli).
- **Kanıt:** `b11_kaliciDurumYokken_yerelGdenYirmiSaniyeSonra_kopukDenmemeli` → `but was:<[bld.kopuk_yerel]>`.
- **Yön:** telefonda yerel yol kopukluğu ya hiç kullanılmasın ya da WebView akış canlıyken düzenli
  `yerelGoruldu` yollasın.

### B12 · orta · Zarf yenilemesi geçici hatada o bağlantı boyunca bir daha denenmez
- **Yer:** `src/cekirdek/bildirim.js:202–208` (yalnız `!oncekiBagli` iken), `:211` (`g === sonG` → izleme de
  yeniden denenmez).
- **Senaryo:** bağlanınca `GET /bildirim/bilgi` bir kez `ag` ile düştü (kart meşgul / zaman aşımı). Kayıt
  sürüyor: `izlemeBaslat` → `zarf-yok`. 60 s bağlı kalınsa da ne zarf yeniden istenir ne izleme yeniden
  denenir; `son()` "ag"da kalır. Ancak bağlantı kopup gelirse ya da kullanıcı elle "Karttan yenile" derse düzelir.
- **Kanıt:** `izleyici-kenar.test.js` B12 → `expected 'ag' to be 'yazildi'`.
- **Yön:** yenileme başarısızsa aralıkla yeniden dene; zarf yazılınca süren kayıt için izlemeyi yeniden başlat.

### B13 · düşük · Servis ayağa kalkmadan iletilen yerel durum kaybolur ve bir daha iletilmez
- **Yer:** `src/cekirdek/bildirim.js:211–217` (`iletildi` sonucuna bakılmıyor, `sonG` önceden yazılıyor);
  `bildirim/IzlemeServisi.kt:230–231` (`calisanKimlik != kimlik` → sessiz dönüş; `calisanKimlik` ancak
  `onStartCommand`'da, ana iş parçacığında atanır — `:80`).
- **Neden yanlış:** `izlemeBaslat` `startForegroundService` döner dönmez çözülür; hemen ardından gelen `yerel`
  çoğunlukla servis henüz `onStartCommand`'a girmeden eklentiye ulaşır ve düşer. `bekleyenYerel` yalnız
  "`onStartCommand` çalıştı ama karar kurulmadı" penceresini kapsıyor. Sonuç: servis başlangıç `(durum, oturum)`
  çiftini bilmez → kayıt bitince `yerelG`'nin ilk çağrısı "önceki yok" diye bildirim üretmez (A35'in yerel
  yolu ölü); kart → aracı yolu kesikse "kayıt bitti" hiç gelmez.
- **Kanıt:** JS yarısı `izleyici-kenar.test.js` B13 (iletilmediği bildirilen durum sonraki tiklerde yeniden
  yollanmıyor). Kotlin yarısı: **kanıt: kaynak okuması** (Android servisi JVM'de koşmaz).
- **Yön:** `iletildi === false` ise `sonG`'yi geri al; ya da eklenti servisi başlatırken ilk durumu Intent'e koysun.

### B14 · düşük · Bağlantı kopmadan kart değişirse yeni kartın zarfı / adresi / durumu işlenmez
- **Yer:** `src/cekirdek/bildirim.js:197–212` (`oncekiBagli` ve `sonG` kimliğe bağlı değil).
- **Senaryo:** iki ardışık tikte `bagli: true` ama kimlik farklı (elle başka adrese bağlanma 1 s'den kısa
  sürerse): yeni kart için `adresYaz` / `yenile` çağrılmaz; G satırı aynıysa `yerel` de gitmez.
- **Kanıt:** `izleyici-kenar.test.js` B14 → `expected 1 to be 2`.
- **Yön:** durumu `kimlik` ile anahtarla.

### B15 · düşük · "Aç" işlemi sürerken kayıt biterse izleme yine başlatılır
- **Yer:** `src/cekirdek/bildirim.js:160–171` (`k === kusak` yalnız sonucu YAZARKEN denetleniyor, `:168`'den önce değil).
- **Senaryo:** soru → "Aç" → Android'in izin penceresi açık; o sırada kayıt biter (`kayitBitti`); kullanıcı
  pencereyi kapatır → `izlemeBaslat({ buKayit: true })` bitmiş kayıt için çağrılır (servis ~10 s yaşar ya da
  B5'e düşer).
- **Kanıt:** `izleyici-kenar.test.js` B15.
- **Yön:** her `await`'ten sonra kuşağı denetle.

### B16 · düşük · Rapor metninde satır sonu içeren değer rapora SAHTE satır sokar
- **Yer:** `src/cekirdek/rapor_metin.js:42` (`return String(v)`).
- **Senaryo:** not `"olcum tamam\nKalibrasyon: no 7 (onayli)\nUyari: yok"` → paylaşılan `.txt` raporda sütun
  0'da iki uydurma "alan: değer" satırı. Kart komut satırından satır sonu geçmez, ama not baytları kayıt
  dosyasından gelir (içe alınmış / başka kaynaktan `.kyt`).
- **Kanıt:** `rapor-kenar.test.js` B16 (iki test).
- **Yön:** metin değerlerinde `\r` / `\n`'yi boşluğa ya da görünür kaçışa çevir; devam satırını girintile.

---

## Bulgular — Android'e özgü (kanıt: kaynak okuması)

Bunlar `Service` / `Worker` / `Plugin` sınıflarında; JVM birim testinde koşmuyor. Her biri için satır, neden ve
senaryo verildi; cihazda doğrulanmalı.

### B17 · orta · Başlat → durdur hızlı gelirse izleme iş parçacığı servis öldükten sonra YAŞAR
- **Yer:** `bildirim/IzlemeServisi.kt:126` (`dongu = d` iş parçacığında, geç atanıyor) ↔ `:187–189`
  (`onDestroy`: `dongu?.durdur()` — `dongu` hâlâ null ise hiçbir şey durdurulmaz) ↔ `:113`
  (`if (dongu == null) i.durdur()` — atamadan SONRA `dongu` null değildir).
- **Senaryo:** `onStartCommand` iş parçacığını başlatır; iş parçacığı kasa / özet dosyalarını okurken
  (`:90–102`) `stopService` gelir (ör. `ayarYaz({anlik:false})` — `BildirimPlugin.kt:134`) ve `onDestroy` çalışır. Sonra iş
  parçacığı `dongu = d` yapar, `yerelYoklamayiBaslat` yeni bir zamanlayıcı kurar (`onDestroy` onu artık
  kapatamaz) ve `d.calis()` döner: aracıya bağlanır, bildirim gösterir, `izlemeGuncelle` ile "izleniyor"
  kalıcı bildirimini servissiz yeniden asar. `calisanKimlik == null` olduğu için eklenti "çalışmıyor" der;
  yeni bir başlatma İKİNCİ bir izleyici açar (çift bildirim). Kayıt bitene (ya da süreç ölene) dek sürer.
- **Yön:** `dongu`'yu iş parçacığını başlatmadan önce kur ya da tek bir `@Volatile durduruldu` bayrağını
  `calis` her adımda denetlesin; `onDestroy` iş parçacığını beklesin.

### B18 · orta · Servis bir kartı izlerken başka kart için `izlemeBaslat` "başladı" der ama hiçbir şey olmaz; yoklama da öbür kartları atlar
- **Yer:** `bildirim/BildirimPlugin.kt:184–191` (`calisanKimlik == kimlik` değilse `baslat`, dönüş
  `basladi: true`) ↔ `bildirim/IzlemeServisi.kt:66` (`if (is_ != null) return` — kimliğe bakılmıyor);
  `bildirim/YoklamaIsi.kt:33` (`calisanKimlik != null` → BÜTÜN kartlar için dönüş).
- **Senaryo:** iki eşleşmiş kart. A izlenirken B'de kayıt başlatılır, soruya "Aç" denir → ekranda "açıldı",
  servis hâlâ A'yı izliyor. A izlendiği sürece B için 15 dakikalık yoklama da hiç çalışmaz: B'nin "kayıt
  bitti"si / "karttan haber yok"u gelmez. (Bildirim etiketleri `baglanti`, `os-<oturum>` kart kimliği
  taşımadığı için iki kartın bildirimleri de birbirini ezer.)
- **Yön:** servis kimlik değişimini ele alsın (reddet + `neden: "baska-kart"` ya da yeniden başlat); yoklama
  yalnız İZLENEN kimliği atlasın.

### B19 · orta · Çalışan servis ayar değişikliğini görmez: kapatılan sınıf bildirilmeye devam eder
- **Yer:** `bildirim/IzlemeServisi.kt:68` (ayar `onStartCommand`'da BİR kez okunur) → `:96`
  (`acik = { ayar.acik(it) }`), `:69` (dil); `bildirim/BildirimPlugin.kt:125–136` (yazım servise haber vermez).
- **Senaryo:** izleme sürerken Ayarlar › Bildirimler'de "eşik" (ya da başka sınıf) kapatılır → ekran "kapalı"
  der, servis o kayıt bitene dek aynı sınıfı göstermeyi sürdürür. Dil değişikliği de yansımaz (A38, A42).
- **Yön:** `acik` her soruda ayar dosyasını (ya da bellekteki güncel kopyayı) okusun.

### B20 · orta · Eşleşme kaldırılınca çalışan servis durdurulmaz
- **Yer:** `src/cekirdek/kart.js:243–261` ve `src/ekran/Baglanti.vue:64–70` (yalnız `kasa.sil`; `izlemeDurdur`
  hiçbir yerden çağrılmıyor — `grep izlemeDurdur src` yalnız tanımı buluyor); `bildirim/IzlemeServisi.kt:106–109`.
- **Senaryo:** izleme sürerken "eşleşmeyi kaldır". Çözülmüş aracı bilgisi oturum boyunca bellekte olduğu için
  servis kaldırılmış kartı izlemeyi ve bildirim göstermeyi sürdürür; `olayYaz` / `durumYaz` silinen
  `<kimlik>.olay` / `.durum` dosyalarını YENİDEN oluşturur ("`KasaDeposu.sil` hepsini siler" iddiası kalıcı
  olmaz). Bağlantı ilk koptuğunda oturum `zarf` ile biter ve kaldırılmış kart için "Bildirim ayarı yenilenmeli —
  uygulamayı kartın ağında aç" bildirimi çıkar.
- **Yön:** kasa silme yolunda (Kotlin tarafında, tek yerde) o kimliği izleyen servisi durdur.

### B21 · düşük · Zarf dosyası yokken K bellekte sıfırlanmadan bırakılır
- **Yer:** `bildirim/IzlemeServisi.kt:107–109`: `kayit` okunur; `zarf == null` ise `IzlemeBitis("zarf")` döner,
  `kayit.anahtar.fill(0)` yalnız `else` dalının `finally`'sinde (`:120`).
- **Senaryo:** zarf silinmiş (404 → `zarfSil`) ama anahtar duruyor; servis başlatılır → K çöp toplayıcıya kalır.
  "Anahtar dizileri çıkışta sıfırlanır (hata yollarında da)" iddiasının tutmadığı tek yol.
- **Yön:** `kayit`'i `try/finally` içine al ya da önce zarfı denetle.

---

## Yaşayan mutasyonlar

Yöntem: kaynak GEÇİCİ değiştirildi → test koşuldu → kaynak aynen geri yazıldı (her adımda bayt karşılaştırması).
Kotlin: `./gradlew testDebugUnitTest -q` (bütün JVM testleri). JS: `npx vitest run --exclude 'test/curutucu-5e/**'`.
Denenen 57 (Kotlin 32, JS 25); **yaşayan 21** (`yasayan-liste.mjs`'te `bul` / `koy` tam dizgileriyle).

| # | Dosya | Bul → koy (özet) | Koşulan | Sonuç |
|---|---|---|---|---|
| K01 | `Izleyici.kt` | `bilgi.anahtar.fill(0)` → (yok) | gradle, tümü | YEŞİL — "anahtar çıkışta sıfırlanır" hiçbir testle ölçülmüyor |
| K05 | `MqttIstemci.kt` | `if (c.first shr 4 != CONNACK) return bicim` → (yok) | gradle | YEŞİL |
| K09 | `Izleyici.kt` | `if (kalan == "durum") durumGoruldu(icerik)` → `durumGoruldu(icerik)` | gradle | YEŞİL — yoklama bir OLAY mesajını durum sanabilir |
| K14 | `BildirimDeposu.kt` | `adresOku` boy sınırı → (yok) | gradle | YEŞİL |
| K16 | `BildirimDeposu.kt` | `BildirimAyar.oku` `length() <= 1024` → (yok) | gradle | YEŞİL |
| K18 | `BildirimDeposu.kt` | `"redmi" / "poco"` → (yok) | gradle | YEŞİL — geliştirme telefonu Redmi; marka alanı sınanmıyor |
| K20 | `TlsBaglanti.kt` | `soket.soTimeout = BAGLANTI_MS` → (yok) | gradle | YEŞİL — susan sunucuda el sıkışma sonsuza dek bekler |
| K21 | `TlsBaglanti.kt` | `connect(adres, BAGLANTI_MS)` → `connect(adres)` | gradle | YEŞİL |
| K26 | `Zarf.kt` | `anahtar.size != ANAHTAR \|\|` → (yok) | gradle | YEŞİL |
| K32 | `Izleyici.kt` | `istemci = null` (finally) → (yok) | gradle | YEŞİL (gözlenebilir etkisi küçük) |
| J02 | `bildirim.js` | `kayitBasladi`: `k !== kusak \|\|` → (yok) | vitest | YEŞİL — biten kaydın sorusu sonradan çıkar |
| J03 | `bildirim.js` | `kayitBasladi` başındaki `yay("yok")` → (yok) | vitest | YEŞİL |
| J05 | `bildirim.js` | `calisiyor: y.calisiyor === true` → `Boolean(…)` | vitest | YEŞİL |
| J06 | `bildirim.js` | `zarf: y.zarf === true` → `Boolean(…)` | vitest | YEŞİL |
| J09 | `bildirim.js` | `hayir`: `if (hal === "soruluyor")` → (yok) | vitest | YEŞİL — "hayır" açılmış izlemenin sonucunu siler |
| J11 | `bildirim.js` | `neden` süzgeci → `neden: y.neden` | vitest | YEŞİL |
| J12 | `bildirim.js` | `.iletildi === true` → `.iletildi` | vitest | YEŞİL |
| J13 | `rapor_metin.js` | kodsuz değerde `metin` → hep `metin (kod)` | vitest | YEŞİL — "… (null)" yazar |
| J15 | `rapor_metin.js` | `\|\| v === ""` → (yok) | vitest | YEŞİL |
| J18 | `kayitlar.js` | `TextDecoder(…, { fatal: true })` → `TextDecoder("utf-8")` | vitest | YEŞİL |
| J23 | `BildirimAyar.vue` | `if (!mesgul.value) oku()` → `oku()` | vitest | YEŞİL |

**Ölen 36** (testler ısırıyor): K02 anahtar hex biçimi · K03 konu boyu · K04 SUBACK paket no · K06 el sıkışma
süresi · K07 `GEREKSIZ_MS` · K08 internet bekleme tavanı · K10 `t <= 0` · K11 yerel → kopuk ikinci bildirim ·
K12 `maxOf(once, n)` · K13 `bs-` etiketi · K15 `kimlikler` süzgeci · K17 eşik kanalı · K19 port aralığı ·
K22 `\/` kaçışı · K23 paylaşım adının ilk karakteri · K24 MIME kümesi · K25 / K30 yerel pencereler · K27 kısa
zarf · K28 / K29 bitiş sınıfları · K31 sessizlik eşiği · J01 zarf alt sınırı · J04 `pilMuaf` · J07
`cihaz-silinmis` · J08 kimlik biçimi · J10 `sonG` sıfırlama · J14 sonlu olmayan sayı · J16 / J17 rapor boş
satırları · J19 `guven` uyarısı · J20 düğme izleyicisi · J21 ad deseni · J22 rapor uzantısı · J24 adres türü ·
J25 "aç" hata yolu. (Kotlin'de "öldü" = `BUILD FAILED`; hepsi derlenen değişikliklerdi.)

---

## Çürütemediklerim (denedim, tuttu)

- **Sır sızıntısı (iddia 1):** `ZarfHatasi` / `MqttHatasi` / `AraciHatasi` / `JsonHatasi` / `PaylasHatasi` yalnız
  sabit tür taşıyor, `cause` zincirlenmiyor; `AraciBilgisi` / `AraciAdresi` / `IzlemeBitis` `toString`'leri maskeli;
  eklenti köprüye yalnız tür adı ve boolean / sınıf adı döndürüyor (`durum`'da aracı alanı yok); `.durum` /
  `.olay` / `.adres` dosyalarında sır yok; bildirim metinleri yalnız oturum / sayı. JS `cagir` yalnız `e.code`'u
  desenle geçiriyor. (Tek istisna B21.)
- **TLS (iddia 2):** 47 girdi denendi (büyük harf, sondaki nokta, punycode, alt çizgi, `%`, boşluk, IPv6, port 0 /
  65536 / `:` fazlası, kullanıcı bilgisi, yol / sorgu, tam genişlikli harf, ideografik nokta, çok uzun etiket).
  Sertifika / ad doğrulamasını atlatan girdi YOK. Kabul edilen sıra dışılar "Küçükler"de (K-1).
  El sıkışmada kapanan bağlantı JVM'de `ag` çıktı (Conscrypt'teki sınıflandırma cihazda ölçülmeli).
- **Yalnız abone (iddia 3):** PUBLISH üreten kod yok; QoS 2 → `bicim`; QoS 3 / kısa gövde / bozuk UTF-8 konu →
  `bicim`; işleyici hatası oturumu düşürmüyor. (Bellek: B6, B7.)
- **Zarf (iddia 4):** yanlış konuya mühürlenmiş, başka anahtarlı, kısa / sihirsiz mesaj işlenmiyor; önek dışı konu
  yok sayılıyor. (Karar eşiğinin kendisi: B1, B2.)
- **Karar katmanı (iddia 5):** `BildirimKarar` `pc_bildirim.py` `Mantik` ile satır satır karşılaştırıldı; fark
  bulunamadı. `Yoklama.degerlendir`: `c` 1.0 / `true`; BEKLİYOR → KAYIT; DOLU → BOŞ; kopukken oturum değişimi;
  bozuk özet (ilk yoklama gibi); kapalı sınıfta özetin ilerlemesi — beklenen çıktılar. (B4, B10 hariç.)
- **Izleyici yarışları (iddia 6):** bağlanmadan önce / el sıkışmada / mesaj işlerken `durdur()` → `durduruldu`;
  `istemci` alanı `@Volatile` ve atamadan sonra `dur` yeniden denetleniyor. Karar nesnesine kilitsiz erişim
  bulunamadı (`karar` çağrılarının hepsi `kilit` altında).
- **BildirimDeposu (iddia 7):** kimlik her işlemde denetleniyor; `KasaDeposu.sil` `"<kimlik>."` önekli her dosyayı
  siliyor (`.zarf/.olay/.durum/.adres` dahil); özel-IP kuralını atlatan adres bulunamadı (`http://`, sondaki `/`,
  boşluk hep AYNI özel IP'ye URL kuruyor; ad / herkese açık IP yazılamıyor ve okunamıyor).
- **`zarfYaz` doğrulaması (iddia 8):** K ile açılmayan, başka kimliğe / başka `n`'ye ait, adresi `mqtts://`
  olmayan zarf yazılmıyor; atlatılamadı. `ayarYaz` yalnız açık → kapalı geçişte durduruyor.
- **WebView (iddia 9):** `bildirim.js` zarfı açmıyor; sıra adres → zarf → izleme → yerel korunuyor; soru:
  çift dokunma, "aç" sürerken "hayır", art arda iki kayıt doğru. `KayitDugmesi.vue`'nun iki örneğinden biri
  kaldırılınca `kayitBitti` tetiklenmiyor (yalnız dinleyici bırakılıyor).
- **Paylaşım (iddia 10):** `PaylasDeposu` ad deseni (JS ve Kotlin aynı), boy / sıra sınırları, `file_paths.xml`
  yalnız `cache/paylas/`; `sadeAd` her adı desene uyduruyor (en uzun ad 81 karakterin altında). **CSV formül
  koruması telefonda da geçerli** (`rapor-kenar.test.js` son test YEŞİL: `=`, `+`, `-`, `@` ile başlayan ad /
  not / etiket).

---

## Küçükler (zayıf / kozmetik / tasarım notu; kanıt: kaynak okuması, aksi yazılmadıkça)

- **K-1** `AraciAdresi.coz` (`TlsBaglanti.kt:28–35`): `mqtts://0x7f.0.0.1`, `mqtts://1.2.3.4a`, `mqtts://a.b` AD
  sayılıp KABUL ediliyor; Kelvin işareti (U+212A) `lowercase()` ile `k`'ye dönüşüyor; sondaki satır sonu
  kırpılıyor (çalıştırılarak görüldü). "IP reddedilir" iddiası yalnız noktalı-onluk için doğru; TLS adı
  doğrulanamayacağı için bağlantı kurulamaz — atlatma değil. `AraciAdresi`'nin kurucusu herkese açık (`coz`'u
  atlayarak nesne kurulabiliyor; üretimde tek çağıran `coz`).
- **K-2** `IzlemeServisi.kt:74–77`: `startForeground` atarsa `stopSelf()` — yorum "sessizce vazgeç" diyor.
  `startForegroundService` ile başlatılmış servis `startForeground`'u tamamlamadan durursa Android süreci
  `ForegroundServiceDidNotStartInTimeException` ile düşürür (AOSP `ActiveServices.bringDownServiceLocked`).
  ÇALIŞTIRILAMADI; cihazda (izin eksik / tür reddi) doğrulanmalı. `:65`'teki `kapat()` dalı da aynı yola düşer.
- **K-3** `IzlemeServisi.kt:132`: ölmekte olan eski iş parçacığı `sonDurum = bitis` yazar; o sırada yeni bir
  servis örneği "izleniyor"daysa `durum()` "durduruldu" gösterir (statik alan iki örnek arasında paylaşılıyor).
- **K-4** `IzlemeServisi.kt:123` + `:177`: `uyandir()` iş parçacığı beklemiyorken gelirse kaybolur ("ağ geri
  geldi" → tam bekleme süresi, güvende 15 dk'ya kadar); durdurmada da aynı pencere var (iş parçacığı servis
  öldükten sonra bekleme süresi kadar yaşar).
- **K-5** `IzlemeDongusu.kt:39`: bağlanıp hemen kopan aracıda `deneme` hep 1 → 2 s'de bir sonsuz TLS el sıkışması
  (geri çekilme yok). "Uzun izlemeden sonraki ilk kopma hızlı denensin" niyeti kısa oturumu ayırt etmiyor.
- **K-6** `Izleyici.kt:72`: tek seferlik okumanın 20 s'si BAĞLANMADAN önce başlıyor; belge "abone olduktan
  sonra" diyor. El sıkışma aşamasında `tik` dönmediği için süre o aşamada uygulanmıyor (en kötü ~10 + 10 + 10 s ek).
- **K-7** `IzlemeServisi.kt:115`: kart kayıt sürerken temelli kapanırsa (`c:0` kalıcı) `kayitSuruyor()` son
  çevrimiçi durumdan `true` kalır → servis kullanıcı durdurana dek yaşar (vazgeçme süresi yok).
- **K-8** `kasa/AtomikYazim.kt:17`: geçici dosya adı sabit (`<hedef>.gecici`); servis ve yoklama aynı `.durum`'u
  aynı anda yazarsa (yoklama servis başlamadan az önce başladıysa) biri ötekinin yarım dosyasını taşıyabilir →
  bozuk özet = "ilk yoklama" = bir geçiş bildirilmez. Ayrıca yoklama eski okumasını servisin yeni özetinin
  üstüne yazabilir (oku-değiştir-yaz kilitsiz).
- **K-9** `YerelYoklama.kt:18–27`: `/eslestir/bilgi` imzasız ve kimlik mDNS'te açık; aynı ağdaki biri kart
  kapalıyken o IP'den aynı kimliği döndürürse "karttan haber yok" yerine "ev interneti koptu, kart çalışıyor"
  yazar. Etki YALNIZ bildirim metni (yanlış güven); başka durum değişmiyor (`yerelGoruldu` yalnız `yerelSon`).
- **K-10** `bildirim.js:71–74`: imzasız yanıtta 404 → eldeki zarf silinir. Yerel ağda araya giren biri sahte
  404 ile bildirimleri sessizce kapatabilir (zarfı üretemez ama sildirebilir).
- **K-11** `KayitDugmesi.vue:24` + `canli_gorunum.js:47–53`: `is` yalnız KAYIT (2) iken "durdur"; KAYIT →
  BEKLİYOR (4) geçişinde izleyici `kayitBitti()` çağırır (soru / sonuç satırı kalkar), oysa bildirim katmanı
  4'ü "kayıt sürüyor" sayıyor (`KAYITTA = [2, 4]`).
- **K-12** `rapor_metin.js:63–68`: `nesne()` içindeki `derinlik === 0 && ATLA.has(k)` dalı ölü kod (işlev hep
  derinlik ≥ 1 ile çağrılıyor). `sayiMetni(-1e-7)` → `"-0"`.
- **K-13** `Yoklama` yalnız `(k, o)` değişimine bakar: kart kayıt sürerken yeniden başlayıp AYNI oturuma devam
  ederse (açılış `a` değişti) yoklama hiçbir şey demez; servis aynı durumda "yeniden başladı, kayıt sürüyor"
  der. Pil oturumunun yeniden başlamayla kesilmesi yoklamada sıradan "kayıt bitti" (sınıf `bitti`) olur —
  `yeniden_basladi` sınıfı yoklamada hiç üretilmez. (DURUM.md'deki "sınır" notunun kapsamadığı kısım.)
- **K-14** PC ile ortak (iddia "aynı" olduğu için bulgu değil): `pil_bitti`'den sonraki 120 s içinde biten BAŞKA
  bir oturumun "kayıt bitti"si, oturumu bilinmeyen kayıtla eşleşip düşer (`BildirimKarar.kt:235–248`).
- **K-15** `Zarf.bilgiCoz` (`Zarf.kt:59–65`): çözülmüş düz metin baytları ve anahtarın onaltılık `String`'i
  sıfırlanamıyor (JVM `String`); "yalnız bellekte" doğru, "sıfırlanır" yalnız `ByteArray` kopyası için.

---

## Çalışma ağacı

Mutasyon turlarından ve geçici Kotlin kopyalarından sonra `git status --short`:

```
?? mobil/test/curutucu-5e/
```

`git diff --stat` boş (izlenen hiçbir dosya değişmedi).
