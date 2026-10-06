# Alt proje 1 — açık işler ve ertelenenler

> Durum: 2026-10-01 (4H'de, 2026-10-03, sonraki işlerle kapananların üstü çizildi). Kapsam: 1A-1 · 1A-2 · 1B · 1C-1 · 1C-2 · 1C-3 · 1C-4.
> Geri dönüldüğünde **buradan** başlanır. Her maddenin kaynağı köşeli parantezde.
> - "DEVIR x" mühendislik günlüğündeki girdidir.
> - "inceleme" o dilimin bağımsız son incelemesidir.
>
> 1A-1, 1A-2, 1B ve 1C-1'in çalışma defterleri silindi. Maddeleri DEVIR'den ve
> oturum dökümünden kurtarıldı; bu dosya artık tek kayıt.
> Kapanan madde **silinmez**: üstü çizilir, kapanış commit'i yazılır.

Öncelik:
- **Y** — veri doğruluğunu ya da kullanıcının gördüğünü etkiler; geri dönünce önce bunlar.
- **O** — nadir durumda yanlış davranış.
- **D** — kozmetik, test boşluğu, belge.

## Önce bakılacaklar (Y)

| # | Ne | Neden önemli | Dilim |
|---|---|---|---|
| ~~Y1~~ | ~~Kayıtsız bir pil testinin DCIR olayları ve `KN_DCIR` noktaları, o sırada açık bir ÖLÇÜM oturumuna düşebilir. Bu, `p1` açılış taraması sırasında ya da kuyruk doluyken verilirse olur~~ | ~~Ölçüm kaydına yabancı olay girer, PC onu pil olayı sanar. Düzeltme: `kyn_olay` yalnız PİL oturumuna yazsın~~ | 1C-1 [inceleme M7] — **Kapandı (dal `1-duzeltme`):** olay mesajı hedef oturum türünü taşır (`KM_PIL_OLAY`, `kyn_olay(m, tür, …)`); `KN_DCIR` yalnız PİL oturumunda kalır (`kn_ek_suz`). B71.PL8, B72.Y1 |
| ~~Y2~~ | ~~`plan_basliyor` NVS'e oturum açma isteğinden **sonra** yazılıyor. Arada elektrik giderse plan açılışta BEKLİYOR görünür, kendi DEVAM almış oturumunu "meşgul" sayıp ATLANDI olur, o kayıt bitişsiz sürer~~ | ~~Kullanıcı planlı kaydın kendiliğinden biteceğini sanır. Düzeltme: isteği göndermeden önce yaz, gönderemezse geri al. 1C-4 düzeltmesiyle pencere ms'ye indi, kapanmadı~~ | 1C-4 [inceleme M3] — **Kapandı (dal `1-duzeltme`):** incelemenin önerisi ("önce yaz") kaydı yine bitişsiz bırakıyordu → KANITLI bağlantı: çekirdek 0 oturumu açmadan önce NVS'e plan no + sıra yazar, açılışta yayınlar; çekirdek 1 `plan_acilis` ile benimser. B71.R14–R16, PK1–PK5, B72.Y2 |
| ~~Y3~~ | ~~Plan NVS'i açılamaz ya da yazılamazsa (örneğin NVS kalibrasyon geçmişiyle dolarsa) `plan_kur` yine başarı döner, kart "plan kuruldu" der~~ | ~~Plan yalnız RAM'de; yeniden başlamada sessizce kaybolur. Düzeltme: `KP_NVS` hatası~~ | 1C-4 [inceleme M4] — **Kapandı (dal `1-duzeltme`):** `plan_kur` NVS hatasında `KP_NVS`, önceki plan RAM'e ve NVS'e geri; alan hatasında durum yazılmaz. B71.R17 (kısmi hata), B72.Y3 |
| ~~Y4~~ | ~~Kalibrasyon geçmişinin `adet` anahtarı kaybolursa `kgc_ac` 1 numaranın üzerine yazar~~ | ~~Kalibrasyon geçmişinin başı sessizce ezilir. Düzeltme: `k1…k40`'ı tarayıp sayıyı yeniden kur~~ | 1B [inceleme M1] — **Kapandı (dal `1-duzeltme`):** `adet` okunamazsa k1…k40 taranır (ortadaki bozuk kayıt durdurmaz), geri yazılır. B71.C14 |
| ~~Y5~~ | ~~Yazma hatası yolunda ayrıntılı örnek sayılmadan düşüyor (`KA_KAYIP_ONCE` + düşen yok); yeniden denemede aynı kayıt iki kez yazılabiliyor ve PC `ayrinti_ornekler` bunu ayıklamıyor~~ | ~~Nadir, ama olunca çift ya da sayılmamış örnek~~ | 1C-2 [inceleme] — **Kapandı (dal `1-duzeltme`):** yazılamayan örnek sayılır, boşluğu açan kayıt `KA_KAYIP_ONCE`; PC ayrıntı örneklerini VE noktaları sıra başına bir kez verir (yeniden deneme kopyası). B71.A11–A13 |
| ~~Y6~~ | ~~Bozuk kalibrasyon kaydı `/kal/liste`'de sessizce atlanıyor. Doğrusu `{"no":n,"bozuk":true}`~~ | ~~PC eksik geçmişi tam sanır~~ | 1B [inceleme M2] — **Kapandı (dal `1-duzeltme`):** kart bozuk kaydı `{"no":n,"bozuk":true}` yazar; PC'de sağlam kopyası varsa o kalır (`kartta_bozuk`), yoksa bozuk işaretiyle. B72.Y6a/Y6b |
| ~~Y7~~ | ~~Ekli oturumda (ÖLÇÜM + skop günlüğü) kayıt sırası tam zaman sırası değil. Görev noktaları mesajlardan önce boşaltıyor, ~100 ms. Yakalamanın ölçümde bıraktığı boşluk AYRINTI'da bayraksız~~ | ~~PC yakalamayı yanlış zamana koyabilir. Alt proje 2: META `t_ms` ile yerleştir~~ | 1C-3 [inceleme] — **Kapandı (W1, dal `w1-veri`, commit `296c2e2`, DEVIR 5.12.100):** PC yakalamayı META `t_ms` + kendi açılışıyla yerleştirir (`skop_yerleri`/`skopYerleri`, kayıt sırası değil); boşluktan sonraki ilk satır CSV'de `SKOP`, rapor `skop_bosluk`, grafikte `S<no>` (WK5–WK6). Kanıt: W1.K14–K17, kayit.json `yerlesim`, disari/rapor W1 testleri, B7 K3c · **Kartta ölçüldü (W5, T8):** `Gb200` + `Gt2000/3000`'de 200 ms'lik noktalar arasında en büyük boşluk 423 ms; W1'in `SKOP` işareti nokta oturumlarına da (`noktaSerileri`) uygulanıyor |

**D0 (1D çalışmasında bulundu, bu dalda kapandı):** `N?` ve AP kipindeki açılış afişi AP WiFi
parolasını `Serial` aynasıyla basıyordu. Ayna her satırı `/akis` SSE'siyle ağa taşıdığı için parola ağa
çıkıyordu. Artık yalnız ham UART'a gidiyor (`Serial.ham`, B72.D0).

**W1 kararları (2026-10-03, dal `w1-veri`, ajan; "bensiz yapabileceklerinle devam et"):**
- **WK1** PC'nin ayrıntılı W'si kartın `o.watt` tanımıdır (`olcum_al`): V, akım örneğinin anına
  4 düğümlü Lagrange ile taşınır, I ile çarpılır, `sebeke_hz > 0`'da iki RC'nin ters kazancı
  (`suzgec_ters_kazanc`, kanal `tau` + `TAU_AKIM`) uygulanır. Fark: kart sabit aralık varsayar ve
  sonucu 2 örnek geç verir; PC GERÇEK örnek zamanlarını kullanır, W'yi örneğin kendi anına koyar.
  Nokta oturumlarında W kartın kendisi (değişmedi).
- **WK2** V–I başlatma kayması kayıtta yok: `VI_KAYMA_US = 152` (B29, kartta ölçülen; ±20 µs ≈ 50 Hz'te
  0.36°) + `faz_kal_us[menzil]` (örneğin menzili). Kaymayı kayda yazmak biçim + firmware değişikliği;
  bu dilimde yapılmadı (aşağıda O-W1).
- **WK3** Örnek damgasının `olcum_al` dönüşünde (~1.8 ms geç) olması V ve I'ya aynı: W'ye girmez. Ham
  zaman (`kart_us`) değiştirilmez.
- **WK4** Düğüm: k−1..k+2 aynı kesintisiz parçada (aynı açılış, ardışık 0 < dt ≤ 16 380 µs) ve V'leri
  geçerliyse; değilse kaymanın yönündeki komşuyla doğrusal; o da yoksa V_k (hizasız). x düğüm
  aralığına kırpılır (kartın `d` kırpması). V ya da I hatalı örnek: NaN.
- **WK5** Yakalamanın açılışı = kayıt sırasında önündeki DEVAM sayısı (yuva yeniden başlamayı geçmez).
  Zaman sırası (açılış, t_ms). `sonra` = istekten sonraki ilk ölçüm verisi: ayrıntılıda zamanı
  ≥ (t_ms+1) ms (istek `loop`'ta `olcum_al`'dan ÖNCE verilir, o tur ölçmez; `t_ms` tabana yuvarlı),
  noktada kart_ms > t_ms (yakalamanın içine düştüğü nokta).
- **WK6** Kartın ham bayraklarına dokunulmaz: boşluk CSV `bayraklar` METNİNDE PC türetimi `SKOP`
  (EN `SCOPE_CAPTURE`), rapor uyarısı `skop_bosluk` (yalnız ölçümün İÇİNE düşen yakalama), kayıt
  görünümü grafiğinde kesik dikey işaret `S<no>`.
- **WK7** Rapor/okuma Wh'si ayrıntılıda hizalı W'den; mAh değişmedi.
- **WK8** (inceleme düzeltmesi, DEVIR 5.12.100b) Ayrıntılı oturumda sıralı örnek listesi
  (`ayrintiOrnekler(o, true)`) seriler başına BİR kez kurulur. Hizalı güç (`ayrintiGuc(o, {orn,
  dizi: true})`, Float64Array) ve Y7 yerleri (`skopYerleri(o, orn)`) aynı listeyi kullanır.
  Seriler `yerler`'i taşır; rapor ve yakalama işaretleri onu kullanır. Yeni seçenekler yalnız JS'te
  var: Python API'si ve vektörler değişmedi, `api` eşlemesi yeni dışa açık işlev istemedi.

## Kartta / tezgahta yapılmamış doğrulamalar

| # | Ne | Neden yapılmadı | Dilim |
|---|---|---|---|
| T1 | Osiloskop yakalamalarında 1 kHz frekans / dalga biçimi doğruluğu | Skop girişinde sinyal yok (RC düzeneği sökülü). Biçim ve boru hattı ölçüldü, dalga doğruluğu ölçülmedi | 1C-3 |
| T2 | Gerçek fiş çekme: USB + PİL kapalı, 5 kez, elle | Elle iş | 1A-2 |
| T3 | ADS takılınca `--durma` tekrarı ve Python çözücünün volt/amper çevriminin `D` satırıyla karşılaştırılması | ADS takılı değil | 1A-2 |
| T4 | Kalibrasyon komutları (`z g Z i s f F R`) kartta hiç çalıştırılmadı. Tezgah `--kal` yalnız listeleme yolunu sınıyor | ADS takılı değil | 1B |
| T5 | Pil testi kartta yalnız "ret" yolundan sınandı (`p1` gerilim yok diye reddediliyor) | ADS ve analog ön uç yok | 1C-1 |
| T6 | Dolu kalibrasyon geçmişinde tarama süresi (`kgc_esle` en fazla 39 NVS okuması) | Geçmiş dolu değil | 1B |
| ~~T7~~ | ~~Tezgahta "plan sürerken `Gd` + `Gb`" (elle kayıt plan bitişini geçmeli) ve "DOLU'da oturumsuz pil testi + plan" durumları yok~~ | **Kapandı (W5, 2026-10-03, DEVIR 5.12.104):** `tezgah_kayit.py --plan-elle` kartta 3/3. Plan sürerken `Gd` + `Gb` hem 3 s arayla hem aynı anda denendi: planın oturumu sebep 1 ile kapandı (GP 3), elle kayıt yeni oturumda planın bitişinden 10 s sonra da sürdü. Skop günlüğü sürerken plan atlandı (GP 4). "DOLU + oturumsuz pil testi" kartta **sınanamaz**: `p1` ister (ADS ve yük yok, T5), DOLU ~1.6 sa doldurma ister. Bu durum AVR'de (B71.R) ve F70'te sınanıyor. Ölçü aleti: B72.TZ1/TZ4 | 1C-4 [inceleme M6] |
| ~~T8~~ | ~~Tezgah `--skop`, `Gb` sürerken günlüğü ve aynı oturumda yeniden `Gt`'yi kartta sınamıyor (PC tarafı B29'da)~~ | **Kapandı (W5, DEVIR 5.12.104):** `tezgah_kayit.py --skop-olcum` kartta 1/1. `Gb200` sürerken `Gt2000` → `Gtd` → aynı oturumda `Gt3000` → `Gtd` denendi: tek ÖLÇÜM oturumu, 9 + 8 yakalama, ortanca aralıklar 2002 ve 3003 ms. Numaralar 1–17 tekrarsız, iki SKOP_KAL olayı var, noktalar kesintisiz ve ölçüm kapanmadı. Eşitlenen veride doğrulandı. Gözlem Y7'ye eklendi: noktalar arası en büyük boşluk 423 ms. Ölçü aleti: B72.TZ2–TZ4. **İnceleme (2026-10-04, 5.12.104a):** eşitlemenin onaysız olduğunu TZ4 sınamıyordu, artık `esitle_onaysiz`'in gövdesini TZ5 davranışla sınıyor. `esitle_onaysiz` verilen `--dizin`'i akış değişince siliyordu; artık yalnız varsayılan geçici dizini siliyor (TZ6) | 1C-3 |
| T9 | B10 (kayan nokta FMA) gerçek ESP32 derleyicisiyle tekrarlanmadı | Etkisi örnek başına ≤ 1 µW; PC kartın toplamını okuyor → kabul edildi | 1A-1/1A-2 |
| T11 | ADS takılınca: PC'nin hizalı ayrıntılı W'si ile kartın `D` satırı / nokta W'si karşılaştırılmalı (dirençli ve reaktif yük) | ADS takılı değil | W1 |
| ~~T10~~ | ~~3A paneli karta yüklenmedi~~ **Kapandı (2026-10-02 akşam):** 3A–3D kartta, MIME+gzip doğru, Playwright ile sınandı (DEVIR 5.12.78). Kalan: ADS takılınca canlı veri + blokaj (#71 son madde) | 3A |

## Sonraki alt projelere devredilenler

| Ne | Nereye | Dilim |
|---|---|---|
| ~~Onay ve `/kayit/veri` okuması kimliksiz; ağdaki herkes onay yollayabilir (yalnız verilmiş sıralar)~~ | **Kapandı (1D, `8058560`, DEVIR 5.12.72):** eşleştirme + imzalı istekler; zorunlulukta `/kayit/*` ve `Go` imza ister (köprü 4B'de eşleşmiş cihaz olarak imzalar, DEVIR 5.12.87; kartta 4G). İmzasız yolun KAPANMASI `Ez1`'e bağlı: önerisi DEVIR 5.12.92, kullanıcı kararı | 1A-1, 1A-2 |
| ~~Cihazdan saat alma (bugün yalnız NTP; internetsiz ağda plan kurulamaz, çevrimdışı unix 0)~~ | **Kapandı:** kartta imzalı `/saat` (1D, DEVIR 5.12.72); panelden "saati ayarla" (3H-2, DEVIR 5.12.85); köprü NTP'siz kartın saatini her bağlantıda kurar (4B-9, DEVIR 5.12.87) | 1B M7, 1C-4 K4 |
| ~~Açılıştan kaydın sürmesine 2.5–6.3 s; büyüğü `setup()`'taki WiFi beklemesi. Ağ kurulumu görev içine taşınmalı~~ | **Kapandı (1E-2, 2026-10-02):** STA beklemesi ağ görevine (`ag_bekle_tamamla`); `setup()` yalnız radyoyu açar. Kartta: sıfırlamadan ilk `D`ye 6.35 s → **1.32 s**; 20 sıfırlamada kayıt aynı oturumla sürdü. AP'ye düşüş yolu kartta sınanmadı (ev ağı kapatılmadı) | 1A-2 |
| ~~"Pil testi kesildi" bildirimi~~ | **Kapandı (1E):** `pil_bitti` olayı `pil_durdur`'dan; kayıtsız test de bildirilir | 1C-1 |
| ~~PC'de W'nin hizalamalı hesabı (örnek zamanında ~1.8 ms kayma; V–I başlangıç kayması saklanmıyor) ve grafik~~ | **Kapandı (W1, dal `w1-veri`, commit `296c2e2`, DEVIR 5.12.100):** `ayrinti_guc`/`ayrintiGuc` kartın `o.watt` tanımı, gerçek örnek zamanlarıyla (WK1–WK4); CSV, rapor Wh, kayıt görünümü ve karşılaştırma bunu kullanır. Kanıt: W1.K1–K13/K18, kayit.json `ayrinti_guc`, disari W1 testi (bağımsız Python ile bit bit). Kalan: firmware kaymayı yazmıyor → sabit 152 µs (WK2); tezgah T11 | 1C-2 |
| Eski kayda başka kalibrasyon uygulama, dönem uyarısı, "daha yeni ince ayar öner" | **2** + 3 | 1B |
| ~~Kayıt ekranları; `G` arayüzde yok. Ayrıca ad/not web ucu, `/pil`, `PilHalka` panelden kalkması ve yakalama gösterimi~~ | **Kapandı (alt proje 3):** Kayıtlar + kayıt görünümü 3C (DEVIR 5.12.77); `G`/`GP`/`GA`/`GT` pasif durum + `Gn` 3D (5.12.78); yakalama gösterimi 3E (5.12.80); `/pil` eğrisi + `Ga` (PU7) 3F (5.12.81) | 1A-2, 1C-1, 1C-3 |
| ~~Plan gösterimi (panel / PC / telefon)~~ | **Kapandı (panel + PC):** Canlı'da "Zamanla" formu + `GP` durumu 3D (DEVIR 5.12.78); PC aynı paneli köprüden açar (4D, 5.12.89). Telefon uygulaması alt proje 5'in kapsamı | 1C-4 |
| ~~`Gn` ile yazılan notun sıra numarası kartta basılmıyor (`Gx` için eşitlenen dosyadan okunuyor); `G` satırında `son_not` alanı~~ | **Kapandı (W2, `A3-W2`, DEVIR 5.12.101):** `G` satırının SONUNA `son_not` (son Ga/Ge/Gn/Gx'in NOT sırası; < 0 KG_*) + `mesaj_dusen`; değişince G hemen basılır. Panel / pc_bildirim / tezgah ayrıştırıcıları eski 13 alanlı satırı da kabul ediyor (B7 W2, B72.W2a–c); inceleme sonrası `tezgah_kart` / `tezgah_blokaj`'ın ön silme bekleyişi de (B72.W2h, DEVIR 5.12.101a). Panelde sıranın GÖSTERİLMESİ (Gx kısayolu) yapılmadı | 1C-1 |
| B34 ADC doğrusalsızlık düzeltmesi | **Karar bekliyor** (kullanıcı) | 1B |

## Nadir durumda yanlış davranış (O)

- [1A-1] `menzil` bölmesi nokta çizelgesini kaydırıyor; DURAKLAMA ile birleşince noktanın başlangıcı bilinmeyebilir. Bir "nokta süresi" alanı düşünülmeli.
- ~~[1A-1] `ky_nokta` KG_HATA sonrası tampon doluyken reddettiği noktayı `dusen`'e saymıyor.~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** reddedilen nokta sayılır (B71.Y15, emüle NOR yazma arızasıyla). Bayrak (sonraki noktada `KN_KAYIP_ONCE`) eklenmedi.
- [1A-1, 1C-2] `kg_ilerle` / ön silme: silme başarısızsa sektör tablosu zaten düşürülmüş, yeniden denemede `silinen_sektor` iki kez sayılır; ön silme hatasında geri çekilme yok (`temiz_ms` güncellenmiyor).
- [1A-2] `Gb` kayıt sürerken yeniden verilirse kuyruktaki 1–2 eski nokta yeni oturuma girebilir. [1C-2] Oturum sınırında halkadaki örnekler de öyle (ms mertebesi; zaman damgası gösterir).
- [1A-2] Bölüm doluyken baş sektörde yarım yazma varsa açık oturum sürdürülemez → durum 4 (BEKLİYOR). Yedek sektör ayrılmadı. Kullanıcı durdurduysa ilk geçerli onayda BITIR yazılır, yoksa DEVAM.
- [1B M8] Kuyruk doluysa oturumsuz kayıt kalabilir.
- [1C-2] PSRAM ayrılamazsa `Gb0` yine kabul ediliyor; yalnız `GA` düşen sayısı gösterir.
- [1C-2] NaN watt, ham kodu geçerli örneğe V/I hata bayrağı koyuyor.
- ~~[1C-2] 16.38 ms'den kısa skop duraklaması işaretlenmiyor (zaman doğru, sebep kayboluyor).~~ **PC tarafında kapandı (W1):** işaret kayıt bölünmesine değil META `t_ms`'ye bağlı (`skop_yerleri`), kısa duraklamanın da sonraki satırı `SKOP` alır. Kartın ham bayrağı yine yok.
- [1C-2] İzin yarışı: ön silme sürerken bir skop yakalaması ~%5 olasılıkla 25 ms'lik duruşa denk gelir; hazır alan dolunca biter.
- [1C-3] `Gtd`, SKOP oturumu öğrenilmeden ya da açılış taramasında gelirse kuyruktaki `KM_SKOP_BASLAT` kimsenin yazmadığı bir oturum açar; kullanıcı `Gd` demeli.
- [1C-3] Ayar komutları pratikte çoğu an uçuştaki yakalamaya takılır. `Gt0`'da kip OTO'ya çekilirse tetiksiz yakalama kaydedilir.
- [1C-3] SKOP_KAL tablosu, kalibrasyon tablosu geçersizken de yazılıyor; PC ayırt edemez.
- [1C-4 M1] Planın oturumu DEVAM için yer beklerken (KDR_BEKLIYOR) her saniye etkisiz bir "bitir" isteği ve seri/SSE mesajı gidiyor; yer açılınca oturum ~1 s fazla sürüyor.
- [1C-4] Açılışta "sürüyor" ama oturumu bilinmeyen plan (sonuç gelmeden elektrik gitti) bitti sayılır. O ms'lik pencerede açılmış bir kayıt otomatik bitmez.
- [1C-4] Plan artık beklemiyorken geç açılan oturum sebep 7 ile kapatılır; `Gp-` yarışında yanlış sebep etiketi olabilir.
- ~~[W1 inceleme] Hizalı W + Y7 ayrıntılı oturumda sıralı örnek listesini 3–4 kez kuruyordu: 1.9 M örnekte `ayrintiSerileri` 2.5–3.5 s → 7.4–11 s, yığın tepesi ~0.55 → 1.2–1.8 GB, 1 GB yığında yakalamalı oturum OOM.~~ **Kapandı (WK8, DEVIR 5.12.100b):** 1.9 M örnek 1.9–2.4 s, tepe 0.46–0.52 GB, 1 GB yığında 2.4 s. Bunlar W1 öncesinden de iyi. Kanıt: `disari.test` "W1-tek-kurulum" (t0_us okuma sayacı: seriler/CSV/rapor birer kurulum) ve "W1-bellek" (600 k örnek 250 MB yığında; W1 öncesi kod 200 MB'ta geçiyordu, `296c2e2` 300 MB'ta OOM), `kayit.test` "W1 inceleme", B7 K3c sayacı, mutasyon W1 inceleme 9/9.
- [W1 inceleme] O-W1b: Kayıt görünümü bir oturum için seriyi yine iki kez kuruyor: grafik (`grafikSerileri`) ve rapor (`oturumRaporu`). Bu W1'den önce de böyleydi; artık her biri tek kurulum. Telefonda ya da WebView'da 1.9 M örnek için oturum başına önbellek (WeakMap) düşünülebilir. Oturum nesnesi eşitlemede değişebildiği için bu dilimde yapılmadı.
- [W1] O-W1: AYRINTI kaydı V–I başlatma kaymasını taşımıyor; PC sabit 152 µs kullanıyor. I²C yükü değişirse (başka cihaz, hız) gerçek kayma kayar. Öneri: AYRINTI başına `t_kayma_us` ortalaması (biçim + firmware).
- [1A-1, kabul] Sektörde ilk bozuk kayıttan sonrası okunamaz (yeniden senkron yok). Bilinçli tasarım.
- [1A-1, kabul] Yavaş hızda bitmemiş noktadaki örnekler kesmede kaybolur (1/dk'da en fazla 1 dk).
- [1A-1, kabul] `kart_ms` 49.7 günde sarar; tüketici SAAT kayıtlarıyla çözer.

## Kozmetik, test boşluğu, belge (D)

- [1A-1] `KayitNoktaci.bekleyen` hiç 0 dışında bir değer almıyor (ölü alan; 2026-10-01'de yeniden bakıldı, hâlâ öyle).
- ~~[1A-1] Noktacıda `watt` NaN/Inf ise `(int64_t)` dönüşümü tanımsız. Yapıştırıcı NaN'ı hata sayıp dönüşümü atlatıyor, ama `kayit_nokta.h`'de `isfinite` yok.~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** `kn_ornek` sonlu olmayan watt'ı V+I hatalı sayar (B71.P7, NaN ve +Inf).
- [1A-1] `kg_oku` 0/0/0 hem "yeni yok" hem "kap küçük" demek; asgari kap belgelenmeli.
- ~~[1A-1] Python `basla_coz` / sürüm çözümü `rstrip(b"\0")` ilk NUL'dan sonraki çöpü tutar; ilk NUL'da kesilmeli.~~ **Kapandı (2026-10-02, Python + JS):** ilk NUL'da kesiliyor; vektör `surum_nul` (832), mutasyon 2/2.
- ~~[1A-1] "Kullanmadan önce hep sil" için mutasyon yok (inceleyici elle denedi, test ısırıyor).~~ **Kapandı (W4, DEVIR 5.12.103):** mutasyon `W4: [1A-1]` eklendi, `test_kayit.py` YAKALADI.
- ~~[zincir] Yarım/kırık bir `dogrula3.py` koşusu `_tezgah.md`'yi kısaltarak yazıyordu (W4 ağacında 122 → 81 kalem; kalem basmayan adım KIRMIZI deniyor ama liste yine yazılıyordu).~~ **Kapandı (W4, DEVIR 5.12.103):** eksik koşu eski listeyi ezmiyor; `test_zincir_hiz.py` `test_tezgah_eksik_kosu` 3/3, mutasyon `W4:` ×2 YAKALANDI.
- ~~[zincir] Aynı anda koşan zincirlerin `cop_topla`'sı ortak `%TEMP%`'teki canlı `kayit_*`/`spice-*` dizinlerini siliyor; başka ağacın zinciri bitince B71 sessizce ölüyordu (yarım koşunun sebebi).~~ **Kapandı (W4, DEVIR 5.12.103):** `dogrula3.ozel_temp_kur` — adımlar zincirin özel TEMP'inde; `test_ozel_temp` 2/2, mutasyon `W4:` ×2 YAKALANDI. Kalan: zincir DIŞINDA tek başına koşan betikler (`python test_kayit.py`) hâlâ ortak TEMP'te; bir zincirin süpürmesi onları da vurabilir.
- [1A-2] `--esit` yalnız "eşitlenen ⊆ flaş" denetliyor; tamlık denetimi yok.
- [1B M3] `/kal/liste` kayıt başına ~20 `sendContent` yapıyor.
- [1B M5] Bayat yorumlar (`kayit_oturum.h`, spec §5 "116 baytlık TEKRAR" → 118).
- [1B M6] `kn<no>` boş metinle notu siliyor (bilinçli sayılabilir).
- [1B M9] `Gb`'de NVS yazma duraklaması.
- [1B M10] Sürüm 1'den uçtan uca devam sınanmıyor; ESP yapıştırıcısı yalnız kaynak iddiasıyla sınanıyor.
- [1B M11] Okuyucular tam blob boyu istiyor (B34 büyütmesi için).
- ~~[1C-1 M9] `kayit_mesaj_dusen` sayacı hiçbir yerde okunmuyor (G satırında yok).~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** `G` satırının son alanı `mesaj_dusen` (B72.W2a).
- ~~[W2 inceleme] `tezgah_kart.py` (`_on_silme_bekle`) ve `tezgah_blokaj.py` `G?` yanıtını hâlâ 13 alanlı desenle bekliyordu: A3-W2'nin 15 alanlı satırı eşleşmez, bekleyiş anında biter ve kararlı-hal `loop_azami` boşta ön silme sürerken ölçülürdü (kart listesi madde 9 yanıltıcı kırmızı).~~ — **Kapandı (W2, DEVIR 5.12.101a):** iki modülde `G_DESEN` 13 ya da 15 alan (14/16 RET), `sil_adet` yeri sabit; `tezgah_blokaj` bekleyişi `on_silme_bekle` işlevine çıktı ve çözülemeyen `G`'de artık sessizce "durdu" demiyor, iki araç da "BEKLENEMEDİ" uyarısı basıyor. Davranışla sınanıyor (sanal saat + sahte kart: 15/13 alan 5→9→9 = 6 s, 3 sorgu; 14/16 None) — B72.W2h, mutasyon 3/3.
- [1C-1 M12] `ky_olay`, `kyn_pil_bitir` ve `kyn_not`'un DOLU yolları testsiz; iki kuyruk arasında en fazla bir nokta olaydan sonra yazılabilir.
- [1C-1 M13] `kayit_komut` ve `kayit_not_komut` yığında ikişer ~254 B `KayitMesaj` tutuyor.
- [1C-2] 4095/4096 dt sınırı, `kg_on_sil_adim`'daki `kg__sektor_dusur`, C tarafında `micros` sarması doğrudan sınanmıyor.
- [1C-3] `GT` "yazılamayan" sayacı günlük başına atlananla açılıştan beri `skop_hata`'yı karıştırıyor; kullanıcının kestiği yakalama da "yazılamayan" sayılıyor.
- [1C-3] `kyn_skop` açıklaması `kyn_pil_bitir`'inkinden ayrılmalı; `ky_devam`'da yalnız ÖLÇÜM için ayrıntılı koruması yok (bugün ulaşılamaz); `SKOP_AZAMI_ADET <= KAYIT_SKOP_AZAMI` için derleme denetimi yok.
- [1C-4 M5] `GP`: saatsiz SÜRÜYOR düz 2 görünüyor; atlandı/kaçırıldı/bitti geçişleri o an yazılmıyor (yalnız `G?`); ATLANDI eşitlenen veride iz bırakmıyor; bekleyen planın üzerine yazmak sessiz.
- [1C-4 M6] Çekirdek 0'ın `KM_PLAN_BITIR` mantığı yalnız kaynak metin iddiasıyla sınanıyor (platformsuz `kyn_plan_bitir` yok); `plan__yaz` sırası ve `plan_ac` kırpması mutasyonsuz.

## Bilinçli kabul edilen sınırlamalar (geri dönmek gerekmez, bilinsin)

- [1A-2] Biçimleme mantıksal: silinen veri, eski sektörler arka planda silinene kadar (dolu bölümde ~24 dk) esptool ile flaştan okunabilir. Kartın hiçbir ucu onu vermez.
- [1A-2, 1C-2] Arka plan temizliği ve boşta ön silme 500 ms'de bir 25 ms iki çekirdeği durdurur. Açılıştan / eşitlemeden sonra ~4 dk canlı ölçümde takılma görülebilir; GF! + doldurmadan sonra temizlik ~24 dk sürer, her yeniden başlama temizliği baştan alır.
- [1A-2] Onay NVS'e kısıtlı yazılıyor (16 sıra ya da 30 s). Elektrik kesilirse onay en fazla o kadar geri gider; kayıp ya da tekrar yok.
- [1C-2] Onaylı veri kartta erken siliniyor (veri PC'de; tek cihaz eşitlemesi varsayımı).
- [1C-2] Her açılışta en fazla 480 boş sektör yeniden silinir. NOR ömrü için ihmal edilebilir.
- [1C-4] İstek numarası 8 bit; 255 plandan sonra sarmada eski geç bir sonuç karışabilir (pratikte yok).
- [1A-1] Zayıf silinmiş/programlanmış NOR hücresi davranışı emülatörde modellenmiyor; tezgah kesme denemeleri kapsıyor.

## 1D — eşleştirme + imzalı istekler (kararlar ONAYLANDI 2026-10-01; dal `1-birlesik`)

| # | Ne | Durum |
|---|---|---|
| ~~D0~~ | ~~⚠ **`main`'deki firmware'de ön-cesi sızıntı:** `N?` AP WiFi parolasını `Serial` aynası üzerinden açık `/akis` SSE'sine (ağa) basıyor. Düzeltme yalnız 1D dalında (`Serial.ham`).~~ | **Kapandı:** `a3650d7` (dal `1-duzeltme`, DEVIR 5.12.72a, B72.D0), `main`'e `8058560` ile girdi; ham UART'taki satır 4B'de tek `ham()` yazımına indi (A3-4B, DEVIR 5.12.87) ve köprü süzgeci (4A-5) ağa taşımaz. 4G (DEVIR 5.12.92): köprü↔kart trafiği kaydında sır yok (Ö5) |
| ~~D1~~ | ~~Kart tezgahı hiç koşulmadı~~ → **2026-10-01 akşam koşuldu: ilk koşu 15/18**, üç gerçek bulgu: (a) PBKDF2 50 000 tur 4.76 s; (b) her `Ez`/`Em` P'yi yeniden hesaplatıp çekirdek 1'i 4.7 s donduruyordu, sonraki seri komutlar bekliyordu; (c) tezgahın SSE dinleyicisi `olcum.local` çözümü (~3 s) bitmeden `Ep` gönderiyordu, "anahtar SSE'de yok" denetimi BOŞ yere geçebilirdi. Tanı koşusunda anahtar SSE'ye DÜŞMÜYOR (doğrulandı). Üçü de düzeltildi (B71.U19, B72.F98–F101), **son koşu 19/19**. Kart ardından tam yedekten `main` firmware'ine (A3-1C4) döndürüldü | Kapandı |
| ~~D2~~ | ~~Varsayılan tur ölçülmedi~~ → kartta ayrı bir ölçüm eskiziyle beş PBKDF2 yolu karşılaştırıldı (hepsi `hashlib` ile aynı sonuç): her turda HMAC kurulumu 85 µs/tur · mbedTLS PBKDF2 56.7 · `hmac_reset` 56.3 · yazılım SHA 43.3 · **ipad/opad kopyası 30.5** (seçildi). Firmware içinde ~38 µs/tur: 25 000 tur 956 ms (pay %4), **varsayılan 20 000 = 764 ms**. 50 000 bu çipte < 1 s OLAMAZ (en iyi yol 1.9 s) | Kapandı (karar spec K4'te; kullanıcı onayına açık) |
| ~~D3~~ | ~~Parolalı eşleştirmenin BAŞARI yolu kartta sınanmadı~~ | **Kapandı (2026-10-01 gece):** kullanıcı web parolasını 12 karaktere çıkardı (USB `Ns`). Kartta (`A3-1D`) parolalı eşleştirme başarılı (karşılıklı kanıt), imzalı `/kayit/liste` 200, imzalı `/cihaz/liste` anahtarı göstermiyor; test cihazı silindi (`cihaz=0`). Yan bulgu: kart WPA3-yalnız telefon hotspot'una bağlandı, ağ adının sonundaki BOŞLUK kayıtta korunmalı (tanı: kanal/bayt taraması) |
| ~~D4~~ | ~~Onay bekleyen kritik kararlar (spec 1–7)~~ | **Kapandı:** kullanıcı önerilerin hepsini onayladı (2026-10-01); en kısa parola 10 → **12** (B71.U5, B72.I8) |
| D5 | Ertelenen küçükler (son inceleme #8, #10–#12, #14–#19) | Aşağıdaki liste |

**D5 — son incelemenin ertelenen küçükleri** (hiçbiri bugün sömürülebilir değil; birleştirmeden önce ya da 1E'de):

- [1D #8] GET dışındaki her yöntem "GET" diye imzalanıyor; PUT/PATCH/DELETE gövdesi özetlenmiyor (kartta böyle bir uç yok).
- ~~[1D #10] `/saat`'in üst sınırı yok; `strtoul` bitişi denetlenmiyor (`"-1"` → 2106).~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** `guv_saat_coz` yalnız rakam, taşmasız, 1 700 000 000 ≤ unix < 4 102 444 800 (2100); dışı 400 (B71.U20, B72.W2d).
- ~~[1D #11] `Ex<n>` önce kesiyor, sonra denetliyor (`Ex257`, `Ex-255` cihaz 1'i siler; yalnız USB).~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** `guv_cihaz_no_coz` önce TAM çözer: yalnız `!` ya da 1..8; `Ex257`, `Ex-255`, `Ex!x`, 32 bit taşan sayı RET (B71.U21, B72.W2e).
- ~~[1D #12] `EK` satırı üç `ham()` çağrısında basılıyor; araya IDF günlüğü girerse hex ayrı satıra düşer ve köprü süzgeci yakalamaz. Çözüm: tek çağrı + köprüye 64-hex satır süzgeci.~~ **Kapandı (4B, 2026-10-03, firmware `A3-4B`):** `EK` satırı ve AP parolası satırı (`N?` + AP afişi, `ap_parolasi_bas`) tek tamponda, TEK `ham()` ile; tamponlar silinir (B72.F77/D0/F91). Köprü süzgeci (4A-5) derinlemesine savunma olarak duruyor. ~~⚠ Kartta henüz yüklenmedi~~ Kartta (`A3-4B`, DEVIR 5.12.87: `--guvenlik` 14/14, EK satırı seride tek parça, SSE'de yok); tek `uart_write`'ın IDF günlüğüyle kesişmezliği hâlâ kanıtlanmadı.
- ~~[1D #14] Eşleştirme numarası (`eno`) ardışık `uint8`: üçüncü kişi bekleyen eşleştirmeyi tüketip ortak geri çekilmeyi büyütebilir. Çözüm: rastgele `eno`.~~ — **Kapandı (W2, dal `w2-fw`, firmware `A3-W2`, DEVIR 5.12.101; ⚠ karta henüz YÜKLENMEDİ):** `eno` rastgele 31 bit (`uint32`, 0 ve tekrar yok); kanıt ucu tam çözer, yanlış numara bekleyeni TÜKETMEZ (B71.U22, B72.W2f). İstemciler (`imza.py`, `imza.js`) değişmeden uyumlu.
- [1D #15] 401 metni "cihaz kayıtlı değil" ile "imza geçersiz"i ayırıyor (cihaz numarası taranabilir).
- ~~[1D #16] İstemci dosyası `fsync`'siz `os.replace` ediliyor; `.tmp` adı süreçler arası ortak; POSIX'te `chmod`'dan önce K'li geçici dosya oluşuyor.~~ **Kapandı (2026-10-02):** gerçek yarıştı — `kaydet()` her imzalı istekte çağrılıyor, iki süreç aynı dosyada `PermissionError` alıyordu (test kırmızıyla gösterdi). `mkstemp` (benzersiz ad, POSIX'te baştan 0600) + `fsync` + Windows'ta kısa yeniden deneme (benzersiz adla bile gerekli — mutasyon gösterdi). B72.I8c, mutasyon 3/3.
- [1D #17] İmza her uçta sorgu dizgisinde kabul ediliyor (K9 yalnız EventSource diyor) — **AÇIK**. ~~İmzalı `/akis` adresi tek kullanımlık: tarayıcının otomatik yeniden bağlanması 401 alır~~ **Kapandı:** panel 3H-2'de (`ImzaliAkis`), PC köprüsü 4B'de (`kart_wifi.WifiKart`: her yeniden bağlanmada yeni imzalı adres, artan bekleme; B72.W2/W2b).
- [1D #18] `N?` zorunlu/misafir/saat kaynağını göstermiyor · `/eslestir/bilgi` `X-Olcum` istemiyor · `yardim()` E'yi listelemiyor · kapı kodu `kok_sayfa`'nın eski yorumuyla işlevin arasında · ~~`ac()` kartın kimliğini cihaz dosyasıyla karşılaştırmıyor · `ac()`'taki `HTTPError` kapatılmıyor~~ (**4B'de kapandı:** `imza.ac`/`akis_url` açılışı `bilgi`'den alırken kimliği denetler, 401 yolunda ilk yanıtı kapatır; köprü her bağlanmadan önce kimliği denetler ve ret yanıtlarını kapatır — B72.W3/W6/W7/W7b; JS istemcisinde kimlik denetimi hâlâ yok) · spec "çekirdek 1 E'yi kuyrukla yollar" diyor, kod muteks kullanıyor.
- [1D #19] F80 üst sınırı sınamıyor; boş `X-Imza` başlığının kartta imzasız sayılması ölçülmedi (zararsız: imzasız yol daha serbest değil).
- [1D karar] Kartın `/komut` ucu gömülü satır sonuna karşı düzeltilmedi: kuyruk komutu bölmeden çalıştırıyor, yalnız seri girişi bölüyor. Kuyruk ileride bölmeye başlarsa aynı açık doğar.

## 1E — MQTT bildirimleri (dal `1e-mqtt`, 2026-10-01 gece)

Tasarım `tasarim/2026-10-01-1e-mqtt-bildirim.md` (K1–K12 + "Uygulama sırasında verilen kararlar").

| # | Ne | Durum |
|---|---|---|
| ~~E1~~ | ~~Gerçek TLS hiç denenmedi~~ | **Kapandı (2026-10-02):** EMQX Serverless'a TLS ile bağlandı (CA demeti zinciri doğruladı), el sıkışma 0.9–2.0 s, el sıkışma sırasında `loop_azami` değişmedi (7.1–7.6 ms vs taban 7.2–7.4 ms), 120 s kopmasız. HiveMQ ücretsiz Serverless'ı kaldırdığı için aracı EMQX (K2) |
| ~~E2~~ | ~~Ö4 gerçek ağda, 10 tekrar~~ | **Kapandı (RTS sıfırlamasıyla):** 16/16 vasiyet 4.0–7.9 s (ortanca ~7 s, hepsi ≤ 10 s). Gerçek fiş çekme (USB + PİL kapalı) elle yapılmadı; RTS ile aynı yol (TCP kapanmadan kopuş) |
| E6 | Dahili yığının en düşük değeri açılış + el sıkışma anında 54–60 KB (bağlıyken 82–83 KB; K11 ≥ 60 KB bağlıyken tutuyor). Ağır web yükü + el sıkışma çakışırsa TLS ayırması başarısız olabilir (kart yeniden dener) | İzle; gerekirse 3 KB olay kuyruğu ve paket tamponu PSRAM'e. **W5 ölçümü (2026-10-03, A3-4B, gerçek aracı, web yükü yok):** 3 sıfırlamada `QY dahili_en_az` 59.5 / 61.7 / **42.8 KB** çıktı. 42.8 KB'lik açılışta düşüş bağlandıktan SONRA oldu (12 s'de 47.7, 25 s'de 42.8). E7'nin 16 hızlı sıfırlamasının son açılışında **20.7 KB** görüldü; o açılışta karta yalnız `Q?` / `G?` gitti, köprü kapalıydı (tarayıcı paneli açık mıydı bilinmiyor). Hangi işin düşürdüğü ayrılmadı. E6'nın 54–60 KB'si artık iyimser. **2026-10-04 (A3-4B, 2.9 sa çalışma, eşitleme/web yükü yok):** `QY dahili_en_az=2504` — **2.5 KB**; ÖNCELİKLİ, DEVIR 5.12.105. **Ölçüm aracı hazır (E6, dal `e6-olcum`, DEVIR 5.12.105a; karta YÜKLENMEDİ):** `QY` sonuna `dahili_en_buyuk` (en büyük serbest dahili blok) + `ayirma_hata` (açılıştan beri başarısız ayırma sayısı); USB'den `QH` = bölge bölge dahili yığın (IDF dökümü, yalnız UART) + son 4 başarısız ayırma (halka 8 → 4: statik DRAM %25 sınırı, DEVIR 5.12.105) (`QF no= boyut= caps= ms= cekirdek= gorev=`). **Kartta:** yükle → birkaç saat bekle (aynı koşul) → `Q?` ve `QH`. **Okuma:** `ayirma_hata=0` ve `dahili_en_buyuk` ≥ ~17 KB → dip zararsız tepe, ayırma hiç düşmedi. `QF` ~1.6 KB `caps=0x080C` (INTERNAL|DMA|8BIT), görev `wifi`/`tiT` → **Wi-Fi dinamik tamponu** (F2 `WiFi.useStaticBuffers` / F4). `QF` ~16.7 KB `caps=0x0804` (INTERNAL|8BIT), görev `bld` (MQTT TLS) → **mbedTLS içerik tamponu** (F1 PSRAM'e). `QF` ≤ 1.6 KB `caps=0x0008` (yalnız DMA), görev `bld` → **AES DMA ara tamponu** (yalnız E6F'den SONRA: TLS kaydı PSRAM'de, AES DMA'sı hizasız dış bellek çıktısını kayıt başına dahili ara tamponla yazar; ayrılamazsa o kayıt -1, MQTT bağlantısı düşer ve yeniden kurulur) — dahili DMA'lı bölgelerde (asıl DRAM + `0x3fcf0000`) 1.6 KB'lik blok kalmamış demek, dip gerçek; `QH`'de o iki bölgenin en büyük bloğuna bak. `caps=0x1000` = düz `malloc` (≤ 4 KB önce dahili, sonra PSRAM denenir; düşmesi için ikisi de dolu olmalı — beklenmez); görev `tiT` = lwIP, `ag` = web sunucusu/SSE. `dahili_bos` büyük ama `dahili_en_buyuk` küçük → parçalanma. `QH` bölge satırlarında `min_free` hangi bölgede sıfıra yakın (DRAM / RTC FAST) — toplam minimum yanıltabilir **Düzeltme hazır, KARTA YÜKLENMEDİ (E6F, dal `e6-duzeltme`, DEVIR 5.12.106):** F1 mbedTLS ayırıcısı setup'ın ilk işi olarak önce PSRAM, yoksa dahili (`mbedtls_platform_set_calloc_free`; Wi-Fi WPA, imza/PBKDF2, MQTT TLS hepsi); F4 `/kayit/veri` tamponu (8 KB) ve akış kuyruğu (10.7 KB) PSRAM'de, dahili yedekle; F3 SSE kısa yazmada istemci düşer. F2 (Wi-Fi statik tampon) ve F5 (ping) yapılmadı. Statik DRAM değişmedi (81 836). **Kartta:** açılışta `Bellek (E6F): tls=PSRAM veri=PSRAM akis=PSRAM`; birkaç saat sonra `QH` asıl DRAM bölgesinin `min_free` + en büyük blok önce/sonra (≥ ~40 KB artış beklenir), `ayirma_hata=0` (bir `QF caps=0x0008 gorev=bld` = AES DMA ara tamponu ayrılamadı, MQTT o anda koptu — E6F'nin bedeli, dip hâlâ < 1.6 KB; bkz. okuma); `el_sikisma_ms` (önce 0.9–2.0 s, biraz yavaşlama beklenir); köprü tam eşitleme (~18 s); `K` sıfırla → 40 s → `loop_azami` (7.5 ms). Geri dönüş: `main`'den `yukle.py` (NVS/kayıt kalır) ya da tam yedek `tam-20261004-025819.bin`. **İnceleme (DEVIR 5.12.106):** F1'in bedeli belgelendi: AES DMA'sı PSRAM'deki TLS kaydı için kayıt başına ≤ 1.6 KB DAHİLİ ara tampon ayırır, ayrılamazsa bağlantı düşer (yukarıdaki `caps=0x0008` okuması). Kod değişmedi. Açık küçükler (**E6K kapattı**, dal `e6-kucukler`, DEVIR 5.12.106a; firmware değişikliği karta YÜKLENMEDİ): ~~`QF boyut` mbedTLS'te `n*size` değil `size`~~ → ayırıcı taşma denetimli toplamı `heap_caps_malloc_prefer`'e verip sıfırlıyor, `QF boyut` artık gerçek istek (libheap sökümü; B72.E6Fb) · ~~E6Fe/E6Ff `#if`'le ölü kodu görmez~~ → `kosulsuz()` ön işlemci koşulu içindeki satırı kırmızı yapıyor (B72.E6Fa–g, yardımcının kendisi E6Fi; eski iddialarla 4 `#if 0` mutasyonu KAÇIYORDU) · ~~E6F kart kanıtı tezgah listesinde yok~~ → `_tezgah.md`'de 4 kalem: açılış satırı, `QH` önce/sonra, `QF` okuma, ağ geri dönüşü (B72.E6Fj) · ayrıca mutasyon koşucusu her hedef dosyayı CRLF'ye çeviriyordu, B7 "TEK write()" 1 değil 3 kırmızıydı (`test_zincir_hiz.py` A18) · **E6K incelemesi:** ~~`kosulsuz()` dosya ortasındaki `#ifndef X`/`#define X`'i (ör. `ARDUINO`) ve korumanın `#else` kolunu koşulsuz sayıyordu~~ → koruma yalnız dosyanın ilk yönergesi (B72.E6Fk). Açık (küçük): E6Fj'nin `caps` bit denetimi kendi sabitleriyle karşılaştırıyor (`esp_heap_caps.h`'ye bağlı değil); ` veri=` mutasyonu E6Fj'yi yalıtmıyor, önce E6Fg kırmızı (DEVIR 5.12.106a) | **E6F KARTTA (2026-10-04, `4816a3e`):** asıl DRAM `min_free` 11.4 KB (A3-W2, ~9 sa) → **95.2 KB** (E6F, ~1 dk), en büyük blok 102 KB, `ayirma_hata=0`, el sıkışma 1.05 s, döngü 7.6 ms. Uzun koşu (saatler + köprü eşitlemesi) SIRADA; o zaman kapanır. ~~Yeni açık: AP gidip gelince STA'ya dönüş ölçülmedi~~ — **ölçüldü, döndü** (4 senaryo, 5 dk kesinti dahil, 7–14 s; DEVIR 5.12.106; `_tezgah.md` `[!]` kalemi bu ölçümle karşılandı).
| ~~E7~~ | ~~İlk gerçek aracı koşusunda 16 sıfırlamadan birinin `basladi` olayı aboneye ULAŞMADI; hedefli tekrar 6/6 geldi. Kartın `olay` sayacı o an kaydedilmedi → kayıp kartta mı (uçuştaki olay + sıfırlama) aracıda mı ayırt edilemiyor~~ | **Kapandı (W5, DEVIR 5.12.104): kayıp KARTTA.** `tezgah_bildirim.py --basladi 16` gerçek aracıyla koştu ve her sıfırlamadan hemen önce `Q? olay` kaydedildi. `--kip bagli` (ilk koşunun zamanlaması) 15/16 verdi; tek kayıpta kart bağlıydı ama `olay=0 kuyruk=1` idi. `--kip rastgele` 8/16 verdi; 8 kaybın hepsi `olay=0`'dı. PUBACK'i alınmış 23/23 `basladi` aboneye ulaştı, aracıda kayıp 0. Bağlandıktan sonra birkaç saniye RAM kuyruğundaki olay sıfırlamayla gidebiliyor; bu E4'ün bilinçli kararı. Ölçü aleti: test_bildirim E7.1–E7.7 |
| ~~E3~~ | ~~Eşik (`esik`) 500 binde sabit; kullanıcı ayarı yok~~ | **Kapandı (W2, `A3-W2`, DEVIR 5.12.101; karta yüklenmedi):** `Qe<binde>` (100..1000, boş = varsayılan 500), YALNIZ USB (/komut Q'yu 403 ile reddeder), NVS `mqtt`/`esik`, bağlantıyı kesmeden uygulanır, `Q?` satırında `esik=`. Eşiği indirmek bildirilmiş doluluğu tekrar bildirmez, yükseltmek histerezisle yeniden kurar (B71.Q21–Q22, B72.W2g) |
| E4 | Olay kuyruğu RAM'de (16); kart yeniden başlarsa gönderilmemiş olaylar kaybolur (spec kapsam dışı: kalıcı kuyruk) | Bilinçli |
| E5 | ~~Telefon/PC bildirim arayüzü yok; PC'de yalnız `kopru/bildirim.py dinle`~~ PC: 4E'de yapıldı (köprüde MQTT aboneliği + Windows bildirimi, `tasarim/2026-10-03-alt-proje-4-pc.md` "4E"); telefon kaldı | Alt proje 5 |
| ~~E8~~ | ~~MQTT görevi (`bld`) bloklayıcı sokette: mbedTLS katmanı "would block" döndürmez, tek takılı gönderme `SO_SNDTIMEO` 10 s'ye kadar sürebilir (5 s PINGRESP ölçütünü aşar; `bld__yaz` yeniden deneme dalı ölü), kısmi TLS kaydında `bld__oku` 10 s bekleyip -7 yerine -6 der; görevin canlılığı dışarıdan görünmez (`durum=4` yalnız bağlanınca yazılır)~~ | **Kodda kapandı (dal `e8-mqtt-canlilik`, DEVIR 5.12.107; karta YÜKLENMEDİ):** bağlandıktan sonra `SO_SNDTIMEO`/`SO_RCVTIMEO` 1.5 s (`BLD_SOKET_MS`), ölü `WANT_*` dalı kalktı, kısmi yazma 3 s; ping beklenirken soket zaman aşımı **-7** (aracı kapattıysa yine -6/-4); PINGREQ yazılmadan önce "bekleniyor"; bağlı tur > 8 s → yeni kod **-11**; `Q` satırının sonunda `tur adim adim_yas ping_yas pong_yas` (+16 B DRAM, 81 852). Kanıt: B72.QE8a–g, `test_bildirim` E8.1–16 (sahte aracı `sessiz()` + `KaraDelikVekil`), mutasyon `E8:` 27. **Kartta kaldı:** `tezgah_bildirim.py` S1 (sessiz aracı) / S2 (kara delik). Bunların ≤ 9.5 s ve `hata=-7` denetimleri yalnız GERİLEME: aracı düz TCP olduğu için E8 öncesi firmware de geçer (inceleme, DEVIR 5.12.107). Bu tezgahta E8'e özgü kanıt yalnız canlılık izi: `Q` alanları, tur artışı, susma sırasında takılı adım yok + ping bekleniyor (`yanitsiz_hukum`/`ara_hukum`, kartsız E8.17–19). Gerçek aracıda `pong_yas` ≤ ~9 s olmalı. 1.5 s soket tavanı, kısmi TLS kaydının -7 sayılması ve takılı PINGREQ yalnız kaynak biçim iddiaları (B72.QE8a–d). Kara delik pencereyi doldurmuyor; gönderme tavanı ancak TLS'li yerel aracıyla ya da gerçek ağ tıkanmasında görülür. **Açık küçükler (inceleme):** (1) S1'in 9.5 s sınırı yaklaşık %6 yanlış kırmızı verir: susmada 60 s'lik retained `durum` yayını PINGREQ'i 4 s'ye kadar öteler. (2) TLS'te `BLD_YAZ_MS` ve -11 yavaş damlayı durduramaz; "paket başına ~4.5 s" yalnız düz TCP'de geçerli. (3) Gözden geçirenin üç mutasyonu (pong anı, `adim_ms` sıfırlaması, tezgahın tur denetimi) kartsız iddialardan sağ çıkıyordu; sonuncusu artık E8.17'de | 1E [inceleme, DEVIR 5.12.106] |
| ~~W6~~ | ~~Kartın sunduğu uygulama dosyaları `no-cache` ama ETag/Last-Modified yok: her açılışta ~90 KB (gzip) baştan iner, 304 olamaz (telefonda hotspot üzerinden açılış yine 0.6 s)~~ | ~~`_fs.json` sürümünden (ya da dosya özetinden) ETag + `If-None-Match` → 304; B22b'ye iddia~~ | Telefon web testi [DEVIR 5.12.106] — **Kapandı (dal `w6-etag`, DEVIR 5.12.108; KARTTA DENENMEDİ):** görüntüye `etag.txt` (dosya başına görüntü baytlarının sha256'sı, 16 onaltılık), platformsuz `web_etag.h` (AVR'de üretecin gerçek satırlarıyla), `serveStatic` yerine `ArayuzIsleyici` + `kok_sayfa` aynı yoldan: ETag + eşleşen `If-None-Match` → gövdesiz 304, index ASLA immutable. Statik açılış kümesinin no-cache kısmı 141.9 KB (künyeden sayıldı) ikinci açılışta ~1.2 KB başlığa iner. B22b 6q (+12 iddia), mutasyon W6 17/17. Kalan: tezgah kalemi B22b "W6" (curl 304 + telefonda ikinci açılış). **İnceleme (DEVIR 5.12.108 "İnceleme"):** `.gz`e düşüş ve MIME artık firmware'in kendi kodunda ama 6n yalnız alt dize arıyordu — `exists(yol + ".gz")` → `exists(yol)` ve `endsWith` → `startsWith` (ikisi de paneli öldürür) B22b 125/125 ile sağ kalıyordu (bu dalda yeniden koşuldu: 4 yeni W6 mutasyonu da KAÇTI). Yeni 6r: `arayuz_tur` + `class ArayuzIsleyici` `.ino`dan BİREBİR kesilip AVR'de çekirdeğin kendi `mimetable.cpp`'siyle ve görüntünün gerçek dosya listesiyle koşuyor (15 istek); 4 mutasyonun 4'ü YAKALANDI |
| W6b | W6 incelemesinin iki küçüğü (düzeltilmedi): (a) `If-None-Match` toplaması gereksiz — çekirdek 3.3.11 `collectHeaders` bu başlığı zaten ekliyor (`WebServer.cpp:1024`, `ETAG_HEADER`); `.ino` yorumu, 6q'nun ilgili iddiası ve iki W6 mutasyonu ("If-None-Match toplanmaz", "elle sayı 7") OLAMAYACAK bir arızayı iddia ediyor. (b) `etag_eslesir` sonu `*` olan listeye (`"x", *`) 1 döndürüyor — kendi yorumu (`*` yalnız tek öğe) ve simetrik `*, "x"` → 0 test durumuyla çelişiyor (biçimsiz başlık; 304 zararsız ama tutarsız) | (a) yorum + iddiayı "çekirdek topluyor; listede tutmak sürüm değişimine karşı" diye düzelt ya da toplamayı kaldır; (b) `*` öğesine yalnız ilk öğeyken izin ver + `"x", *` → 0 vektörü | W6 incelemesi [DEVIR 5.12.108] |
| ~~AG1~~ | ~~Açılışta kayıtlı ev ağı (STA) yoksa kart 10 s sonra kendi AP'sine düşüp STA'yı BİR DAHA denemiyor; ev ağı dakikalar sonra dönse de AP'de kalıyor (MQTT `durum=2`). Elektrik kesintisinden sonra yönlendirici karttan yavaş açılınca kart elle sıfırlanana dek ev ağına dönmez, bildirim yok. Kartta ölçüldü 2026-10-04; çalışırken kopma sorunsuz (5.12.106: 7–14 s)~~ | **Kodda kapandı (dal `ag-ap-donus`, DEVIR 5.12.109; KARTA YÜKLENMEDİ):** AP'ye düşüş artık AP+STA — aynı SSID/parola/192.168.4.1; otomatik bağlanma kapalı, STA 30 s'de bir `WiFi.begin()`; bağlanınca kip STA (mDNS + `_http._tcp` sürer), AP 5 s sonra kapanır, otomatik bağlanma geri açık. Kayıtlı ağ yoksa saf AP, bağlandıktan sonraki kopma değişmedi. Karar platformsuz `ag_karar.h`, AVR'de 9 senaryo (B22b 5m, +17 → 144); mutasyon `AGD:` 32/32. Statik DRAM +8 (81 868). **Kartta kaldı:** tezgah kalemi B22b "AGD" (erişim noktası kapalı açılış → AP; açınca ≤ 60 s STA, AP kalkar, `Q?` durum=4, mDNS servisi). Ölçülmeyen: AP'deki istemcinin 30 s'lik taramada ve kanal değişiminde gördüğü kesinti. **İnceleme (DEVIR 5.12.109 "İnceleme"):** iki yapıştırıcı mutantı B22b'yi 144/144 yeşil bırakıyordu: `ag__sta_oldu`'da `localIP` → `softAPIP` (dönüşte `ag_durum.ip` AP adresi kalır, IP ile gelen istek 403 alır) ve `ag_isle`'de `bagli` ↔ `iliskili` (kip DHCP bitmeden STA olur, ip 0.0.0.0). Artık yapıştırıcının `ag.h` metni AVR'de sahte sürücüyle koşuyor (3 senaryo, +4 iddia → 148). İki mutant da yakalanıyor; `AGD:` 34/34. Firmware değişmedi | Kart ağ testi [DEVIR 5.12.106] |
| AG1b | AG1 incelemesinin küçükleri (düzeltilmedi): (1) AP+STA'ya geçişte softAP radyo durdurulmadan kuruluyor; softAP başarısızsa AP bir daha denenmiyor, kip KAPALI kalıyor. (2) DHCP kapısının gerekçesi yanlış: argümansız `WiFi.begin()` bağlıyken KOPARMAZ; `ag_karar.h` yorumu ve 5m iddia metni hatalı, kapının kendisi zararsız. (3) 10 s'lik açılış beklemesi DHCP sürerken dolarsa `AP_KUR` yeni ilişkiyi koparıyor, sonraki deneme 30 s sonra; gerileme yok, kaçan bir fırsat. (4) "İlişkiliyken deneme yok" kararının SDK gerekçesi de aynı sebeple yanlış. (5) Tezgahın dayandığı `(ev agi 30 s'de bir deneniyor)` eki test edilmiyor. (6) Kart tezgahı `host_gecerli` değişikliğini doğrulamıyor: geçiş payında AP'deki telefona 403 gitmemeli | (1) softAP sonucuna göre yeniden dene ya da `mode` + `softAP` sırasını eski haline getir; (2)/(4) yorum ve iddia metnini düzelt; (3) BEKLE'de ilişkiliyse süre dolsa da bekle (üst sınırla); (5) `Ag:` satırı ekine kaynak iddiası; (6) tezgah adımına AP'deki telefondan 192.168.4.1 isteği ekle | AG1 incelemesi [DEVIR 5.12.109] |

## Alt proje 2 (`ortak/`) çalışırken bulunanlar (2026-10-02 gecesi)

Çapraz uygulama (JS ↔ Python ↔ AVR) başvuruların kendisinde kusur buldu. Kartın ölçümünü
etkileyenler **Y** (veri doğruluğu):

| # | Ne | Nerede | Durum |
|---|---|---|---|
| S1 | **Skop Vac düz DC'de 0.196 V** (doğrusu ~0): float32'de `Vrms² − Vort²` büyük sayıların farkı (sadeleşme); ±3 kodluk gerçek gürültüde 0 okuyor | `olcum2.h` → `skop_olc.h` `skop_olc` | ~~Y~~ **Kapandı (1F):** tam sayı S1/S2 (u64), tek sqrt; düz çizgi Vac 0, kartta doğrulandı (−63.53 V düz: Vac 0.0000, Vrms = \|Vort\|) |
| S2 | **ESP32 derlemesi skop_olc'ta kayan nokta işlemlerini birleştiriyor** (`madd.s`/`msub.s`: Vrms/Vac toplamları, %10/%90 eşikleri) → kart AVR başvurusundan farklı; Vac'ta ~%5'e dek. "AVR ile ESP32 aynı IEEE sonucu" varsayımı YANLIŞ | firmware derlemesi | ~~Y~~ **Kapandı (1F)** skop_olc için: pragma; objdump denetimi (B6). ⚠ Aynı birleştirme `guc_olc` (6), `olcum_al` (5), `skop_gorevi` (4), `suzgec_ters_kazanc` (1)'de de var → **S8** |
| S3 | Görev oranı bir örnek fazla sayıyor: temiz %50 kare %49.79 | `skop_olc` | ~~Y~~ **Kapandı (1F):** (bas, son] sayımı; %50 kare 50.000 |
| S4 | tr/tf %10 geçişinden sonra yeniden kurulmuyor: %90'a varmayan darbe yükselme süresini sonraki kenara uzatıyor | `skop_olc` | ~~Y~~ **Kapandı (1F):** ters eşik geçişi başlangıcı bırakır |
| S5 | `oturumlari_kur` CRC'si geçerli ama boyu yanlış kayıtta (`struct.error`) çöküyor; DEVAM/BİTİR/SAAT TAM boy istiyor → ileride uzayan bir biçim eski PC istemcisini eşitlemede düşürür ("bilinmeyen tür geçerli" niyetine aykırı). JS birebir kopyaladı | `kopru/kayit_bicim.py`, `ortak/src/kayit.js` | ~~O~~ **Kapandı (2026-10-02, iki dilde birden):** uzun kayıt → bilinen önek; en kısa boyun altı → atlanır + `uyarilar` (Python `Oturumlar.uyarilar`, JS Map'te görünmez `uyarilar`); BAŞLA sürümü boya göre (98–101 v1, ≥ 102 v2) |
| S6 | `flas_coz` tam sektör olmayan ve geçerli kayıttan sonra < 16 B ile biten görüntüde çöküyor; `amper` `sont_ohm` 0'da ZeroDivisionError; kısa NOT / bilinmeyen tür boş oturum yaratıyor | `kayit_bicim.py` | ~~D~~ **Kapandı:** kısa/bilinmeyen kayıt oturum açmaz; kesik flaş görüntüsü temiz durur; `sont_ohm` 0 → NaN |
| S7 | `zarf_ac`/`bilgi_coz` düz metin JSON'da NaN/Infinity kabul ediyor (JS reddediyor); `_bilgi_denetle` tamsayı kimlik, `tur` 20000.7 → 20000, `"20_000"` ve `True` kabul ediyor; parola uzunluğu Python'da kod noktası, kartta UTF-8 bayt | `kopru/bildirim.py`, `imza.py` | ~~D~~ **Kapandı (2026-10-02, Python + JS birlikte):** zarf içeriğinde NaN/Infinity → ValueError; kimlik/tuz/açılış yalnız METİN, tur yalnız JSON tamsayısı (20000.0 ikisinde de kabul — JS ayırt edemez); parola sınırı UTF-8 BAYT (kartla aynı: 6 Türkçe harf = 12 bayt kabul). B72.I8b, vektör `bilgi_denetle`/`esles_akis` genişledi; mutasyon S7 |
| S8 | **AVR'de doğrulanan ölçüm matematiği kartta bit bit aynı değil:** ESP32 derlemesi `guc_olc`, `olcum_al`, `skop_gorevi`, `suzgec_ters_kazanc`'ta kayan nokta işlemlerini birleştiriyor (madd.s); B4/B5'in "AVR = kart" varsayımı bu işlevlerde geçersiz | firmware | ~~Y~~ **Kapandı (1F-2):** `.ino`'nun başında `#pragma GCC optimize ("fp-contract=off")`; B6 eskizin nesne dosyasının TAMAMINI tarar (449 kayan nokta komutu, 0 madd/msub); kartta örnek sayısı aynı (32.99), en uzun tur 7.31 → 7.19 ms |
| S9 | `istatistik.js`: zaman dizisinde NaN aralığı sessizce kesiyor (`[0, NaN, 2]` → 1 örnek) | `ortak/src/istatistik.js` | ~~D~~ **Kapandı:** sonlu olmayan zamanlı örnek eksik sayılır |
| S10 | Kayıt biçimi: NOT ve OLAY kayıtlarında açılış numarası yok → yeniden başlamadan sonra notun konumu tahmin; olayın açılışı ancak ham kayıtlarla bulunuyor (`oturumlariKur` DEVAM sıralarını düşürüyor); `ayrintiOrnekler` kayıt başına KA bayraklarını kaybediyor | `kayit_bicim.py` / `kayit.js` | O — biçim sürümü 3'te |

## Panel açılış bütçesi (W3, 2026-10-03)

Açılış kümeleri sözlük eklemeleriyle sınıra dayanmıştı (`#/skop` 250 794 / 256 000 B, eşleşmiş açılış
259 996 / 262 144 B). Karar ve ölçüm: `tasarim/2026-10-02-alt-proje-3-panel.md` **EU32**, DEVIR 5.12.102.

| # | Ne | Durum |
|---|---|---|
| ~~W3-1~~ | ~~Açılış bütçesinde pay yok: `#/skop` ~5 KB, eşleşmiş açılış ~2 KB; her yeni metin açılışa giriyordu~~ | **Kapandı (EU32):** Kayıtlar/Karşılaştırma (`sozluk_kayit.js`) ve Ayarlar modülünün (`sozluk_ay.js`) metinleri açılıştan çıktı. Açılış 209 404 → 199 864 B, `#/skop` 250 794 → 241 254 B, eşleşmiş açılış 259 996 → 250 456 B (gzip; B7). Büyüme kilidi: `sozluk.js` ≤ 19 500 B (B7) + B73 yerleşim iddiası (yalnız bir tembel ekranın kullandığı metin açılışta kalamaz) |
| W3-2 | `os.` / `pl.` metinleri hâlâ açılışta (~2.6 + 3.3 KB gzip) | Bilerek: iki ekran kabuğun parçası, modül inmeden çizilir (PU1: DURDUR modülü beklemez). Ayırmak için görünüm değişiminde sözlük yükleyip yeniden çizdiren reaktif bir yol gerekir; `#/skop`'u küçültmez. Gerekirse yalnız `pl.`'nin DURDUR/okuma dışı kısmı ayrılabilir |
| W3-3 | Eşleşmiş açılışın EU31 istisnası: bayt artık 3D sınırının altında (250 456 < 256 000) ama dosya sayısı 15 > 12 | Açık (D): dosya sayısı imza/kripto birleşmesi ister; EU31 tavanı (262 144 B) bilerek değiştirilmedi — kullanıcı kararıydı. İstenirse tavan 256 000'e çekilebilir |
| W3-4 | Ayarlar modülü kartta artık iki dosya indirir (ayarlar.js + sozluk_ay.js, 4.6 KB) | Kabul (AY2 güncellendi): her açılışta −9.5 KB'a karşı yalnız Ayarlar'ın modül bölümleri ilk açılınca +1 istek |

## Kutuda ilk kalibrasyon (12.x, 2026-10-05) — firmware'e dönenler

Kart kutuda, gerçek yük ve gerçek ön uçla ilk kez kalibre edilirken bulundu (firmware `A3-W2`).

- **K1 · Hızlı yol ve skop Vref'i NOMİNAL varsayıyor.** `hizli_olcekle()` ve `SKOP_VOLT_OFSET`
  `VREF_NOMINAL` (1.7153 V) kullanıyor; bu kartta gerçek Vref **1.771 V** (R8/H9). Sonuç: hızlı akım
  yolunda **+3.34 A** sabit ofset (`(1.771−1.7153)/4.7/0.003563`, `w` çıktısı I_ort 4.29 A, gerçek 0.95 A
  — sayı birebir tutuyor) ve skopta **~+2 V** DC kayma (×SKOP_ORAN−1). ADS yolları etkilenmiyor (sıfır
  kalibrasyonu yutuyor). Öneri: Vref'i ADS ile ÖLÇ (U7 A1/A3 = VREF_ADS, R36 1 kΩ) ya da `w`/skop için
  sıfır kalibrasyon komutu; NVS'e yaz. Kapı 7 (12.6, PF) bu düzelmeden anlamlı geçmez.
- **K2 · `sebeke_hz` varsayılanı 50 Hz → DC güç ×1.82.** `tipler3.h` `a->sebeke_hz = 50.0f`; DC yükte
  `D` satırı W'si V·I'nın 1.82 katı (6.34 W, gerçek 3.48 W). Kullanıcı yalnız DC ölçüyor (şebeke yok);
  kartta `f0` verildi. Varsayılan 0 olmalı ya da arayüz bunu açıkça göstermeli.
- **K3 · Skop M satırı gürültüye dayanıksız.** ESP32 ADC σ≈11 kod + tekil ±60–150 kod sıçramalar; M satırı
  min/max ve histerezissiz kenar sayımı kullandığı için aynı 1 kHz CAL verisinde f 313…1143 Hz, Vpp 8.5–11.7 V
  (gerçek ~2.5 V). Ham veri temiz (tam 20 örnek periyot). Yüzdelik seviye + histerezis gerekir.
- **K4 · Akım ADS'i RDY çipten çipe değişiyor.** Üç modülden biri kusurluydu (±0.256'da ¼ okuyor), biri RDY
  üretmiyor (ALRT sağlam, `baslangic=YUKSEK`). RDY'siz döngü ~160/s'e düşüyor; şimdi RDY'li modül U6'da.
- **K5 · HV kazancı kalibre edilmedi** (≥31 V kaynak yok; 24 V'ta −%2.5). İki yalıtılmış kaynak seri ile `y`+`g`.
- **K6 · Vref tamponu (U3A) çıkışı girişten ~37 mV farklı** — iki LM358'de aynı, besleme doğru; kök neden
  açık (C2/C3 100 nF doğrudan çıkışta → salınım şüphesi, osiloskopsuz kanıtlanmadı). K1'i büyütüyor.
- **K7 · Pil testi kesmesi TEK örneğe bakıyor.** `pil_kesmeli_mi(o.volt, …)` her örnekte `v <= kesme_v`.
  12.7'de buck elle kısılırken 200 ms ortalamaları 3.65 V'tayken (kesme 3.50) test kesildi — muhtemelen
  potun anlık sıçraması tek bir örneği eşiğin altına düşürdü. Gerçek pilde nadir ama tek bir bozuk örnek
  (I²C, menzil geçişi) testi erken bitirir. Öneri: N ardışık örnek ya da süzülmüş gerilim (ör. 100 ms).
- **K8 · Pil testi durumu canlı akışta yok.** Android'de DURDUR şeridi artık yalnız pil testi sürerken (ya da durum
  bilinmezken) görünüyor (kullanıcı kararı 2026-10-05). Oturum açmayan bir pil testi PC'den başlatılırsa telefon bunu
  `/pil` yoklamasıyla en geç 30 s sonra fark ediyor. Tam çözüm: pil durumunu (çalışıyor/bitti) canlı akış satırına koymak.
- **K9 · "Yalnız USB, PİL kapalı" kipi geçerli bir ölçüm kipi değil ama kart ölçüyor gibi görünüyor.** PİL kapalıyken
  kart USB'den besleniyor (analog taraf devkit'in 5V'u üzerinden); V jakı boşken okuma ~11 V (PİL açıkken ~1.7 V = Vref).
  Arayüz bu kipi bilmiyor ve sayıları normalmiş gibi gösteriyor. Firmware 5V barası/±12 V'u ölçebiliyorsa "analog besleme
  yetersiz" uyarısı vermeli.
- **K10 · Yerel yoklama ucu imzasız (Android K-9).** Yerel ağdaki biri kart kimliğini taklit ederek telefona
  "karttan haber yok" yerine "ev interneti koptu, kart çalışıyor" yazdırabilir (etkisi yalnız bildirim metni).
  Kapatmak için yerel yoklamanın imzalı bir uca (ya da imzalı yanıta) dönmesi gerekir.
