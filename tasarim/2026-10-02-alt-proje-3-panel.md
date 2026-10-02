# Alt proje 3 — Web paneli (PC öncelikli; kartın ve PC uygulamasının sunduğu panel)

> Üst tasarım: `2026-09-29-yazilim-sistemi.md` §9 (ekranlar, `ortak/`, rapor, dil), §10, Ö1/Ö6.
> Alt proje 2 (`ortak/`) bitti (`main` 606bb80). **Görsel yön kullanıcının devriyle seçildi**
> (2026-10-02: "ben karar veremedim, sen karar ver"; adaylar
> https://claude.ai/artifact/NHA6NxtMTM1n5aW5MkcATb). Seçilen birleşik maket depo dışında:
> `.yedek/olcum-karti/panel-secilen-tasarim.html`.

## Kararlar

| # | Karar | Gerekçe |
|---|---|---|
| P1 | **Tek düzen, geçişli görünümler.** Düzen = A (sol gezinme şeridi) + B'nin aranabilir kayıt listesi (tür, tarih, süre, **nerede**) + C'nin iki imleci (A/B, aralarında ΔV · ort · mAh · Wh). **Görünümler:** Koyu (A, varsayılan) · Açık (B'nin renkleri) · Ön panel (C'nin grafit + turuncu renkleri, cihaz rakamları). Ayarlar'dan seçilir, tarayıcıda hatırlanır (cihaz başına) | Kullanıcı birden çok tasarım arasında geçiş istedi (2026-10-02). Düzen geçişi her özelliği 3 kez yazdırıp sınatırdı; görünüm geçişi CSS değişkeni, her ekranda kendiliğinden çalışır. Kartta maliyet yalnız birkaç KB, işlemci yükü yok (çizim tarayıcıda) |
| P2 | **Yazı tipi sistemden** (`system-ui` / `ui-monospace`, Windows'ta Segoe UI + Cascadia/Consolas); dış yazı tipi YOK | Kart AP kipinde internetsiz → Google Fonts gelmez; yazı tipini karta gömmek dosya indirmeyi gerektirir (kullanıcı izni). İstenirse IBM Plex ileride gömülür (~60 KB) |
| P3 | **Grafik çekirdeği bizim** (`ortak/src/grafik.js`, `<canvas>`, bağımlılık yok) — ana tasarımdaki uPlot YERİNE | uPlot dış dosya (indirme izni); `ozet.js` Ö1'i zaten BİREBİR sağlıyor (sütun uçları); çizim + etkileşim ~600 satır. Bugünkü panel de kendi kanvasını çiziyor |
| P4 | **Derleme yok, tarayıcının ES modülleri; KADEMELİ bölme:** `app.js` modül olarak yüklenir ve yeni ekranlar baştan `ekran/*.js` modülleridir; eski ekranlar ancak yeniden yazıldıklarında `app.js`'ten çıkar (bir seferde bölmek B7/B22'nin `app.js` metnine bakan onlarca iddiasını ve mutasyon girdisini boşa düşürürdü, kullanıcıya getirisi yok). Vue 3 global yapısı (vendor) kalır; `ortak/src` panelle birlikte karta `/ortak/` altında yazılır (`arayuz-uret.py`), köprü de aynı yolu sunar | §9 "derleme adımı yok"; aynı dosyalar kart, köprü ve PC'den sunulur |
| P5 | **Bütçe iddiası:** kartın arayüz görüntüsü (gzip) ≤ 600 KB (bölüm 1.5 MB); `ortak/` dahil | Bugün ~350 KB ham arayüz + 216 KB ham `ortak/`; büyüme sınırı ölçülür |
| P6 | **Kayıtlar tarayıcıda:** eşitleme `ortak/src/esitle.js` + IndexedDB deposu (`depo` arayüzü); grafik/istatistik/dışa aktarma `ortak/`'tan | Tek kopya hesap kodu (§9); PC uygulaması (4) diske yazan depoyu takar |
| P7 | **Dil:** TR + EN, `ortak/src/sozluk.js`; yeni ekranlarda gömülü metin yok, eskiler taşındıkça | §9 Dil |

## Dilimler (sıra)

| Dilim | İçerik | Kabul |
|---|---|---|
| **3A** | Görünüm altyapısı: tasarım belirteçleri (`--…`) üç görünüm için, Ayarlar'da seçim + hatırlama; `app.js`'i davranış DEĞİŞMEDEN modüllere bölme iskeleti; `ortak/` karta yazılır | B7 (test_arayuz3.js) yeşil; başsız tarayıcıda üç görünüm render, konsol hatası yok; bütçe iddiası |
| 3B | Grafik çekirdeği `grafik.js`: çok kanallı çizgi, Ö1 (özet piramidi), boşluk kesik, tekerlek/sürükleme/iki parmak, gezgin şeridi, iki imleç + okuma | Node: sahte kanvas bağlamının çizim çağrılarında Ö1 (sıçrama her yakınlaştırmada) ; başsız tarayıcıda etkileşim |
| 3C | Kayıtlar + Kayıt görünümü: liste (arama, etiket, nerede), eşitleme (IndexedDB), grafik + imleçler, aralık istatistiği, notlar, dışa aktarma (CSV/ham), rapor sayfası | Sahte karta karşı uçtan uca (Python sahte kartı); gerçek kart tezgahı |
| 3D | Canlı (yenilenmiş), kayıt başlat/durdur/plan | Bugünkü iddialar korunur |
| 3E | Osiloskop (`skop.js` ölçümleri + FFT, yakalama günlüğü) | — |
| 3F | Pil testi (yeni kaydediciyle) | — |
| 3G | Karşılaştırma (çok kayıt; eksen zaman / mAh / başlangıçtan beri) | — |
| 3H | Ayarlar: bağlantı, güvenilir cihazlar, bildirimler, kalibrasyon geçmişi, depolama, dil, görünüm, Gelişmiş (konsol) | — |

## 3C kararları (2026-10-02, kullanıcının devriyle: "sen uygun gördüğün gibi hallet")

| # | Karar | Gerekçe |
|---|---|---|
| C1 | **Eşitleme yalnız panel kartın KENDİ adresinden açıldığında** (aynı köken). Köprü / USB / `kartTaban` ile başka kökenden açılan panelde Kayıtlar bu tarayıcıdaki kopyayı gösterir, eşitleme düğmesi yerine "paneli kartın adresinden açın" yazar | `/kayit/veri` seri yoldan yok; kart CORS'u yalnız kayıtlı köprü kökenine ve `X-Kayit-*` başlıklarını açmadan veriyor. Firmware değişikliği (flaş + tezgah) 3C'ye girmez; PC'de arşiv `kopru/kayit_esitle.py`, alt proje 4 |
| C2 | **Depo IndexedDB, kart kimliği (`X-Kayit-Kimlik`) başına bir akış**; `esitle.js` DEPO arayüzünün birebir uygulaması (`ekran/depo_idb.js`). Yazmalar `durability: 'strict'`; `kilitAl` Web Locks (`navigator.locks`) varsa onunla, yoksa sekme içi kilit | Ortak eşitleyici olduğu gibi kullanılır (P6); iki sekme aynı akışa yazmasın. Kimlik değişirse (kart biçimlendi) yeni akış — eski kopya silinmez, listede "eski kart kopyası" diye durur |
| C3 | **Varsayılan: karta "aldım" onayı GÖNDERİLMEZ.** Kayıtlar ekranında açıkça "Bu tarayıcı arşivdir" seçilirse (kart başına, tarayıcıda hatırlanır) onay panelin komut yolundan `Go<sıra>` ile gider | Kartın akıllı temizliği yalnız onaylara bakar; bir telefonun geçici kopyası "arşivlendi" sayılırsa kart veriyi silebilir ve tek kopya o telefonda kalır |
| C4 | **Liste = kartın dizini (`/kayit/liste`) ∪ bu tarayıcıdaki oturumlar**, satırda tür · ad · başlangıç · süre · nokta · etiketler · **nerede** (`kartta` / `bu tarayıcıda` / `ikisinde`) · durum. Arama ad/etiket/not/numarada (Türkçe karakter duyarsız); süzgeç tür + nerede | Kullanıcı "bu kayıt nerede, silinirse kaybolur mu" sorusunu listeden görmeli |
| C5 | **Kayıt görünümü yalnız bu tarayıcıdaki veriden** (kartta olup eşitlenmemişse "önce eşitle"). Grafik `grafik.js` (V · I · W), iki imleç + `imlecOkuma`; zaman ekseni `disari.zamanEkseni` (saat yoksa açılıştan beri); ayrıntılı kip oturumu `ayrintiSerileri`; notlar listesi (tıklayınca grafik o ana gider); pil olayları (DCIR, sonuç) özet kutusunda. Osiloskop oturumunda yakalama TABLOSU + yakalama başına CSV; yakalamanın grafiği 3E'de | Hesap tek kopya `ortak/`'ta; osiloskop ekranı 3E'nin işi, 3C onu yarım yapmaz |
| C6 | **Dışa aktarma:** CSV (Excel-TR `;`/`,` ve EN), ayrıntılı CSV, pil CSV, ham `.kyt` (o oturumun kayıtları, `hamDisari`); **rapor** `rapor.oturumRaporu` → yazdırılabilir sayfa (tarayıcının "PDF olarak kaydet"i) | §9; dosya indirmek kartı yormaz (tarayıcıda üretilir) |
| C7 | **Gezinme:** Kayıtlar mevcut sekme düzenine yeni görünüm (`#/kayitlar`); kayıt `#/kayit/<oturum>` — geri tuşu çalışır. Sol şerit düzenine (P1) geçiş 3D'de, Canlı yeniden yazılırken | Kademeli bölme (P4): kabuğu şimdi değiştirmek B7'nin sekme iddialarını iki kez yazdırırdı |
| C8 | **Dil:** yeni ekranların metni `sozluk.js` anahtarlarından (TR + EN); dil seçimi 3H'de, o zamana dek TR | P7 |

### 3C uygulama kararları (C1–C8 dışında; uygulayan, kullanıcının devriyle)

| # | Karar | Gerekçe |
|---|---|---|
| U1 | Kayıtlar modülü `defineAsyncComponent` + dinamik `import()` ile **ekran ilk açılınca** iner; inmezse sekmede sebep + çare yazar | Açılışta istenen dosya ≤ 8 (B7 bölüm 15); karttan her dosya isteği döngüyü bloklar |
| U2 | Her eşitleme **taze `/kayit/liste`** ile başlar; akış eşitleme ortasında değişirse dizin bir kez daha alınıp yeni akışa geçilir | Eski dizinle başlamak, kart biçimlenince eşitlemeyi "akış değişti" ile durduruyordu (tarayıcı testinde yarış olarak görüldü) |
| U3 | Yeni akış kaydı kimlikle **önceden tohumlanır** (durum.kimlik) | Liste ile ilk veri yanıtı arasında kart biçimlenirse Esitleyici yanlış akışa YAZMAZ |
| U4 | "Arşiv" seçimi `localStorage['olcum.arsiv.<kimlik>']` (kart akışı başına); panel bağlı değilse onay gönderilmez ve bu yazılır | C3: biçimlenen kartta seçim kendiliğinden kapanır (güvenli yön) |
| K1 | Grafik x = oturum başından geçen ms; saatsiz yeniden başlamada parça öncekinin ardına (3 × boşluk eşiği) konur ve "konumu tahmini" yazar | Zaman uydurulmaz, görünür kılınır |
| K2 | Nokta oturumunda ort + ince min/maks çizgileri; okumanın min/maks'ı min/maks kodlarından | Ö1: tek örneklik sıçrama ortalamada erir |
| K3 | Okumanın mAh/Wh'si **açılış başına** ve Wh **kartın W'sinden** (rapor.js ile aynı kural; tam aralıkta raporla bit bit aynı) | Ort V × ort A dalgalı yükte ayrışır |
| K4 | Sağ eksen tek birim: Akım **ya da** Güç | İki birim tek eksende eksen yazısını yalancı yapar |
| K5 | İmleç rengi temanın `--yazi`'sı | grafik.js'in `imlec` yedeği sabit renk; üç görünümde de en yüksek karşıtlık |
| K6 | Rapor yazdırılırken (beforeprint) geçici olarak Açık görünüm, afterprint geri alır; yeni renk tanımlanmaz | Koyu zemin kâğıda basılmaz, koyu temanın açık yazısı beyaz kâğıtta okunmaz |

## 3D kararları (2026-10-02, aynı devirle)

| # | Karar | Gerekçe |
|---|---|---|
| D1 | **Kabuk sol şeride geçer (P1):** ad + firmware sürümü (afişten) · bağlantı (WiFi / USB / köprü / demo) · gezinme Canlı · Osiloskop · Pil testi · Kayıtlar · Ayarlar · Konsol. Henüz yazılmamış ekran (Karşılaştırma) şeritte YOK. Alt bilgi: eşitlenmemiş oran (`G` satırının `onaysiz` alanı). ≤ 900 px'te şerit çekmece olur, seçimde kapanır. Eski adresler (`#/olcum` …) çalışmaya devam eder | Seçilen maket; ölü bağlantı kullanıcıyı boş ekrana götürür |
| D2 | **Canlı okuma kartları** V · A · W · Enerji (oturum); her birinin altında son 10 s'nin min … maks'ı (canlı örneklerden, tarayıcıda) | Kullanıcı ilkesi: sıçrama gözden kaçmasın |
| D3 | **Canlı grafik `grafik.js`'e geçer** (tek çekirdek, P3). Bugünkü pencere / yenileme / temizle / CSV davranışları korunur; "dondur" ile canlıda da imleç ve yakınlaştırma | Kayıt görünümüyle aynı etkileşim, iki çizim kodu kalmaz |
| D4 | **Kayıt denetimi Canlı'nın başlığında:** Başlat (hız → `Gb<ms>`, "her örnek" → `Gb0`) · Durdur `Gd` · Not ekle `Gn<oturum> <metin>` · Zamanla (`Gp<unix>,<süre_s>,<hız_ms>`, yerel saatten; iptal `Gp-`). Komutlar mevcut komut yolundan; kartın ret satırı (`! G: …`) olduğu gibi gösterilir | Kurallar kartta (pil sürerken ret vb.); panel kopyasını yazmaz, firmware değişmez |
| D5 | **Kayıt durumu PASİF dinlemeyle:** kartın kendiliğinden bastığı `G` (kayıtta saniyede bir + değişimde), `GP`, `GA`, `GT`; `G?` yalnız bağlanınca bir kez ve bir kayıt komutundan sonra. Yoklama döngüsü yok | "Ölçerken pasif dinle" kuralı; `G` zaten akıyor |
| D6 | **Aktif kayıt kartı:** oturum · nokta · süre · hız · doluluk çubuğu · "~X sa kaldı" (doluluğun ölçülen artış hızından, en az 60 s gözlemle; öncesinde "hesaplanıyor") · plan · `dusen` > 0 ise uyarı | Tahmin yalnız ölçülenden |
| D7 | **Son olaylar:** panelin gördüğü kayıt durum değişimleri, `!` satırları, kartın yeniden başlaması (afiş); en fazla 20, yalnız bu sekmede | Maket |
| D8 | Yeni metinler `sozluk.js`'ten, TR + EN | P7 |

### 3D uygulama kararları (D1–D8 dışında; uygulayan, kullanıcının devriyle)

| # | Karar | Gerekçe |
|---|---|---|
| E1 | **Kabuk, okuma kartları, kayıt denetimi ve `G`/`GA`/`GT`/`GP` ayrıştırıcıları `app.js`'te; Canlı'nın GRAFİĞİ `ekran/canli.js`, ekran ilk görünür olunca `import()` ile iner** (U1 deseni). Açılışta istenen statik dosya ≤ 8 (B7 bölüm 15) korunuyor: index + style + vue + app + manifest + ikon + tema + sözlük = 8. Canlı varsayılan ekran olduğundan grafik zinciri (canli + grafik + ozet + istatistik) açılışta da iner — B7 bunu AYRICA sayıyor: toplam ≤ 12 dosya ve ≤ 250 KB gzip | Tek ayrıştırıcı `satirIsle`'de (B22.2). Okuma kartları ve kayıt durumu grafik modülünü beklemez. Statik içe aktarılsaydı açılış 12 dosya olurdu (≤ 8 iddiası) |
| E2 | **Bütçe (yöneticinin kararı) ölçümü:** `arayuz-uret.py` künyeye (`_fs.json`) dosya başına gzip baytı yazıyor (`bayt`); B7 açılış kümesini html referansları + `app.js`'in statik içe aktarma ağacından TÜRETİP topluyor | Elle liste yok: yeni statik import kendiliğinden sayılır |
| E3 | **Enerji kartı "Enerji (sayaç)"**: `D` satırının kart sayacı (`e` ile sıfırlanır), kayıt oturumuna bağlı değil — maket "(oturum)" diyordu | Kart oturum enerjisini canlı yayınlamıyor; "oturum" demek yanlış sayı vaadi olurdu |
| E4 | **Sağ eksen tek birim** (Akım · Güç · yok; 3C K4 ile aynı). Eski üç onay kutusu (`gosterI`/`gosterW`) ilk açılışta bu seçime çevrilir | grafik.js eksen YAZIYOR; iki birim tek eksende eksen yazısını yalancı yapar (eski tuval yazmıyordu) |
| E5 | **Canlıda grafik etkileşimi kapalı, Dondur'da açık** (`pointer-events`), x ekseni "şimdi"ye göre (−00:00:30 … 00:00:00); gürültü tabanı (B45) `enAzAralik` = 2 × taban | Her D satırı pencereyi yeniden kurar — yakınlaştırma 200 ms sonra silinirdi; telefonda grafiğin üstünden sayfa kaymalı |
| E6 | **"~X kaldı" ONAYSIZ artışından**, çubuk doluluk. Binde nicemleme yüzünden hız DEĞİŞİM ANLARINDAN; < 60 s "hesaplanıyor", değişim yoksa ALT SINIR ("> X") | Kart onaysız veri yüzünden DOLU olur (kg: onaysız ASLA silinmez); onaylı eski veri yerini açar — dolulukla tahmin, onay verilmiş kartta yanlış olurdu. D6'nın "doluluk artış hızı" onay yokken (varsayılan, C3) aynı sayı |
| E7 | **Not `Gn<oturum>@<kart_ms> <metin>`** (son D taze ise) — not kayıt görünümünde kendi anında durur. Kartın SESSİZCE attığı karakterler (çift tırnak, ters bölü, denetim) ve 120 baytı (KAYIT_NOT_METIN) aşan metin REDDEDİLİR; her kayıt komutu ≤ 175 BAYT (UTF-8; kartın `String::length()`'i) | Yazılan, kaydedilenle aynı olsun; Türkçe harf 2 bayt |
| E8 | **Aralık kaynağı:** bu sekmenin `Gb`'si (15 s içinde beliren oturum) → plan (`GP`) → `GA` (her örnek) → yoksa nokta artışından ÖLÇÜLEN ("~200 ms (ölçülen)"). Süre = nokta × aralık; değilse panelin GÖRDÜĞÜ başlangıçtan; görmediyse "—" | `G` satırı aralığı taşımıyor; tahmin yalnız ölçülenden |
| E9 | **Ret:** bir kayıt komutundan sonraki 5 s içinde gelen `! G…` satırı o komutun reddi — denetimin yanında OLDUĞU GİBİ; her `!` satırı ayrıca son olaylarda | Komutla ilgisiz `! G plan atlandı` "komutun reddedildi" sanılmasın |
| E10 | **Yeniden başlama:** afiş YA DA `D` satırının `ms`i geri gitmesi; zaman ekseni AZALMAZ (3 rapor aralığı boşlukla sürer, çizgi kopar), millis sarması (49.7 gün) ayrı; 15 s içinde tek olay; sonraki `G` aynı oturumu sürdürüyorsa "Kayıt sürdü" | grafik.js/ozet.js azalmayan zaman ister (eski tuval geri çiziyordu); WiFi'de afiş görülmez, `ms` her taşıyıcıda var |
| E11 | **Sürüm:** kartın açılış afişi firmware sürümünü (KAYIT_FW_SURUM) TAŞIMIYOR — şerit afişteki aşama metnini gösterir, afiş görülmediyse (WiFi'de hep) yalnız yer + açıklayan ipucu | Firmware değişmez (3D); açık iş: afişe sürüm eklemek |
| E12 | **Demo kartı** (`sahte-kart.js`) kayıt motoru: `G` alt komutları + `G`/`GA`/`GT`/`GP` satırları, ret metinleri firmware'in; demo bağlanınca da `G?` bir kez | `?demo` Canlı'yı gerçek yolundan çalıştırsın |
| E13 | **Kabuğun `:class`ı `#uyg`'nin İÇİNDEKİ öğede** | Vue 3 bağlama noktasının kendi özniteliklerini derlemez (yalnız içini) — başsız tarayıcıda çekmece hiç açılmıyordu |

## 3E kararları (2026-10-02, aynı devirle; kullanıcı dışarıdayken)

| # | Karar | Gerekçe |
|---|---|---|
| OS1 | **Düzen:** dalga geniş alanda (sol, ≥ 2/3 genişlik), kontroller sağda dikey sütunda; ≤ 900 px'te kontroller dalganın altına iner. Kontroller kümelenir: Yakalama (Yakala · Sürekli · Otomatik) · Zaman tabanı · Tetik (kip · kenar · eşik · ön-tetik · onay) · Günlük · Kalibrasyon çıkışı | §9 "dalga geniş alanda, kontroller yanda"; bugünkü tek satırlık düğme şeridi telefonda iki satıra taşıyor |
| OS2 | **Dalga kendi tuvalinde kalır** (10 × 8 bölmeli ızgara, tetik seviyesi + ön-tetik işaretleri, yatay/dikey zoom — B42–B46'da kartla doğrulanmış çizim); yalnız renkleri tema belirteçlerine bağlanır. **Spektrum `grafik.js` ile** (x ekseni Hz biçimli — grafik.js'e x biçimleyici seçeneği eklenir, B73'te sınanır) | Osiloskop ızgarası "zaman/bölme" sözleşmesi genel zaman grafiğinden farklı; kartta doğrulanmış çizimi yeniden yazmanın kullanıcıya getirisi yok. Spektrum düz bir x–y grafiği, tek çekirdek ilkesi (P3) orada uygulanır |
| OS3 | **FFT:** `fft.spektrum` — Hann (varsayılan) / dikdörtgen, DC çıkarılır, genlik V (tepe) ya da dBV seçilir; tepe frekansı + ilk 5 harmonik (genlik, THD yaklaşığı) listesi. Kaynak her zaman o anki yakalamanın HAM kodları (görüntülenen zoom penceresi değil) | §9; kartta FFT yok. Zoom penceresi kısa olunca frekans çözünürlüğü sessizce bozulurdu |
| OS4 | **Ölçümler:** canlı yakalamada kartın `S` satırı ölçümleri (bugünkü gibi); kayıtlı / arşivden açılan yakalamada aynı sayılar `skop.skopOlc` ile tarayıcıda (bit bit kartla aynı, 2E). Hangisinin kaynağı olduğu ölçüm kutusunda yazar | Kayıt (SKOP 10) ölçüm taşımıyor, ham kod taşıyor; kart = panel kanıtlı |
| OS5 | **Yakalama günlüğü denetimi** Osiloskop'ta: "Her tetikte" `Gt0`, "Her N s" `Gt<ms>` (1 s … 1 sa, kartın sınırı), Durdur `Gtd`; durum PASİF `GT` satırından (D5 deseni), ret satırı olduğu gibi (E9 deseni) | 1C-3 komutları panelde yoktu |
| OS6 | **Kayıtlı yakalamayı aç:** Kayıtlar'daki yakalama tablosunda (3C) satır → `#/skop/kayit/<oturum>/<sıra>[@kimlik]`: osiloskop ekranı o yakalamayı ARŞİV şeridiyle gösterir (bugünkü köprü arşivi deseni), "Canlıya dön" | 3C "yakalamanın grafiği 3E'de" dedi; iki arşiv aynı görünümü paylaşır |
| OS7 | **Bugünkü iddialar korunur:** köprü arşivi, kırpık blok reddi, ADS susturma, tetik onayı, hızlı ölçüm (gerçek güç / PF) davranışları değişmez; B7'deki ilgili iddialar zayıflatılmaz | Kartta bulunmuş kusurların (B35, B41–B47) geri gelmemesi |
| OS8 | Yeni metinler `sozluk.js`'ten, TR + EN; erişilebilirlik Web Interface Guidelines'a göre (aria-live ölçüm/ret, klavye kısayolları görünür) | P7; kullanıcı WIG yeteneğini kullanmamı istedi |

### 3E uygulama kararları (OS1–OS8 dışında; uygulayan, kullanıcının devriyle)

| # | Karar | Gerekçe |
|---|---|---|
| S1 | **OS4'ün hesabı `skopOlc` DEĞİL `skopOlcKart`** (`ortak/src/skop.js`): kartın `skop_olc_kalibre` (eğri geçerliyse gerilimler eğriden, zaman büyüklükleri eğriyle doğrusallaştırılmış koddan) + `skop_ofsetle`. Eğri = oturumdaki OLAY `KO_SKOP_KAL` | Kart `M` satırını çıplak `skop_olc`'tan basmıyor (B43); gerçek kartta eğrisiz hesap ~7 V ayrışırdı. Gerçek kart fikstüründe (`olcum-skop-fikstur.json`) gerilimler, f, T, n basılan haneye kadar aynı (B73 + T3E) |
| S2 | **Eğri geçerliliği = kartın `kal_tab_var`ı:** 17 nokta, ilk ≥ 0, kesin artan; değilse eğrisiz yol (ölçüm de eksen de) | Firmware eğri olayını HER Gt'de yazıyor — eğri kuramamışsa sıfır/yarım dizi |
| S3 | Yakalamanın eğrisi: kayıt sırasından ÖNCEKİ en son `KO_SKOP_KAL`; hiç yoksa (baş temizlenmiş) oturumdaki ilki | Eğri yonga başına sabit (eFuse); Gt her başlangıçta bir tane yazar |
| S4 | `#/skop/kayit/<oturum>/<sıra>` @kimliksizse oturumu TAŞIYAN en yeni akış; Kayıtlar'ın bağlantısı kimliği HER ZAMAN yazar | Eski kart kopyasında yanlış yakalama açılmasın |
| S5 | Kayıtlı yakalamanın ekseni KENDİ eğrisiyle (`osilo.kal`); canlı kartın `CT`si ona uygulanmaz; rozet "eksen kaydın eğrisiyle / eksen HAM (kayıtta eğri yok)" | Kayıt başka kartın / başka ayarın olabilir |
| S6 | Spektrumda 0. kutu (DC) çizilmez, değeri yazılır; x ekseni Hz/kHz (grafik.js `xEksen`, 1-2-5) | Skop VREF ofsetli (~63 V): DC çubuğu bileşenleri ezer |
| S7 | Harmonikler n = 1 … 5 (1 = temel = tepe). Komşulukta (≤ temel aralığının yarısı) en büyük YEREL tepe; o tepe n·f0'dan bir çözünürlük hücresinden (max(df, hz/n)) uzaksa ya da yerel tepe yoksa harmonik "≤" (sızıntı tabanı, üst sınır). THD yaklaşığı 2 … 5'ten | Başsız tarayıcıda temiz sinüste temelin yamacı ve gürültü tepeleri "2. harmonik 68 Hz / 1930 Hz" diye görüldü |
| S8 | `GT` yalnız `G?` ile basılıyor: durum Gt/Gtd'den sonra bir `G?` ile; günlüğün KENDİLİĞİNDEN durması kartın `* G osiloskop gunlugu durdu: …` / `! G: … oturumu acilamadi` satırından. Yoklama yok | D5 |
| S9 | Günlük sürerken Yakala / Otomatik / Sürekli(başlat) kapalı (kart reddeder), gerekçe yazılı; elle yakalamanın reddi (`! skop…`, `! tetiklenemedi`, `! otomatik…`) 30 s içinde Yakalama kümesinde olduğu gibi | NORMAL kipte tetik 20 s beklenebilir (`osiloYakala` tavanı) |
| S10 | Düzen ızgara alanlarıyla; DOM sırası dalga → denetimler → spektrum: geniş ekranda denetim sağda iki satır boyu, dar ekranda dalganın HEMEN altında | OS1; klavye sırası da aynı |
| S11 | Dalga ızgarası 10 × 8 bölme (yatay = firmware `SKOP_BOLME`), orta eksenler `--kenar-koyu` | OS2 "10 × 8" diyordu; eski çizim 4 yatay çizgiydi |
| S12 | Spektrumda grafik.js imleçleri: çift tık / A, B → okuma (Hz + seçili birimde genlik); klavye ipucu görünür | OS8 "kısayollar görünür" |
| S13 | Eski açıklama metinleri ve B7'nin çivilediği seçenek metinleri (tetik onayı, zoom, CAL ipucu, menzil, B36/B39 uyarıları) TR kaldı; başlıklar, kümeler, düğmeler, yeni işlevler `os.` sözlükte | P7 "eskiler taşındıkça"; B7 iddialarını zayıflatmamak (OS7) |
| S14 | Demo kartı (`sahte-kart.js`) `Gt`/`Gtd`/`GT` + günlükte elle yakalama reddi, firmware metinleriyle | E12 |

## 3F kararları (2026-10-02 akşam, aynı devirle; kullanıcı dışarıdayken)

| # | Karar | Gerekçe |
|---|---|---|
| PL1 | **Firmware değişmez; `p0` emniyeti aynen:** acil şerit + Pil sekmesindeki DURDUR tek tık, onaysız, hiçbir koşulla `:disabled` olmaz (B7 EMNIYET-P0 ve acil şerit iddiaları korunur) | Deşarjı kesen komut; WIG'in iki aşamalı onayları bilerek dışında |
| PL2 | **Düzen Canlı'yla aynı dilde:** üstte okuma kartları (V · I · mAh · Wh · geçen süre · kesme gerilimi), altında eğri, yanında/altında DCIR tablosu ve test parametreleri. Test sürmüyorsa son testin özeti + "Kayıtlar'da aç" | Kabuk (3D) ve görünümler tutarlı; ölçüm aleti hissi |
| PL3 | **Eğri `grafik.js` ile** (bugünkü özel tuval yerine): V–zaman, sağ eksende akım; eksen seçimi "zaman / mAh" (3G karşılaştırmasının hazırlığı); DCIR anları grafikte işaret | Tek çizim çekirdeği (P3); pil eğrisinde sıçrama gözden kaçmasın (Ö1 piramidi) |
| PL4 | **Veri kaynağı:** canlı test sırasında bugünkü `/pil?sira=` artımlı yoklama KALIR (ağ çekirdeğinde, ölçümü bloklamıyor; sayfa yenilense de eğri gelir) ama yalnız Pil sekmesi görünür ve test sürerken; test bitince kaynak kartın PİL oturumu (1C-1) — aynı kökendeyse Kayıtlar eşitlemesiyle (3C), değilse `/pil`'in son hali. Kart `/pil`'i ve `PilHalka`'yı sağlamaya devam eder (firmware değişmez) | Pasif dinleme ilkesi (D5) ölçüm çekirdeğine yük getirmemekle ilgili; `/pil` HTTP'si çekirdek 0'da. Kayıt motoru tek gerçek kaynak, eşitleme varsa ona dayanılır |
| PL5 | **Başlatma formu:** kesme gerilimi (0.5…38.5 V, bugünkü sınırlar, Li-ion / kurşun-asit hazır değerleri), DCIR aralığı/devre dışı, oturuma ad (Ga) — komutlar kartın kabul ettiği biçimde (bugünkü `P`, `p1`, …); kartın ret satırı olduğu gibi (E9 deseni) | Kurallar kartta; panel kopyasını yazmaz |
| PL6 | **Bittiğinde:** sonuç (mAh, Wh, süre, bitiş sebebi), DCIR özeti; pil CSV (3C `pilCsv`) ve "Kayıtlar'da aç" (`#/kayit/<oturum>`) | Test sonrası analiz Kayıtlar'da tek yerde |
| PL7 | Metinler `sozluk.js` (`pl.*`, TR + EN); WIG kuralları (aria-live okuma/ret, etiketli denetimler, odak) | P7, kullanıcı WIG istedi |

### 3F uygulama kararları (PL1–PL7 dışında; uygulayan, kullanıcının devriyle)

| # | Karar | Gerekçe |
|---|---|---|
| PU1 | **Emniyet ve durum `app.js`'te, eğri `ekran/pil.js`'te** (E1 deseni): `p0` (acil şerit + Pil sekmesi), durum makinesi, `/pil` yoklaması, kartın pil satırları, komut üreticileri ve okuma kartları `app.js`; eğri (`PilGrafik`), mAh ekseni ve kayıt kaynağı `ekran/pil.js` — Pil sekmesi ilk görünür olunca `import()` | DURDUR ve okumalar modül inmese de çalışmalı (kart yeniden başlarken modül 404 olabilir). Açılış kümesi değişmedi (≤ 8 dosya); `#/pil` ile açılış 223 KB gzip, 12 dosya |
| PU2 | **PL4 ölçüldü:** bugüne dek pil BAĞLIYKEN HER ZAMAN yoklanıyordu (B27 A4: boşta 10 s, Pil sekmesinde ya da test sürerken 2 s — 1 sa Canlı = 360 `/pil`). Artık sürekli yoklama YALNIZ (bağlı ∧ Pil sekmesi ∧ belge görünür ∧ test sürüyor), 2 s. Tek seferlik: bağlanınca (acil şerit için durum), Pil sekmesi açılınca (durum bayatsa), test bitince (sekme görünürse; değilse sekme açılınca). Testin başladığı / bittiği kartın KENDİLİĞİNDEN bastığı satırlardan (`* pil testi BASLADI …`, `BITTI`, `DURDURULDU`, `! pil testi: azami sure`, `! pil testi REDDEDILDI`) — SSE her istemciye yayar | Pasif dinleme (D5); T3F istek sayarak ölçtü: Canlı'da 4 s 0, Pil + test 6 s'de 3, sekme gizli 5 s 0, belge gizli 5 s 0, bitişten sonra 5 s 0 |
| PU3 | **Acil şeritteki mAh değerinin YAŞI yazılır** ("… mAh (00:02:05 önce)") | Pil sekmesi dışında yoklama yok (PL4); bayat sayı taze görünmesin. V şeritte canlı (`D`) |
| PU4 | **Başlat = kesme (gerekirse `P<v>`) + kartın onayı → `p1`.** Kartın `* pil kesme gerilimi <v> V` satırı 3 s içinde gelmezse `p1` GİTMEZ. Kart testi BAŞLADI satırında istenenden farklı kesmeyle başlattıysa panel HEMEN `p0` yollar ve söyler | Yanlış kesmeyle deşarj (ör. kurşun-asit 3 V'a kadar) pili bitirir; firmware değişmeden yapılabilen en sıkı emniyet |
| PU5 | **PL5'in "DCIR aralığı / devre dışı" uygulanamadı:** aralık ve darbe `pil_test.h` derleme sabiti (`PIL_DCIR_ARALIK_MS` 300 000, `PIL_DCIR_MS` 200), komutu yok; PL1 firmware değişmez → formda salt okunur + açık iş | Panel kartın yapamadığını vaat etmesin |
| PU6 | **PİL oturumunun numarası YALNIZ `G` satırından:** `/pil` taşımıyor, OLAY'lar oturumun içinde (numarayı bilmeden okunamaz). Kural: BAŞLADI görülünce o an açık oturum not edilir; ondan FARKLI ilk KAYIT durumlu `G` = PİL oturumu (p1 açık ölçüm kaydını kapatır; pil sürerken `Gb` reddedilir). Test sürerken açılan sayfa ilk KAYIT `G`'sini alır, "başlangıcı görülmedi" yazar. `! pil testi KAYDEDILMIYOR — …` → oturum yok, sebep ekranda. Numara `localStorage`'da (yenilemede bağlantı kalır) | `/kayit/liste` sonradan tür 2 oturumları verir ama "bu test hangisi" belirsiz kalırdı |
| PU7 | **Oturuma ad `Ga<oturum> <ad>`** — numara G'den öğrenilince gider; metin kuralları `Gn` ile aynı (kartın attığı karakter ve 120 baytı aşan metin reddedilir) | Yazılan, kaydedilenle aynı olsun (E7) |
| PU8 | **Okuma kartlarının KAYNAĞI her kartın altında:** V, I canlı (`D`); mAh, Wh **kartın sayacı** (`/pil` `mah`/`wh` — her örnekte birikir, DCIR darbesi hariç; tarayıcı HESAPLAMAZ); geçen süre kartın son noktası; kesme kartın ayarı. Test bitip kayıt açılınca PIL_SONUC / PIL_AYAR (aynı sayaçların kaydı) | Kullanıcı "bu sayı nereden" sorusunu ekranda görsün |
| PU9 | **mAh ekseni TARAYICI hesabı:** 1 Hz noktaların yamuk integrali; eksen sonu kartın sayacıyla yan yana yazılır. Boşluk (kayıp nokta, eşik 2.5 × aralık) ya da eksi akım varsa eksen KURULMAZ, zaman eksenine düşülür, sebep yazılır | Boşluğun üstünden integral uydurulmaz; azalan x grafik.js sözleşmesini bozar |
| PU10 | **DCIR tablosu:** canlıda yoklamanın gördüğü ölçümler (`dcir_n` artınca son ölçüm; mAh yoklama anında, "≈"); atlanan numaralar "görülmedi" (—, değerleri kayıtta). Anın zamanı kartın kuralından: n × (300 000 + 200) ms. Kayıt açılınca OLAY DCIR'lerin KENDİ zamanı ve değerleri. Grafikte "R1, R2 …" kesik çizgi | `/pil` yalnız son ölçümü taşıyor; zaman uydurulmaz, kuraldan hesaplanır |
| PU11 | **Kayıt kaynağı:** test bitince (Pil sekmesi görünürken) önce bu tarayıcının IndexedDB kopyası; yoksa ve panel kartın adresinden açıldıysa (C1) BİR KEZ eşitleme — Kayıtlar'ın `EsitlemeDenetcisi`, C3 aynen (onay yalnız "bu tarayıcı arşivdir" seçiliyse). `#/kayit/<oturum>@<kimlik>` | PL4 "kaynak kartın PİL oturumu"; eşitleme zinciri yalnız burada iner |
| PU12 | **Yeni test = yerel nokta kopyası baştan** (BAŞLADI görülünce ya da `/pil` `sira`sı bizdekinden küçükse ve test sürüyorsa). Kart yeniden başladıysa (BEKLEMEDE, sıra 0) eski testin eğrisi korunur. `kalan=` varken aynı yoklamada devam | **Bulunan kusur:** eski testin sırasıyla istenince yeni testin noktaları HİÇ gelmiyordu (kart o sırayı henüz üretmemiş → 0 nokta) |
| PU13 | **Taşıyıcı:** `/pil` yalnız kartın kendi HTTP'sinde. USB'de / köprüde (`/pil` yok) durum `p` komutunun `B` satırından (sürücüyse; izleyici yalnız dinler), eğri yok — sebebi yazılı. Demo kartı `/pil` gövdesini ve satırları firmware biçiminde taklit eder (zaman ×30) | Bugün USB/köprüde Pil ekranı "HTTP 404" diyordu |
| PU14 | Pil sekmesindeki DURDUR **her zaman görünür ve etkin**; test sürmüyorken `p0` güvenli (kart "zaten çalışmıyor; yük kapalı" der) | PL1 |
| PU15 | Kesme / ad hatası **alanın yanında** (`pilUyari`, role=alert) — eski genel `hata` kutusu yerine | WIG (faz hatasıyla aynı kural) |
| PU16 | **grafik.js `isaretler` seçeneği** (kesik dikey çizgi + kısa etiket, plan dil metni taşımaz — G8; B73'te sınandı). Seriler sırası I sonra V: dirençli yükte I ∝ V ve iki eğri üst üste biner, birincil ölçüm (V) üstte kalsın | T3F'de V hiç görünmüyordu |
| PU17 | **`.iki-sutun` telefon kuralı taban kuralından SONRA** (3D'nin kuralı önce yazılmıştı; aynı özgüllükte sonraki kazanır) | T3F 390 px'te ölçtü: Canlı'nın da iki kartı telefonda 171 px'lik iki sütundaydı |

## 3G kararları (2026-10-02 akşam, aynı devirle)

| # | Karar | Gerekçe |
|---|---|---|
| KR1 | **Seçim Kayıtlar listesinden:** satırlarda seçim kutusu (yalnız bu tarayıcıdaki kopyası olan oturumlar; en fazla 6), "Karşılaştır" → `#/karsilastir/<no>[@kimlik],<no>[@kimlik],…` — paylaşılabilir, geri tuşu çalışır | Kayıtlar tek giriş noktası (C4); adres durumu taşır (WIG) |
| KR2 | **Tek grafik, tek birim:** V · I · W'den biri seçilir (K4 ilkesi: iki birim tek eksende yalan söyler); her kayıt ayrı çizgi, renkler tema belirteçlerinden türetilen ve renk körlüğüne dayanıklı ayrık bir dizi (3 görünümde okunur), lejantta kayıt adı + numara | P3 tek çekirdek; renk yalnız ayırt etmek için, anlam için değil |
| KR3 | **x ekseni üç kip:** "başlangıçtan beri" (varsayılan; her kayıt kendi başlangıcından, K1 kuralıyla — saatsiz yeniden başlama tahmini işaretli), "saat" (unix; saati olmayan kayıt bu kipte dışarıda ve bunu söyler), "mAh" (yalnız pil oturumları; 3F PU9 kuralı: kartın sayacına göre değil nokta integrali, boşluk/negatif akımda o kayıt zaman eksenine düşmez, dışarıda kalır ve sebebi yazar) | §9 "eksen zaman / mAh / başlangıçtan beri" |
| KR4 | **İmleçler:** iki imleç, okuma KAYIT BAŞINA tablo (A, B, Δ, ort; mAh/Wh yalnız zaman kiplerinde) — `imlecOkuma` her kayıt için ayrı | Karşılaştırmanın asıl çıktısı sayı yan yana |
| KR5 | **Veri yalnız bu tarayıcıdaki kopyadan** (C5); kartta olup eşitlenmemiş oturum seçilemez, sebebi yazar | Kayıt görünümüyle aynı kural |
| KR6 | **Şerit menüsünde Karşılaştırma artık görünür** (D1 "yazılmamış ekran şeritte yok" kuralının karşılığı); seçim yokken ekran Kayıtlar'a yönlendiren boş durum gösterir | Ölü bağlantı yok |
| KR7 | **Dışa aktarma:** birleşik CSV (Excel-TR ve EN) — her kayıt için kendi x ve seçili kanal sütunları yan yana (zamanlar ortak değil, enterpolasyon YOK) | Uydurma veri yok; analiz Excel'de yapılabilir |
| KR8 | Metinler `sozluk.js` (`kr.*`, TR + EN); WIG kuralları; telefonda (390 px) kullanılabilir | P7, WIG |

### 3G uygulama kararları (KR1–KR8 dışında; uygulayan, kullanıcının devriyle)

| # | Karar | Gerekçe |
|---|---|---|
| KU1 | **Ekran `ekran/karsilastir.js`, ilk açılışta `import()`** (U1/E1 deseni); hesap kodu yeniden kullanılır: seriler ve K1 ekseni `kayit_gorunum.grafikSerileri`, okuma `okumaHesapla` (imlecOkuma + K3), mAh ekseni `pil.mahEkseni` (PU9), sayı/hücre `disari.sayiYaz`/`metinHucre`. Bütçe kuralı (B7): Kayıtlar zincirine YALNIZ `karsilastir.js` + `pil.js` ekler, ≤ 20 KB gzip (ölçülen 18.1 KB); açılış kümesi (≤ 8 dosya, ≤ 250 KB) değişmedi | KR1 gereği ekrana Kayıtlar'dan gelinir, zincirin geri kalanı zaten inmiştir. Doğrudan `#/karsilastir/…` ile açılış Kayıtlar açılışı kadar dosya ister (≈ 300 KB) — Kayıtlar'da da kural yok; "≤ 250 KB" açılış kümesi için |
| KU2 | **Kip ve kanal adreste sorgu olarak** (`?x=saat&k=I`; varsayılan `baslangic`/`V` yazılmaz), değişince `history.replaceState` | Adres paylaşılınca aynı görünüm (WIG); kip değişimi geçmişe girdi eklerse geri tuşu ekrandan çıkamazdı |
| KU3 | **Renk tarifi `KR_RENKLER`:** 1–3. kayıt `--volt` / `--amper` / `--watt` düz; 4–6. kayıt `--volt`→`--yazi` %50, `--amper`→`--yazi` %35, `--vurgu`→`--kart` %35 karışımı **ve kesik çizgi** ([7, 4]; imleç B'ninkinden ayrı). Yeni belirteç tanımlanmadı. Renk **seçim sırasına** bağlı (bir kayıt bir kipte dışarıda kalınca diğerlerinin rengi kaymaz). grafik.js'e `seri.desen` seçeneği eklendi (B73) | Koyu takım 3A öncesine kilitli (B7) — yeni token konamaz. Altı ayrık renk tek başına renk körlüğünde yetmiyordu (aranan en iyi altılının Machado 2009 benzetiminde en kötü çifti ΔE 10.8); renk + desen ile aynı desenli her çift ΔE ≥ 16.8 (B7 üç görünümde, protan/deutan/tritan ölçer), kart zeminine ≥ 3.31:1 |
| KU4 | **İmleç bir kaydın aralığının dışındaysa o kaydın değeri "—"**; Δ, ort, mAh, Wh yalnız iki imleç de kaydın içindeyse | En yakın örneğe yapışmak kısa kayda uydurma değer yazdırırdı (B imleci 42 s'de, kayıt 41.5 s'de bitiyor) |
| KU5 | **Kayıtlar'ın "Karşılaştır" bağlantısı kimliği HER ZAMAN yazar**; elle yazılmış `@kimlik`siz adreste oturumu taşıyan EN YENİ akış (3E S4). Bağlantı en az 2 seçimde etkin; seçim kutusu satır bağlantısının DIŞINDA (iç içe etkileşimli öğe yok), seçilemeyenin kutusu kapalı ve sebebi etiketinde (KR5: yalnız kartta · osiloskop günlüğü · noktasız kopya · 6 dolu) | Eski kart kopyasında aynı numaralı başka oturum açılmasın; WIG |
| KU6 | **Saat kipinde** her noktanın saati bilinmeli: hiç yoksa "saat yok", kısmen yoksa "N / M noktanın saati bilinmiyor", saat geri gidiyorsa "geri gitti" — üçü de dışarıda. Eksen çizgileri ilk anın yerel gece yarısından (yuvarlak saatlere oturur), yazı yerel SS:DD[:SN] | Zaman uydurulmaz (K1 ilkesi); grafik.js azalmayan x ister |
| KU7 | **mAh kipinde x = `mahEkseni(K1 ekseni, I ort, nokta boşluğu)`**; DEVAM'lı pil kaydı K1'in tahmini boşluğu yüzünden "boşluk" sebebiyle dışarıda. Lejantta eksen sonu yazılır | PU9 aynen; pil oturumu yeniden başlamada kapanır (1C-1), DEVAM görülmez — görülürse integral uydurulmaz |
| KU8 | **Karşılaştırmada min/maks zarfı YOK**, her kayıt tek çizgi (ortalama ya da ayrıntılı örnek); Ö1 piramidi sıçramayı yine gösterir | Altı kayıt × üç çizgi okunmaz; zarf kayıt görünümünde |
| KU9 | **Birleşik CSV:** başlık `kayit<no>_<x>` / `kayit<no>_<kanal>` (EN `rec…`; x `gecen_ms` 3 ondalık · `unix_s` 3 · `yuk_mAh` 6; kanal disari.js adları: nokta `v_ort_V`…, ayrıntılı `v_V`…), aynı numara iki akıştan seçilmişse `@kimlik`; yalnız o kipte ÇİZİLEN kayıtlar; satır j = her kaydın j. örneği, kısa kayıt BOŞ hücre | KR7; dışarıda kalan kaydın sütunu olsaydı ya boş ya uydurma olurdu |
| KU10 | `KR_AZAMI` ve adres yazıcısı `kayitlar.js`'te (seçim orada), çözücü `karsilastir.js`'te; B7 ikisinin birbirinin tersi olduğunu 200 rastgele seçimle sınar | Tek kaynak; karşılaştırma modülü Kayıtlar açılışına yük olmasın |

## 3H kararları (2026-10-02 akşam, aynı devirle) — 3H-1 şimdi, 3H-2 ayrı

| # | Karar | Gerekçe |
|---|---|---|
| AY1 | **3H iki dilim:** 3H-1 = düzen + dil + depolama + kalibrasyon geçmişi + bağlantı/ağ/görünüm (mevcut bölümler korunur); 3H-2 = tarayıcı eşleştirmesi, güvenilir cihazlar, bildirim durumu (ayrı tur — cihaz anahtarını tarayıcıda saklamak güvenlik kararı) | Güvenlik kararını alelacele değil kendi turunda vermek |
| AY2 | **Ayarlar bölümlere ayrılır, sol iç gezinme / bölüm başlıklarıyla:** Bağlantı · Ağ · Kalibrasyon · Kalibrasyon geçmişi · Depolama · Dil ve görünüm · Gelişmiş. Her bölümün adresi `#/ayar/<bölüm>` (geri tuşu, paylaşılabilir); telefonda üst üste | Bugünkü uzun tek sayfa; adresli bölüm (WIG "URL durum taşır") |
| AY3 | **Dil seçimi (TR/EN):** `localStorage['olcum.dil']` (3C'nin `dilOku`'su), anında uygulanır (yeniden yükleme yok), `<html lang>` ve sekme başlığı da değişir; sözlüğe girmemiş eski metinler Türkçe kalır ve EN'de hangilerinin kaldığı B7'de LİSTE olarak sayılır (gizlenmez). **Sayı biçimi değişmez ('.' ondalık)** — ölçüm aleti alışkanlığı; CSV'nin Excel-TR biçimi ayrı | P7; sessiz yarım çeviri yerine sayılan eksik |
| AY4 | **Depolama:** bu tarayıcıdaki kayıt kopyaları (akış başına boyut, oturum sayısı, son eşitleme, "eski kart kopyası"), `navigator.storage.estimate()` kullanım/kota, kalıcı depolama isteği (`navigator.storage.persist()`, sonucu yazılır), kopya silme Kayıtlar'daki iki aşamalı onayla aynı. Arşiv seçimi (C3) burada da görünür | Kullanıcı verinin nerede durduğunu ve silinebilir olup olmadığını görmeli; tarayıcı kotası dolarsa kayıp sessiz olmasın |
| AY5 | **Kalibrasyon geçmişi (1B) salt okuma:** `/kal/liste` (yoksa bu tarayıcıdaki `kalibrasyon.json` kopyası) — numara, tarih, not, etkin olan, taslak durumu; değerler tablo. Geçmişi değiştiren komutlar (kk/kn/kt) bu dilimde YOK (ADS takılı değilken kartta sınanamaz) | Görmek güvenli; yazmak kartta sınanmadan eklenmez |
| AY6 | **Gelişmiş:** ham komut konsolu Konsol sekmesinde kalır; Ayarlar'da firmware bilgisi (afiş görüldüyse), panel sürümü (görüntü künyesinin özeti), "tarayıcı ayarlarını sıfırla" (localStorage'ın `olcum.*` anahtarları, iki aşamalı onay) | Destek/hata ayıklama için sürüm görünür olmalı |
| AY7 | Mevcut bölümlerin bütün B7/T iddiaları korunur (bağlantı, ağ, kalibrasyon, görünüm, WIG etiketleri, p0); yeni metinler `sozluk.js` (`ay.*`, TR + EN); WIG kuralları | Önceki dilimlerin kazanımları |

## Doğrulama

B7 (`test_arayuz3.js`) ve B22 tarayıcı denetimleri genişler; her dilimde başsız tarayıcı (Edge) ile
üç görünümde render + telefon genişliği + konsol hatası yok; yeni iddiaların yalanlayıcı mutasyonu.
Kart tezgahında: panel kartta açılır (STA + AP), ölçüm döngüsünde yeni blokaj yok (`K` satırı).

## Kapsam dışı

Android ekranları (5) · PC uygulamasının disk/bildirim kısmı (4) · yazı tipi gömme (P2, izinle).
